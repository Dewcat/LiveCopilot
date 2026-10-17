#!/usr/bin/env python3
"""Offline V12 augmentation. No text transformation is added to inference.

Expose the previous final as regression, add pragmatic intent contrasts and
label-preserving caption typography. New final remains entirely out of training.
"""
import argparse, copy, datetime, hashlib, json, random, re, sys, unicodedata
from pathlib import Path
from make_laya_finetune_data import case, turn, worker_module
from review_laya_response_labels import normalized

# Each row is an independently phrased response invitation and a no-response
# contrast, not a runtime pattern or a topic-substitution classification rule.
PAIRS = '''
你刚提了一下交接，我对那一段还没有画面|交接那一段我已有完整画面，不必再说
我希望能听到你决定改变方向的瞬间|我决定改变方向的那一刻，接下来我自己讲
你的解释让我没弄明白是哪个环节先出错|你的解释已经让我弄明白了最先出错的环节
关于那个人的反对意见，我还想听更多|关于那个人的反对意见，我已经了解够了
你从发现异常直接跳到修好了，中间还有一段没说|你从发现异常到修好的过程已经说清，我记住了
你把这段压得太短，我还没听出你做了什么|这段压得很合适，我知道你做了什么了
只报一个结果无法看出你的思考，我想听过程|我报这个结果只是为了记录，不是在向你提问
这一步我需要你拿一次真实经历来说明|这一步我会拿自己的真实经历来说明，你先听
第一段先别过去，我还想了解当时的处境|第一段可以过去了，当时的处境我了解了
我仍然不清楚你为什么宁可多花这笔钱|我先前不清楚原因，刚才听完已经知道了
你个人如何拍板的部分还没有讲|我个人如何拍板的部分，我现在自己补上
我更想听到是你亲眼看到什么才这样判断|我已经听到你的观察，没有需要接着问的
这里如果能听到一次失败的经历，会更容易懂|这里那次失败的经历我听懂了，先停在这
从你的描述里我还拼不出完整的操作顺序|我已经从你的描述里拼出了完整的操作顺序
我希望你把刚才略过的两个步骤接起来|我会自己把文稿里略掉的两个步骤接起来
这里还缺从提出假设到验证假设的那部分|我的记录刚才缺了一部分，现在我已自行补齐
我想听个你独立处理的例子，团队成果先放一边|我现在会讲自己独立处理的例子，你不必接话
光讲成功的结果还不够，想听一次卡住的过程|成功的结果已经记好了，其他过程今天不用讲
你怎么应对质疑，我这边还没听见|你怎么应对质疑，我已经听得很清楚了
这个选择说得再实在些我会更好理解|这个选择现在说得很实在，我理解了
对于那次失败，我对过程比结果更感兴趣|对于那次失败，我已经没有想追问的了
你的贡献和别人的贡献这里还是混在一起的，我想区分开|我已经能区分各自的贡献，不用你再分开介绍
只给我结论没法看出你的推理|你给出的结论和推理已经足够了
关于第二次尝试，你说得好像太快了一点|关于第二次尝试，这个说明已经足够
我是想听你说自己的选择，刚才听到的全是团队的|我只是总结刚才听到的是团队的选择，没有新要求
我还没理解为什么第三天才采取行动|我已经理解为什么第三天才采取行动
你给出的名称对我没有帮助，我要知道实际干了什么|我现在已经知道实际做了什么，不再需要解释
你自己遇到的一个小例子就很好|我自己遇到的例子我稍后补充，你先别答
这条因果关系我仍然没看出来|这条因果关系我现在看出来了
我听到了风险，但没有听到你怎么应对它|风险和应对办法我都听到了，够了
如果你能复原一下当时的场面就更好了|我来复原一下当时的场面，你先听
我对最开始的那个误判有点好奇|我曾对那个误判好奇，现在已经弄清了
还有为什么没有尝试另一条路，我也想了解|为什么没尝试另一条路我刚才已解释过
前面那点你一笔带过了，我还等着听详细内容|前面那点已经解释过，我不再等补充内容了
我还在等你交代自己如何做的验证|我已经知道你如何验证，不必再交代
你说得都是背景，我关心的决定还没听到|你刚才说的背景和决定我都记好了
我期待的是你能举出真正用过的办法|我会自己举出真正用过的办法，暂时不用你讲
如果从你自己的角度再说一次会更好|从你自己的角度已经讲得很清楚了
比起描述系统，我对你具体做过什么更感兴趣|我只是记录你做过哪些工作，没有新问题
你讲完这条路径以后，还需要告诉我另一条为什么不行|另一条为什么不行我已明白，先不讨论
An example of what you actually tried would be welcome.|I have already heard the example of what you tried.
I would be interested in the moment you changed your mind.|I was interested earlier, but that has now been explained.
Your explanation leaves me unsure how the pieces fit together.|Your explanation has made the connections clear to me.
The transition from suspicion to proof needs more detail from you.|The transition is already described in my notes; no more detail is needed.
I still cannot follow the middle of your account.|I can now follow the middle of your account.
I am missing your personal reasoning in that description.|I am adding my personal reasoning to my own description now.
The part about how you convinced them would be worth hearing.|The part about how you convinced them was worth hearing, thank you.
Some context from your actual experience would be useful.|I will provide the context from my own experience; just listen.
That tells me the outcome, but leaves your actions unexplained.|That tells me both the outcome and your actions; I am satisfied.
You have skipped the very step I wanted to understand.|You have now explained the step I wanted to understand.
I would like to see what the decision looked like in practice.|I have seen what it looked like in practice and have no question.
A closer account of the disagreement would help me.|A closer account is already in the document; you need not elaborate.
Your own role seems lost in the team summary.|Your own role is clear from the team summary now.
I am still waiting for your explanation of the last change.|I am no longer waiting; you can leave the last change unexplained.
A description of the actual handoff would make this clearer.|I will describe the actual handoff myself to make this clearer.
There is a jump in your story between the alert and the fix.|There was a jump in the written story; I have corrected it myself.
I have heard the names of the tools but not why you used them.|I have heard why you used those tools and that is sufficient.
I was expecting to hear what you personally observed.|I was expecting that earlier; your last response covered it.
I could use a little more of the process behind that result.|I no longer need any more of the process behind that result.
The account of the failed attempt is what interests me here.|I read the account of the failed attempt and understood it.
I need you to separate your decision from the team's decision.|I will separate my decision from the team's in my own report.
It would help if you brought that back to a concrete incident.|You have brought it back to a concrete incident, which answers me.
Your explanation does not yet show how you found the fault.|Your explanation now shows how you found the fault.
I am not seeing the connection between those measurements and your conclusion.|I see the connection now and have nothing to add.
The missing detail is what happened when the first fix failed.|The missing detail has been supplied; we can move on.
You could make this clearer by describing one actual execution.|You made this clear by describing one actual execution, thanks.
I would like the part about the compromise unfolded a bit.|I no longer need the part about the compromise unfolded.
Your account stops just before the decision I care about.|Your account covered the decision I cared about, so we are done.
I want your interpretation of the evidence, rather than another label.|I will offer my interpretation of the evidence myself.
The explanation should include the alternatives you rejected.|The explanation already includes the alternatives you rejected.
'''

CONTEXTS = '''
你漏掉的那部分|我讲了准备和最后的结果，中间没有展开。|我在逐字朗读过去的批注，下一句是旧批注不是当前请求。
更早的那个|我刚说了两次失败，较早一次是我独立处理的。|我在回答自己记事本里的选项，下面是我的选择。
还是最开头那一小节|我可以接着讲后半，也可以再讲开头，你想听哪个？|我在说明自己校对到了哪里，下一句只标记位置。
不是工具名称，是你怎么用的|我刚才只列出了用过的工具名称。|我在念以前的一条评语，下一句不要求你回应。
你在里面的作用|团队最终交付了两个模块，我还没说自己的职责。|我在读一份去年访谈的章节标题，并不是向你提问。
剩下的细节我还想听|我刚说了第一步，后面还有两步，你需要我接着说吗？|下面我念一下旧录音里对方当时说过的原话。
你自己能改变的那一点|有些约束是组织决定的，也有些由我决定。|下一句是我抄录的旧题目，当前没有请求。
前一种的限制|我刚介绍了两种办法，但只讲了后一种的限制。|我在复述旧问卷中的一个栏目名称，不需要你回答。
The part you left out.|I covered the setup and outcome but skipped the middle.|I am quoting an archived comment next, not asking you anything.
The earlier attempt.|There were two failed attempts. Which should I describe?|I am reading out my own selection from an old list, not requesting a description.
Your own decision.|I have only described what the committee decided.|The next line is the heading of an old interview note, not a live request.
The mechanism rather than its name.|I just named the algorithm we used.|I am now quoting feedback I received years ago, not posing a question.
More of the first section.|I can go over the first section again if you would like.|I am about to read a line from a completed interview verbatim.
The reason it took that long.|The migration took four weeks.|I am merely naming a section in an archived report.
The bit you handled alone.|We shared some tasks and I handled another part alone.|I am quoting an old interview prompt without requesting an answer.
The other direction.|I described how we transfer data from A to B.|I am correcting my own statement about where I was walking.
'''

ASR = '''
why did we choose method be and what is its lenc|1
WHY DID WE CHOOSE METHOD BE AND WHAT IS ITS LENC|1
why did we choose method b and what is its latency|1
WHAT IS THE REASON FOR THE EXTRA RE TRY AND HOW LONG DOES IT TAKE|1
can you tell me how the cash in validates itself|1
why did the queue grow so large and how did you bring it back down|1
what did you do when the first re quest timed out|1
how would you compare a full re load with an incremental one|1
COULD YOU GIVE AN EXAMPLE OF A ROLL BACK THAT FAILED|1
I WANT TO KNOW HOW YOU CONFIRMED THE RE COVERY|1
you mentioned two checks i still dont understand the first|1
what do we lose if we drop the second check and|1
I HAVE NOT HEARD HOW YOU RE COVERED THE DATA|1
please walk me through why the back up stopped responding then|1
he asked why did we choose method be and what is its lenc last year|0
WHY DID WE CHOOSE METHOD BE AND WHAT IS ITS LENC IS AN OLD QUOTED QUESTION|0
I WILL EXPLAIN THE EXTRA RE TRY MYSELF|0
we saw the cash in validate itself in the trace|0
the queue grew so large that we had to restart it|0
I AM RECOUNTING HOW HE ASKED WHAT HAPPENED WHEN THE FIRST RE QUEST TIMED OUT|0
the notes say could you give an example of a roll back that failed|0
DO NOT ANSWER ABOUT THE RE COVERY UNTIL I FINISH THE SCENARIO|0
I NO LONGER NEED TO KNOW ABOUT THAT CHECK|0
I WANT YOU TO TAKE THE NOT YET NAMED ITEM AND|0
DO NOT EXPLAIN THE BACK UP YET I AM STILL TALKING|0
how you confirmed the recovery was the old chapter heading|0
'''


def caption(text, mode):
    # Offline typography only. Keep words intact, remove punctuation and vary
    # case as real ASR engines do. Never truncate a semantic word or negation.
    s=''.join(c for c in text if not unicodedata.category(c).startswith('P'))
    s=re.sub(r'\s+',' ',s).strip()
    return s.upper() if mode=='upper' else s.lower()


def extras():
    rows=[]
    for i,line in enumerate(PAIRS.strip().splitlines()):
        yes,no=line.split('|')
        for label,text in [(True,yes),(False,no)]:
            rows.append(case(f'v12-pragmatic-{i}-{int(label)}',f'v12-pragmatic-{i}',text,label))
    for i,line in enumerate(CONTEXTS.strip().splitlines()):
        text,yes,no=line.split('|')
        for label,prior in [(True,yes),(False,no)]:
            rows.append(case(f'v12-context-{i}-{int(label)}',f'v12-context-{i}',text,label,[turn('You' if label else 'Them',prior)]))
    for i,line in enumerate(ASR.strip().splitlines()):
        text,label=line.rsplit('|',1)
        rows.append(case(f'v12-asr-{i}',f'v12-asr-{i}',text,label=='1'))
    return rows


def long(row, label):
    c=copy.deepcopy(row);c['id']+=label
    c['context']['recentTurns']=[turn('Them' if i%2 else 'You',('能讲一下上一次记录校验吗？这个问题已处理。' if i%2 else '上一次校验已经讲完，记录已归档。')*17,bool(i%2)) for i in range(40)]+c['context']['recentTurns']
    return c


def main():
    p=argparse.ArgumentParser()
    for name in ['previous','holdouts','audio','runtime','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen data')
    rng=random.Random(20261027)
    old={s:json.loads((a.previous/(s+'.json')).read_text()) for s in ['train','calibration','acceptance','regression']}
    new=extras();exposed=copy.deepcopy(old['acceptance'])
    for c in exposed:c['training_provenance']='V11 final already scored; known training/regression from V12.'
    fixtures={c['id']:c for c in old['acceptance']}
    audio=[]
    for row in json.loads(a.audio.read_text())['rows']:
        c=copy.deepcopy(fixtures[row['id']]);c['text']=row['asr'];c['id']+='-asr';c['category']='known_native_asr';audio.append(c)
    originals=old['train']+exposed+audio+new
    # Preserve all old examples and add a stratified, reproducible distribution
    # of caption-like variants. Positives AND negatives receive augmentation.
    buckets={}
    for c in originals:
        k=(c['respond'],bool(re.search('[A-Za-z]',c['text'])),len(c['context']['recentTurns'])>10)
        buckets.setdefault(k,[]).append(c)
    variants=[]
    for key,rows in sorted(buckets.items()):
        sampled=rng.sample(rows,min(len(rows),400 if key[1] else 300))
        for j,c in enumerate(sampled):
            r=copy.deepcopy(c);r['id']+='-caption';r['text']=caption(c['text'],'upper' if j%2 else 'lower')
            for t in r['context']['recentTurns']:t['text']=caption(t['text'],'upper' if j%2 else 'lower')
            if r['text']!=c['text'] or r['context']!=c['context']:variants.append(r)
    # Every new semantic contrast is also taught in the exact ASR surface.
    for j,c in enumerate(new):
        r=copy.deepcopy(c);r['id']+='-new-caption';r['text']=caption(c['text'],'upper' if j%2 else 'lower')
        for t in r['context']['recentTurns']:t['text']=caption(t['text'],'upper' if j%2 else 'lower')
        variants.append(r)
    augmented=originals+variants
    for label in [False,True]:
        eligible=[c for c in new+variants if c['respond']==label and len(c['context']['recentTurns'])<10]
        augmented.extend(long(c,'-saturated') for c in rng.sample(eligible,min(96,len(eligible))))
    # Reject conflicting labels on identical actual observable states.
    seen={};train=[]
    for c in augmented:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen:
            assert seen[key]==c['respond'],c['id'];continue
        seen[key]=c['respond'];train.append(c)
    rng.shuffle(train)
    dev=json.loads((a.holdouts/'development.json').read_text())
    for label in [True,False]:
        dev.extend(long(c,'-long') for c in [r for r in dev if r['respond']==label][::4][:16])
    final=json.loads((a.holdouts/'acceptance.json').read_text())
    protected={normalized(c['text']) for c in old['calibration']+dev+final}
    assert not protected.intersection(normalized(c['text']) for c in train)
    regression=old['regression']+exposed+audio+[c for c in new if c['family'].startswith('v12-asr-')]
    sets=dict(train=train,calibration=old['calibration'],development=dev,acceptance=final,regression=regression)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    manifest=dict(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),context_tokens=1024,threshold=.8,question=worker.QUESTIONS,long_context_stride=1,
        acceptance_gate=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True),
        development_scope='independent_selection',provenance='Local synthetic authored samples plus exposed V11 examples; no recordings or paid API.',
        augmentation='Implicit pragmatic contrasts; same utterance in answer vs quotation context; offline punctuation/case variants; known actual ASR captions. No runtime transformations.',
        selection_data_policy='New development only for checkpoint selection. New final frozen before data preparation; never read by trainer. V11 final explicitly exposed training/regression.',
        annotation_limit='Single annotator synthetic engineering fixtures; no claim of population accuracy.',splits={},counts=dict(previous_train=len(old['train']),exposed_final=len(exposed),known_audio=len(audio),new_semantic=len(new),caption_variants=len(variants)))
    a.out.mkdir(parents=True)
    for split,rows in sets.items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        d=a.out/(split+'.jsonl');d.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(d.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest,ensure_ascii=False,indent=2))

if __name__=='__main__':main()
