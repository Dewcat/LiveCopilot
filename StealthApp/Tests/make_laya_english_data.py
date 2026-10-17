#!/usr/bin/env python3
"""V17 broader English pragmatics with isolated real-ASR development gates."""
import argparse,copy,datetime,hashlib,json,random,sys
from pathlib import Path
from make_laya_finetune_data import case,worker_module
from make_laya_joint_data import variant
from augment_laya_history_response import history
from review_laya_response_labels import normalized

CONTRASTS='''
You have not explained what you personally changed in the intake procedure.|You have explained your change to the intake procedure and I understand it.
I would like a clearer distinction between your work and the consultant's.|I now have a clear distinction between your work and the consultant's.
I am still waiting for the detail about how you spotted the wrong label.|I have finished noting how you spotted the wrong label.
The route from the initial alarm to the final diagnosis is missing for me.|The route from the alarm to the diagnosis is clear in my notes now.
I would appreciate a closer look at your method of checking the bookings.|I appreciate the explanation you have already given about checking bookings.
Your own contribution is still hard to identify in that group description.|Your own contribution is now identifiable and I need no further detail.
I need you to walk me through the point where the plan went off track.|I can now follow the point where the plan went off track without more explanation.
There is a gap in your account between changing the file and testing it.|The gap between changing the file and testing it has been filled in your account.
I was hoping to hear how you decided to reject that first delivery.|I had hoped to hear about the first delivery but your explanation has now satisfied me.
You still owe me the explanation of why the spare was not used.|The reason the spare was not used is already clear, so leave it there.
I cannot picture how you handled the angry visitor without an example.|That visitor example has made your method clear and no more is needed.
I want to hear the evidence you relied on before changing the appointment.|I am recording the evidence you already gave for changing the appointment.
The story does not yet show how you knew the problem was resolved.|The story now shows how you knew the problem was resolved.
I need the practical steps you took to get permission restored.|I have written down your practical steps for restoring permission.
I would like you to untangle your decision from the decision of the director.|The distinction between your decision and the director's is clear now.
You have not covered the way you checked the final quantities.|You covered the final quantity checks fully and I have no follow-up.
I am missing what you tried before contacting the manufacturer.|I am noting what you tried before contacting the manufacturer.
Hearing the details of that early conversation would help me follow.|I have heard enough of the early conversation to follow now.
The explanation of your failed trial is still too brief for me.|The explanation of the failed trial is sufficient for me now.
I still have a question about how you verified the replacement part.|I no longer have a question about the replacement part verification.
I would welcome a specific account of how you reassigned the workload.|I welcome the account you just gave and do not need another one.
I am trying to understand how your proposed safeguard actually works.|I understand how the proposed safeguard works after your explanation.
You have told me the outcome but skipped the actions that produced it.|You have connected the actions to the outcome and answered my concern.
I still need the reasoning behind keeping two copies of the schedule.|I am just writing down the reasoning you gave for keeping two copies.
I would find a concrete walkthrough of the complaint useful here.|Your walkthrough of the complaint has already given me what I needed.
I was expecting to hear what you did when the supplier stopped replying.|I had wanted that supplier detail but the written record has already supplied it.
The account is still missing the reason you delayed the inspection.|The account now includes the reason you delayed the inspection.
I have not yet heard how you distinguished a real alarm from a false one.|I have noted how you distinguished the real alarm and am not asking again.
That leaves me needing an example of the change you personally made.|That example of your personal change has resolved my question.
I would like to understand the disagreement before you reached consensus.|I understand the disagreement before the consensus now and need no reply.
Please fill in the missing explanation of how the error was detected.|The missing explanation of the error detection has already been filled in.
I am still interested in what you learned from the abandoned trial.|I was interested earlier but the abandoned trial no longer needs discussion.
Explain how you confirmed the address before the parcel left.|I am quoting an old request to explain checking the address before the parcel left.
Tell me about the decision to close the reception desk early.|That old note contains a request to describe closing reception early.
I would like you to compare a shared queue with separate queues.|The archived worksheet tells the reader to compare shared and separate queues.
Walk me through the first attempt to restore the damaged file.|Walk me through the first restoration attempt is the title of the old worksheet.
Please describe your part in resolving the appointment conflict.|Please describe your part was printed on last year's interview handout.
How did you find out that the permit had been issued to the wrong person?|The transcript records someone previously asking about the wrongly issued permit.
Why did you set aside the initial estimate and start again?|I am reading the historical question about setting aside the initial estimate.
I want to hear how you checked whether the message had been received.|I am only noting an earlier wish to hear how receipt of the message was checked.
Describe the evidence for changing the seating plan.|The old presentation contains the heading describe the evidence for the seating change.
What convinced you to ask for a second opinion?|I am quoting the examiner's past question about seeking a second opinion.
Could you explain the difference between the two replacement options?|She once asked another colleague about the replacement options; this is a recollection.
I still do not see why you changed the sequence of checks.|I am copying his earlier remark that he did not see why the checks changed order.
Give me an example of a decision you made without a supervisor.|Give me an independent decision example is an exercise in the archived booklet.
How did you tell that the revised instructions had reached everyone?|I am recording a past question about whether everyone received the revised instructions.
Please expand the part about checking the supplier's claim.|The words please expand the supplier check are from an old interview recording.
I want an explanation of how you tracked the missing key.|A former manager wanted an explanation of the missing key back then, not now.
How would you handle a room booking made twice, especially when|How would you, hold on, I have not said what the situation is yet.
Explain how you test that a repair is safe, starting with|Explain how, no wait, I have not told you what should be tested.
Compare checking every item and checking a sample, particularly if|Compare, just a moment, I still need to name both things.
Tell me about your busiest shift, focusing on|Tell me about, let me first choose the subject I want to ask about.
Describe how you recover a lost booking, given that|Describe how you, stop there, the actual operation has not been named yet.
Why did you move the inspection earlier, taking into account|Why did you, wait, I have not introduced the action I am referring to.
How do you check the returned equipment, for example|How do you check, I need to tell you what needs checking first.
Explain how you allocate scarce equipment, especially when|Explain the, hold on, I have not supplied the topic of the explanation.
What would you do if a visitor refused to leave, assuming|What would you do, please wait until I state the actual circumstances.
Describe settling a dispute about payment, with emphasis on|Describe, actually do not start because I have not named the task.
I need your view on allowing remote access, in particular|I need your view on, hang on while I decide what topic to put to you.
How would you prioritize urgent repairs, beginning with|How would you, let me finish specifying the problem before you respond.
Tell me why you rejected the damaged delivery, especially|Tell me why you, no response yet because the subject has not been introduced.
Explain checking a visitor's authorization, assuming that|Explain, wait until I say what operation I want explained.
Compare replacing the part and repairing the part, focusing on|Compare the thing I have not identified with the other unspecified thing.
I want you to describe handling a missed deadline, starting from|I want you to describe, I have not yet given the event and will do so next.
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['previous','older','holdouts','audio','older_audio','development_audio','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen data')
    read=lambda p:json.loads(p.read_text());old={s:read(a.previous/(s+'.json')) for s in ['train','calibration','development','acceptance','regression']}
    extra=[]
    for i,line in enumerate(CONTRASTS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:extra.append(case(f'v17-english-{i}-{int(label)}',f'v17-english-{i}',text,label))
    assert len(extra)==128
    rng=random.Random(20261101);unique={}
    for r in old['train']:
        if len(r['context']['recentTurns'])<10:
            key=(normalized(r['text']),json.dumps(r['context'],sort_keys=True));unique.setdefault(key,r)
    replay=[]
    for label in [True,False]:replay.extend(rng.sample([r for r in unique.values() if r['respond']==label],64))
    ambiguous={'history-joint-final-essential_intent_missing-6','history-joint-final-essential_intent_missing-16','history-joint-final-essential_intent_missing-18'}
    exposed=[copy.deepcopy(r) for r in old['acceptance'] if r['id'] not in ambiguous]
    excluded={
        'history-consistency-final-context_followup-18':'ASR destroys the question marker and route reference.',
        'history-consistency-final-reported_only-0':'ASR removes the old-archive cue.',
        'history-consistency-final-reported_only-16':'is -> AS can make the reported title sound like a live instruction.',
        'history-consistency-final-essential_intent_missing-18':'ASR destroys the not-yet qualification.',
        'history-joint-final-asr_request-6':'I am -> HIM can change the identity of the person requesting explanation.'}
    for k in ambiguous:excluded[k]='Self-repair without prosody/context is ambiguous; retained unchanged in known regression, not taught as an equivalent pair.'
    audio=[];pairs=[];prototypes=replay+exposed+extra
    for i,c in enumerate(prototypes):
        cap=variant(c)
        if cap['text']!=c['text'] or cap['context']!=c['context']:pairs.append((c,cap,'short_asr_typography'))
        pairs.append((c,history(cap,i,'-english-history'),'joint_asr_long_history'))
    for folder,audio_file in [(a.older,a.older_audio),(a.previous,a.audio)]:
        source={r['id']:r for r in read(folder/'acceptance.json')}
        for i,row in enumerate(read(audio_file)):
            c=copy.deepcopy(source[row['id']]);c['id']+='-v17-known-native';c['text']=row['text'];audio.append(c)
            if row['id'] not in excluded:pairs.append((c,history(c,i,'-english-history'),'native_asr_long_history'))
    rng.shuffle(pairs);train=[];ledger=[]
    for i,(a0,b,kind) in enumerate(pairs):
        for suffix,r in [('base',a0),('variant',b)]:
            r=copy.deepcopy(r);r['source_id']=r['id'];r['id']=f'v17-pair-{i}-{suffix}';r['pair_id']=i;r['pair_kind']=kind;train.append(r)
        ledger.append(dict(pair_id=i,source_id=a0['id'],label=a0['respond'],kind=kind))
    dev=copy.deepcopy(old['development'])
    for r in dev:r['development_group']='existing'
    dev_original=read(a.holdouts/'development.json');dev_captions=read(a.development_audio)
    assert len(dev_original)==len(dev_captions)==64
    caption_by_id={r['id']:r for r in dev_captions}
    for i,c in enumerate(dev_original):
        native=caption_by_id[c['id']];assert native['spoken']==c['text'] and native['respond']==c['respond'] and native['context']==c['context']
        for group,text in [('english_text',c['text']),('english_asr',native['text'])]:
            short=copy.deepcopy(c);short['text']=text;short['id']+='-'+group;short['context_condition']='short';short['development_group']=group
            long=history(short,0,'-saturated');dev.extend([short,long])
    final=read(a.holdouts/'acceptance.json')
    protected={normalized(r['text']) for r in old['calibration']+dev+final}
    assert not protected.intersection(normalized(r['text']) for r in train)
    labels={}
    for r in train:
        ctx=copy.deepcopy(r['context'])
        for t in ctx['recentTurns']:t['text']=normalized(t['text'])
        key=(normalized(r['text']),json.dumps(ctx,sort_keys=True))
        if key in labels:assert labels[key]==r['respond']
        labels[key]=r['respond']
    sets=dict(train=train,calibration=old['calibration'],development=dev,acceptance=final,regression=old['regression']+old['acceptance']+audio+extra)
    assert len({r['id'] for r in sets['regression']})==len(sets['regression'])
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),question=worker.QUESTIONS,context_tokens=1024,threshold=.8,long_context_stride=1,
        acceptance_gate=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True),
        development_scope='independent_selection',development_context_gate=True,development_group_gate=True,paired_consistency=True,
        selection_data_policy='Reserved old development plus fresh64 English original/native captions, each short/long. Every group/context separately gated before final. No final scores choose weights or thresholds.',
        annotation_limit='Single-annotator synthetic engineering fixtures, not population accuracy.',
        augmentation='English pragmatic contrasts plus paired ASR formatting/history and known native captions; no runtime sentence/case/punctuation rules.',
        excluded_training_audio=excluded,excluded_training_originals=sorted(ambiguous),
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
    for ext in ['json','jsonl']:assert (a.out/('calibration.'+ext)).read_bytes()==(a.previous/('calibration.'+ext)).read_bytes()
    (a.out/'pairs.json').write_text(json.dumps(ledger,indent=2)+'\n');manifest['pair_ledger_sha256']=hashlib.sha256((a.out/'pairs.json').read_bytes()).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
