#!/usr/bin/env python3
"""Fresh V23 software/project interview final, frozen before model selection."""
import argparse,datetime,hashlib,json
from pathlib import Path
from make_laya_history_holdouts import build
from review_laya_response_labels import normalized

FINAL={
'implicit_request':(True, '''
缓存击穿那次你讲得太快，我想听你怎样缩小排查范围
第一版被否决的原因，我现在还没形成清晰的认识
你说召回改善了，但我还缺你对比前后效果的过程
我更关心你自己在接口改造里具体改了哪一处
这个压测结果和你最后的选择之间，我还没连起来
评审时别人反对的那一点，你好像还没有展开
你先前删掉那个步骤时的考虑，我特别想了解
如果能说一段真实的用户反馈，我会更容易理解这项改动
我还需要你解释一下为什么没有采用现成组件
你说解决了延迟问题，中间怎么验证原因的我还不知道
The way you isolated the failing service is still the missing piece for me.
I would like the reasoning that connected your measurements to that design choice.
Your description does not yet show what you personally changed in the build system.
I was hoping to hear what made the team reject the initial prototype.
The example would help more if you explained the disagreement during review.
I still need to understand why you removed that validation step.
You have named the improvement without describing the experiment that established it.
I am interested in the actual user feedback behind the change to the search page.
Your explanation has not addressed why the existing library was unsuitable.
I cannot yet picture how you proved the slow response came from the database.
'''),
'context_followup':(True, '''
如果旧客户端还在调用\t我们把新版接口切换到了新的字段格式。
那次没有达到指标的实验\t三个实验里只有最后一个达到了指标。
你提到的第二个检索阶段\t检索流程分为召回和重排两个阶段。
如果两条消息顺序反了\t消费者按收到消息的顺序更新状态。
写到一半进程退出\t数据写完以后才会发送成功通知。
你负责设计的那个边界\t我和同事分别设计了两个模块之间的边界。
没有网络的那几分钟\t客户端每隔一分钟向服务器同步。
哪一项证据让你改变判断\t我开始怀疑网络，后来认为是磁盘。
数据量再扩大十倍\t当前版本只在十万条记录上测试过。
你做决定之前的备选方案\t最终我选择用队列处理这些任务。
If the old mobile client still sends the previous format?\tThe new endpoint accepts a different request structure.
The test run that failed your target.\tOnly the last of our three runs met the target.
The stage between retrieval and presentation.\tWe retrieve candidates, rank them, and then display the results.
If the events arrive in reverse order?\tThe consumer updates state in arrival order.
With a crash halfway through the write?\tWe send confirmation after the write finishes.
The interface you personally designed.\tMy colleague and I designed separate parts of the integration.
During the period with no connection.\tThe client normally synchronizes once a minute.
What changed your initial suspicion?\tI suspected the network first and later focused on storage.
At ten times that number of records?\tWe tested the current version with a hundred thousand records.
The alternatives before your final choice.\tI eventually chose a task queue for the background work.
'''),
'asr_request':(True, '''
HOW DID YOU VERIFY THE RETRY DID NOT CREATE A DUPLICATE
id like more detail about the change you made to the parser
YOU STILL HAVENT SAID WHY THE FIRST BENCHMARK WAS MISLEADING
what happened when the remote service stopped accepting requests
can you explain how you chose the size of each batch
THE PART ABOUT YOUR OWN DEBUGGING IS STILL TOO BRIEF
why did you keep the old format alongside the new one
TELL ME WHAT YOU LEARNED FROM THE ROLLBACK REHEARSAL
what made you decide to cache those results
i need an example of how you checked the generated answer
你怎么确认重试没有创建重复记录
解析器那次修改我想听你多讲一点
你还没说第一份性能测试为什么会误导你
远端服务不再接请求的时候后来发生了什么
你解释一下每个批次大小是怎么定的
你自己调试的那部分我觉得还太简略
为什么新格式上线以后仍然保留旧格式
告诉我回滚演练中你发现了什么
什么依据让你决定缓存那些结果
我需要你举个检查生成答案的例子
'''),
'clear_intent_fragment':(True, '''
介绍一下资源紧张时怎样保证请求不丢失，特别当
解释为什么把索引更新放到后台，主要考虑
你如何验证跨语言检索的结果，假如用户
比较本地缓存和共享缓存的取舍，先从
给我讲一次你追查偶发错误的经历，重点在
如何避免日志里面留下敏感数据，比如
说明你会怎样处理知识库文档互相矛盾，尤其
描述一下模型输出超时以后如何恢复，假设
你为什么把大任务拆成多个小任务，考虑到
讲讲你怎样向其他团队解释这次接口变更，从
Explain how you avoid losing requests when resources are scarce, particularly if
Describe validating the results of a multilingual search, beginning with
Why did you move the index update into a background job, considering
Compare a shared cache with a local cache, especially in
Tell me about investigating an intermittent failure, focusing on
How would you keep sensitive data out of application logs, for example
Explain dealing with conflicting documents in a knowledge collection, assuming
Describe recovering when a model request times out, starting from
Why did you split the large operation into smaller jobs, given
How do you explain an interface change to another team, particularly when
'''),
'reported_only':(False, '''
这是以前招聘问卷的原文，你如何避免重复请求
我正在抄去年的复盘，里面有人希望多听一些解析器细节
请解释缓存淘汰过程是那本旧教程的小节名称
你为什么保留旧格式这句话，是他当时向前同事问的
这段培训录像里的人要求给一个调试案例，我只在转录
我在为旧访谈标注角色，原话是你个人负责什么
过期的需求单里写着请比较两个检索方案
这是已经结束的答辩中评委要求解释日志处理的记录
我只念题目标签，不在提问，标签叫说明你的回滚步骤
这句还想听得更细是旧反馈中的内容，问题早已处理完
I am quoting an interview from last year that asked how retries were handled.
The old retrospective records someone's wish for more detail about the parser.
Explain cache eviction is the heading of a section in the archived tutorial.
Why did you retain the old format was his question to a previous colleague.
I am transcribing a training video where the speaker requested a debugging example.
Those words about your own responsibility belong to a completed interview.
The expired requirement sheet asks the reader to compare two retrieval approaches.
This is a record of a past examiner requesting an explanation of log handling.
I am reading a topic label, describe your rollback procedure, without asking it now.
The wish for a fuller account is old feedback about an issue that was already resolved.
'''),
'withdraw_or_wait':(False, '''
先不回答重试的题，我需要更正失败发生的位置
缓存比较这个问题取消了，现在不问
请等我介绍完数据来源，再开始组织答案
你先别讲调试案例，我还有前提没说
关于接口变更不需要再解释，我收回这个请求
先听我描述两份文档的冲突，暂时不要回应
我还在修改超时场景，等我说完再答
日志那件事先停在这里，不用继续补充
现在先不要总结，我要重新排列这几段内容
你准备讲的回滚步骤暂时搁置，我先查一条记录
Do not answer the retry question while I correct where the failure occurred.
The cache comparison is cancelled and needs no response.
Wait until I finish explaining the data source before you begin answering.
Hold the debugging example because I still have another condition to give.
I withdraw the request for another explanation of the interface change.
Listen to the document conflict first and do not respond yet.
I am still revising the timeout scenario, so wait for me to finish.
Leave the logging issue there; no more detail is needed for now.
Please do not summarize while I reorder the material.
Put the rollback explanation on hold while I check a record.
'''),
'essential_intent_missing':(False, '''
接下来有个结果要你评估，结果本身还没展示
我会让你从一组还未列出的工具中选择
帮我判断接下来那个条件能否成立，条件我还没讲
有一段伪代码要你解释，不过我还没把代码读出来
要比较的两种策略尚未指定，我现在才开始介绍
我需要你估一个值，但是估算目标还没说
请分析下面这个异常，我还没有给出异常的现象
有个取舍想听你的意见，具体是哪两个选项我还没提
我准备让你给几个任务排序，但任务列表仍未提供
我想问你会如何应对，具体发生了什么我下一句才说
I have a result for you to assess, but the result itself has not been shown yet.
I will ask you to choose from a set of tools that I have not listed.
Judge whether the next condition holds, although I have not stated that condition yet.
There is pseudocode I want explained, and the code has not been supplied so far.
The two strategies to compare have not been named at this point.
I need an estimate, but the quantity to estimate remains unspecified.
Analyze the fault I am about to describe; its symptoms have not been given yet.
I want your view on a tradeoff whose alternatives I have not introduced.
Rank several tasks for me, but the task list has not been provided.
How would you respond, with the actual event still to be described in my next sentence.
'''),
'narration_or_ack':(False, '''
重试为何没有重复记录你已经解释得足够清楚
解析器的细节我现在明白了，没有新的追问
我在把你刚才的性能测试说明写进笔记
这是我处理远端故障的经历，已经讲完
每批大小的依据我自己找到了，不需要再答
你给的调试例子已经满足我的要求
旧格式保留的原因在文档里有，我看明白了
我已经把回滚演练的步骤全部记下来了
我当时先检查数据，再调整缓存配置
这个答案校验方法你说完整了，我没有补充问题
Your explanation makes clear why the retry did not create another record.
I understand the parser details now and have no further question.
I am adding your benchmark explanation to my notes.
That finishes my own account of handling the remote failure.
I found the reason for the batch size myself and do not need another answer.
The debugging example you gave meets my request fully.
I have understood the reason for retaining the format from the documentation.
I have finished recording all the steps of the rollback rehearsal.
At that point I checked the data and then adjusted the cache configuration.
You have covered the answer-checking method completely and I have nothing more to ask.
''')}

def main():
    p=argparse.ArgumentParser();p.add_argument('--previous',type=Path,nargs='+',required=True);p.add_argument('--out',type=Path,required=True);a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite holdout')
    used=set()
    for folder in a.previous:
        for f in folder.glob('*.json'):
            rows=json.loads(f.read_text())
            if isinstance(rows,list):used.update(normalized(r['text']) for r in rows if isinstance(r,dict) and 'text' in r)
    rows=build('noisy-final',FINAL);keys=[normalized(r['text']) for r in rows]
    assert len(rows)==160 and sum(r['respond'] for r in rows)==80 and len(set(keys))==160
    assert not used.intersection(keys),used.intersection(keys)
    a.out.mkdir(parents=True);f=a.out/'acceptance.json';f.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
    review=dict(frozen_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),count=160,positive=80,sha256=hashlib.sha256(f.read_bytes()).hexdigest(),model_scores_seen=False,
        annotation='Understandable current request or contextual follow-up is positive even with incomplete grammar; actual quotation, wait/withdrawal, resolved statements and missing essential task are negative. Single-annotator synthetic benchmark, no population claim.',
        policy='All160 original/native-ASR short/long contexts, frozen labels and no exclusions. Existing gates unchanged.',disjoint_from=[str(x) for x in a.previous])
    (a.out/'pre-score-review.json').write_text(json.dumps(review,indent=2)+'\n');print(json.dumps(review,indent=2))

if __name__=='__main__':main()
