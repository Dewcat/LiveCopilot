#!/usr/bin/env python3
"""V14 small, balanced intent-contrast fine-tune; V13 final stays unscored."""
import argparse, copy, datetime, hashlib, json, random, sys
from pathlib import Path
from make_laya_finetune_data import case, worker_module
from review_laya_response_labels import normalized
from augment_laya_asr_robustness import caption
from augment_laya_history_response import history

PAIRS='''
你的描述还没说清最早是谁察觉到了故障|你的描述已经说清最早察觉故障的是谁
我仍不理解增加这一道复核的理由|增加这一道复核的理由我已经理解
为什么要留着原来的那份记录|当时为什么留原记录已经解释过，我不再问了
你决定保留旧路径的考虑是什么|我来讲我决定保留旧路径的考虑，你先听
解释一下两套数据为什么要独立保存，尤其在|要你解释的具体内容我尚未说明，接下来是
请讲讲为什么没有覆盖原文件，假如|请对那个尚未命名的文件执行一个我还未说明的
谁最先提出这个怀疑，我这里还没有听到|谁最先提出怀疑我已经听到了，不用重复
我还是没搞清楚额外一步到底防了什么|额外那一步防什么我已搞清楚了
旧版本还留着是基于什么考虑|我记得你讲过旧版本为何保留，这里无需再答
我现在想听保留历史数据的理由|我现在撤回了解保留历史数据理由的要求
你说的是后来确认的人，最先注意到的呢|你说清了发现和确认的人，已经够了
多出来这个环节，我还想知道它的用处|多出来的环节我会自己查资料，先别解释
为什么这两个版本要分开维护，特别考虑|请把还没指出的某个版本变成另一个未指定的
说明你怎样确认第一条线索可靠，假设我们|我让你说明的那个对象和行为还没有讲明白
你个人为何选择让旧服务继续运行|我在引用去年那句你为何让旧服务继续运行
你最初的判断是哪位同事提醒你的|我现在自己补上最初是谁提醒我的
有三个可用办法，你怎样权衡风险和耗时|我要你从尚未列出的办法里选一个具体的
比较一下已经说过的人工校验和自动校验|比较的两项我还没有介绍，请等它们的名字
我不清楚冗余的那一次检查有什么意义|冗余检查的意义我现在清楚了，谢谢
刚才关于谁报告问题的部分还缺个人名|我自己的记录里刚才缺个人名，现在已补齐
Why did you retain the earlier record instead of replacing it?|Why you retained the earlier record is already clear to me.
Explain the reason for preserving the obsolete version even when|The operation and the version it applies to have not been specified yet.
I cannot tell from your account who first noticed the failure.|I can now tell from your account who first noticed the failure.
I still do not understand the purpose of the additional verification.|The purpose of the additional verification is clear now.
Tell me why the two datasets need independent storage especially if|Please perform the unspecified task on two datasets I have not identified.
What led you to keep the old service running?|What led you to keep the old service running was a previous survey question.
Your story has not identified the person who raised the first alarm.|Your story has identified the person who raised the first alarm, thanks.
I would like to understand what the extra check protects against.|I no longer need to understand that extra check, so do not answer.
Why store the earlier revision as well as the replacement?|I am recording the old prompt asking why both revisions were stored.
Describe why you separated the logs from the data assuming|The things you should separate and the purpose remain unspecified.
Who gave you the first clue about the problem?|Who gave me the first clue is something I will explain myself.
The reason for leaving the older entry intact is still missing.|The reason for leaving the older entry intact has been supplied.
Can you explain why those duplicate copies are kept apart when|Please replace an unidentified copy with another copy I have yet to name.
I have not understood why another inspection was necessary.|I have understood why another inspection was necessary now.
The first person to spot the discrepancy interests me here.|I already know who spotted the discrepancy and have no question.
Why did you decide against deleting the old backup?|I withdraw my request to discuss deleting the old backup.
Compare the safety of the two approaches you just described.|Select one of the approaches whose details I have not provided.
Explain why the archived record must stay separate particularly|The object to work on and the action to take are both still unspecified.
Your answer has left out who actually reported the warning.|Your answer has settled my concern about who reported the warning.
What benefit justified that second pass through the data?|I have not told you what alternatives to choose between yet.
'''


def main():
    p=argparse.ArgumentParser()
    for n in ['previous','replay','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace a frozen dataset')
    old={s:json.loads((a.previous/(s+'.json')).read_text()) for s in ['calibration','development','acceptance','regression']}
    rng=random.Random(20261029);pool=json.loads((a.replay/'train.json').read_text());replay=[]
    for label in [True,False]:replay.extend(rng.sample([c for c in pool if c['respond']==label],512))
    extra=[]
    for i,line in enumerate(PAIRS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:extra.append(case(f'v14-intent-{i}-{int(label)}',f'v14-intent-{i}',text,label))
    augmented=replay+extra
    for i,c in enumerate(extra):
        r=copy.deepcopy(c);r['id']+='-caption';r['text']=caption(c['text'],'upper' if i%2 else 'lower');augmented.append(r)
        for variant in range(4):
            base=r if variant%2 else c
            augmented.append(history(base,variant,f'-history-{variant}'))
    seen={};train=[]
    for c in augmented:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen:assert seen[key]==c['respond'];continue
        seen[key]=c['respond'];train.append(c)
    protected={normalized(c['text']) for s in ['calibration','development','acceptance'] for c in old[s]}
    assert not protected.intersection(normalized(c['text']) for c in train)
    rng.shuffle(train);sets=dict(old,train=train);sets['regression']=old['regression']+extra
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    prior=json.loads((a.previous/'manifest.json').read_text())
    manifest=dict(prior,created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),splits={},
                  augmentation='Balanced replay plus newly authored current-vs-handled request, known-vs-unknown intent contrasts under four long histories. No V13 development/final texts in training.',
                  selection_data_policy='One fixed small epoch, unchanged calibration; V13 development retained for selection, V13 final remains unscored before candidate freeze.',
                  counts=dict(replay=len(replay),new_semantic=len(extra)))
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    for s in ['calibration','development','acceptance']:
        for ext in ['json','jsonl']:assert (a.out/(s+'.'+ext)).read_bytes()==(a.previous/(s+'.'+ext)).read_bytes()
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
