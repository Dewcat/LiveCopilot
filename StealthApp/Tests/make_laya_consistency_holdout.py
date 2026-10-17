#!/usr/bin/env python3
"""V15 final, authored and frozen without candidate scores or label selection."""
import argparse, datetime, hashlib, json
from pathlib import Path
from make_laya_history_holdouts import build
from review_laya_response_labels import normalized

FINAL={
'implicit_request':(True, '''
你说的这一跳对我还是个黑箱，我想知道里面发生了什么
我听出了团队的成果，但还没看见你的那份工作
最开始你凭什么相信那个方向，我有些好奇
比起工具名称，我更想了解你真正用它解决了什么
这段如果带上你当时看到的证据，我会更容易跟上
你们从争议到同意的过程，似乎还没展开
这里我还缺一个能从头走通的具体案例
我期待听到你遇到第一处阻力时怎样改变计划
你只说事情后来好了，中间那段我仍然不明白
你省略掉的验收过程恰好是我感兴趣的
I would find it useful to hear what you saw before making that call.
The explanation still skips the point where you stopped trusting the first result.
Your personal part is getting lost in the description of the wider effort.
I am interested in how the disagreement actually ended.
I need a concrete run through the example to follow this part.
You have described the symptoms; the connection to your decision is still missing.
I was expecting more about what you tried when progress stalled.
The description of how you checked the handoff remains rather vague to me.
Some detail about your own investigation would make the story clearer.
The transition from the complaint to the remedy is what I still want to hear.
'''),
'context_followup':(True, '''
如果到场的只有一位\t通常我们会安排两位现场人员交叉核对。
那张已发出去的单子呢\t我们发现错误后可以修改还没有提交的申请。
后来的负责人没参与过怎么办\t每个项目开始时会共同讨论一次风险。
我想听你没有选择的那条路径\t我们评估后选用了把任务拆开的办法。
当时怎么排除另一个解释\t我最后判断问题来自缓存而不是上游。
那段时间里你自己干了什么\t那一周大家分头联系了合作方。
如果确认消息比数据先到\t接收端等数据落盘后发一条确认消息。
最后剩下的那个疑点\t我们一开始有三个怀疑，前两个已经解释了。
换个不熟悉现场的人呢\t平时是熟悉设备的值班员操作。
为什么没按原来的安排\t我们在最后一天更改了验收顺序。
And if neither observer turns up?\tTwo observers normally check each delivery.
The invitations that have already gone out.\tWe can edit an event before publishing it.
What did you personally do during that week?\tThe team split up to contact the partners.
How did you dismiss the other explanation?\tI concluded that the issue came from the cache.
If the receipt arrives before the payload?\tThe receiver sends confirmation after saving the payload.
The remaining doubt you mentioned.\tWe started with three concerns and I have covered the first two.
Why depart from the original schedule?\tWe changed the review order on the last day.
With an operator who has never seen the equipment?\tOur usual operator knows the equipment well.
What stopped you taking the other route?\tWe decided to split the work after considering two approaches.
And if the replacement manager missed that discussion?\tWe discuss the risks at the beginning of each project.
'''),
'asr_request':(True, '''
WHAT DID YOU DO AFTER THE TIME OUT WAS REPORTED
id like more detail on how you tracked down the missing event
WHY WAS IT NECESSARY TO KEEP BOTH RECORDS
can you walk me through what happened during the cut over
I DONT YET SEE HOW YOU KNEW THE RESULT WAS CORRECT
how did you deal with a re quest that was received twice
what made you trust the back up after the first failure
PLEASE EXPLAIN THE PART THAT YOU HANDLED WITHOUT HELP
you mentioned one more inspection what did that add
how would you recover if the ack came too late
嗯你刚说的那个缓存失效具体是怎么检查的
你给我再讲讲为什么两边的数据要分别存
那个问题一直没复现你后来怎么继续查的
你们说已经恢复了你用什么确认这件事
我想听你自己处理的那次返工经过
刚刚跳过的那一步能从你的操作讲起吗
额外等这一会儿到底解决什么我还没弄明白
要是收到的是重复的那条消息你怎么应对
你说做过好几种尝试我想先听失败的那个
你最后怎么确认没有把旧数据盖上去
'''),
'clear_intent_fragment':(True, '''
给我比较一下集中审批和分散审批，先谈那个
解释你为什么保留两份不同版本的记录，尤其遇到
你怎么检查恢复后的数据是不是完整，假设
请讲一次你重新安排人手的经历，重点我想
谈谈你怎样从几个相似故障里确定原因，先从
为什么最后改用分批执行，主要考虑的是
你怎样证明一次改动真的解决了问题，比如当
描述你与别的团队协调冲突的过程，先说那次
比较自动回退和人工回退各有什么代价，接着
请说明你如何给新接手的人传递背景，尤其是
Compare a central review with separate team reviews starting from
Explain why you preserved two different revisions particularly when
How do you check whether recovered data is complete assuming that
Tell me about a time you reassigned people with emphasis on
Describe how you narrowed down several similar faults beginning with
Why did you eventually switch to smaller batches especially under
How would you prove that a change actually fixed the issue given
Walk me through resolving a conflict with another team before we discuss
Compare the costs of automatic and manual rollback focusing first on
Explain how you bring a replacement up to speed particularly the
'''),
'reported_only':(False, '''
旧档案里那位面试官想听任务失败以后我做了什么
这段旧录音的题目是你为什么要分别保存两个版本
我在转述她当年的评价，说准备阶段还不够具体
有人去年问过额外检查的作用，我现在只是整理记录
请讲你自己处理的部分这句话是旧讲义的标题
这份历史问卷上有一题让候选人比较两种审批方式
那位同事以前希望我描述失败的尝试，这是往事
你怎样证明修复有效是当时老师写在纸上的问题
我在抄录过去的留言，里面有人说还没听懂中间步骤
这句话来自已经结束的评审，原文是我还想听完整案例
WHAT HAPPENED AFTER THE TIMEOUT IS THE HEADING OF A PAST INTERVIEW
I am entering an old comment that the verification was not specific enough.
Last year's reviewer asked the previous team why both copies were kept.
The archived exercise tells the reader to compare the approval methods.
I am reporting how she once requested details of a failed attempt.
The transcript includes his earlier question about trusting the backup.
Please describe your contribution is the title on the old worksheet.
I am reading a past remark that the middle of the account was unclear.
The question about proving the fix belongs to a completed assessment.
That was a request for an example made during last month's discussion.
'''),
'withdraw_or_wait':(False, '''
刚才让你比较的那项先撤掉，不用回答了
先别解释版本的区别，我还要把限制补齐
我不需要那次失败的例子了，先到这儿
这句追问收回，我准备换一个方向
请等我讲完全部选项再回应
不要现在接着说，我还在修改条件
关于额外检查的那项我不问了
让我先把参与人的情况交代全，你再开始
先暂停这个话题，我不再要求展开
你先听着，等我明确请你答了再说
DO NOT ANSWER THE COMPARISON I HAVE WITHDRAWN THAT REQUEST
Please hold off while I finish describing the available choices.
I no longer need the failed example, so stop on that point.
Wait before explaining the revisions; another condition is coming.
I am retracting that follow-up and moving to another subject.
Keep listening until I explicitly invite your reply.
Do not continue now, I am correcting the setup.
I have dropped the question about the additional inspection.
Pause this topic; no further detail is requested at present.
Let me finish giving the staffing constraints before responding.
'''),
'essential_intent_missing':(False, '''
我准备给你的实际问题还没有说出来，它是
请对那个还未指明的材料采取我接下来才会定义的
要你选择的候选项都还没列出来，分别为
让我先介绍你需要处理的具体对象，它叫
请把尚未给出的这份与另一份尚未给出的
我需要你进行的操作名字还没说，是
这次请你回答的事项还没指定，具体要问
需要替换的是什么以及换成什么我都还没讲，首先是
我打算要求你把还没提及的东西移交给还没介绍的
接下来才是实际题干，现在我要念的是
The actual question has yet to be given and it will be
The requested operation is still unnamed and applies to an unspecified object
The alternatives you must choose among have not been listed and they are
Let me identify the subject of the task first which is
Please compare an item I have not supplied with another I have not supplied
I have not specified what action you should carry out and it is
The issue for your response has not been identified yet and concerns
Both what to replace and its replacement remain unstated namely
Send the not yet mentioned item to the not yet introduced recipient
I am about to state the actual task for the first time as follows
'''),
'narration_or_ack':(False, '''
你这次补的过程让我看明白了，不需要再解释
两份记录分别保存的原因我已经记住了
我此前想听失败的例子，现在材料已经满足了
我们收到告警以后自己重新检查了一遍
这个结果已经把我刚才的疑惑消除了
那就是我当年协调排班的完整经过
我自己来补充尚未提到的一段背景
你讲到这里已经足够，我没有新问题
最先发现异常的是我，这是我的补充说明
我会把今天听到的区别写进笔记
The explanation you added makes the sequence clear to me now.
I have recorded why the revisions were saved separately.
I wanted an example before, but the material has now supplied one.
We checked the data again after receiving the alert.
That result resolves the uncertainty I mentioned earlier.
That is the complete account of how I arranged the staffing.
I will supply a piece of background from my own experience.
You have said enough on that point and I have no new question.
I was the person who first noticed the discrepancy; that is my clarification.
I will add the distinctions I heard today to my notes.
''')}


def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite final holdout')
    used=set()
    for folder in a.previous:
        for f in folder.glob('*.json'):
            rows=json.loads(f.read_text())
            if isinstance(rows,list):used.update(normalized(r['text']) for r in rows if isinstance(r,dict) and 'text' in r)
    rows=build('consistency-final',FINAL);keys=[normalized(r['text']) for r in rows]
    assert len(rows)==160 and sum(r['respond'] for r in rows)==80 and len(set(keys))==160
    assert not used.intersection(keys),used.intersection(keys)
    a.out.mkdir(parents=True);f=a.out/'acceptance.json';f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    report=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),count=160,positive=80,model_scores_seen=False,annotation='Single-annotator synthetic engineering fixtures, all reviewed before scoring. Clear response intent sufficient despite unfinished grammar; essential unknown task, quoted history, explicit waiting and satisfied acknowledgement wait.',disjoint_from=[str(x) for x in a.previous],scope='New final, not used in training or model selection; every case also receives saturated-history evaluation.')
    (a.out/'pre-score-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))


if __name__=='__main__':main()
