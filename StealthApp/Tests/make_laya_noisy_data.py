#!/usr/bin/env python3
"""V23 pragmatic speech robustness; new training audio is never final audio."""
import argparse,copy,datetime,hashlib,json,random,sys
from pathlib import Path
from make_laya_finetune_data import case,worker_module
from make_laya_joint_data import variant
from augment_laya_history_response import history
from review_laya_response_labels import normalized

CONTRASTS='''
你略去的那次复测正是我想了解的部分。|那次复测你刚才已经解释充分了，我不需要更多内容。
我仍然想知道你在替换组件之前做过哪些检查。|替换组件前的检查我已经看懂，目前没有新的问题。
假如把最初排除的可能性说一说，我就能理解你的推理。|你已经说清了最初排除的可能性，我现在能够理解你的推理。
你只说效果变好，我还没听到你测量效果的办法。|效果怎样测量你已经讲明白，我只是把它记在笔记里。
初次演示失败的那段，我还希望你展开谈谈。|初次演示失败那段你已经展开过，现在先停在这里。
我没有弄清你怎么区分权限问题和文件问题。|权限问题和文件问题如何区分，我现在已经弄清了。
我想补上从发现异常到找到具体原因之间的过程。|从异常到原因之间的过程你已补上，这个疑问解决了。
你在评审中坚持那个修改的理由，我还想多听一点。|你坚持修改的理由足够清楚，我没有更多追问。
请介绍一个请求被取消以后怎样清理后台任务。|请介绍取消请求后如何清理任务是过去那页讲义的标题。
解释一下你如何确认迁移后的记录没有缺失，尤其当。|解释迁移记录的检查方式这句话来自旧访谈，我只是在引用。
描述你验证备份确实可恢复的过程，从你。|描述备份恢复验证过程是一本旧教材上的练习名称。
比较批量写入和逐条写入的风险，主要在。|比较批量和逐条写入的风险是已经结束的考试里的一道题。
说说你怎样识别重复提交的订单，假设当时。|说说识别重复订单的办法是去年录音里评委说过的原话。
你如何确认报错位置就是产生错误的位置，比如。|如何确认错误位置这段话是我在抄过去的培训材料。
解释一下任务排队太久时你会怎样处理，特别是。|排队问题暂时不用解释，我先补充新的条件。
介绍一下你怎么验证新旧版本的计算结果一致，考虑到。|新旧版本结果的问题我撤回，现在不需要回答。
Your account omits the trial I was hoping to understand in detail.|Your account now covers that trial in enough detail for me.
The part about rejecting the initial measurement is what I still want explained.|The rejection of the initial measurement is already explained and needs no more discussion.
I have not grasped how you separated the permission failure from the file failure.|I now understand the difference between the permission failure and the file failure.
You mentioned a check but left out what you actually checked, which I want to know.|You have supplied what was checked and my question is settled.
I need the missing connection between the first symptom and the root cause.|You have provided the connection between the symptom and root cause, thank you.
Your summary does not include the experiment I was asking to hear about.|Your summary includes the experiment fully and I am simply recording it.
I am still interested in the reasoning you used to defend the change during review.|I was interested in that review earlier, but the record has already answered my question.
I would find it easier to follow if you unpacked the unsuccessful rehearsal.|The account of the unsuccessful rehearsal is clear enough for me now.
Describe checking whether a restored backup contains all the records, especially when|Describe checking a restored backup is the heading of an archived lesson.
Explain how you verify that a cancelled request releases its resources, assuming|I am quoting an old exercise asking how cancelled requests release resources.
Compare writing one item at a time with writing a batch, beginning with|Compare item writes and batch writes is an old worksheet title, not my current request.
Walk me through finding an error that appears only after a restart, focusing on|Those words about finding an error after restart are from a past transcript I am reading.
How do you confirm that a warning points to the actual cause, for example|I am copying the historical question about warnings pointing to the actual cause.
Describe your process for handling a job that remains queued too long, starting|I am recording a past request for a description of handling a long queue.
Explain validating a replacement component before use, considering|The request about validating the replacement is withdrawn and should not be answered now.
Tell me how you would diagnose a mismatch between two versions, particularly|Please stop the version comparison while I revise the question; no response yet.
'''

def new_cases():
    rows=[]
    for i,line in enumerate(CONTRASTS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:rows.append(case(f'v23-training-{i}-{int(label)}',f'v23-training-{i}',text,label))
    assert len(rows)==64 and sum(c['respond'] for c in rows)==32
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--training-fixture',type=Path)
    for n in ['previous','holdouts','audio','new_audio','runtime','out']:p.add_argument('--'+n,type=Path)
    a=p.parse_args()
    if a.training_fixture:
        if a.training_fixture.exists():raise SystemExit('Refusing to overwrite training fixture')
        a.training_fixture.parent.mkdir(parents=True,exist_ok=True);a.training_fixture.write_text(json.dumps(new_cases(),ensure_ascii=False,indent=2)+'\n');print('64 independently authored speech-training cases');return
    assert all(getattr(a,n) for n in ['previous','holdouts','audio','new_audio','runtime','out'])
    if a.out.exists():raise SystemExit('Refusing to replace data')
    read=lambda f:json.loads(f.read_text());old={s:read(a.previous/(s+'.json')) for s in ['train','calibration','development','acceptance','regression']}
    extra=new_cases();rng=random.Random(20261104);prior=[old['train'][i:i+2] for i in range(0,len(old['train']),2)];pairs=[]
    for label in [True,False]:pairs.extend((x,y,'balanced_replay') for x,y in rng.sample([v for v in prior if v[0]['respond']==label],128))
    for i,c in enumerate(old['acceptance']+extra):
        cap=variant(c);pairs.append((c,cap,'short_format'));pairs.append((c,history(cap,i,'-noisy-history'),'long_format'))
    audio=[]
    for originals,source in [(old['acceptance'],a.audio),(extra,a.new_audio)]:
        by={r['id']:r for r in originals};captions=read(source);assert len(captions)==len(by)
        for i,r in enumerate(captions):
            c=copy.deepcopy(by[r['id']]);assert r['spoken']==c['text'] and r['respond']==c['respond'] and r['context']==c['context'];c['text']=r['text'];c['id']+='-v23-native';audio.append(c);pairs.append((c,history(c,i,'-noisy-history'),'native_asr_history'))
    rng.shuffle(pairs);train=[];ledger=[]
    for i,(x,y,kind) in enumerate(pairs):
        assert x['respond']==y['respond']
        for suffix,r in [('base',x),('variant',y)]:
            r=copy.deepcopy(r);r['source_id']=r['id'];r['id']=f'v23-pair-{i}-{suffix}';r['pair_id']=i;r['pair_kind']=kind;train.append(r)
        ledger.append(dict(pair_id=i,source_id=x['id'],label=x['respond'],kind=kind))
    assert len(train)==1856 and sum(r['respond'] for r in train)==928
    final=read(a.holdouts/'acceptance.json');protected={normalized(r['text']) for r in old['calibration']+old['development']+final};assert not protected.intersection(normalized(r['text']) for r in train)
    sets=dict(train=train,calibration=old['calibration'],development=old['development'],acceptance=final,regression=old['regression']+old['acceptance']+audio+extra)
    assert len({r['id'] for r in sets['regression']})==len(sets['regression'])
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16');manifest=copy.deepcopy(read(a.previous/'manifest.json'))
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),counts=dict(new_semantic=64,exposed_final=160,native_captions=224,pairs=928),
        augmentation='Offline bilingual implicit/withdrawal/quotation contrasts, actual64 new TTS-native-ASR captions and exposed160 captions; balanced replay; no runtime text rules.',
        selection_data_policy='One fixed incremental epoch. All1024 prior development rows and original127 calibration unchanged; fresh160 software interview final untouched by training/selection.',splits={})
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        if split in ['calibration','development']:
            for ext in ['json','jsonl']:(a.out/(split+'.'+ext)).write_bytes((a.previous/(split+'.'+ext)).read_bytes())
            manifest['splits'][split]=read(a.previous/'manifest.json')['splits'][split];continue
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n);prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n');d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(r['respond'] for r in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    (a.out/'pairs.json').write_text(json.dumps(ledger,indent=2)+'\n');manifest['pair_ledger_sha256']=hashlib.sha256((a.out/'pairs.json').read_bytes()).hexdigest();(a.out/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n');print(json.dumps(manifest,indent=2))

if __name__=='__main__':main()
