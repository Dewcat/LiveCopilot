#!/usr/bin/env python3
"""Training-only contrastive examples for pragmatic intent, not inference rules.

Uses known development error categories. Frozen calibration/development/holdout
are copied unchanged; no holdout predictions or utterances become training data.
"""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys
from make_laya_finetune_data import case, turn, worker_module
from review_laya_response_labels import normalized

TOPICS = ['权限审批', '工作交接', '设备巡检', '实验复现', '异常归档', '消息投递']
# (positive, negative) are labelled by their conversational action. Optional
# dangling grammar is positive when the main action is already answerable.
PAIRS = [
    ('把{t}仔细说一说', '他说把{t}仔细说一说'),
    ('请把{t}的细节介绍给我', '她说请把{t}的细节介绍给我'),
    ('{t}这件事细讲讲吧', '对方说{t}这件事细讲讲吧'),
    ('{t}给个例子吧', '他说{t}给个例子吧，这句是原话'),
    ('别人请我介绍{t}，你示范一下该怎么答', '别人请我介绍{t}，这是刚才的原话'),
    ('下面我问你：{t}怎样避免遗漏', '下面我复述：{t}怎样避免遗漏'),
    ('我现在想听你解答{t}的问题', '我现在想把{t}的问题写完整'),
    ('{t}的问题讲完了，你开始答', '{t}的问题还在调整，你继续等'),
    ('{t}这个方向麻烦再展开一些', '{t}这个方向暂时不必展开'),
    ('{t}这么做的缺点也补上', '{t}这么做的缺点我已经补上'),
    ('你认为{t}还有没有负担更小的做法', '我认为{t}还有负担更小的做法'),
    ('关于{t}，除刚才那个还有啥选择', '关于{t}，除刚才那个还有啥选择我稍后自己查'),
    ('先别讲日期，谈谈{t}的执行次序', '先别讲日期，{t}的执行次序也先别谈'),
    ('{t}这题不讨论了，转而说说人员分工', '{t}这题不讨论了，其他题也先不要答'),
    ('前半段略过，后半段的{t}讲清楚', '前半段略过，后半段的{t}也略过'),
    ('{t}解释一下，尤其', '关于{t}，我还不知道想问哪一方面'),
    ('把{t}实施的顺序说说，因为我们', '把{t}实施的顺序说说，稍等，我还没开始问'),
    ('如果{t}只能保留一项步骤，你会', '如果{t}出现一个问题，而这个问题是'),
    ('你准备怎样应付{t}人手不够的情况，假如', '你准备将{t}的结果转换成'),
    ('请从{t}里挑一段经历讲给我听，关于', '请对比{t}和另一个叫作'),
    ('说说{t}的收益，以及', '说说{t}的收益，先暂停回答，我还要改题'),
    ('{t}这事我们要怎样推进，另外', '我想问{t}能否将'),
    ('{t}如果无法联网，你会如何', '为什么要把{t}的结果合并进'),
    ('请讲{t}发生故障时怎么办，比方说', '请将{t}的故障类型和'),
]
CONTEXT_PAIRS = [
    ('还有其他路子没有', '目前选定了一条实现路径。', '我读的问句是：'),
    ('这段也往细里说', '刚才只提了这部分工作的概要。', '他给我的评语原文是：'),
    ('给它再加点细节', '我简单讲了一下方法。', '笔记里那条建议写着：'),
    ('便宜点的行不行', '现在的做法需要额外买一套设备。', '我在抄录之前的一句提问：'),
    ('你给个判断', '这个选择各有优劣，还没有决定。', '她当时说的话是：'),
    ('后一个怎么安排', '前一个方案是先做试验，后一个方案是逐步迁移。', '录音中的最后一句是：'),
    ('这块我想再听些', '这部分的原理刚刚提了一句。', '他当时的原话如下：'),
    ('那内存怎么算', '我们估算过带宽开销。', '题卡上的文字我继续读：'),
    ('How about something cheaper?', 'Our solution needs extra hardware.', 'The reviewer wrote the following sentence:'),
    ('More detail on that part, please.', 'I have only given a brief outline.', 'I am quoting the audience member:'),
    ('Say a little more about it.', 'There are several interesting implementation details.', 'The old note contains just these words:'),
    ('Which would you keep?', 'One component can stay; the other must go.', 'I am reading a question from a previous interview:'),
]
EN_PAIRS = [
    ('Please describe {t} more carefully.', 'He said please describe {t} more carefully.'),
    ('Talk about {t}, particularly', 'Regarding {t}, I have not decided what to ask yet.'),
    ('Explain how {t} keeps working, even when', 'Explain how {t} turns the value into'),
    ('How would you handle {t} without enough staff?', 'Could you compare {t} with'),
    ('Help me answer the quoted question about {t}.', 'I am quoting a question about {t}, without asking you to answer.'),
    ('Skip the first topic; focus on {t}.', 'Skip the first topic and do not answer the {t} question either.'),
    ('What other way could you handle {t}?', 'I will discuss another way of handling {t}.'),
    ('Tell me what {t} costs, and also', 'Tell me what {t} costs, but wait until I finish asking.'),
    ('What if only one part of {t} could stay?', 'What if {t} were asked to turn the input into'),
    ('Go into {t} again, this time with an example.', 'I will go into {t} again, this time with an example.'),
]


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--previous', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists(): raise SystemExit('Refusing to replace data')
    old = {s: json.loads((a.previous / f'{s}.json').read_text())
           for s in ['train', 'calibration', 'development', 'acceptance', 'regression']}
    additions = []
    for i, pair in enumerate(PAIRS):
        for j, topic in enumerate(TOPICS):
            for label, text in zip([True, False], pair):
                history = [] if j % 2 == 0 else [turn('Them', '先介绍相关工作。', True), turn('You', f'我参与过{topic}。')]
                additions.append(case(f'intent-context-zh-{i}-{j}-{int(label)}', f'intent-context-zh-{i}',
                                      text.format(t=topic), label, history))
    for i, (text, positive, negative) in enumerate(CONTEXT_PAIRS):
        for j, topic in enumerate(TOPICS[:4]):
            for label, prior in [(True, positive), (False, negative)]:
                history = [turn('Them', f'我们谈谈{topic}', True), turn('You', f'我参与过{topic}。'),
                           turn('You' if label else 'Room', prior)]
                additions.append(case(f'intent-context-pair-{i}-{j}-{int(label)}', f'intent-context-pair-{i}', text, label, history))
    for i, pair in enumerate(EN_PAIRS):
        for j, topic in enumerate(['team onboarding', 'device monitoring', 'experiment tracking']):
            for label, text in zip([True, False], pair):
                additions.append(case(f'intent-context-en-{i}-{j}-{int(label)}', f'intent-context-en-{i}', text.format(t=topic), label))
    rng = random.Random(20261021)
    for label in [True, False]:
        for c in rng.sample([c for c in additions if c['respond'] == label], 48):
            r = copy.deepcopy(c); r['id'] += '-long'
            history = [turn('Them' if i % 2 else 'You', ('请讲讲以前的工作。' if i % 2 else '以前的工作已介绍完并记录好了。') * 12, bool(i % 2)) for i in range(10)]
            r['context']['recentTurns'] = history + r['context']['recentTurns']; additions.append(r)
    protected = {normalized(c['text']) for s, rows in old.items() if s != 'train' for c in rows}
    assert not protected.intersection(normalized(c['text']) for c in additions)
    rows = old['train'] + additions; rng.shuffle(rows)
    sys.path.insert(0, str(a.runtime / 'source'))
    import laya_mlx
    worker = worker_module(); agent = laya_mlx.load(a.runtime / 'model', dtype='float16')
    a.out.mkdir(parents=True)
    shutil.copy2(a.previous / 'label-audit.json', a.out / 'label-audit.json')
    for s in ['calibration', 'development', 'acceptance', 'regression']:
        for ext in ['json', 'jsonl']: shutil.copy2(a.previous / f'{s}.{ext}', a.out / f'{s}.{ext}')
    manifest = json.loads((a.previous / 'manifest.json').read_text())
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    training_augmentation='Synthetic contrastive intent and context coverage. No runtime rules and no holdout predictions used.',
                    added_training_rows=len(additions), previous_manifest_sha256=hashlib.sha256((a.previous / 'manifest.json').read_bytes()).hexdigest())
    fixture=a.out/'train.json'; fixture.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    prepared=[];counts=[]
    for c in rows:
        state,count=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False))
        prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])));counts.append(count)
    data=a.out/'train.jsonl';data.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
    manifest['splits']['train']=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),
                                    sha256=hashlib.sha256(data.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(added=len(additions),train=manifest['splits']['train'])))


if __name__=='__main__': main()
