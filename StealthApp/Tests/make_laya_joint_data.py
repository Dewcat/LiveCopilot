#!/usr/bin/env python3
"""V16 offline joint ASR/long-context equivalent pairs; no runtime rules."""
import argparse,copy,datetime,hashlib,json,random,sys
from pathlib import Path
from make_laya_finetune_data import case,worker_module
from make_laya_consistency_data import typography
from augment_laya_history_response import history
from review_laya_response_labels import normalized

CONTRASTS='''
你把批准后的事讲了，批准之前那场争论我还想听|批准之前那场争论已经讲明白了，我没有追问
我想把最初的迹象和你的第一步行动联系起来|我已经把最初的迹象和第一步行动对应起来了
我本来期待你说说没有选中的供应商哪里不合适|我原本想问供应商，但现在不需要解释了
你给的例子还是让我看不出那个操作的实际作用|这个例子让我看出了操作的实际作用，谢谢
你个人和同事分别做了什么，这一点仍有些模糊|你个人和同事分别做了什么我现在已经分清
我还需要你把那次检查从准备到结束串起来|那次检查从准备到结束我已经自己串起来了
我想从一次真实的预约冲突理解你的处理方式|我已从这个预约冲突理解了你的处理方式
你省掉的那段查证过程恰恰是我关心的|我关心的那段查证过程已经补足，不用再说
关于为什么放弃第一种报价，我仍没有听到根据|第一种报价被放弃的根据我已经清楚
我更想听你自己如何处理那批缺失的附件|那批缺失的附件我自己来处理，不需要回答
你说测试通过，但通过的依据我还不明白|测试通过的依据我现在明白了
这部分我仍然跟不上，请带着我慢慢过一遍|这部分我已经跟上，不必再重复一遍
I was expecting an account of the debate before the approval.|The debate before the approval is clear now and I have no follow-up.
I need to connect the first sign you noticed with your first action.|I have now connected the first sign with the action you took.
I had hoped to hear why the other supplier was unsuitable.|I had planned to ask about the supplier but no longer need an explanation.
The example still leaves me uncertain what that operation achieves.|That example has clarified what the operation achieves, thank you.
The distinction between your work and your colleague's remains vague.|I can now distinguish your work from your colleague's.
I need you to connect the inspection's preparation to its final outcome.|I have connected the preparation and final outcome myself.
A real booking conflict would help me understand your method.|The booking conflict you described has explained your method.
The verification you left out is the part that interests me.|The verification I wanted has been supplied and needs no more detail.
I still have not heard what justified rejecting the first quote.|I understand what justified rejecting the first quote now.
I would rather hear how you personally handled the missing attachments.|I will handle the missing attachments myself and do not need a reply.
You said the test passed but I still do not know what counted as a pass.|I now know what counted as a passing test.
I am still unable to follow this part and need a slower walk through.|I can follow this part now and need no repetition.
'''

def variant(c):
    r=copy.deepcopy(c);r['text']=typography(r['text'],True)
    for t in r['context']['recentTurns']:t['text']=typography(t['text'],True)
    return r

def main():
    p=argparse.ArgumentParser()
    for n in ['previous','holdouts','audio','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen dataset')
    old={s:json.loads((a.previous/(s+'.json')).read_text()) for s in ['train','calibration','development','acceptance','regression']}
    rng=random.Random(20261031);unique={}
    for r in old['train']:
        if len(r['context']['recentTurns'])<10:
            key=(normalized(r['text']),json.dumps(r['context'],sort_keys=True));unique.setdefault(key,r)
    replay=[]
    for label in [True,False]:replay.extend(rng.sample([r for r in unique.values() if r['respond']==label],64))
    extra=[]
    for i,line in enumerate(CONTRASTS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:extra.append(case(f'v16-pragmatic-{i}-{int(label)}',f'v16-pragmatic-{i}',text,label))
    exposed=copy.deepcopy(old['acceptance']);source={r['id']:r for r in exposed}
    # Known ASR errors with damaged essential intent are not safe equivalent
    # training pairs. Keep every one in known regression and final audit.
    excluded={
        'history-consistency-final-context_followup-18':'What -> LETS and route -> RUDE damages the question.',
        'history-consistency-final-reported_only-0':'Old-archive cue disappears in 就当按理.',
        'history-consistency-final-reported_only-16':'is -> AS can turn a reported title into a live instruction.',
        'history-consistency-final-essential_intent_missing-18':'not-yet -> NAZIED destroys the missing-object qualification.'}
    audio=[];pairs=[];prototypes=replay+exposed+extra
    for i,c in enumerate(prototypes):
        cap=variant(c)
        if cap['text']!=c['text'] or cap['context']!=c['context']:
            pairs.append((c,cap,'short_asr_typography'))
        pairs.append((c,history(cap,i,'-joint-history'),'joint_asr_long_history'))
    for i,row in enumerate(json.loads(a.audio.read_text())):
        c=copy.deepcopy(source[row['id']]);c['text']=row['text'];c['id']+='-native-asr';audio.append(c)
        if row['id'] not in excluded:
            pairs.append((c,history(c,i,'-joint-history'),'native_asr_long_history'))
    rng.shuffle(pairs);train=[];ledger=[]
    for i,(a0,b,kind) in enumerate(pairs):
        for suffix,r in [('base',a0),('variant',b)]:
            r=copy.deepcopy(r);r['source_id']=r['id'];r['id']=f'v16-pair-{i}-{suffix}';r['pair_id']=i;r['pair_kind']=kind;train.append(r)
        ledger.append(dict(pair_id=i,source_id=a0['id'],label=a0['respond'],kind=kind))
    # Add joint formatting variants of existing development, still reserved
    # from all training; no new final or final-ASR scores used for selection.
    dev=copy.deepcopy(old['development'])
    for c in old['development']:
        r=variant(c);r['id']+='-joint-caption';dev.append(r)
    final=json.loads((a.holdouts/'acceptance.json').read_text())
    protected={normalized(r['text']) for r in old['calibration']+dev+final}
    assert not protected.intersection(normalized(r['text']) for r in train)
    labels={}
    for r in train:
        ctx=copy.deepcopy(r['context'])
        for t in ctx['recentTurns']:t['text']=normalized(t['text'])
        key=(normalized(r['text']),json.dumps(ctx,sort_keys=True))
        if key in labels:assert labels[key]==r['respond']
        labels[key]=r['respond']
    sets=dict(train=train,calibration=old['calibration'],development=dev,acceptance=final,regression=old['regression']+exposed+audio+extra)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),question=worker.QUESTIONS,context_tokens=1024,threshold=.8,long_context_stride=1,
        acceptance_gate=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True),
        development_scope='independent_selection',development_context_gate=True,paired_consistency=True,
        selection_data_policy='V13 development plus offline ASR typography variants, reserved from training. V16 final and full audio frozen before training; no selection using final.',
        annotation_limit='Single-annotator synthetic engineering fixtures, not population accuracy.',
        augmentation='Equivalent paired current-intent states under joint ASR typography and unrelated handled long history; known native captions paired with long history. No runtime rules.',
        excluded_training_audio=excluded,counts=dict(replay=len(replay),exposed_final=len(exposed),known_asr=len(audio),new_semantic=len(extra),pairs=len(pairs)),splits={})
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(r['respond'] for r in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    for ext in ['json','jsonl']:assert (a.out/('calibration.'+ext)).read_bytes()==(a.previous/('calibration.'+ext)).read_bytes()
    (a.out/'pairs.json').write_text(json.dumps(ledger,indent=2)+'\n');manifest['pair_ledger_sha256']=hashlib.sha256((a.out/'pairs.json').read_bytes()).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
