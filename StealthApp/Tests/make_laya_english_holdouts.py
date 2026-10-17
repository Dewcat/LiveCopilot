#!/usr/bin/env python3
"""Separate V17 English-ASR development and fresh bilingual final fixtures."""
import argparse,datetime,hashlib,json
from pathlib import Path
from make_laya_history_holdouts import build
from review_laya_response_labels import normalized

DEVELOPMENT={
'implicit_request':(True, '''
You have not yet made clear how you knew the account was genuine.
I was hoping for a closer account of your conversation with the inspector.
I still need to distinguish your decision from the decision made by your supervisor.
The link between the unusual reading and your diagnosis is missing for me.
I would appreciate hearing what you did with the incomplete submission.
That leaves me wondering how you established which copy was authoritative.
I need the missing step between the warning and the evacuation.
Your account of the second negotiation still needs a concrete example for me.
'''),
'context_followup':(True, '''
If they had already left the venue?\tWe handed out feedback forms at the exit.
The record that was overwritten.\tWe could reconstruct most of the records from the journal.
Your decision before the committee met.\tI proposed a change and the committee later approved it.
And if the permit expired that morning?\tWe verify the permit before loading the truck.
How did you decide between those two?\tThere were two locations available for the workshop.
The person who could not attend.\tEveryone at the demonstration was asked to sign the checklist.
What made you reject the smaller one?\tWe considered two rooms and booked the larger room.
If nobody could read that language?\tThe supplier sent the instructions in a single language.
'''),
'asr_request':(True, '''
ID LIKE YOU TO EXPLAIN THE DISAGREEMENT ABOUT THE HANDOVER
you still havent said how the wrong address was discovered
what did you learn from the test that lost its connection
I NEED MORE ABOUT HOW YOU NOTICED THE MISSING SIGNATURE
im curious how you knew the gate was actually closed
the part about your own repair is not clear to me yet
CAN YOU DESCRIBE WHAT HAPPENED BETWEEN THOSE TWO CALLS
how did you make sure the operator understood the warning
'''),
'clear_intent_fragment':(True, '''
Explain how you handle a damaged shipment particularly when
Compare a printed checklist with a digital checklist starting from
How would you confirm that every participant received the notice assuming
Tell me about resolving a dispute over responsibility with emphasis on
Why did you keep a duplicate of the signed form especially
Describe how you organized the evacuation before we move to
What would you do if two clients booked the same slot for example
Explain how you checked the translated instructions focusing on
'''),
'reported_only':(False, '''
I am reading an old interview that asked why the handover took so long.
How did you check the address is a chapter title in the archived notes.
The retired inspector once asked the previous manager for a fuller account.
That historical questionnaire contains a request to compare the checklists.
I am copying her past remark about wanting to hear the missing step.
The request for your own example was made in a discussion that has already ended.
Please describe the evacuation appears as a heading on this old worksheet.
I am quoting what a customer asked last winter rather than asking you now.
'''),
'withdraw_or_wait':(False, '''
Wait for me to finish the location details before you give an answer.
Do not respond to the checklist comparison because I have withdrawn it.
I no longer want the example about the inspector so leave it there.
Let me complete the question and I will tell you when to begin.
Stop explaining that point while I correct the dates.
Keep your answer for later because I have not finished the conditions.
The request to explain the duplicate is cancelled.
Please just listen until I explicitly ask for your response.
'''),
'essential_intent_missing':(False, '''
Could you take the thing I have not described and put it in the place I have not named.
I would like your view on a subject I still need to introduce.
Which of the choices I have not listed would you
How would you deal with a situation I have yet to describe.
I want you to compare two things but neither has been identified yet.
Can you tell me whether the statement I am about to read is
Please perform the operation whose name I will give in a moment.
I have not given the task itself yet and it concerns
'''),
'narration_or_ack':(False, '''
I am only noting the sequence you have already explained.
The extra detail has filled the gap in my notes and I need no more.
I can now distinguish what you did from what your supervisor did.
I checked the address myself before sending out the form.
I am recording your explanation of the warning rather than requesting another one.
That is the whole account of my conversation with the inspector.
I had wanted a closer explanation but the one you just gave is sufficient.
I understand the reason for the duplicate now, thank you.
''')}

FINAL={
'implicit_request':(True, '''
最开始那次尝试我还没听清过程
你怎么从那个现象想到要换方法，这里我没跟上
我想弄明白你在这次恢复中到底承担了哪一步
关于你如何确认客户同意，我还缺些细节
你说质量提高了，可我没听到判断质量的依据
第一场讨论和最终决定之间的变化，我比较想了解
如果讲一个你实际处理的失败案例，我会理解得更清楚
你略过的测试准备恰好是我想听的部分
我还不知道那次临时加班是怎样决定的
这段只描述了现象，我还想知道你怎么找到原因
The earliest attempt still needs a fuller explanation from you.
I have not followed the connection between that symptom and your change of method.
I want to understand exactly which recovery step you personally owned.
Your way of establishing the customer's agreement is still unclear to me.
You say quality improved but have not told me how you judged it.
I am interested in what changed between the first discussion and the final choice.
An actual failure you dealt with would make this easier for me to understand.
The preparation you skipped is precisely the part I wanted to hear.
I still do not know what led you to arrange that extra shift.
You have described the symptom but I am waiting to hear how you found the cause.
'''),
'context_followup':(True, '''
那封已经寄出的通知呢\t草稿阶段我们可以随时更改活动时间。
假如门口的设备离线\t访客到门口后扫描二维码登记。
你自己负责审核的那部分\t这份报告由几个人共同审核后发出。
如果两个人同时改它\t成员可以直接编辑共享表格。
那个没通过的选项\t三个候选工具里有两个进入了下一轮。
后一批也赶不上呢\t我们打算把缺的零件放在下一批送来。
如果现场找不到负责人\t工作人员通常向现场负责人确认安排。
你改变主意之前的证据\t开始我支持甲方案，后来转向了乙方案。
那台从未联网的机器\t我们通过网络给设备更新配置。
别人没有你那些经验的话\t我凭过去的经验很快排除了错误位置。
What about the notice that has already been mailed?\tWe can change the event time while the notice is a draft.
If the device at the entrance is offline?\tVisitors scan a code at the entrance to register.
The review that you personally handled.\tSeveral people reviewed the report together before it was released.
If two people edit it at once?\tMembers can edit the shared sheet directly.
The option that did not make it through.\tTwo of the three tools went on to the next round.
What if the following shipment is late as well?\tWe plan to include the missing parts in the next shipment.
With no coordinator available on site?\tStaff normally confirm the arrangement with the site coordinator.
The evidence before you changed your mind.\tI supported the first plan initially and later preferred the second.
The machine that has never been connected.\tWe send configuration updates over the network.
Without the experience you had?\tMy earlier experience helped me rule out the wrong location quickly.
'''),
'asr_request':(True, '''
ID LIKE MORE ABOUT THE STEPS YOU TOOK TO RESTORE ACCESS
what made you decide the first result could not be trusted
YOU STILL HAVENT EXPLAINED WHY THAT EXTRA MEETING WAS NEEDED
im trying to understand how you identified the wrong version
can you explain your own role in dealing with the interruption
THE CONNECTION BETWEEN THE ERROR AND YOUR NEXT STEP IS STILL MISSING
tell me what you checked before letting the work continue
how did you find out that the instructions had not arrived
I WOULD APPRECIATE AN EXAMPLE OF YOUR OWN DECISION
what did you do when the two measurements gave different answers
嗯我更想知道那个权限到底是怎么恢复的
你当时怎么判断第一份结果不能用
你还没说为什么一定要多开那场会
我想把那个版本搞错的原因听明白
这次中断你自己负责处理什么
报错之后你做的第一步我还没听到
你让他们继续干之前检查了哪些东西
你怎么发现对方没有收到操作说明
能给我一个你亲自做决定的实际例子
两次测量对不上你后来采取了什么办法
'''),
'clear_intent_fragment':(True, '''
解释你怎样确认权限恢复成功，尤其当
比较先发通知再升级和先升级再通知，主要从
你怎样分配同一时间出现的几项紧急工作，比如说
讲讲你独立处理一次系统中断的经历，先谈那
为什么你保留了未采用的那份设计，特别是
介绍你如何让第一次操作的人完成任务，假设他
你怎样证明测试覆盖到了真正的风险，考虑到
请描述你怎么和持不同意见的人达成决定，尤其
解释你为何在发布前重新检查数据，从那个
说说收到互相矛盾的报告时你会怎么查，先从
Explain how you verify that access has been restored particularly when
Compare notifying people before an upgrade and notifying them afterwards focusing on
How do you allocate several urgent tasks that appear together for example
Describe a system interruption you handled independently starting from
Why did you keep the design that was not selected especially
Explain how you help a first time operator complete the task assuming they
How do you demonstrate that a test covers the real risk given
Describe reaching a decision with someone who disagrees particularly
Explain why you rechecked the data before release beginning with
How would you investigate contradictory reports starting with
'''),
'reported_only':(False, '''
这是去年访谈的摘录，其中有人问怎样恢复访问权限
那本旧手册的练习标题是比较升级前后发通知的区别
我是在引用当年的提问，原话是为什么保留这个设计
已经结束的会议记录里写着还想听更多测试细节
这段话是她当年向另一位同事要解释，不是我在问你
我在抄旧题库里关于处理系统中断的问题
请说明发布之前检查了什么是这页旧教材的标题
那封过期邮件里，客户曾要求讲清楚测量差异
这里记录的是以前有人想了解紧急任务分配
这句给我讲个实际例子来自过去的培训录像
This is an extract from last year's interview about restoring access.
The old manual has an exercise titled comparing notices before and after an upgrade.
I am quoting a past question about why the design was retained.
The minutes of the completed meeting record a wish for more testing detail.
She was asking another colleague for an explanation back then; I am not asking you.
I am copying the interruption question from an old exercise collection.
Please explain the checks before release is the title on this old course page.
In that expired email a customer had requested an account of the measurement difference.
This records someone's earlier interest in how urgent tasks were assigned.
The words give me a real example come from a past training recording.
'''),
'withdraw_or_wait':(False, '''
恢复权限那个问题先别回答，我还要改一下场景
我刚才让你讲中断处理的要求取消了
现在不用比较通知顺序，等我把对象说完
关于测量差异先到这里，不再追问
请继续听我把条件讲完，暂时别开始组织答案
让你举例的那句话我收回，不需要例子了
先别接话，我还没讲完谁在使用这个系统
这次你只要听，等我说可以回答了再答
我暂停发布检查这个话题，先不需要补充
那份设计不用你解释了，我已经找到原因
Do not answer the access question yet because I am changing the scenario.
My request for the interruption account has been cancelled.
Hold the notification comparison until I have finished naming the participants.
Leave the measurement difference there; I am not asking for any more.
Keep listening to the conditions and do not start your answer for now.
I withdraw the request for an example and no longer need one.
Do not jump in while I am still describing who uses the system.
Just listen this time until I explicitly say you may answer.
I am pausing the release check topic and do not need additions yet.
You need not explain the design because I have already found the reason.
'''),
'essential_intent_missing':(False, '''
请把我还没指定的内容放到我还没指定的位置
我想听你对一个尚未提出的话题的看法
要你判断的具体情况还没告诉你，是这样的
我有一组还没列出来的选项，请从中选
我要你分析的两个对象都还没说，第一个是
请按我还未说明的办法处理一个还未说明的东西
你会怎样应对，我先说明到底是什么状况
我准备给你的条件尚未说出，实际问题接下来才是
请判断这句话是否正确，但我还没把那句话念出来
我需要一个建议，不过建议针对的事情还没提及
Put the content I have not specified in the location I have not specified.
I want your view on a topic that I have not brought up yet.
The particular situation for your judgment has not been described and is
I have a list of options not yet given and want you to pick from it.
Neither subject of the analysis has been stated; the first is
Use an unnamed method on an object I have yet to identify.
How would you respond, let me explain what the situation actually is first.
I have yet to supply the conditions and the actual question comes next.
Judge whether the following statement is correct but I have not read it out yet.
I need a recommendation but have not said what it concerns.
'''),
'narration_or_ack':(False, '''
你给的权限恢复说明已经解决了我的疑问
通知先后的区别我现在清楚了，不用重复
我是在记录那次中断的经过，没有提出新问题
第一份结果不可信的原因我自己找到了
我当时先暂停了任务，然后检查连接
这就是我负责的部分，已经讲完了
关于两个测量的差异，你刚才已经说得足够清楚
我原来想问设计，现在看资料已经明白了
我把你刚才介绍的检查步骤记下来
不用再举例，这个案例已足够说明问题
Your explanation of the access recovery has resolved my concern.
The notification order is clear to me now and needs no repetition.
I am noting the interruption account without raising another question.
I found the reason the first result was unreliable on my own.
At the time I suspended the task and then checked the connection.
That is the part I owned and I have finished describing it.
You have already explained the two measurements clearly enough.
I had a question about the design but the document has now answered it.
I am writing down the checks you just described.
No further example is needed because this one explains the issue.
''')}

def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to replace frozen holdouts')
    used=set()
    for folder in a.previous:
        assert folder.is_dir(),folder
        for f in folder.glob('*.json'):
            rows=json.loads(f.read_text())
            if isinstance(rows,list):used.update(normalized(r['text']) for r in rows if isinstance(r,dict) and 'text' in r)
    groups=dict(development=build('english-dev',DEVELOPMENT),acceptance=build('english-final',FINAL));keys=[];report={}
    for split,rows in groups.items():
        expected=64 if split=='development' else 160
        assert len(rows)==expected and sum(r['respond'] for r in rows)==expected//2
        current=[normalized(r['text']) for r in rows];assert len(set(current))==len(rows)
        assert not used.intersection(current),used.intersection(current)
        assert not set(keys).intersection(current),set(keys).intersection(current)
        keys.extend(current)
    a.out.mkdir(parents=True)
    for split,rows in groups.items():
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        report[split]=dict(count=len(rows),positive=sum(r['respond'] for r in rows),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    report.update(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),model_scores_seen=False,
        annotation='Current understandable response intent is positive without syntactic completeness. Actual quoted/history-only, explicit wait/withdrawal, answered acknowledgements and essential unknown tasks are negative. Single annotator synthetic benchmark.',
        policy='New English real-ASR development is separately gated short/long before touching final. All160 final original/ASR texts receive short/long evaluation, with frozen labels and no exclusions.',
        disjoint_from=[str(p) for p in a.previous])
    (a.out/'pre-score-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
