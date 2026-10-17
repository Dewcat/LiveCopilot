#!/usr/bin/env python3
"""V16 fresh semantic and full-audio final; never used for model selection."""
import argparse, datetime, hashlib, json
from pathlib import Path
from make_laya_history_holdouts import build
from review_laya_response_labels import normalized

FINAL={
'implicit_request':(True, '''
你谈了发布结果，我还等着听发布之前你具体做了什么
那次客户改变主意的来龙去脉，我想再听仔细一点
讲到瓶颈这儿我跟丢了，需要你带着走一遍
我还是没弄清为什么非得加一道审批
关于资源不够时的取舍，我期待更具体的说明
你当时犹豫的地方反而是我最想了解的
从收到投诉到找到原因，中间好像省了一段
这段只听到团队做了什么，我想分清你本人的贡献
你说提前发现了风险，依据是什么我还没有听出来
我对这次调岗的判断过程还没有完整的印象
I was looking for more detail about how you prepared the launch.
The negotiation with that customer still feels like a missing chapter.
I lost track at the bottleneck and need you to take me through it.
I have yet to understand the reason for the extra approval.
Your explanation of the resource shortage needs a practical example for me.
I am particularly curious about the decision you hesitated over.
There seems to be a gap between receiving the complaint and finding its cause.
I would like to separate your contribution from the wider team's work.
The evidence that made you spot the risk is still unclear to me.
I was expecting to hear more about the judgment behind that reassignment.
'''),
'context_followup':(True, '''
如果财务已经结账了呢\t通常我们直接修改当月的费用记录。
那轮被你删掉的实验\t我们试了四种方案，其中一轮结果没有保留。
后来加入的人怎么知道\t讨论结束后大家口头确认了分工。
要是两个班次都没人接\t夜班发现异常会交给白班处理。
你自己在第二天的部分\t第一天由经理对接，第二天我和同事分别跟进。
前面那条假设不成立的话\t我们假设供应商能在周五之前送到。
那个已经签了的合同呢\t我们建议调整还在商谈中的合同价格。
不是你们团队，我想听你个人的\t整个团队一起完成了系统迁移。
那张后来补交的表\t最初提交的申请表都已经审查完成。
同一批里有一件坏了\t我们按整批统计到货并给仓库确认。
What if finance has already closed the books?\tWe normally edit the current month's expense entry.
The trial you decided to leave out.\tWe ran four trials but did not keep one of the results.
How would a later arrival find out?\tEveryone agreed verbally on the roles at the end of the discussion.
And if neither shift picks it up?\tThe night shift passes any incident to the day shift.
Your own part on the second day.\tThe manager handled day one and my colleague and I followed up on day two.
Without that assumption holding?\tWe assumed the supplier would arrive before Friday.
The contract that has already been signed?\tWe suggested changing the price on contracts still being negotiated.
I mean you personally rather than your department.\tThe whole department helped with the migration.
The form submitted later.\tThe forms in the initial submission have all been checked.
If just one item in the batch is damaged?\tWe confirm delivery to the warehouse for the entire batch.
'''),
'asr_request':(True, '''
WHAT MADE YOU DECIDE TO MOVE THE DEADLINE
id appreciate a closer look at the way you checked the totals
I STILL NEED TO HEAR YOUR REASON FOR THE SECOND INTERVIEW
how did you cope when the part time staff were unavailable
walk me through the work you did before the client signed
CAN YOU CLARIFY WHY THE MANUAL CHECK WAS KEPT
im wondering how you knew the figures were out of date
what would change if the team had half as many people
tell me more about that wrong turn in your investigation
YOU HAVENT EXPLAINED HOW THE TWO REPORTS WERE RECONCILED
嗯你为什么把那两个人安排到同一班
我想听听你是怎么发现账目不一致的
就是那个延期的决定你给我讲具体一点
你刚刚说的名单漏人最后怎么补救的
你说最后省了时间但我没听懂怎么省下来的
那个轮岗你自己负责的是哪一块
如果预算再砍掉一半你会优先留什么
你当时是凭什么认定那个数字不对
让我听一个你亲自处理供应商投诉的例子
你能再说说那个交付日期为什么不能动
'''),
'clear_intent_fragment':(True, '''
介绍你如何安排资源不足时的工作，先说当
比较集中培训和分散带教的效果，尤其在
你怎样确认一份账单没有重复计算，比如
讲一次你帮助新成员上手的经历，重点是那个
为什么你坚持把交付日期提前，考虑到
说明你怎么处理供应商突然缺货，假如那时
你怎样评价一次招聘是否成功，特别是
谈谈你如何让两组人达成一致，先从那次
你为什么取消第二轮问卷，我主要想知道
请描述你在客户拒绝方案后做了什么，最好先
Describe how you prioritize work with too few people especially when
Compare centralized training with mentoring in separate teams starting with
How would you check that an invoice was not counted twice for example
Tell me about helping a new colleague settle in with emphasis on
Why did you insist on moving the delivery earlier considering
Explain how you handle an unexpected shortage from a supplier assuming
How do you judge whether a recruitment round succeeded particularly
Describe how you brought two groups into agreement beginning with
Why did you cancel the second survey especially given
Tell me what you did after the client rejected the proposal focusing on
'''),
'reported_only':(False, '''
我在整理去年的访谈，里面有句请讲你为什么换供应商
旧教材把怎样分配人手列为一道练习题
他回忆那次答辩时老师让他解释预算变化
这封历史邮件写的是我想听资源不足时的安排
我正在引用一段已经结束的面试，不是在提问
当年客户说还想了解延期原因，这件事后来解决了
你怎样核对发票这几个字是旧文件的标题
录音里那位经理曾经要求对比两套排班表
这是过去讨论的摘录，原话是我还没听懂审批理由
讲述个人贡献是去年培训材料中的一个题目
I am cataloguing last year's interview in which someone asked about suppliers.
The old textbook lists allocating staff as an exercise for the reader.
She recalled being asked to explain the budget change at her defense.
That archived email said the writer wanted details about the staffing shortage.
I am quoting a completed interview rather than putting a question to you.
The customer wanted to know the delay's cause back then and it was resolved.
How do you check an invoice is the heading on an old document.
In that recording a manager once asked for the two schedules to be compared.
This is an extract from a past discussion about not understanding the approval.
Describing a personal contribution was an exercise in last year's training.
'''),
'withdraw_or_wait':(False, '''
别急着答排班的问题，我还要把人数改一下
刚才那个关于发票的问题不算，我撤回
先不用解释预算，等我把数字核对完
我已经不想问客户那部分了，到这里就好
让我把供应商的情况讲完以后再请你答
关于第二轮培训先别给意见，我还有条件没说
我收回让你比较那两种办法的要求
先停在这儿，等我示意之后你再继续
你现在只要听着，我整理好问题才会请你答
那一段暂时不用展开，我先找一下材料
Do not answer the staffing question yet because I need to change the numbers.
The invoice question is withdrawn and no longer needs a response.
Hold the budget explanation until I have checked the figures.
I have decided not to ask about the customer after all.
Wait until I finish the supplier background before answering.
Please withhold your view on the training while I add a condition.
I am taking back my request to compare those methods.
Stop here and resume only when I give the signal.
Just listen for now and I will invite an answer when the question is ready.
Leave that part alone for the moment while I find the material.
'''),
'essential_intent_missing':(False, '''
我想请你把
你能不能帮我对这个
接下来需要选择的是，嗯
如果你面对的是那个，我指的是
请分析两件事，第一件还没说，是
我有一个需要你判断的情况，先等我找出来
想知道你对，嗯我要问的是什么来着
请拿刚才没有给你的那个东西和
你会如何，我先把要做的事说清楚
我的问题涉及一位还没介绍的人与
I would like you to take the
Could you help me with this thing which
What I need you to choose is um
Suppose the thing you face is the one I mean
Please analyze two situations the first of which is
There is a scenario for you to judge but I need to find it first.
I want your view on um what was I going to ask
Compare the item I have not given you with
How would you let me first explain what the action is
My question concerns a person I have not introduced and
'''),
'narration_or_ack':(False, '''
你补充的安排已经让我理解了，不用再讲
这下我知道当时为什么调整日期了
我自己会继续查那几张发票
那天我是先联系供应商，再通知仓库
现在这份说明已经回答了我的疑问
我只是记一下你刚才说的人员分工
我原先想听更多，现在这些已经足够
那就是我处理这次客户争议的过程
你解释的预算变化我已经记住了
我接下来自己补充一个背景，不是问你
The extra detail has cleared it up and no more explanation is needed.
I now understand why you changed the delivery date.
I will continue checking those invoices myself.
I contacted the supplier first that day and then informed the warehouse.
This explanation already answers the concern I had.
I am just noting the allocation of staff you described.
I had wanted more detail earlier but this is enough now.
That was my account of handling the customer dispute.
I have noted your explanation of the budget change.
I am going to add some background myself rather than ask you anything.
''')}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--previous',type=Path,nargs='+',required=True)
    p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite final holdout')
    used=set()
    for folder in a.previous:
        for f in folder.glob('*.json'):
            rows=json.loads(f.read_text())
            if isinstance(rows,list):used.update(normalized(r['text']) for r in rows if isinstance(r,dict) and 'text' in r)
    rows=build('joint-final',FINAL);keys=[normalized(r['text']) for r in rows]
    assert len(rows)==160 and sum(r['respond'] for r in rows)==80 and len(set(keys))==160
    assert not used.intersection(keys),used.intersection(keys)
    a.out.mkdir(parents=True);f=a.out/'acceptance.json';f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    report=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),fixture_sha256=hashlib.sha256(f.read_bytes()).hexdigest(),count=160,positive=80,model_scores_seen=False,annotation='Single-annotator synthetic engineering benchmark. Respond when current intent permits a useful answer, regardless of finished grammar. Unresolved references without context, quotation, withdrawal, explicit wait and satisfied acknowledgements are negative.',disjoint_from=[str(x) for x in a.previous],scope='All 160 cases receive original and saturated history, both original text and actual native ASR. No exclusions or post-score relabeling. Not population accuracy.')
    (a.out/'pre-score-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
