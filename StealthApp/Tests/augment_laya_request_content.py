#!/usr/bin/env python3
"""Distinguish an understandable main request from an empty request preface.

Offline training examples only. The previous final test is explicitly exposed;
an entirely new final test is required and never read by the trainer.
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

# Positive requests specify an action and topic; negatives have no actionable
# current request yet. Past topics are already handled, not new instructions.
PREFACES = [
    ('我想麻烦你做的是讲讲{t}的教训', '我想麻烦你做的是'),
    ('我希望你帮我理解{t}的作用', '我希望你帮我把某个'),
    ('今天想问的是{t}如何改进', '今天想问的是'),
    ('我有件事希望你能解释，就是{t}的原因', '我有件事希望你能'),
    ('我准备让你先介绍{t}', '我准备让你先'),
    ('我打算请教你的地方是{t}的取舍', '我打算请教你的地方是'),
    ('你先帮我把{t}的经验归纳一下', '你先帮我把'),
    ('我想让你给我们讲解{t}', '我想让你给'),
    ('你能否把{t}讲得再明白点', '你能否把那个'),
    ('我们真正想确认的是{t}是否可靠', '我们真正想确认的是'),
    ('能不能请你把{t}的利弊说出来', '能不能请你把'),
    ('我接下来需要你解释{t}的风险', '我接下来需要你'),
    ('我的要求是让你介绍{t}', '我的要求是让你'),
    ('我现在希望知道的是{t}该怎么做', '我现在希望知道的是'),
    ('有道题要你说明{t}的流程', '有道题要你说明的是'),
    ('刚才的问题换成{t}的原理，请解释', '刚才的问题应该换成'),
    ('Can you help me understand {e}?', 'Can you help me with'),
    ('I need you to explain {e}.', 'I need you to'),
    ('I would like you to tell me how {e} works.', 'I would like you to tell me'),
    ('What I want to know is why {e} was needed.', 'What I want to know is'),
    ('The task I need help with is explaining {e}.', 'The task I need help with is'),
    ('Could you please describe {e}?', 'Could you please take the'),
    ('I want to ask whether {e} is reliable.', 'I want to ask whether the'),
    ('I need your explanation of {e}.', 'I need your explanation of the'),
]
TAILS = [
    ('{t}你讲讲，主要就是', '{t}我来讲，主要就是'),
    ('我想了解{t}的经历，后面的', '我在记录{t}的经历，后面的'),
    ('麻烦介绍{t}，我想了解的还有', '我来介绍{t}，我想说的还有'),
    ('请复盘{t}，当时你', '我复盘了{t}，当时我'),
    ('把{t}说给我听，特别是其中', '我把{t}说给他听，特别是其中'),
    ('{t}怎么才能做好，比如', '{t}做得好是因为，比如'),
    ('请你评价{t}，我的意思就是', '我评价过{t}，我的意思就是'),
    ('请解释{t}，此外还有', '我已经解释了{t}，此外还有'),
    ('谈谈{t}的难点，后面那个', '我知道{t}的难点，后面那个'),
    ('如果{t}人手不够，你怎么安排，假设', '如果{t}人手不够，我会另作安排，假设'),
    ('{t}出现问题你怎么办，主要是', '{t}出现问题我已经处理了，主要是'),
    ('讲讲{t}的过程，我说的是', '{t}的过程我讲完了，我说的是'),
    ('Tell me how {e} was done, what I mean is', 'I will explain how {e} was done, what I mean is'),
    ('Explain your experience with {e}, and the next', 'I recorded my experience with {e}, and the next'),
    ('How would you manage {e} with less money, given', 'I managed {e} with less money, given'),
    ('Describe the difficulty with {e}, especially the', 'I have described the difficulty with {e}, especially the'),
]


def main():
    p=argparse.ArgumentParser()
    for name in ['previous','fresh','runtime','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen data')
    old={s:json.loads((a.previous/f'{s}.json').read_text()) for s in ['train','calibration','development','acceptance','regression']}
    fresh=json.loads(a.fresh.read_text())
    exposed=copy.deepcopy(old['acceptance'])
    for c in exposed:c['training_provenance']='Previous final holdout exposed by failed V7 evaluation; no longer unseen.'
    additions=[]
    topics=[('交接评审','handover reviews'),('演练安排','rehearsal scheduling'),('数据核查','data reconciliation'),('任务拆分','task decomposition')]
    for family,pairs in [('preface',PREFACES),('tail',TAILS)]:
        for i,pair in enumerate(pairs):
            for j,(topic,english) in enumerate(topics):
                history=[turn('Them',f'我们先回顾{topic}。',True),turn('You',f'{topic}那部分已经讲完，以下是一个新话题。')]
                for label,text in zip([True,False],pair):
                    additions.append(case(f'content-{family}-{i}-{j}-{int(label)}',f'content-{family}-{i}',text.format(t=topic,e=english),label,history if j%2 else []))
    rng=random.Random(20261023)
    pool=exposed+additions
    for label in [True,False]:
        for i,c in enumerate(rng.sample([c for c in pool if c['respond']==label],64)):
            r=copy.deepcopy(c);r['id']+='-content-long'
            prior=topics[i%len(topics)][0]
            history=[turn('Them' if k%2 else 'You',(f'请解释此前{prior}的依据。' if k%2 else f'{prior}的依据已经回答完毕，讨论已结束。')*15,bool(k%2)) for k in range(40)]
            r['context']['recentTurns']=history+r['context']['recentTurns'];additions.append(r)
    train=old['train']+exposed+additions
    protected={normalized(c['text']) for c in old['calibration']+old['development']+fresh}
    assert not protected.intersection(normalized(c['text']) for c in train)
    past={normalized(c['text']) for rows in old.values() for c in rows}
    assert not past.intersection(normalized(c['text']) for c in fresh)
    rng.shuffle(train)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    a.out.mkdir(parents=True)
    for name in ['label-audit.json','calibration.json','calibration.jsonl','development.json','development.jsonl']:
        shutil.copy2(a.previous/name,a.out/name)
    manifest=json.loads((a.previous/'manifest.json').read_text())
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    split_policy='V7 final test is now exposed training/regression. Independent development and calibration unchanged. New final holdout authored before V8 training; no normalized utterance overlap with any earlier split.',
                    regression_scope='Known training regressions, not unseen accuracy.',
                    training_augmentation='Main request plus dangling elaboration versus empty request preface; balanced long histories; training data only, no runtime rules.')
    for split,rows in dict(train=train,acceptance=fresh,regression=old['regression']+exposed).items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        fixture=a.out/f'{split}.json';fixture.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        data=a.out/f'{split}.jsonl';data.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(data.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest['splits'],indent=2))


if __name__=='__main__':main()
