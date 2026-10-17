#!/usr/bin/env python3
"""V13 offline long-history contrast training with deterministic replay.

Nothing in this module is imported by the application or inference worker.
"""
import argparse, copy, datetime, hashlib, json, random, sys
from pathlib import Path
from make_laya_finetune_data import case, turn, worker_module
from review_laya_response_labels import normalized
from augment_laya_asr_robustness import caption

PAIRS='''
你跳过的那次交涉，我到现在还没有弄清经过|那次交涉的经过我刚刚已经弄清楚了
这段还是太抽象，我需要知道你实际上怎么做的|这段现在不抽象了，我知道实际怎样做了
我想听的关键一步你还没有谈到|关键一步你已经谈过，我没有新的追问
你介绍了结果，但让我困惑的过程还没解释|结果和过程都解释清楚了，不需要再补充
前两步之间缺了一块，我想把它接起来|我自己在记录中把前两步之间的缺口补上了
我还没看出这里哪些是你的工作|你的工作我现在能分清了，谢谢
你刚才提到做了取舍，我想听取舍的根据|刚才的取舍根据已经足够，不必再次说明
你一带而过的那个困难，我反而更感兴趣|那个困难我已了解，现在不想再继续
你能把这部分讲得更有画面就好了|这部分已经很有画面，我理解了
这个解释仍然没让我明白为什么要延期|这个解释解决了我对延期原因的疑问
我没跟上两种方案之间的差别|两种方案之间的差别我已经跟上了
我还等着你说那次故障是谁先注意到的|我已经知道是谁先注意到故障，不用答了
这里提到的操作听起来很空泛，我想听实操|这里提到的实际操作已经讲清楚了
你省略的准备阶段也是我想了解的|省略的准备阶段我会自己看文稿，暂不需要回应
我还听不出你怎么从现象找到那个根因|现象和根因之间的关系我现在听明白了
你补上当时各自说了什么，我会更容易理解|你补上的对话已经让我理解，不用接着补
The crucial exchange you skipped is exactly what I want to understand.|The crucial exchange you added has answered my question.
I am still missing what happened between the proposal and the vote.|I have already found what happened between the proposal and the vote.
Your explanation remains too abstract for me to picture the work.|Your explanation is concrete enough for me to picture the work now.
I have not caught the detail about how you tested the replacement.|I have caught the detail about that test and need no more.
The part I wanted to hear is still absent from your account.|The part I wanted to hear is now covered in your account.
I do not yet see which actions were yours rather than the team's.|I can now see which actions were yours and which were the team's.
More about the reasoning that led you to compromise would help.|The reasoning you gave for compromising resolves my concern.
Your account would be clearer if you described the actual conversation.|Your account is clear after the conversation you described.
I am still unclear on what you changed after the failed rehearsal.|I am clear on what you changed after the failed rehearsal now.
I would appreciate the evidence behind that initial suspicion.|I appreciate the evidence you have already given, thank you.
That leaves unanswered how you verified the final result.|That answers how you verified the final result.
The missing preparation is something I am interested in hearing.|The preparation is no longer missing from my notes.
I was hoping you would unpack the disagreement rather than just name it.|You unpacked the disagreement fully and I have no further question.
I need the intermediate steps to make sense of your conclusion.|I now have the intermediate steps and your conclusion makes sense.
There is still no explanation of why the first attempt was abandoned.|There is now a sufficient explanation of why the first attempt was abandoned.
Your explanation leaves me wanting an example from your own work.|Your example from your own work has satisfied my request.
'''


def history(c,variant,suffix):
    r=copy.deepcopy(c);r['id']+=suffix
    pairs=[('请解释上周测试数据的来源。','测试数据来自合成样本，已经归档。'),
           ('你当时怎样排查这个问题？现在已回答。','我检查了采集、处理和存储三个阶段，这一项已处理完。'),
           ('Could you explain the previous experiment? This request has been answered.','The experiment and its result have already been explained and recorded.'),
           ('Tell me about the earlier incident. The discussion is now complete.','We reviewed the evidence, explained the response and closed that topic.')]
    q,a=pairs[variant%len(pairs)]
    old=[turn('Them' if i%2 else 'You',(q if i%2 else a)*(16 if variant%4==0 else 13),bool(i%2)) for i in range(40)]
    r['context']['recentTurns']=old+r['context']['recentTurns'];r['context_condition']='long'
    return r


def main():
    p=argparse.ArgumentParser()
    for n in ['previous','holdouts','audio','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite a frozen dataset')
    rng=random.Random(20261028)
    old={s:json.loads((a.previous/(s+'.json')).read_text()) for s in ['train','calibration','development','acceptance','regression']}
    exposed=copy.deepcopy(old['acceptance']+old['development'])
    # Existing long dev rows become known regression as well; avoid extending
    # an already 40-turn synthetic history past the worker's 80-turn bound.
    for c in exposed:c['training_provenance']='V12 scored development/final; exposed training/regression, never fresh V13 acceptance.'
    source={c['id']:c for c in old['acceptance']};audio=[]
    for r in json.loads(a.audio.read_text())['rows']:
        c=copy.deepcopy(source[r['id']]);c['id']+='-native-asr';c['text']=r['asr'];c['category']='known_native_asr';audio.append(c)
    extra=[]
    for i,line in enumerate(PAIRS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:extra.append(case(f'v13-pragmatic-{i}-{int(label)}',f'v13-pragmatic-{i}',text,label))
    replay=[]
    for label in [True,False]:
        eligible=[r for r in old['train'] if r['respond']==label]
        replay.extend(rng.sample(eligible,768))
    originals=exposed+audio+extra
    variants=[]
    for i,c in enumerate(originals):
        r=copy.deepcopy(c);r['id']+='-caption';r['text']=caption(c['text'],'upper' if i%2 else 'lower')
        for t in r['context']['recentTurns']:t['text']=caption(t['text'],'upper' if i%2 else 'lower')
        variants.append(r)
    augmented=replay+originals+variants
    # Equal positive/negative long-context coverage, with different preceding
    # questions and answers. The current turn and relevant recent context remain
    # identical. Histories are offline supervision, not an inference rule.
    for label in [True,False]:
        pool=[c for c in originals+variants+replay if c['respond']==label and len(c['context']['recentTurns'])<10]
        chosen=rng.sample(pool,min(512,len(pool)))
        augmented.extend(history(c,i,f'-history-{i%4}') for i,c in enumerate(chosen))
    seen={};train=[]
    for c in augmented:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen:
            assert seen[key]==c['respond'],c['id'];continue
        seen[key]=c['respond'];train.append(c)
    rng.shuffle(train)
    dev=json.loads((a.holdouts/'development.json').read_text());final=json.loads((a.holdouts/'acceptance.json').read_text())
    for c in dev:c['context_condition']='short'
    dev+= [history(c,i,'-long-development') for i,c in enumerate(list(dev))]
    protected={normalized(c['text']) for c in old['calibration']+dev+final}
    assert not protected.intersection(normalized(c['text']) for c in train)
    regression=[];keys=set()
    for c in old['regression']+exposed+audio+extra:
        if c['id'] not in keys:regression.append(c);keys.add(c['id'])
    sets=dict(train=train,calibration=old['calibration'],development=dev,acceptance=final,regression=regression)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),context_tokens=1024,threshold=.8,question=worker.QUESTIONS,long_context_stride=1,
        acceptance_gate=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True),
        development_scope='independent_selection',development_context_gate=True,
        provenance='Local synthetic authored data and already-exposed native-ASR captions; no paid API or user recording.',
        augmentation='Fixed balanced replay; full exposed V12 final/development; pragmatic contrasts; equal positive/negative long-context supervision with four history styles; offline typography.',
        selection_data_policy='One predeclared epoch, then original independent calibration; final never used for selection. Separate short and long development gates.',
        annotation_limit='Single-annotator synthetic engineering fixtures, not population accuracy.',splits={},counts=dict(previous_train=len(old['train']),replay=len(replay),exposed=len(exposed),known_audio=len(audio),new_pragmatic=len(extra)))
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print(json.dumps(manifest,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
