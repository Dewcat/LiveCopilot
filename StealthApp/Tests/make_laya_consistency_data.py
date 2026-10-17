#!/usr/bin/env python3
"""Create reviewed adjacent equivalent training pairs, never runtime rules."""
import argparse, copy, datetime, hashlib, json, random, re, sys, unicodedata
from pathlib import Path
from make_laya_finetune_data import case, worker_module
from review_laya_response_labels import normalized
from augment_laya_history_response import history

REQUESTS='''
请比较分批发送与逐条发送的差别|尤其遇到
说明为什么读请求需要校验时间戳|假设当时
你是怎样确认日志里没有漏事件的|比如在
给我讲讲一次你亲自跟进的故障|先从那个
为什么两份备份不放在同一个地方|特别当
解释一下最后那轮测试想验证什么|考虑到我们
你如何判断上一次重试有没有成功|接下来还想
说说你为何决定让旧版本继续保留|尤其是当
你怎样在几个同时告警的设备里排优先级|从你
我想听你用来排除另一个猜测的证据|假如那时
比较一下先确认再写入和先写入再确认|主要围绕
请讲你怎样防止同一个动作执行两遍|先考虑
Compare sending items in batches and sending them individually|especially when
Explain why read requests have to validate a timestamp|assuming that
How did you check that the log contained every event|particularly in
Tell me about an incident you personally followed through|starting with
Why were the two backups kept in different places|especially if
Explain what the final round of testing was meant to establish|given that
How do you determine whether the previous retry succeeded|and then
Describe your reason for keeping the previous release available|especially when
How would you prioritize devices that all raise an alarm together|starting from
I would like to hear the evidence you used to reject the other hypothesis|particularly if
Compare confirming before a write with confirming after a write|focusing on
Explain how you prevent the same action from being executed twice|assuming
'''
NEGATIVES='''
真正要比较的东西我还没有给你，现在要介绍的是
需要处理哪个事件还未确定，请等我把事件说出来
我想请你做的并非刚才那件事，实际任务我还没讲
需要操作的目标和方式目前都尚未指定
你要选的候选方案还未展示出来，分别是
问题的具体内容还在后面，我现在先描述背景
让我先给出题目是什么，而不是现在请你回答
我还没有提出任何具体要求，接下来才会说
这个请求的关键对象还没告诉你，其实是
不要根据旧题回答，我的新题目还没读出来
我的意思不是让你解释，只是记录过去有人这样要求
关于漏掉的日志我已经理解，不必再接着说
The subjects of the comparison have not been supplied yet and will be
I have yet to specify which event needs attention, so wait for that information
The actual task differs from the earlier one and has not been stated yet
Neither the target nor the operation has been specified at this point
The options for your selection have not been shown and are going to be
The question itself comes later; I am still describing the background
Let me give you the actual question before inviting a response
I have not made a concrete request yet and am about to do so
The essential object of this request has not been identified and is
Do not answer the old question, my new one has not been read out yet
I am only recording that someone previously requested an explanation
I understand the missing log entries now and need no further explanation
'''


def typography(text,upper):
    # Preserve quotation marks: removing a quotation boundary could change the
    # intent. Apostrophes/other punctuation and case can mimic ASR typography.
    keep='"“”‘’'
    s=''.join(c for c in text if c in keep or not unicodedata.category(c).startswith('P'))
    s=re.sub(r'\s+',' ',s).strip()
    return s.upper() if upper else s.lower()


def main():
    p=argparse.ArgumentParser()
    for n in ['previous','replay','holdouts','audio','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen data')
    old={s:json.loads((a.previous/(s+'.json')).read_text()) for s in ['calibration','development','acceptance','regression']}
    rng=random.Random(20261030);pool=json.loads((a.replay/'train.json').read_text());unique={}
    for r in pool:
        if len(r['context']['recentTurns'])<10:
            key=(normalized(r['text']),json.dumps(r['context'],sort_keys=True));unique.setdefault(key,r)
    replay=[]
    for label in [True,False]:replay.extend(rng.sample([r for r in unique.values() if r['respond']==label],128))
    exposed=copy.deepcopy(old['acceptance']);source={r['id']:r for r in exposed};audio=[]
    for row in json.loads(a.audio.read_text())['rows']:
        r=copy.deepcopy(source[row['id']]);r['text']=row['asr'];r['id']+='-known-native-asr';audio.append(r)
    extra=[];tails={}
    for i,line in enumerate(REQUESTS.strip().splitlines()):
        text,tail=line.split('|');r=case(f'v15-ready-{i}',f'v15-ready-{i}',text,True);extra.append(r);tails[r['id']]=tail
    for i,text in enumerate(NEGATIVES.strip().splitlines()):extra.append(case(f'v15-wait-{i}',f'v15-wait-{i}',text,False))
    prototypes=replay+exposed+audio+extra;pairs=[]
    for i,c in enumerate(prototypes):
        variants=[]
        r=copy.deepcopy(c);r['text']=typography(r['text'],i%2==0)
        for t in r['context']['recentTurns']:t['text']=typography(t['text'],i%2==0)
        if r['text']!=c['text'] or r['context']!=c['context']:variants.append(('asr_typography',r))
        variants.append(('handled_long_history',history(c,i,'-history')))
        if c['id'] in tails:
            r=copy.deepcopy(c);r['text']+=('，' if i%2 else ' ')+tails[c['id']]
            variants.append(('optional_trailing_fragment',r))
        for kind,r in variants:
            assert r['respond']==c['respond'];pairs.append((c,r,kind))
    rng.shuffle(pairs);train=[];ledger=[]
    for i,(a0,b,kind) in enumerate(pairs):
        for suffix,r in [('base',a0),('variant',b)]:
            r=copy.deepcopy(r);r['source_id']=r['id'];r['id']=f'pair-{i}-{suffix}';r['pair_id']=i;r['pair_kind']=kind;train.append(r)
        ledger.append(dict(pair_id=i,source_id=a0['id'],label=a0['respond'],kind=kind))
    final=json.loads((a.holdouts/'acceptance.json').read_text());protected={normalized(r['text']) for r in old['calibration']+old['development']+final}
    assert not protected.intersection(normalized(r['text']) for r in train)
    # Equivalent normalized states may repeat in pairs, but labels must agree.
    labels={}
    for r in train:
        context=copy.deepcopy(r['context'])
        for t in context['recentTurns']:t['text']=normalized(t['text'])
        key=(normalized(r['text']),json.dumps(context,sort_keys=True))
        if key in labels:assert labels[key]==r['respond']
        labels[key]=r['respond']
    sets=dict(train=train,calibration=old['calibration'],development=old['development'],acceptance=final,regression=old['regression']+exposed+audio+extra)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),question=worker.QUESTIONS,context_tokens=1024,threshold=.8,long_context_stride=1,
        acceptance_gate=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True),
        development_scope='independent_selection',development_context_gate=True,paired_consistency=True,
        selection_data_policy='Retained V13 development for selection only. New V15 final frozen before training. V14 final/captions explicitly exposed known training and regression.',
        annotation_limit='Single-annotator synthetic engineering fixtures. No population accuracy claim.',
        augmentation='Adjacent same-label pairs: original/ASR typography preserving quote boundaries, handled unrelated long history, or optional unfinished grammar after a fully specified request.',
        counts=dict(replay=len(replay),exposed_final=len(exposed),known_asr=len(audio),new_semantic=len(extra),pairs=len(pairs)),splits={})
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(r['respond'] for r in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    for split in ['calibration','development']:
        for ext in ['json','jsonl']:assert (a.out/(split+'.'+ext)).read_bytes()==(a.previous/(split+'.'+ext)).read_bytes()
    (a.out/'pairs.json').write_text(json.dumps(ledger,indent=2)+'\n');manifest['pair_ledger_sha256']=hashlib.sha256((a.out/'pairs.json').read_bytes()).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))


if __name__=='__main__':main()
