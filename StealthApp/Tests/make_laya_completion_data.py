#!/usr/bin/env python3
"""Small V18 pragmatic repair, retaining V17's unscored final and all dev gates.

Only offline training changes. No final scores, runtime lexical rules, threshold
changes, or promotion of development examples into training.
"""
import argparse,copy,datetime,hashlib,json,random,sys
from pathlib import Path
from make_laya_finetune_data import case,worker_module
from make_laya_joint_data import variant
from augment_laya_history_response import history
from review_laya_response_labels import normalized

# Each line contrasts a current response request with no current response duty.
# Topics and wording are independently authored, not the failed dev utterances.
CONTRASTS='''
Your account of the evacuation still leaves the decision to reopen unexplained.|Your account of the evacuation has explained the reopening decision to my satisfaction.
I was looking for the sequence of approvals and I still have not heard it.|I was looking for the sequence of approvals and your last answer has provided it.
The example about the missing luggage is useful but I need the recovery steps.|The example about the missing luggage includes all the recovery steps I needed.
I had hoped for more detail about the stock count and that detail is still missing.|I had hoped for more detail about the stock count and now I have all of it.
There is still an unanswered point about who authorized the refund.|The point about who authorized the refund is answered and I have nothing to add.
I have your result but not the method of checking the shipment.|I have both your result and your method of checking the shipment now.
The part about resolving the noise complaint still needs an example for me.|The example of resolving the noise complaint has settled my concern.
I appreciate the overview and would still like your reasoning for the cancellation.|I appreciate the reasoning for the cancellation you have just given; that is enough.
I remain unsure how you verified that every room was empty.|Your explanation has removed my uncertainty about verifying that every room was empty.
Your last answer did not cover how you selected a safe meeting point.|Your last answer covered the safe meeting point fully and I am satisfied.
That is a useful start but I need to hear how you documented the exception.|That is the documentation explanation I needed; I have finished with this question.
I can see what changed but not why you moved the deadline.|I can now see both what changed and why the deadline moved.
The chart has not resolved my question about the difference between the two estimates.|The chart has resolved my question about the difference between the two estimates.
I expected an example of the authorization check and am still waiting for one.|I expected an authorization example and the one you just provided meets that need.
I still want to understand why the temporary entrance was closed.|I used to want an explanation of that entrance but the report has already answered it.
I have not received the practical explanation of how you reconciled the invoices.|I have received the practical invoice explanation and am simply recording it.
We have yet to hear how your group found the source of the leak.|We have heard how your group found the leak and that question is settled.
There is a missing link between your observation and your decision to stop work.|Your explanation has supplied the missing link between the observation and stopping work.
I need a fuller account of the conversation that changed the delivery plan.|The account of the delivery conversation is full enough for my purposes now.
That still does not tell me which clue led you to inspect the valve.|That tells me which clue led you to the valve, so my question is answered.
I would like your reasons for deciding to bring in an interpreter.|I have your reasons for using an interpreter and do not require any further response.
The question I asked about the revised fee remains open.|The question I asked about the revised fee is closed after your answer.
I was interested in the missing receipt and still need you to explain the search.|I was interested in the missing receipt earlier, but I have since found it myself.
I need to hear more about the checks that prevented a second dispatch.|The checks preventing a second dispatch are now fully explained in my notes.
Tell me whether the revised rota gives everyone a rest day, particularly when|Tell me whether, I have not specified a proposition for you to judge yet.
Could you judge whether moving the inspection would be safer, considering|Could you judge whether the proposal I have not introduced is, let me state it first.
Explain why the temporary barrier was removed, starting with|Explain why, I have not named the event or action in question yet.
What made the first invoice invalid, especially regarding|What made, one moment, I have not identified what I am asking about.
Compare a numbered ticket system with a single waiting line, with respect to|Compare the two items I am about to name, the first item is still to come.
How would you check that the food was stored safely, assuming|How would you check whether the object I have not identified is.
Why did the revised opening hours reduce the queue, given|Why did the, I still have to tell you what happened.
Describe your procedure for handing over a lost wallet, including|Describe the procedure for, I have yet to specify the task.
I want your opinion on extending the clinic hours, especially|I want your opinion on something I have not described; wait while I describe it.
How did you establish which medicine had been dispensed, particularly|How did you establish, the fact I want established has not been stated yet.
Tell us how you would organize an emergency phone tree, starting|Tell us how you would, I have not provided the activity or problem yet.
Explain your response when the card reader stopped working, assuming that|Explain your response to the event I will describe next, but I have not described it yet.
What is the difference between a deposit and a booking fee, in terms of|What is the difference between the thing I will name and, I have not named either one.
Describe how you made sure the replacement ladder was safe, focusing on|Describe how you made sure, the object and the property have not been introduced.
How would you resolve two customers claiming the same parcel, even if|How would you resolve the situation I am about to introduce, before I have introduced it.
Explain how you allocate the last available appointment, taking account of|Explain how you allocate, wait for me to identify what is being allocated.
Find the cause of the repeated alarm in your example, beginning with|Find the cause of, I have not told you which event needs an explanation.
Give your assessment of letting guests enter without a badge, especially|Give your assessment of whether the unnamed action is, I need to name the action first.
How did you know the backup generator could support the lights, even when|How did you know whether the unspecified equipment could, I have not said what it must do.
Explain how you settled the disagreement over the repair charge, with|Explain how you settled, I have not supplied the disagreement or incident yet.
What would you change in the visitor registration process, specifically|What would you change in, wait while I choose which process to ask about.
Please describe how you would respond to a missing safety seal, including|Please describe how you would respond to, the triggering event is still unstated.
What led you to replace the access code after that incident, particularly|What led you to, I have not named the decision I want you to explain.
I want to hear how you dealt with insufficient parking space, assuming|I want to hear how you dealt with, the difficulty I mean has not been identified yet.
刚才那段停电处置的介绍，我还缺你检查备用电源的过程。|刚才停电处置的介绍已经把备用电源讲清楚了，这点我没有疑问。
我原来想了解调班的原因，现在还没听到。|我原来想了解调班的原因，你刚才已经解释到位了。
你说完了处理结果，我还想听听怎么找回丢失的包裹。|找回包裹的过程和结果我都了解了，先记录到这里。
这个例子还没说明你为什么先联系物业。|这个例子已经说明先联系物业的原因，我理解了。
我还没弄明白你如何判断这个投诉需要升级。|你刚才把投诉升级的依据说明白了，我没有新的问题。
第一步核对收货人这一块，我还想听你展开。|第一步核对收货人这一块，细节已经够了，不用再讲。
我现在仍然需要你解释账目对不上的原因。|账目对不上的原因刚才已经解释完，我只是把它记下来。
我想听听你发现电梯异常之后具体做了什么。|我本来想问电梯异常的处理，但刚才的演示已经回答了。
介绍一下你如何分配临时病房，尤其是在。|介绍一下你如何，等我把要介绍的事情说出来。
请判断重复预约时是否应该保留最早的记录，考虑到。|请判断我接下来要念的这个结论是否，结论还没念出来。
你怎么确认这台打印机还能安全使用，比如说。|你怎么确认这个我还没有提到的设备是否，先等我介绍设备。
说说你为什么调整取餐顺序，重点放在。|说说你为什么做了那件我还没说明的事，事情我接着讲。
如果临时没有备用车辆，你会怎么组织接送，特别是。|如果发生某个情况你会，情况我还没说，先等一下。
比较一下提前通知和现场通知的效果，主要从。|比较一下我接下来要说的两种方法，第一种还没介绍。
解释一下你怎么处理票据遗失的问题，假设。|解释一下你怎么处理这个，具体是哪件事我还没有讲。
我想了解设备不够时怎么安排轮换，具体到。|我想了解这个事情是否，事情和要判断的内容我都还没说。
'''

def main():
    p=argparse.ArgumentParser()
    for n in ['previous','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace data')
    read=lambda f:json.loads(f.read_text())
    old={s:read(a.previous/(s+'.json')) for s in ['train','calibration','development','acceptance','regression']}
    extra=[]
    for i,line in enumerate(CONTRASTS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:
            extra.append(case(f'v18-completion-{i}-{int(label)}',f'v18-completion-{i}',text,label))
    assert len(extra)==128
    protected={normalized(r['text']) for s in ['calibration','development','acceptance'] for r in old[s]}
    assert not protected.intersection(normalized(r['text']) for r in extra)
    # Balanced replay of complete equivalent pairs, retaining actual native-ASR
    # and implicit/contextual requests. Pair members must remain adjacent.
    previous_pairs=[old['train'][i:i+2] for i in range(0,len(old['train']),2)]
    rng=random.Random(20261102);pairs=[]
    for label in [True,False]:
        choices=[pair for pair in previous_pairs if pair[0]['respond']==label]
        pairs.extend((x,y,'v17_replay') for x,y in rng.sample(choices,128))
    for i,c in enumerate(extra):
        cap=variant(c)
        pairs.append((c,cap,'new_short_asr_typography'))
        pairs.append((c,history(cap,i,'-completion-history'),'new_long_asr_context'))
    rng.shuffle(pairs);train=[];ledger=[]
    for i,(x,y,kind) in enumerate(pairs):
        assert x['respond']==y['respond']
        for suffix,r in [('base',x),('variant',y)]:
            r=copy.deepcopy(r);r['source_id']=r['id'];r['id']=f'v18-pair-{i}-{suffix}';r['pair_id']=i;r['pair_kind']=kind;train.append(r)
        ledger.append(dict(pair_id=i,source_id=x['id'],label=x['respond'],kind=kind))
    assert len(train)==1024 and sum(c['respond'] for c in train)==512
    assert not protected.intersection(normalized(r['text']) for r in train)
    sets=dict(old,train=train,regression=old['regression']+extra)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=copy.deepcopy(read(a.previous/'manifest.json'))
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),counts=dict(new_semantic=128,replayed_pairs=256,pairs=512),
        augmentation='Offline fulfilled-vs-open request and unspecified-task-vs-clear-incomplete contrast pairs, native-ASR replay; no runtime rules.',
        selection_data_policy='V17 development preserved, never trained on. Its frozen160 final remains wholly unscored and is reused unchanged. One fixed incremental epoch from V17 best; original calibration only.',splits={})
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        if split in ['calibration','development','acceptance']:
            for ext in ['json','jsonl']:(a.out/(split+'.'+ext)).write_bytes((a.previous/(split+'.'+ext)).read_bytes())
            manifest['splits'][split]=read(a.previous/'manifest.json')['splits'][split]
            continue
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    (a.out/'pairs.json').write_text(json.dumps(ledger,indent=2)+'\n')
    manifest['pair_ledger_sha256']=hashlib.sha256((a.out/'pairs.json').read_bytes()).hexdigest()
    (a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
