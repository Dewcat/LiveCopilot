#!/usr/bin/env python3
"""Training-only semantic contrasts with bounded repeated-family rehearsal.

Development failures guide coverage, never a runtime sentence matcher. The
unscored final holdout, original calibration and development labels stay fixed.
"""
import argparse
import collections
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

ZH_ASPECTS=['做这个选择的理由','你独自处理的环节','两个阶段之间的过程','验证那个结论的办法','最后怎样收尾','你放弃那条路的原因']
EN_ASPECTS=['your reason for that choice','the part you handled alone','the steps between those stages','how you verified that conclusion','what happened at the end','why you abandoned that route']
ZH=[
 ('我还没听到{a}', '我已经听到{a}，够了'),
 ('{a}这一点还没有说清', '{a}这一点已经说清，不必再讲'),
 ('你的回答没涉及{a}，这正是我关心的', '你的回答涉及了{a}，我已记录好'),
 ('我需要的是{a}，而非那个结论', '我刚记录的是{a}，并没有提出新问题'),
 ('我想要的不是结论，是{a}', '我想说的不是结论，是{a}，接下来由我讲'),
 ('{a}在你的回答里还是空白', '{a}在笔记里原本是空白，刚才已经补齐'),
 ('你没提{a}，我还在等这个说明', '你已提过{a}，我不需要另一个说明'),
 ('{a}你似乎忘了交代', '{a}我忘了交代，我自己来补充'),
 ('我没弄懂的是{a}', '我曾经没弄懂{a}，现在明白了'),
 ('{a}的解释还欠缺，我想听', '{a}的解释已完整，我听懂了'),
 ('我没有听见{a}，需要你补充', '我已经听见{a}，无需你补充'),
 ('你能补上的话，我最需要{a}', '我能补上的就是{a}，请先听我讲'),
 ('我说的重点是{a}，请对准这个讲', '我说的重点是{a}，这是对自己发言的概括'),
 ('别给我一个名称，我在问{a}', '我给你的是一个名称，我稍后自己说明{a}'),
 ('我不是不想听{a}，恰恰想听得更清楚', '我现在不想听{a}，之后再说'),
 ('我没有让你取消解释{a}', '我现在让你取消解释{a}'),
 ('我不是要你闭口不谈{a}，只是想短一点', '我想让你先别谈{a}，保持等待'),
 ('问题并没有撤回，{a}仍需要你说', '问题已经撤回，{a}现在不用你说'),
 ('不是终止回答，我要你聚焦{a}', '现在终止回答，我自己会说明{a}'),
 ('我只是缩小问题范围，{a}仍然请你回应', '我不再问{a}，请先不要回应'),
 ('给我一个判断，就{a}而言，后面我还', '我有一个判断，就{a}而言，后面我还要自己说'),
 ('就{a}给我解释一下，然后我再', '就{a}我自己解释一下，然后我再'),
 ('旧问题已经读完，{a}请你现在作答', '旧问题写着需要说明{a}，我只是在读旧资料'),
 ('我引那句话就是希望你解释{a}', '我引那句话是在复述过去有人想了解{a}'),
]
EN=[
 ('I have not heard {a} yet.', 'I have now heard {a}; that is sufficient.'),
 ('Your answer still leaves out {a}.', 'Your answer no longer leaves out {a}. Thank you.'),
 ('The explanation of {a} is missing from your response.', 'The explanation of {a} is present in my notes; no need to repeat it.'),
 ('I have yet to hear about {a}.', 'I have finished listening to the explanation of {a}.'),
 ('What I am asking for is {a}, not a name.', 'What I wrote down is {a}, not a new question.'),
 ('I need {a} explained, rather than just labelled.', 'I have already explained {a} myself.'),
 ('The part about {a} remains unclear to me.', 'The part about {a} is now clear to me.'),
 ('You have not covered {a}, which is what I wanted.', 'You have covered {a}, which is all I wanted.'),
 ('I am not withdrawing the request for {a}.', 'I am withdrawing the request for {a}.'),
 ('I did not ask you to stop; I want a focused explanation of {a}.', 'I did ask you to stop; no explanation of {a} is needed now.'),
 ('That is not a request for silence. Tell me {a}.', 'That is a request for silence. Do not tell me {a} yet.'),
 ('The question has not been cancelled; please address {a}.', 'The question has been cancelled; please leave {a} unanswered.'),
 ('I meant {a}. That is the explanation I need.', 'I meant {a}. I am only correcting my own statement, not asking you.'),
 ('The quotation is now my question about {a}, and I want your answer.', 'The quotation is an old question about {a}, and I am merely cataloguing it.'),
 ('Give me your assessment of {a}, then I will', 'I gave my own assessment of {a}, then I went on.'),
 ('I would like you to fill in {a} before we move on.', 'I will fill in {a} myself before we move on.'),
]
CORRECTIONS=[
 ('我说的是测试以后', '我刚才讲的是测试开始之前的安排。', '我刚才把自己的经历说成了测试之前，这里我仅更正时间。'),
 ('我指的是最终用户那边', '我解释的是运维同学如何使用它。', '我在解释自己文稿里“那边”所指的对象，并非提问。'),
 ('不是原理，是实际操作', '我刚才主要解释了它的理论基础。', '我正给自己写的章节重新命名，下面是新标题。'),
 ('我想问的是交付之后', '我描述的是交付之前如何准备。', '我在朗读旧访谈记录中的一句纠正，以下不是当前请求。'),
 ('那个结果是怎样得来的', '最后我们的观测结果是等待时间下降了。', '我现在念的是旧评审表的栏目名称，原文如下。'),
 ('要的是证明，不是猜测', '我的判断主要来自一些经验上的猜想。', '我在复述当年同事给我的要求，下面是引文。'),
 ('我关心的是你，不是团队', '我刚才说的是团队整体交付了哪些东西。', '我接下来念一条已经结束的访谈提问，并不期待你作答。'),
 ('是后一阶段，不是前期', '我只介绍了开始前做的规划。', '我只是在修正我自己刚才描述的时间，不是在提问。'),
 ('我想了解的是没成功的那次', '刚才我分享的是最成功的一次尝试。', '我在念对方去年给我的反馈，请把下一句当引文听。'),
 ('我还是需要中间那一步', '第一步是申请，第三步是发放，我还没讲第二步。', '我在自述自己已完成的操作流程，并非向你索要说明。'),
 ('I meant the period after deployment.', 'I described how we prepared before deployment.', 'I am only correcting the date in my own statement, not asking for an answer.'),
 ('The middle step, not the endpoints.', 'I explained how it begins and how it ends.', 'I am reading the title of an old note, not requesting anything now.'),
 ('I meant the customer side.', 'I explained what the administrator sees.', 'The next line is a quotation from an archived interview, not my current question.'),
 ('Your contribution, rather than the whole group.', 'I have described the output of the group as a whole.', 'I am reciting a remark somebody made last year, not asking you to answer.'),
 ('I was asking about the unsuccessful attempt.', 'I told you about our most successful attempt.', 'I am quoting a correction in an old transcript, not making a live request.'),
 ('The evidence rather than the guess.', 'My explanation was based mainly on a guess.', 'I am about to read an old section heading; no answer is requested.'),
]
PREFACES=[
 ('我希望你将那个尚未讨论的细节说明一下','我希望你将那个未曾说明的'),
 ('请你从那组结果中找出异常的一项','请你从尚未列出的那组'),
 ('我想让你在两种方案中挑一个并解释','我想让你在两个还没给出的'),
 ('你需要把它总结为一句话','你需要把尚未说到的那个'),
 ('我希望你针对这个现象给出解释','我希望你针对后面还没说的'),
 ('请你从下面几种解释中选一个','请你从接下来还没列出的'),
 ('我希望你将这两种办法作个对比','我希望你将这两个尚未列举的'),
 ('请说明你偏向哪个选项','请从我还未介绍的那一组'),
 ('I would like you to explain that unspecified issue in your own words.','I would like you to take the unspecified'),
 ('Choose one option and explain your preference.','Choose from the as-yet unlisted group of'),
 ('Compare the alternatives we have just discussed.','Compare the first as-yet unnamed item with the'),
 ('Tell me which stage you would change.','I need you to take the following unnamed'),
]


def new_cases():
    rows=[]
    for language,pairs,aspects in [('zh',ZH,ZH_ASPECTS),('en',EN,EN_ASPECTS)]:
        for i,pair in enumerate(pairs):
            for j,aspect in enumerate(aspects):
                for label,text in zip([True,False],pair):
                    rows.append(case(f'v10-{language}-{i}-{j}-{int(label)}',f'v10-{language}-{i}',text.format(a=aspect),label))
    for i,(text,positive,negative) in enumerate(CORRECTIONS):
        for label,prior in [(True,positive),(False,negative)]:
            rows.append(case(f'v10-correction-{i}-{int(label)}',f'v10-correction-{i}',text,label,[turn('You' if label else 'Them',prior)]))
    for i,pair in enumerate(PREFACES):
        for label,text in zip([True,False],pair):
            rows.append(case(f'v10-preface-{i}-{int(label)}',f'v10-preface-{i}',text,label))
    return rows


def main():
    p=argparse.ArgumentParser()
    for name in ['previous','runtime','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite frozen data')
    old={s:json.loads((a.previous/f'{s}.json').read_text()) for s in ['train','calibration','development','acceptance','regression']}
    rng=random.Random(20261025);groups=collections.defaultdict(list)
    for c in old['train']:groups[(c['family'],c['respond'],len(c['context']['recentTurns'])>10)].append(c)
    rehearsal=[]
    for key,rows in sorted(groups.items()):rehearsal.extend(rng.sample(rows,min(2,len(rows))))
    new=new_cases()
    # Realistic role/context contrasts also appear with saturated earlier history.
    for label in [True,False]:
        for c in rng.sample([c for c in new if c['respond']==label],48):
            row=copy.deepcopy(c);row['id']+='-long'
            history=[turn('Them' if i%2 else 'You',('请解释此前的数据整理过程。这个请求已被回答。' if i%2 else '此前的过程已经介绍完，结果已归档。')*18,bool(i%2)) for i in range(40)]
            row['context']['recentTurns']=history+row['context']['recentTurns'];new.append(row)
    train=rehearsal+new;rng.shuffle(train)
    protected={normalized(c['text']) for s in ['calibration','development','acceptance'] for c in old[s]}
    conflicts=protected.intersection(normalized(c['text']) for c in train)
    assert not conflicts,conflicts
    seen={}
    for c in train:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen:assert seen[key]==c['respond'],c['id']
        seen[key]=c['respond']
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    a.out.mkdir(parents=True)
    for file in a.previous.iterdir():
        if file.name not in ['train.json','train.jsonl','manifest.json']:shutil.copy2(file,a.out/file.name)
    prepared=[];counts=[]
    for c in train:
        state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
        prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
    fixture=a.out/'train.json';fixture.write_text(json.dumps(train,ensure_ascii=False,indent=2)+'\n')
    data=a.out/'train.jsonl';data.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
    manifest=json.loads((a.previous/'manifest.json').read_text())
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        training_augmentation='Topic-free implicit requests, corrections of prior answers, negation of withdrawal, metalinguistic quotation and unknown task prefixes. Up to two rehearsal rows per old family/label/history-length stratum.',
        selection_data_policy='Existing V9 development informs training coverage, but no exact dev utterance is trained. Final V9 holdout remains unscored and unchanged.')
    manifest['splits']['train']=dict(count=len(train),positive=sum(c['respond'] for c in train),tokens_max=max(counts),sha256=hashlib.sha256(data.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    manifest['rehearsal']=dict(previous_rows=len(old['train']),retained_rows=len(rehearsal),new_rows=len(new),sampling_seed=20261025,grouping='family, label, long-history flag')
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(train=manifest['splits']['train'],rehearsal=manifest['rehearsal']),indent=2))


if __name__=='__main__':main()
