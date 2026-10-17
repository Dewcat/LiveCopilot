#!/usr/bin/env python3
"""New authored V12 holdouts, frozen before training; no model-assisted labels.

Tabs separate current text from the preceding turn; negative quotation contexts
belong to the external speaker, positive answer contexts to the listener.
"""
import argparse, datetime, hashlib, json
from pathlib import Path
from make_laya_finetune_data import case, turn
from review_laya_response_labels import normalized

FINAL = {
'implicit_request': (True, '''
开头提到的那次转折，我有兴趣再听一些
讲到你接手以后就跳过去了，这里我还跟不上
你的介绍还缺你当时作出判断的过程
光有最终排名，我看不出你怎么选出来的
这一段如果能还原成当时的对话就更好了
我期待听到的其实是你遇到阻力时的反应
第二部分对我来说还是有点抽象
你在里面具体做了哪些事，我这里还没听明白
我更在意你没采用的几条路线
听到这里，我仍不清楚第一次尝试为何没有奏效
还欠缺一次真实执行的例子
关于审核人的异议，我希望得到更具体的解释
从准备到落实之间的空白还需要你填上
如果你能把个人贡献单独拎出来会更清楚
这项结论背后的那次观察，我挺想了解
我还在等你说出最终改变主意的契机
I'd appreciate a slower walk through the decision you just skipped.
There is still a gap in your account of the recovery.
Your own intervention is the bit I am interested in.
A worked example from you would make this less abstract.
I cannot yet see what led you to reject the obvious option.
The explanation could use your actual observations.
I was hoping for the circumstances behind that change of plan.
More about the first unsuccessful attempt would help me.
You have left the crucial handover unexplained.
'''),
'context_followup': (True, '''
前面那个怎么落地\t我考虑过让门店自己录入，也考虑过总部统一导入。
那一次之后呢\t我们第一次演练发现了三处缺陷。
要是两个人都没接电话\t我们先找主值班员，联系不上就找备班。
已经排进去的怎么办\t关闭入口以后，不再接收新的预约。
你拿什么说服他们\t两个合作团队当时都不愿意改变接口。
中途换负责人的话\t整个验收由同一位负责人跟进到结束。
这个顺序能倒过来吗\t先锁住库存，再发送确认消息。
我想回到你第一次作判断的时候\t我刚才概括了从观察到决策再到验证的三段过程。
那手工操作的部分\t大多数记录都会自动核对。
轮到第二位提出反对意见的时候\t第一位评审同意了，第二位提出了反对意见。
剩下的那条路呢\t有两条路线可走，我刚才只说了直接迁移。
你对这个负责到哪一步\t这个项目由我和另外两位同学一起交付。
And when both replicas are stale?\tWe read from the backup when the primary cannot be reached.
The reason for trying again.\tOur first two experiments did not give a usable result.
What changed their mind in the end?\tThe support team initially refused to adopt the workflow.
The bit after approval.\tWe prepared the request, got approval and handed it over.
With only one operator on duty?\tThe usual process assigns one person to each of three stations.
How did you narrow it to that one?\tAt first we had five plausible explanations for the outage.
And the requests already waiting?\tDuring maintenance we stop admitting new requests.
I meant your decision, not the committee's.\tI just described the decision taken by the whole committee.
'''),
'asr_request': (True, '''
COULD YOU TAKE ME THROUGH THE PART YOU BUILT YOURSELF
why was the second trial so much slower than the first
WHAT MADE YOU PICK THE SMALLER BATCH SIZE
um so how did you know the queues had drained
can you describe the fall back when the primary dies
I WOULD LIKE THE REASON YOU RE TRIED THAT STEP
what would you do if the clock on the client was wrong
HOW DID YOU ESTIMATE THE MEMORY NEEDED FOR THIS JOB
could you tell me why the read replica lagged so far be hind
what were you responsible for during the cut over
I DIDNT CATCH THE BIT ABOUT HOW YOU CHECKED IT
and how would that work if there were no net work
刚开始你提的那个判断我还想再听听
嗯你把上线以后发现的问题说细点
如果两个服务同时掉线你打算先恢复谁
你当时怎么知道数据已经传完我想听过程
刚才那个超时你是怎么订出来的
你个人参与的那段能不能从头过一下
我想听一下你怎么权衡速度跟准却率
那对方没回消息你后来怎么接着推进的
'''),
'clear_intent_fragment': (True, '''
谈谈你怎样给实验排优先级，先说那个
给我讲一个交付延期的案例，重点在于
出现两条相反证据时你会怎样判断，我的意思
你为什么把校验放在入口，尤其当我们
请你解释一次回滚的全过程，最后还想
挑一次你改变设计的经历讲讲，假设我们
怎样保证轮班交接不丢信息，你先从
你能给我比较一下单人审核和双人审核，主要是
Explain how you found the faulty component especially when
Tell me what you would do with an overloaded worker starting from
Why do you validate the timestamp before processing and then
Describe your response to a missed deadline particularly the
Walk me through an example of conflicting requirements before we
How would you tell whether the recovery succeeded assuming
Give me your reasoning for separating those stages and after
Compare the manual and automatic checks focusing on
'''),
'reported_only': (False, '''
旧表里写的是你接手后改变了什么
他上星期说还想听一次具体失败的经历
会议纪要记着她希望得到更慢一点的说明
为什么选择分批执行是那份问卷上的原题
我在整理过去的提问，其中一道是你为什么坚持这个方案
刚才念的是别人当年的要求，不是现在让我向你提问
这行记录的原话是你自己的贡献我还没听清
那位客户去年希望我们把中间步骤说得更细
旧访谈结束前她问我有没有考虑退出条件
我读一下以前的题目请比较人工核对与自动核对
HOW DID YOU HANDLE THE HANDOVER WAS THE HEADING IN AN OLD INTERVIEW
she asked the previous candidate what made the second test fail
THE ARCHIVE RECORDS SOMEONE ASKING FOR A SLOWER EXPLANATION
can you show your calculations is the sentence I am transcribing
The old checklist contains the prompt describe a difficult decision.
I am recounting how he demanded more evidence last year.
Her recorded question was why did the replica fall behind.
The line I just quoted asked for my contribution, not yours now.
That was a past request for clarification, which I am cataloguing.
I read the old annotation saying the middle step needs explaining.
'''),
'withdraw_or_wait': (False, '''
我又想了一下，这个追问先算了
别接刚才那句，我还在重新组织题目
这次不需要你展开，先听下一位讲
我决定跳过这项，不用给我解释
先别接着答，设备数量还没告诉你
让我先把两个备选方案说完，再轮到你
你先不必回应，刚才那句话我收回
这一段到此为止，剩下的我自己看
等我把最后一个前提补上再开始
停一下我还没给出要对比的另一项
HOLD OFF UNTIL I HAVE FINISHED LISTING THE CONSTRAINTS
please dont answer that follow up I have dropped it
I AM WITHDRAWING THE REQUEST TO EXPLAIN THE FIRST STAGE
wait for the rest of my scenario before you respond
You can leave that point unanswered for today.
Pause your explanation while I correct the premise.
I am not inviting an answer yet; I need to finish the setup.
Cancel my last follow-up and wait here.
Do not jump in now, I still have another condition to state.
No elaboration is necessary; I am dropping this topic.
'''),
'essential_intent_missing': (False, '''
我希望你执行的操作具体叫
将这个对象改成下面这个尚未给出的
请从我即将列出的三个选项里
我这次让你对照的第二份资料是
现在要你回应的那句话还没说是
我要你把这条消息转交给尚未介绍的
请根据我接下来要定义的那个
我要求你先将一个还没说明的东西
能否帮我从下面这些还没列出来的
我的问题到底针对的是接下来这个
THE TASK I WANT YOU TO PERFORM ON THE UNNAMED ITEM IS
please compare the two things that I am about to name first
I NEED YOU TO CHOOSE ONE OF THE FOLLOWING NOT YET LISTED
could you replace this entry with the one I havent identified
The instruction I need you to carry out consists of the following
Send that to the person whose identity I will now give as
What I want you to do next with the unmentioned object is
Please evaluate whichever of these as yet unspecified
The question you should answer is the one that I am about to
'''),
'narration_or_ack': (False, '''
我当时也觉得第一段太简略，后来已经补过了
你这次讲得很具体，我没有别的想问的
我自己先把遗漏的背景交代一下
当时我没听清那句话，回去看记录就懂了
我们的第二次试验用了更小的一批数据
这就是我在这项任务里作判断的经过
我需要更多证据，所以我接着自己查了日志
好的，这个环节可以翻篇了
我会把刚才听到的细节补到自己的笔记里
你不用再讲了，我明白为什么这样安排
I UNDERSTAND THAT PART NOW THANK YOU
we reduced the batch size after the first failed run
I AM ABOUT TO DESCRIBE MY OWN DECISION
that explains the delay I have no further question
I once wanted more detail, but the revised report settled it.
We had already documented the handover by Friday.
I can supply that missing example from my own experience.
Your explanation answers the concern I had earlier.
I have written down the two options you described.
Those were my observations; I am finishing my account here.
''')}

DEV = {
'implicit_request': (True, '''
你说到落地的时候太快了我还没跟上
你具体推动了什么这里仍然不够清楚
我最想听的部分是事情卡住以后的变化
一个真实的故障实例应该能帮我理解
你的个人判断还藏在团队结论里面
前半段的理由对我来说仍是个空缺
我对你如何排除第一个猜想更感兴趣
只听结果还不够我想知道你亲眼看到的情况
I would welcome more on the awkward transition.
The justification for that extra check is still absent.
Your description jumps over the difficult decision.
I am interested in the options you discarded.
Something concrete from your own work would help.
The part about your intervention is not clear yet.
I was expecting a fuller account of the failed attempt.
Your answer has not covered how you knew it worked.
'''),
'context_followup': (True, '''
另一位不同意时\t需要两位负责人签字才可以发放。
那么撤销以后\t我们先接受申请，也允许用户中途撤销。
中间缺人怎么补\t每个时段都需要安排两人值守。
你怎么确认那个猜想\t当时我怀疑是某个锁没有释放。
只有旧版本的现场呢\t测试是在最新固件上运行的。
你自己那半段\t这个任务前半由同事负责，后半由我完成。
还能再省一点吗\t我们最后把内存需求降到了原来的一半。
如果先做第二步\t我们先复制文件，再修改索引。
And if the backup is unavailable too?\tWe switch to the backup when the primary fails.
The explanation for rejecting the first.\tWe tested two options and chose the second.
What happened the day after?\tThe first day ended with an unresolved incident.
Your share of that work.\tThree of us completed the migration together.
What if the connection never returns?\tThe worker waits for the connection to recover.
The check immediately before launch.\tWe validated the files, then ran a check before launch.
And for an existing customer?\tI have described how we onboard a new customer.
How did you persuade the last reviewer?\tThe last reviewer eventually changed her mind.
'''),
'asr_request': (True, '''
HOW DID YOU CHOOSE WHICH RECORD TO RE TRY
could you explain the trade off in that last choice
WHY WAS THE FALL BACK SO MUCH SLOWER
um can you go over your role in the roll out
I WANT TO HEAR HOW YOU SPOTTED THE MIS MATCH
what happens if the request is sent twice by mis take
CAN YOU DESCRIBE YOUR REASON FOR ADDING THE TIME OUT
how did you test the result with out a live server
你再介绍一下当时哪个环节最费劲
最前面的那条路我还想多听点
我想弄懂你为啥在那个地方加锁
如果写到一半突然断电你会怎么补救
你能给个自己处理过的重试案例
那这个响应时间你是用什么来算的
我还想知道你如何判断修复有没有生效
你讲一下这个上限的设置理由
'''),
'clear_intent_fragment': (True, '''
说说你怎么准备值班交接，特别是
请你解释那个报警为什么被忽略，接着我
当用户连续点击时你会怎样处理，假如说
你是怎么查出记录重复的，我主要想
给我一个回归测试的例子，然后说
你觉得一周内能做完吗，考虑到
把那段协调过程展开给我听，从那个
如何决定什么时候停下重试，假设
Explain how you would trace a missing event especially
Give me one example of a difficult rollback before
Why did you choose to validate the file first considering
Tell me how you knew the service had recovered then
How would you split the work with fewer people assuming
Describe a time you revised your plan starting with
Walk me through the approval process and afterwards
Compare retrying with dropping the request focusing on
'''),
'reported_only': (False, '''
她在旧记录里问为什么先做校验
我正在读一段过期的题目叫如何避免数据重复
昨天同事希望我把原因说透
旧评分表上写着个人贡献仍不清楚
那次评审的提问是你如何安排值守
他说想听失败案例我只是转述
我正在抄录一句请把中间步骤展开
以前有人让我解释为什么要加锁
WHY DID YOU WAIT WAS A QUESTION FROM LAST YEARS FORM
I am copying the old request for a more concrete example.
SHE ASKED ANOTHER SPEAKER TO EXPLAIN THE RETRY
he wanted more detail last week I am only recounting it
The historic prompt was how would you divide the work.
The archived interview includes a demand for supporting evidence.
Tell me about the outage is what the earlier speaker said.
I am reading a prior comment that the answer was too general.
'''),
'withdraw_or_wait': (False, '''
先别答我刚才还漏了一个限制
这个问题今天就不问了
我撤销刚才让你多讲一点的要求
你保持等待等我把题干读完
先不用补例子我自己说明
我还要讲第三个选项现在先不要接话
这项追问到此打住不要继续
等一下我把背景说完整再请你答
DO NOT RESPOND WHILE I AM STILL EXPLAINING THE SETUP
please wait until the missing condition has been stated
CANCEL THE REQUEST FOR AN EXAMPLE
hold your answer I havent given you the last option
That follow-up no longer needs an answer.
Please stay quiet until I finish the description.
I will cover this myself, so do not elaborate now.
Wait, I am replacing my question with a different one.
'''),
'essential_intent_missing': (False, '''
我让你选择的具体对象叫作
需要你转换成的格式还没说是
把它交给那个接下来才会介绍的
我真正要你回答的题干是下面这个
请你将尚未提及的那份
请在这两个还未说明的条件中
我希望你执行的是接下来要描述的
需要你评估的对象我还没介绍它叫
THE SPECIFIC ACTION FOR THAT UNNAMED THING IS
please take the as yet unidentified item and
I WANT YOU TO SELECT FROM THE FOLLOWING UNMENTIONED
could you send that to the not yet named
The two unnamed subjects you should compare are
I need you to replace this with the following unspecified
What I want done with that object that I have not described is
The request I will ask you to address is going to be
'''),
'narration_or_ack': (False, '''
你刚才的解释已经把空缺补上了
我曾经也需要更多细节现在懂了
我自己会再检查一遍那个结果
这个判断是我在第二天作出的
谢谢这一部分已经讲得够细
我补充一下自己当时做了什么
我的试验确实少了对照组
我已听明白不用接着解释
I HAVE ALL THE DETAILS I NEED NOW
we only noticed the problem after the second attempt
I WILL EXPLAIN MY OWN ROLE NEXT
that clears up the remaining confusion thanks
My notes already include the missing intermediate step.
I decided to reject the change after reading the logs.
That was the outcome of my own investigation.
We tried the slower route first and then changed the plan.
''')}

def build(name, groups):
    rows=[]
    for category,(label,block) in groups.items():
        for i,line in enumerate(block.strip().splitlines()):
            parts=line.split('\t'); prior=[]
            if len(parts)>1: prior=[turn('You' if label else 'Them',parts[1])]
            r=case(f'robust-{name}-{category}-{i}',f'robust-{name}-{category}-{i}',parts[0],label,prior)
            r['category']=category;rows.append(r)
    return rows

def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite frozen holdouts')
    old=[]
    for f in a.previous.glob('*.json'):
        x=json.loads(f.read_text())
        if isinstance(x,list):old.extend(c for c in x if isinstance(c,dict) and 'text' in c)
    used={normalized(c['text']) for c in old};dev=build('dev',DEV);final=build('final',FINAL)
    assert len(dev)==128 and sum(c['respond'] for c in dev)==64
    assert len(final)==160 and sum(c['respond'] for c in final)==81
    for name,rows in [('development',dev),('acceptance',final)]:
        keys=[normalized(c['text']) for c in rows]
        assert len(keys)==len(set(keys)),name
        assert not used.intersection(keys),(name,used.intersection(keys))
        used.update(keys)
    a.out.mkdir(parents=True)
    for name,rows in [('development',dev),('acceptance',final)]:
        (a.out/(name+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    report=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='New separately authored synthetic single-annotator holdouts; no candidate scoring before freeze.',labels='Intent to receive a useful response now, not grammatical completeness. Mere narration, quoted records, withdrawal and unknown essential task wait.',review='All rows read before scoring. 81/79 final and 64/64 development. No normalized utterance overlaps previous data or each other.',hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.glob('*.json')})
    (a.out/'pre-score-review.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
