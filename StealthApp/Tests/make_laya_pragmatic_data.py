#!/usr/bin/env python3
"""V20 bilingual response-intent training with native-ASR and context pairs."""
import argparse,copy,datetime,hashlib,json,random,sys
from pathlib import Path
from make_laya_finetune_data import case,turn,worker_module
from make_laya_joint_data import variant
from augment_laya_history_response import history
from review_laya_response_labels import normalized

CONTRASTS='''
我想听你解释这次行李转运为何延迟。|我想听你解释的那件事尚未交代，等我先把事情说出来。
请判断没有车票能否直接登车。|请判断一个还没有向你陈述的结论是否合理。
请比较提前预约和到现场排队的优缺点。|请比较两个还没有介绍给你的东西。
请从白天和夜间这两个配送时段里选一个并说明理由。|我想让你从几个时段中选一个，但时段列表尚未提供。
算一下十二个人每人三张票一共需要多少。|我希望你帮我计算，但计算对象和数字还没告诉你。
给我建议怎样给第一次来的访客指路。|我希望听到你的建议，但针对的具体任务尚未说明。
介绍一下天气很差时你如何保证室外活动安全。|我正准备介绍需要你回答的场景，场景内容还没讲。
谈谈在有限预算里如何安排工具更换。|我会给你一个预算问题，不过要解决什么问题还没提出。
解释为什么失物要先登记再交还。|要你解释的内容我还没有提供，正在翻到那一页。
你怎样核实临时通行证没有过期。|我要问的对象还没有确定，先想好再告诉你。
第一段里你怎么说服对方延期，我还想听具体些。|第一段里说服对方延期的过程已经足够具体，我理解了。
我现在还缺你亲自安排运输路线的细节。|你亲自安排路线的细节刚才已经补齐，我不再追问。
你说试过几种办法，我还想听没成功的那次。|没成功那次你已经讲得清楚，我只是记下来。
我比较想听你在现场提出那个异议的依据。|提出异议的依据已经清楚了，不需要补充。
这里你略过了怎么核实损失，我想了解那部分。|核实损失那部分的解释已经满足我的需要。
我还没听明白为什么你拒绝了第一次报价。|第一次报价为什么被拒绝我已经弄明白了。
麻烦介绍一下组织临时搬迁的步骤。|麻烦介绍一下搬迁步骤这句话摘自以前的一张试卷。
我希望你具体说说怎么验证监控是否正常。|我希望你具体说说怎么验证监控是旧讲义上印的一句话。
为什么检查发现问题后没有立即停用。|为什么发现问题后没有停用是那份历史档案里记录的提问。
讲一下那次你主动寻求帮助的过程。|讲一下寻求帮助的过程这段文字来自已经结束的培训。
你再把收费标准如何解释给客户的事展开一点。|你再展开一点是我读的旧访谈原句，并非此时向你提出请求。
给我看一个你如何排列处理顺序的具体例子。|这份去年题库中有一句给我一个排列顺序的例子，我只在读题库。
先讲行李核查这一部分，别讲旅客背景。|行李核查这一部分现在不要讲，等我给出完整情况。
先不解释地理位置，直接说你如何安排巡回检查。|我暂时不需要巡回检查的说明，这个要求取消。
不用讲这次成功的，讲一个你处理失败的经历。|不用讲了，包括失败经历也暂时不需要解释。
无需完整故事，只说你怎么确认申请已经受理。|你还不用回答，等我确认到底是哪份申请。
请介绍没有足够人手时如何分派搬运任务，尤其。|请介绍你怎么，先别答，我还没说具体做什么。
解释你为什么把易碎物品分开放，考虑到。|解释你为什么把，具体物品和动作都还未说明。
说说两队都要用同一间教室时如何安排，假设。|说说发生这件事你会怎么做，但这件事的内容我还未交代。
请比较先维修后付款和先付款后维修，主要从。|请比较第一个和第二个，我还没给出它们是什么。
我想知道你如何核验外来维修人员身份，重点是。|我想知道那个对象是否，至于对象是谁我还没有说。
你怎么安排临时增加的配送订单，尤其当。|你怎么安排，我要你安排的事情马上才开始说。
'''

# Identical current fragments with different dialogue establish that the model
# must resolve intent from context, rather than learn a current-text keyword.
CONTEXTS=[
 ('第二步再具体一些','我先登记物品，第二步核对领用人，再让他签字。','我正在逐字读一条旧批注，接下来的原文是：'),
 ('那没登记的呢','已经登记过的人可以直接在窗口领取。','我给以前的问题起了一个短标题，标题是：'),
 ('如果没人接','我们用电话向夜班负责人确认。','我在引用一个过去培训脚本中的追问：'),
 ('你自己做的那部分','我提出了校验方式，同事完成了界面。','我正在念去年采访里对方说过的一句话：'),
 ('第一轮我还没听够','第一轮我们发现门锁和记录不一致，后来更换了门锁。','这是一条已经解决的旧反馈，我在原样复述：'),
 ('那张已经签过字的','还没签字的清单可以重新打印。','我在给旧照片命名，照片名称为：'),
 ('为什么先做这个','我们先暂停售票，再向大家解释安排。','我只是在读过期的试题卡，卡上写着：'),
 ('没有授权的话','系统会先确认这个人有领取权限。','我正在回顾之前的谈话，接下来是对方当时的原话：'),
 ('The step before that.','I called the duty manager and then closed the entrance.','I am copying the title of an old diagram; its title is:'),
 ('If the receipt is missing.','We inspect the receipt before handing over the package.','I am quoting a heading from the archived exercise:'),
 ('Your part in the inspection.','Two of us inspected the kitchen and a supervisor signed it off.','I am reading a title on a past assessment form:'),
 ('The first attempt needs more detail.','Our first attempt to move the cabinet failed, and we changed the plan.','I am repeating a historical comment that has already been addressed:'),
 ('And without a spare.','We would use the spare cable to restore the connection.','These are the final words on the old question card:'),
 ('Why that person.','We asked the maintenance supervisor to review the fault.','I am reading a chapter title from a book:'),
 ('The number before you corrected it.','After counting again, I entered the corrected number.','I am copying the name of a column in an old worksheet:'),
 ('What if nobody signs.','We keep the signed form as proof of delivery.','This is a line from a past interview, which I am quoting:')]

def main():
    p=argparse.ArgumentParser()
    for n in ['previous','older','holdouts','audio','development_audio','runtime','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen data')
    read=lambda f:json.loads(f.read_text());old={s:read(a.previous/(s+'.json')) for s in ['train','calibration','development','acceptance','regression']}
    extra=[]
    for i,line in enumerate(CONTRASTS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:extra.append(case(f'v20-pragmatic-{i}-{int(label)}',f'v20-pragmatic-{i}',text,label))
    for i,(text,yes,no) in enumerate(CONTEXTS):
        for label,previous in [(True,yes),(False,no)]:extra.append(case(f'v20-context-{i}-{int(label)}',f'v20-context-{i}',text,label,[turn('You' if label else 'Them',previous)]))
    assert len(extra)==96 and sum(r['respond'] for r in extra)==48
    rng=random.Random(20261103);replay=read(a.older/'train.json');pairs=[]
    previous_pairs=[replay[i:i+2] for i in range(0,len(replay),2)]
    for label in [True,False]:pairs.extend((x,y,'broad_native_replay') for x,y in rng.sample([z for z in previous_pairs if z[0]['respond']==label],128))
    # Keep every newly authored V18 pair to avoid losing its fulfilled-request
    # distinctions, but do not duplicate its replay selection.
    for i in range(0,len(old['train']),2):
        x,y=old['train'][i:i+2]
        if x['pair_kind'].startswith('new_'):pairs.append((x,y,'v18_new_replay'))
    for i,c in enumerate(old['acceptance']+extra):
        cap=variant(c);pairs.append((c,cap,'short_format_equivalence'));pairs.append((c,history(cap,i,'-pragmatic-history'),'joint_long_format'))
    by_id={c['id']:c for c in old['acceptance']};audio=[]
    for i,r in enumerate(read(a.audio)):
        c=copy.deepcopy(by_id[r['id']]);assert c['text']==r['spoken'] and c['respond']==r['respond'];c['text']=r['text'];c['id']+='-v20-native';audio.append(c)
        pairs.append((c,history(c,i,'-pragmatic-history'),'native_asr_long'))
    rng.shuffle(pairs);train=[];ledger=[]
    for i,(x,y,kind) in enumerate(pairs):
        assert x['respond']==y['respond']
        for suffix,r in [('base',x),('variant',y)]:
            r=copy.deepcopy(r);r['source_id']=r['id'];r['id']=f'v20-pair-{i}-{suffix}';r['pair_id']=i;r['pair_kind']=kind;train.append(r)
        ledger.append(dict(pair_id=i,source_id=x['id'],label=x['respond'],kind=kind))
    dev=copy.deepcopy(old['development']);captions={r['id']:r for r in read(a.development_audio)}
    for c in read(a.holdouts/'development.json'):
        native=captions[c['id']];assert native['spoken']==c['text'] and native['respond']==c['respond'] and native['context']==c['context']
        for group,text in [('chinese_text',c['text']),('chinese_asr',native['text'])]:
            short=copy.deepcopy(c);short['text']=text;short['id']+='-'+group;short['context_condition']='short';short['development_group']=group
            dev.extend([short,history(short,0,'-saturated')])
    assert len(captions)==64 and len(dev)==1024
    final=read(a.holdouts/'acceptance.json');protected={normalized(r['text']) for r in old['calibration']+dev+final}
    assert not protected.intersection(normalized(r['text']) for r in train)
    sets=dict(train=train,calibration=old['calibration'],development=dev,acceptance=final,regression=old['regression']+old['acceptance']+audio+extra)
    assert len({r['id'] for r in sets['regression']})==len(sets['regression'])
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=copy.deepcopy(read(a.previous/'manifest.json'))
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),counts=dict(new_semantic=len(extra),exposed_final=160,native_captions=len(audio),pairs=len(pairs)),
        augmentation='Offline Chinese pragmatic minimal contrasts and identical-current-text contextual pairs; balanced broad replay; all exposed native captions; no runtime normalization or rules.',
        selection_data_policy='All prior development plus new64 Chinese original/native captions short/long. Every group/context gated before fresh160 final. Lowest development loss across two fixed epochs; unchanged127 calibration only.',splits={})
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
