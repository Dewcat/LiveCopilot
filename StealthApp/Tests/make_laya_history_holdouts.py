#!/usr/bin/env python3
"""Separately authored V13 development/final fixtures, frozen before training.

No model scores are used to select examples or revise labels. Intent, not
syntactic completeness, determines the labels. Text after a tab is context.
"""
import argparse, datetime, hashlib, json
from pathlib import Path
from make_laya_finetune_data import case, turn
from review_laya_response_labels import normalized

FINAL = {
'implicit_request': (True, '''
你把关键的讨论略掉了，我正想听那个
谈到人员分工这儿，我脑子里还没有具体场景
我听到了采用的办法，可是理由这一块仍然空着
你刚提的那次退让，我有点想知道背后的考虑
如果有个从开始到结束的实际例子，我会容易理解些
你发现苗头之后发生的事，这里还缺了一段
我更好奇你怎样从那几个猜想里筛出来
你们最后的共识是怎么来的，我仍没听明白
我想听的是你亲自参与的那一小部分
刚才谈得太概括，我还需要一点当时的细节
The hard choice in the middle of your story is still a blank for me.
I would welcome a concrete account of your own intervention.
Your explanation has yet to connect the symptom to the cause.
I am curious about what you gave up to reach that agreement.
The way you divided the responsibility deserves a closer look from you.
Hearing what happened between those two meetings would help.
I still do not have a picture of the actual procedure you followed.
The part where you ruled out the other possibilities interests me most.
You have told me who approved it, but not what convinced them.
I was hoping to hear the reasoning behind that last adjustment.
'''),
'context_followup': (True, '''
要是签字的人临时离开呢\t每次发货前都由当班经理签字。
同一条记录再来一次\t接收端写入记录后向发送端确认。
那提前退出的成员\t参加者完成全部活动后会拿到反馈。
我指的是你自己否掉的那一个\t我们讨论过三个方案，最后选了第三个。
那层保护也坏了的话\t主存储不可用时会切到备用存储。
最初的估计凭什么\t我们开始时估计两个星期可以完成。
有没有可能换个先后\t先检查许可，再准备要发送的内容。
第一次返工之后的变化\t我们在评审后返工了两轮才交付。
换成经验少的人操作\t这一步由做过多年现场支持的同事处理。
属于你拍板的那一项\t最后的计划同时包含了我的决定和主管的决定。
And if the reviewer is away?\tA reviewer must sign off before the item is published.
The jobs that were already running.\tWe disable submissions during the upgrade.
With a slower connection at the other end?\tThe demonstration used an office network.
What convinced you to discard that possibility?\tAt first I suspected the storage driver.
Your part before the handover.\tI worked on the first phase and then another engineer took over.
If the same event arrives twice?\tThe receiver adds an event to the ledger and sends a receipt.
Why that order in particular?\tWe validate the signature and then unpack the payload.
The exception you mentioned earlier.\tThere is one case where we do not follow the usual schedule.
What happened once the appeal was rejected?\tWe tried to challenge the initial decision.
And without the specialist on site?\tNormally the specialist helps restart the equipment.
'''),
'asr_request': (True, '''
HOW DID YOU KNOW THE REPAIR HAD ACTUALLY WORKED
you mentioned a spare machine how did you keep it in sync
I STILL DONT SEE WHY THE FIRST CHECK WAS NECESSARY
what did you learn from the run that never finished
can you explain the trade off between those two choices
WHAT DID YOU DO WHEN THE ACK NOWLEDGEMENT NEVER ARRIVED
id like to hear what changed after your second attempt
why did you make the read path wait for the write
PLEASE DESCRIBE WHAT YOU DID BEFORE ASKING FOR HELP
the part about your own investigation needs more detail
嗯刚才说的那个隔离你具体怎么做出来的
你发现丢记录以后第一步做了什么
我想再听一遍为什么没用最开始的办法
那个复现不出来的问题你后来怎么查下去的
能给我把这次改动的来龙去脉说一下
你在决定减小批次的时候都考虑了什么
两个结果对不上你怎样确定相信哪个
你提到多试了一次我想听那次到底改了啥
如果记录的先后颠倒了你会如何处理
你给我讲讲凭什么认为那个备份是可用的
'''),
'clear_intent_fragment': (True, '''
讲讲你怎么确定一次演练算成功，特别是在
请比较同步确认和异步确认，先从那个
你怎样处理任务中途换目标的情况，我主要想
解释一下为什么把检查提前，假如当时
给我举个说服别人改变计划的例子，最好是从
你如何验证自己找到了根因，比如说
谈谈你怎样安排几个同时到期的任务，考虑到
为什么最终选择重做而不是修补，尤其是
你能描述一次处理投诉的过程吗，从你
请说说给新同事交接时怎么避免遗漏，接着再
Explain how you would recover from a damaged index especially if
Describe a time you had to challenge an estimate starting with
Why did you split the validation into two steps considering
Compare polling and notifications with particular attention to
Tell me how you decide which alert to investigate first when
Walk me through a failed deployment and the way you
How did you establish that the data was complete given
Give an example of changing a plan after feedback particularly
What would you do if the approval never arrived assuming
Explain why you kept a separate audit trail before we go into
'''),
'reported_only': (False, '''
我翻到去年的笔记，里面有人想再听一遍个人贡献
你怎样验证根因是以前那张题卡的标题
我在转抄别人说的请把现场情况再描述一下
她那天问他为什么没有立刻回滚，我现在只记这件事
旧字幕写着我仍然没听懂这个选择的理由
这不是新的追问，我只是念之前的评语说过程太笼统
去年客户希望我们多举一个例子，这是当时的记录
为什么审批要等这么久这句话来自已结束的访谈
那份历史问卷让受访者谈一次失败的部署
我正在标注一段录音，原话是最前面还想听细一些
HOW DID YOU VERIFY THE PATCH IS THE TITLE OF AN ARCHIVED EXERCISE
I am copying an old remark that the reasoning needs more detail.
She asked the previous team to explain their rollback last month.
The transcript records his demand for another practical example.
Why did you wait for approval was a question in the old survey.
I am quoting a former reviewer who wanted to hear the missing step.
That earlier interview asked the applicant to describe a disagreement.
The old recording says your own contribution is still unclear.
I am cataloguing past requests for a fuller explanation of the test.
Please explain the delay is the sentence I am entering in the archive.
'''),
'withdraw_or_wait': (False, '''
刚刚让你讲具体些的要求撤回了，现在不需要
暂时不要解释，我想先把情境设定改一下
这个例子先不用给了，我已经换了考虑方向
先停在这里，后半段我会自己阅读
等我说可以开始以后你再回应
请先让我把两个相互冲突的要求交代完
不用接刚才那项，我不打算继续问了
别展开，刚才那个前提我说错了
我还没轮到请你答，你先听我说
取消最后那句请求，我们暂且不讨论它
PLEASE DONT RESPOND TO THAT I AM TAKING THE QUESTION BACK
I no longer want an example of the incident, so leave it there.
Hold your response until I finish describing both constraints.
Do not elaborate on the first phase; I am dropping that request.
Wait for me to finish reading the premise before speaking.
I withdraw the invitation to explain your decision now.
There is no need to answer the follow-up I just added.
Keep listening for the moment; I have not finished the scenario.
Stop there while I replace the condition I gave you.
I have cancelled that request for clarification, please wait.
'''),
'essential_intent_missing': (False, '''
我这次要你做的具体事情还没讲，叫作
请对我接下来才会给出的那个对象进行
我要问的内容尚未交代，具体是
需要你采用的操作和目标都还没介绍，是
请选择下面这些我尚未列出来的东西中的
请把那个还没描述的项目转换成我稍后指定的
你要回答的题目我还没读，现在是
让我先讲清要你处理什么，那个是
请比较这两个还没有告诉你的对象，分别是
我希望你把一个尚未说明的东西送到一个未提及的
The action I need from you has not been described yet and is
Please apply the as yet unspecified operation to the item I have not named
The question for you is still to come and it concerns
Choose between the alternatives I have not listed yet which are
What I want done with the unnamed object has yet to be stated
Please compare the two unidentified subjects that I will specify next
The task and its target are both still to be announced namely
Send the thing I have not identified to the destination I have not given
I have yet to tell you which issue to address and that issue is
Replace the unspecified item with another one that I have not described
'''),
'narration_or_ack': (False, '''
刚才听你补充以后，个人贡献这一块已经清楚了
我记下了这个判断的根据，今天就到这里
那次交接的空白我自己已经查记录补上了
我现在来讲自己当时是怎样排查的
你给的例子正好解答了我之前的疑惑
我们确认接收成功后才删除了本地副本
我曾经好奇原因，后来读完报告就懂了
这就是我在验收阶段具体做过的事情
那段说明现在不抽象了，我理解了
我需要更多细节，所以当时我自己找了当事人
Your last example resolved the uncertainty I had about that step.
I have enough detail to understand your part now.
We waited for the receipt before removing the local copy.
I will describe my own checks while you listen.
The revised account has already filled the gap in my notes.
I used to wonder about that choice, but the report answered it.
That is how I reached the decision during the review.
I understand the missing connection after your explanation.
I have recorded the sequence and have no follow-up to add.
We changed the schedule after the operator went home.
''')}

DEV = {
'implicit_request': (True, '''
你的说明还没让我理解当时为什么要冒险
我更想知道你第一次遇到阻力时做了什么
这一段缺了你怎样验证猜想的细节
你提到的那场争论，我还想听听经过
我需要一个有实际数字的例子才能跟上
你的讲法让我看不出是谁先发现了异常
我对最后改方案的契机仍然很好奇
你把准备过程省略了，我其实也想了解
I would find a firsthand account of the dispute helpful.
Your summary leaves out how you tested that assumption.
I still cannot tell what made the original plan impractical.
The events leading up to your intervention would interest me.
An example with real measurements would make your point clearer.
I am waiting to hear your reason for trusting the replacement.
There is a missing link between your observation and your action.
Your explanation has not yet covered why the warning was ignored.
'''),
'context_followup': (True, '''
如果两边都不同意\t我们先征求开发组和运营组的意见。
更晚才来的那一批\t我们在整点把已经收到的数据一起处理。
当时另外一个选择\t我们想了几条路，最后用了人工复核。
你怎么证明是它\t我判断问题出在旧版本的转换模块。
反过来做会怎样\t我们先更新列表，再通知其他节点。
不经过主管的情况\t一般每份申请都要由主管转交给评审。
把时间缩短一半呢\t我们预留了十天来完成检查。
你单独负责的部分\t这个版本是我跟两个同事一起完成的。
What if both teams object?\tWe seek agreement from engineering and operations.
The items arriving after the cutoff.\tWe collect a batch at the start of each hour.
How did you exclude the converter?\tWe initially suspected either the converter or the cache.
With half as much time available?\tWe allowed ten days for the review.
The alternative you abandoned.\tWe chose manual verification after considering several paths.
If the receipt gets lost?\tThe sender waits for confirmation before clearing its buffer.
Your responsibility after launch.\tSeveral of us worked on the release together.
What made the second attempt different?\tWe succeeded only on our second attempt.
'''),
'asr_request': (True, '''
HOW DID YOU FIND OUT WHICH COPY WAS CURRENT
id appreciate more about what you personally changed
what made the first roll out take longer than expected
PLEASE EXPLAIN HOW YOU TESTED THAT FALL BACK
the link between those events still isnt clear to me
WHY DID YOU CHOOSE TO KEEP THE OLD ENTRY
can you take me through how the hand over worked
what did you try once the first check came back empty
你给我讲一下当时怎么找出过期数据的
嗯你最后为什么接受了那个延期我还想听
你做完变更以后怎样确认别的地方没坏
我不太明白为什么多出来一次检查
能不能把从收到消息到确认的过程再说一下
当时人手不够你怎么重新分任务的
第一次没查到记录后来你接着做什么
你个人跟进的那项能讲得具体一点吗
'''),
'clear_intent_fragment': (True, '''
请说明你如何安排上线后的观察，特别当
比较一下预先校验和事后检查，主要从
你会怎样应对一次突然停电，假定那个
给我讲个跟别人意见不合的例子，先谈
为什么把记录分成两份保存，考虑到当时
你怎么确认操作没有被执行两次，譬如
描述一下你处理紧急通知的步骤，接下来
谈谈你如何给没有经验的人做交接，从那个
Tell me how you would detect a stale result especially in
Compare checking before and after the write considering
Explain why you kept those two copies separate when
Describe a disagreement you had during a review beginning with
How would you recover after the device loses power assuming
Walk me through how you verify a handover particularly the
Give an example of reducing work when a deadline changes and
Why did the first experiment take longer than expected if
'''),
'reported_only': (False, '''
笔记上有句旧提问叫你怎样确认操作没有重复
我转述一下他去年的要求，希望得到具体数字
这行是往年访谈的批注，说当时的贡献听不清
她在录音里希望对方重讲那次分歧，我只是抄录
请你解释检查顺序是旧练习册的原文
我正在整理过往的问题，其中问过为何延期
不是让你讲，刚才那句只是历史问卷的标题
那份过期的记录里有人还想听一次失败经历
I am transcribing a past request to explain the review sequence.
WHY DID YOU RETAIN TWO COPIES WAS THE OLD WORKSHEET HEADING
She told the previous applicant to expand the example last year.
The archived note says the personal contribution was unclear.
I am reading the historic question about how the shutdown was handled.
That line quotes another person's request for detailed measurements.
The completed interview included a prompt to describe a failed handover.
I am merely recording that he once wanted a fuller explanation.
'''),
'withdraw_or_wait': (False, '''
暂缓回答那一项，我要先改题干
我已经不想追问那个例子了
请保持安静，等我的全部背景说完
你不用展开那个决定，我收回这个要求
最后那句当我没问，现在先停
先听另一位把条件讲完再开始
这个解释今天不需要了，留在这里
我还在给情境加条件，先不要回应
Wait while I correct the scenario before you answer.
I have abandoned my request for details of that decision.
Do not respond until the remaining premise is stated.
No example is needed now; I have changed the question.
Please let the other speaker finish the setup first.
I am cancelling my demand for a breakdown of the steps.
Hold the explanation, I still need to name the constraints.
There is no current invitation to answer; keep listening.
'''),
'essential_intent_missing': (False, '''
具体需要你操作的对象我还没说，那个是
让我先把问题是什么告诉你，它叫
我要求的动作还没介绍，接下来就是
请按我还没提供的内容去处理尚未命名的
请将未指定的这个换成另外一个未说明的
我想让你从还没列出来的一组选项中
你需要评价的事项我尚未描述，现在是
我即将交给你的那项任务具体为
The object of the requested action has not yet been identified and is
I have not described the task itself yet which will be
Please perform the unnamed operation on the unspecified subject
The matter I want you to assess is still to be described as
I need a selection among alternatives I have yet to tell you
Replace something not yet identified with another unspecified item
The actual question has not been stated and I will give it now as
I have yet to specify either the action or the object which are
'''),
'narration_or_ack': (False, '''
听完这次解释我已经了解为什么多检查一次
我这里没有遗留疑问了，可以结束
后来的报告把那段遗漏补上了，我看懂了
我自己接着讲当时的判断过程
我已经把两个复制品的区别记清楚了
我们是在值班人离开以后发现这件事的
刚才的具体例子足够了，不必再加
我当时想知道原因，于是自己做了实验
That example supplies the detail I was missing earlier.
I now understand why you kept both records.
We discovered the discrepancy after the operator left.
I am going to explain my own decision next.
The updated report has answered my earlier concern.
I have no remaining question about the sequence.
I once wanted to know why, so I ran my own experiment.
Your description is now specific enough for my notes.
''')}


def build(name, groups):
    rows=[]
    for category,(label,block) in groups.items():
        for i,line in enumerate(block.strip().splitlines()):
            parts=line.split('\t');prior=[]
            if len(parts)>1:prior=[turn('You' if label else 'Them',parts[1])]
            r=case(f'history-{name}-{category}-{i}',f'history-{name}-{category}-{i}',parts[0],label,prior)
            r['category']=category;rows.append(r)
    return rows


def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite frozen holdouts')
    old=[]
    for f in a.previous.glob('*.json'):
        x=json.loads(f.read_text())
        if isinstance(x,list):old.extend(c for c in x if isinstance(c,dict) and 'text' in c)
    used={normalized(c['text']) for c in old}
    sets={'development':build('dev',DEV),'acceptance':build('final',FINAL)}
    for name,rows in sets.items():
        assert len(rows)==(128 if name=='development' else 160)
        assert sum(c['respond'] for c in rows)==len(rows)//2
        keys=[normalized(c['text']) for c in rows]
        assert len(keys)==len(set(keys)),name
        assert not used.intersection(keys),(name,used.intersection(keys))
        used.update(keys)
    a.out.mkdir(parents=True)
    for name,rows in sets.items():(a.out/(name+'.json')).write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    review=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),scope='New synthetic, single-annotator engineering fixtures; no scores used for labels or selection.',labels='Respond when a useful answer can start from intent. Grammar need not be complete. Quotation, withdrawal, satisfied acknowledgement and truly unspecified tasks wait.',review='All authored rows reviewed before scoring. Balanced 160 final and 128 development. Normalized utterances disjoint from every V12 split and each other.',hashes={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.out.glob('*.json')})
    (a.out/'pre-score-review.json').write_text(json.dumps(review,ensure_ascii=False,indent=2)+'\n');print(json.dumps(review,indent=2))


if __name__=='__main__':main()

