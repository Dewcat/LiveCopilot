#!/usr/bin/env python3
"""V20 independently authored Chinese development and bilingual final.

No prediction-guided filtering. All cases include the information available at
the current time; understandable incomplete grammar remains a positive request.
"""
import argparse,datetime,hashlib,json
from pathlib import Path
from make_laya_history_holdouts import build
from review_laya_response_labels import normalized

DEVELOPMENT={
'implicit_request':(True, '''
你决定暂停窗口服务的那一步，我还需要听到理由
这段只说有人配合，我仍然分不清你做了什么
设备已经启动之后的检查，你好像还没讲到
要是把你发现错误的过程展开一点，我就能跟上了
你说重新算过人数，我比较想知道是怎么核对的
我原本想听的就是你和司机沟通的细节
你在处理缺货时的判断依据，我还没有听明白
我现在缺少的是你怎样确认申请人身份的说明
'''),
'context_followup':(True, '''
如果钥匙也不在了\t值班人员可以用备用钥匙开门。
第四层那些住户\t我们给每层楼都放了一份告示。
通知发出以前的检查\t检查通过以后我们才发了通知。
那次未获批准的申请\t两次申请里第二次被批准了。
你说的那个临时安排\t正式车辆到来前我们做了一个临时安排。
换成无人接听的情况\t遇到问题时先打电话联系负责人。
如果表格没有填日期\t我们按表格上的日期安排检查。
从你接到那封信开始\t我收到投诉信之后安排了回访。
'''),
'asr_request':(True, '''
嗯你把核对座位数的办法再说具体些
后来那个锁打不开你怎么解决的
你是凭什么确认那张证明有效的
给我说说两次检查看到的区别
我还想听丢失那把钥匙之后的事
你怎么决定先联系哪一户
那我想问的是排队太长你会怎样处理
你自己提出的那个补救措施讲一下
'''),
'clear_intent_fragment':(True, '''
请介绍在电池不足时如何完成巡检，尤其是当
你为什么安排两个人共同核对身份证，考虑到
解释一下处理过期证明的办法，先从
比较定时巡逻和随机巡逻，特别注意
你如何防止同一份申请被重复登记，比如
给我讲一次发现访客走错楼层的经历，重点在
怎样保证分发的材料没有缺页，假设当时
说说两位居民争用停车位时你会怎样调解，主要是
'''),
'reported_only':(False, '''
你如何核对座位数是这份旧练习册的栏目名称
我在逐字复述去年的反馈，原句是最前面还要再讲细些
这段档案记着过去的居民希望听到解释
她之前问的请讲一下巡检经过，我只是把这句话抄下来
这是过去培训中的原话，你怎么确认访客身份
当年的提问卡要求介绍一个处理丢失物品的案例
我正在给旧录像加字幕，字幕内容是说说你负责哪一步
这里的再解释一次不是我在追问，是印在旧封面上的标题
'''),
'withdraw_or_wait':(False, '''
刚才有关停车位的提问作废，不要回答了
先暂停解释，我还要纠正是哪一栋楼
等我把这次巡检的范围说完，再开始答
我暂时不想听座位安排，先让我看一下图
别接这个问题，我已经不需要核对办法了
你先听这封信，信读完以后我才会提问
关于钥匙的追问撤销，我们稍后换一个话题
这段不用回应，我在试一下录音有没有声音
'''),
'essential_intent_missing':(False, '''
我想让你评价的那个东西还没拿出来，我先找一下
要比较的两份文件我都还没告诉你是哪两份
现在有个选择题，选项我马上才开始读
帮我判断一个条件是否满足，但条件本身还没有说
这个请求具体要你做什么，我接下来才解释
需要你给出那个数值，不过要算什么还没告诉你
我希望听你对下面这件事的建议，事情还没有介绍
需要你选一种方案，但可选的方案还没列出来
'''),
'narration_or_ack':(False, '''
钥匙丢失那件事你已经讲清楚，我记好了
座位核对的依据现在足够明确了
我本来还想听细节，看完这张图就都明白了
我在把你刚才说的巡检顺序录入表格
那封信的内容我自己查到了，疑问已经解决
刚才是我的处理经历，已经全部说完
这一点你给的例子够用了，我没有追加问题
我当时先联系了楼长，再到现场确认
''')}

FINAL={
'implicit_request':(True, '''
你提到的第一次误判，我还想弄清它是怎样发生的
我在意的是你为什么放弃原来的排班，而不只是新排班
你和供应商意见不一致的那一段，听起来还不够具体
我仍然拼不出你查到漏水位置的全过程
你说做过核实，可我还不知道核实的是哪些东西
最开始怎么注意到这个风险，我还想听你讲讲
如果把你亲自协调的那部分说清楚，会更有帮助
你介绍了结果，我想补上中间怎么达成一致的过程
我对你发现凭证不对劲的那个瞬间比较好奇
这次你承担的责任和旁边同事的责任，我还分不开
I still need the chain of events that led you to identify the broken sensor.
Your description has skipped the choice I was most interested in understanding.
I cannot yet connect your first observation with the decision to shut the desk.
The conversation that changed the refund decision is what I wanted to hear about.
I would benefit from a detailed account of the checks you personally carried out.
You have described the replacement but not what ruled out repairing the original.
The part where you challenged the delivery estimate remains unclear to me.
I am looking for the reason you used a second witness, which you have not covered.
Your own contribution to settling the seating dispute is still missing from the story.
I would like more than the outcome of the negotiation; I need the steps you took.
'''),
'context_followup':(True, '''
如果原来的收据找不到\t退款前我们先核验原来的收据。
收到第三次催促以后呢\t前两次催促我们都还没有拿到供应商的答复。
那名一直没签到的学生\t签到之后就可以领取资料。
你决定取消之前那一刻\t后来我决定取消预约并通知了客户。
假如备用入口也被堵住\t正门不能通行时我们启用备用入口。
没有带照片的证件呢\t入场时会看证件上的照片是否一致。
那条已经打印出来的标签\t我们可以在系统里修改货品标签。
你独自值班的时候\t通常会有两个人一起检查紧急出口。
如果临时改了集合地点\t我们事先向所有成员发送集合地点。
到现场才发现数量不对\t出库前会核对发货数量。
The guest who arrived after the desk closed.\tThe desk hands out room keys during opening hours.
If the notice was delivered to the wrong flat?\tWe left a notice at every resident's door.
The measurement before the adjustment.\tThe final measurement matched the reference value.
What if the replacement is damaged too?\tWe ask the supplier to send a replacement item.
The booking you declined.\tWe accepted one booking and declined the other.
Without the printed checklist available?\tStaff follow a printed checklist during inspection.
If the same name appears on both forms?\tWe sort the forms by the applicant's name.
Your action while the lift was still stuck.\tThe maintenance team arrived and released the lift.
The moment you first doubted that figure.\tI eventually discovered the count was inaccurate.
If the caretaker cannot hear the alarm?\tThe caretaker normally responds when the alarm sounds.
'''),
'asr_request':(True, '''
HOW DID YOU CONFIRM THE WATER WAS SAFE TO USE
id like to hear how you kept track of the borrowed equipment
YOU HAVENT TOLD ME WHAT CAUSED THE DOUBLE BOOKING
what made you call the technician before restarting it
the part about getting the visitor home still needs detail
CAN YOU WALK ME THROUGH CHECKING THE DELIVERY NOTE
what did you do after the customer disputed the signature
I WANT TO UNDERSTAND WHY THE DOOR WAS LEFT UNLOCKED
tell me how you found the missing item on the list
why did the last inspection change your decision
嗯我想听你怎样确认那水可以用
那个借出去的设备你具体怎么追踪的
你还没有说两个预约怎么撞到一起的
为什么你先叫技术人员而没直接重启
送那个访客回去这件事还想听细些
给我从头讲一下怎么检查送货单
客户说签字不是他的你后来做了什么
我想明白那扇门为什么没锁
清单上少的那个物品你怎么找到的
最后那次检查怎么让你改了主意
'''),
'clear_intent_fragment':(True, '''
讲讲你如何安排人手不足时的交接，特别在
解释你为何重新称量那批物品，考虑到当时
你会怎样应对预约者迟到，尤其当
请比较单人核验和双人核验，先谈
如何确认临时通道可以安全通行，例如
说说你发现登记号码重复之后怎么处理，重点是
请描述一次说服客户接受替代方案的经历，从
你怎样给新人解释紧急撤离路线，假设他
为什么检查结束以后还要留存照片，尤其是
讲一下如何追回误送给别人的文件，先从
Explain how you handle a visitor who cannot find their identification, particularly
Describe checking that a locked storage room is secure, starting from
Why did you recount the items before signing the delivery note, given
Compare taking appointments online and taking them at the desk, especially
How would you organize assistance when several residents need it at once, assuming
Tell me about discovering a discrepancy in a payment record, focusing on
Explain how you verify that a repaired door closes properly, for example
How do you pass on urgent information at the end of a shift, taking into account
Describe a time you had to refuse an unsafe instruction, beginning with
What would you do if a passenger missed the final shuttle, particularly when
'''),
'reported_only':(False, '''
这是旧练习中的一句话，说说你怎样找回文件
我在整理三年前的访谈，那个人当时想听更详细的值班经历
请比较两种预约办法是这个旧章节的名称
这句我还想了解称量过程，是以前客户在邮件里写的
我只是在引用录像里的声音，原话是你为什么叫了技术员
那份已经作废的问卷曾要求介绍交接经验
这句给我举一个实际例子印在过去的培训海报上
我念的是早年投诉记录，里面住户要求解释停水原因
旧题卡上的文字是讲讲你个人做了哪些检查
这里记着当时她向另一人追问那扇门为什么没有锁
I am transcribing a historical interview that asks about an unsafe instruction.
Please describe your shift handover is the heading of the retired training sheet.
That sentence about wanting a fuller example is from a customer letter written years ago.
I am quoting the old examiner asking why the parcel was weighed again.
The archived questionnaire asked people to explain their appointment system.
Those words about the missing identification belong to a recording, not a question from me.
I am cataloguing the former supervisor's request for an account of the late shuttle.
How did you check the lock appears as a chapter name in the old guide.
The cancelled meeting's minutes record a request to discuss the water inspection.
I am reading the past complaint in which someone demanded to know why the desk closed.
'''),
'withdraw_or_wait':(False, '''
先别答人手不足的题，我要换一下人员条件
重新称量那个问题不问了，撤回
我还在读来访者的情况，请先听完再回应
你暂时不要解释通道安全，我还有信息没交代
不必再回答预约迟到的事，我改问别的
让我先说明是谁把文件送错了，暂时别答
你刚准备讲的那个例子取消，我现在不需要它
先停下解释，我得纠正是哪一扇门
对照片留存这点先不要作答，我还没设定用途
现在只听我描述，等我明确让你回应再说
Hold your answer about the spare keys until I finish correcting the location.
I withdraw the question about the final shuttle; no answer is needed.
Do not respond while I am still listing the visitors involved.
Leave the damaged lock question unanswered for now while I check the date.
I am cancelling the request to compare the appointment methods.
Please wait for the full set of conditions before answering the handover question.
Stop explaining the notice because I want to revise what happened.
You need not give the example of the refused instruction after all.
Keep listening and do not begin your response until I give the signal.
The water inspection request is on hold while I replace the scenario.
'''),
'essential_intent_missing':(False, '''
我打算让你给这几个选项排序，选项还没开始列
有段内容想让你解释，我现在还没读到那段内容
请对接下来才要讲的事表个态，事情还没说
你需要决定哪个更合适，但我还没介绍参与比较的对象
我有个计算想交给你，算的项目和数值都还没提供
我马上会给出一句话，现在还没说出来，要你判断它是否成立
要你采取的操作还没指定，我正在想怎么表述
我想听你分析一件尚未叙述的经历，经历是这样的
有张表要你挑出其中一项，不过表格的项目还没念
我还没说明需要推荐什么，马上会把需求告诉你
I will give you alternatives to rank, but none of those alternatives has been listed yet.
There is a passage I want explained, and I have not supplied the passage so far.
I want your decision about an event that I have not described at this point.
Choose the better of the two objects, although neither object has been identified yet.
I have a calculation for you, but its quantity and inputs are both still unspecified.
I will state a claim for you to assess; the claim itself has not been spoken yet.
The action I want you to carry out has yet to be named.
Analyze the experience I am going to relate, but I have not related it so far.
Pick one entry from a list I have not read out or otherwise provided.
I want a recommendation for a purpose I have not explained yet.
'''),
'narration_or_ack':(False, '''
你已经把人手不足时的安排解释明白，我没有别的问题
我在复记刚才的预约说明，没有发起新的提问
这就是我值班期间处理漏水的全过程
那张清单我自己核对过了，现在已经清楚
我原来希望听更多检查细节，但你刚才说的足够了
他是否迟到我已经查明，不需要你再判断
我把文件交给同事以后就回到了接待处
你给的案例已经覆盖了我想了解的地方
这个问题的答案我从记录里找到了，已经解决
我正在保存你刚才说明的路线，先记录下来
You have explained the staffing decision fully enough for me now.
I am only recording the appointment procedure you just described.
That completes my own account of finding the water leak.
I checked the list myself and there is no remaining question about it.
I had wanted more inspection detail, but your last answer has supplied enough.
I already established whether he was late, so no further judgment is needed.
After handing the file to my colleague, I returned to reception.
Your example covers the part I wanted to understand and I need nothing more.
The records have answered my question and the matter is settled.
I am saving the route you have just explained for my notes.
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
    groups=dict(development=build('pragmatic-dev',DEVELOPMENT),acceptance=build('pragmatic-final',FINAL));keys=[];report={}
    for split,rows in groups.items():
        expected=64 if split=='development' else 160
        assert len(rows)==expected and sum(r['respond'] for r in rows)==expected//2
        current=[normalized(r['text']) for r in rows];assert len(set(current))==len(rows)
        assert not used.intersection(current),used.intersection(current)
        assert not set(keys).intersection(current);keys.extend(current)
    a.out.mkdir(parents=True)
    for split,rows in groups.items():
        f=a.out/(split+'.json');f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        report[split]=dict(count=len(rows),positive=sum(r['respond'] for r in rows),sha256=hashlib.sha256(f.read_bytes()).hexdigest())
    report.update(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),model_scores_seen=False,
        annotation='Clear response intent is positive even without grammatical completion. Historical quotation, explicit withdrawal/waiting, resolved statements and missing essential objects are negative. Context follow-ups include their immediate antecedent. Single annotator synthetic benchmark.',
        policy='Same gates, frozen labels, all160 original/native-ASR short/long evaluated without exclusions. Chinese development separately gated to prevent aggregate masking.',disjoint_from=[str(p) for p in a.previous])
    (a.out/'pre-score-review.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
