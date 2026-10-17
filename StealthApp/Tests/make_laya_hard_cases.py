#!/usr/bin/env python3
"""Training-only contrastive examples and a newly authored frozen acceptance set.

No inference rules, user recordings, remote APIs, or previous acceptance rows in
training. Historical tests become exposed development/regression evidence.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import random
import sys

from make_laya_finetune_data import case, manual, turn, worker_module

# Each pair differs in intent despite sharing question words. A family is never
# split across training and validation. These strings are never imported by app code.
REPORT_PAIRS = [
    ("有人在评审中问我{q}", "有人在评审中问我{q}，我也想听听你的答案"),
    ("{q}，这是昨天收到的提问", "{q}，这是我现在想请教你的"),
    ("{q}，这句只是我读的题目，不用作答", "{q}，读完题目了，现在请作答"),
    ("同事留言让我解释{t}，我正在转述留言", "同事留言让我解释{t}，你帮我组织一下怎么回答"),
    ("我以前被问过{q}", "你现在回答一下{q}"),
    ("{q}，这是会议记录里的原话", "{q}，这个问题请你现场回答"),
    ("我在讲一个故事，故事里的人问{q}", "故事里的这个问题也请你解释一下：{q}"),
    ("{q}，这句话是练习朗读的内容", "{q}，请给出你的看法"),
    ("讲一下{t}这几个字出现在屏幕上", "讲一下{t}这几个字是什么意思，解释一下"),
    ("他们的问题围绕{t}，已经回答过了", "他们问了{t}，你也说说你的理解"),
    ("{q}是我给别人准备的题，不是在问你", "{q}是给你的题，现在轮到你回答"),
    ("请说明{t}，这段话是说明书中的要求", "请说明{t}，我现在确实需要你说明"),
    ("{q}这种问法不太清楚，我在评价题干", "{q}这种问法是什么意思，你解释一下"),
    ("我打算明天问他{q}，现在先做个记录", "我想现在问你{q}"),
    ("{q}是上次面试中的一道题", "{q}这道题你会怎么回答"),
    ("他说要我描述{t}，后来我已经给他讲过了", "他说要我描述{t}，请你示范一下怎么讲"),
]
CANCEL_PAIRS = [
    ("{q}，等会儿，先别答", "{q}，现在可以答了"),
    ("{q}，算了，跳到下一项", "{q}，不用长篇大论，简短说说即可"),
    ("{q}，这个问题取消", "{q}，取消前一个问题，回答这个"),
    ("{q}，不用解释，我自己想想", "{q}，不用解释原理，只告诉我结果"),
    ("关于{t}，先不要回答", "关于{t}，先不要讲历史，只讲实现"),
    ("{t}暂时不要求你说明", "{t}不要求推公式，说清含义就好"),
    ("我没让你现在回答{q}", "我没让你讲别的，现在回答{q}"),
    ("停止回答{t}，先听我补充", "停止讲背景，介绍{t}的实际做法"),
    ("{q}，这个等下一轮再谈", "{q}，其他问题等下一轮，这个先说"),
    ("不要急着说{t}，我还在给条件", "不要急着下结论，先解释{t}"),
    ("{q}现在不需要答复", "{q}不需要准确数字，说个大概就行"),
    ("{q}，当我没问", "{q}，不用考虑上个问题"),
    ("{t}先别讲，其他部分也不用讲了", "{t}先别讲，先说你负责什么"),
    ("不谈{t}，也不要求你补充", "不谈{t}的细节，只说明你为什么选它"),
    ("{q}，撤回这句话", "{q}，不要重复刚才的答案，换个例子讲"),
    ("现在请你保持安静，{t}稍后再讲", "现在请你开始说明{t}"),
]
PARTIAL_PAIRS = [
    ("我想问{t}在", "我想问{t}在高负载下如何工作"),
    ("你能不能从{t}的", "你能不能从{t}的成本角度分析一下"),
    ("请你结合{t}以及", "请你结合{t}以及实际需求介绍实现方式"),
    ("{q}，尤其是在", "{q}，尤其是在出错的情况下"),
    ("{q}，因为", "{q}，因为我想了解选型依据"),
    ("如果{t}出现", "如果{t}出现问题，你会怎么处理"),
    ("请描述{t}，假设", "请描述{t}，假设资源只有原来的一半"),
    ("{t}跟", "{t}跟另一种方案比，有什么好处"),
    ("我准备请你说明{t}，要求如下", "我准备请你说明{t}，要求是言简意赅"),
    ("关于{t}，先给你两个前提，第一个是", "关于{t}，你有哪些实践经验"),
    ("{q}，不是，我重新组织一下", "{q}，换句话说，请说说你的判断依据"),
    ("你认为{t}能否", "你认为{t}能否独立运行"),
    ("为什么{t}要使用", "为什么{t}要使用这个组件"),
    ("当{t}还没有", "当{t}还没有上线，你如何测试它"),
    ("我换个问题，{t}到底是怎么把", "我换个问题，{t}到底是怎么把数据保存下来的"),
    ("{q}，让我先补完条件再回答", "{q}，条件补充完了，请回答"),
    ("请比较{t}与", "请比较{t}与现有做法的差异"),
    ("假如把{t}里面的", "假如把{t}里面的缓存去掉，会怎样"),
    ("我的问题是{t}的设计怎样才能", "我的问题是{t}的设计怎样才能更可靠"),
    ("{q}，以及怎么把", "{q}，以及怎么把成本降下来"),
]
STATEMENT_PAIRS = [
    ("{t}是我做过的一项改进", "{t}这一项改进你仔细介绍介绍"),
    ("{t}主要是为了解决重复操作", "{t}主要是为了解决什么问题"),
    ("从{t}的实践里学会了提前验证", "从{t}的实践里学到了什么，你说说"),
    ("我们做{t}的原因是降低维护开销", "你们做{t}的原因，具体说说吧"),
    ("{t}为什么成功，因为需求很明确", "{t}为什么成功，请你说明原因"),
    ("我来详细说一下{t}", "你来详细说一下{t}"),
    ("{t}是这种结构，我接着往下讲", "{t}是怎样的结构，请接着往下讲"),
    ("有关{t}的经验我已写成笔记", "有关{t}的经验，你给大家分享分享"),
]
EN_PAIRS = [
    ("{q} That's the question he asked me last week.", "{q} I'd like your answer now."),
    ("The script reads: {q}", "The script asks {q} Please answer it for me."),
    ("I'm quoting someone who asked me to describe {t}.", "Could you describe {t} for me?"),
    ("{q} Never mind, skip that.", "{q} Skip the introduction, just give me the reason."),
    ("Don't respond yet. I haven't finished asking about {t}.", "Don't explain the theory; tell me how you used {t}."),
    ("{q} Actually, hold your answer.", "{q} You can answer now."),
    ("I am not asking you to explain {t}.", "I am not asking for proof, just explain {t}."),
    ("Explain {t}, especially when", "Explain {t}, especially when the inputs are noisy."),
    ("Could you compare {t} with", "Could you compare {t} with the previous approach?"),
    ("What made {t} work, and how would you", "What made {t} work, and how would you improve it?"),
    ("In the event that {t} fails and", "In the event that {t} fails, what is your plan?"),
    ("Let me tell you how {t} works.", "Tell me how {t} works."),
    ("The lesson from {t} was to validate assumptions early.", "What was your biggest lesson from {t}?"),
    ("{q} This is just me reading aloud.", "{q} This time I want you to respond."),
]

CAL_POS = """
刚才的暂停结束了，现在把系统工作方式说明一下
他没听懂，所以请你重新给我们解释
不要讲资金安排，说明人力分工
不需要回忆日期，描述整个过程就行
别继续等了，请作答
我读完问题了，你现在来答
不用详细推算，给我个粗略估计
那段问题也适用于你，说说你的答案
他说让我解释单点故障，你教我怎么答
我已经把背景交代完了，你怎么看
前一个问题撤回，这个问题保留：你什么时候入职
请把时间线说明白，尤其是发生异常以后
在没有额外机器的条件下，你准备如何测试
这项工作怎么把离线结果用于在线请求
你说的第二项工作，再多讲一点
那个提议是否可行，请分析
The pause is over. Please answer the question now.
I don't need the equations, just the practical reasoning.
My colleague asked about recovery. Help me draft an answer.
Answer the question I just read to you.
Leave out the budget and focus on reliability.
With that extra condition in mind, what would you choose?
Could you finish explaining the installation procedure?
That is the entire question; please respond.
背景我讲完了，你解释一下这个 deployment 的机制
不要讲 framework 的历史，解释为什么要引入它
他说要我介绍 workflow，你示范给我听
我想了解这个任务在输入格式不固定时怎么处理
你提出过哪些改动，我想听具体的
这张流程图中出错的路径你走一遍
只说它为什么有效就可以，不必复述实验
前面说了两项，余下那项也介绍介绍
"""
CAL_NEG = """
先等我把其他条件说完，你再开始
他没听懂，所以我又给他解释了一遍
不要讲资金安排，人力分工也先不讨论
不需要再描述过程了
别作答，先等一下
我还在读问题，你先别答
我知道大致估计了，可以停了
那段问题是采访稿里摘录的
他说让我解释单点故障，这是我讲述的过去经历
我还没把背景交代完
前后两个问题都撤回，先暂停
请把时间线说明白，尤其是发生
在没有额外机器的条件下，如果要把
这项工作怎么把离线结果
你说的第二项工作，我在笔记里标好了
那个提议是否可行，这只是文件里的标题
The pause continues; don't answer yet.
I don't need the equations or any explanation now.
My colleague asked about recovery, and I answered him yesterday.
I am still reading the question to you.
Leave out the whole answer for now.
With that extra condition in mind, if we were to
Could you finish explaining the installation procedure and also the
That is not the entire question yet.
这个 deployment 的机制我自己已经弄明白了
framework 的历史和原因现在都不用讲
他说要我介绍 workflow，这句我已经转述完了
我想了解这个任务在输入格式
你提出过哪些改动，这是我记在纸上的问题，暂时不问
这张流程图我自己走一遍，你不用出声
为什么有效这个问题也先放着
前面说了两项，余下那项也先不用介绍
"""

# Independently authored after v2, frozen BEFORE scoring/training this stage.
# 72 positives and 72 negatives; categories exercise scope, quotation, and ASR endings.
ACCEPT_POS = """
题目念完了，请开始你的陈述
上一位问你如何保证正确性，我也有这个疑问，能解答一下吗
照着刚才那道题，现在现场给我讲一遍你的思路
面试官曾问我容灾怎么做，你能给个参考回答吗
这句话我是在直接问你：团队怎么分配任务
我刚才是在转述，现在请你评价一下那个方案
引用结束了，谈谈你是否赞同
这条留言我不知道怎么回，你帮我拟一下
有人问过类似问题，但这回我想听你的解释
刚才念的那句话是问题，请你就它展开
同样的问题也请你答一答
把面试稿里的这一问回答给我听
他说为什么会超时，你觉得原因是什么
那句话不是让你复述，是希望你解释其中的意思
报告要求阐明局限，你介绍一下我们有哪些局限
在别人答案的基础上，你补充一点自己的看法
不用讨论封面，说明正文的组织方式
不必介绍全部组件，只解释协调器
不要写伪代码，用口头描述就行
忽略之前的限制，现在你准备怎么实现
前面那个不问了，我只想知道出故障后怎么恢复
背景可以省略，核心论据不能省，讲讲吧
不需要给出精确数字，估个范围
先别谈优势，重点讲风险
我不是让你猜，说明你已经观察到的现象
不要求百分百确定，说说你目前的判断
其他部分不用答，单独回答数据怎么来的
先不评价结果，把做法讲清楚
不用重复流程，只谈你修改了哪一步
这次不展开技术，告诉我如何协调资源
我不需要现成结论，想听你的推理过程
暂停结束，接着回答刚才的问题
我想了解你怎样在保证质量的同时控制交付时间
请结合一次具体的返工，说明为什么要改变流程
如果客户迟迟不给反馈，你会怎样推进
比较一下把处理放在客户端和服务端的差别
你的方法在遇到从没见过的输入时会发生什么
当依赖服务全部不可用时，怎样给用户提示
为什么要在提交之前做这次检查
假如只能保留一个检查步骤，你留下哪个
刚才你提到重复处理，具体是怎么避免的
那个中间层你再讲细点
候选方案里剩下的那个，也介绍给我听
在这个假设下呢	刚才说的是所有输入都正确的情况，现在假设有一半输入损坏。
以后谁接手呢	这项工作已经完成交付。
依据哪条证据	我认为延迟主要来自排队。
是怎么算的	我给出了一个预计完成时间。
如果完全没数据呢	我们通常会根据已有记录选择参数。
你个人干的那块呢	团队交付了从采集到报告的一整套系统。
成本能压到多少	目前的方案需要比较多的计算资源。
能换成日常例子讲吗
把最容易被忽略的一点单独拎出来说
请把正常路径和异常路径各走一次
用一句简单的话解释这个结论成立的条件
把这次合作中一次不同意见的沟通过程还原一下
你是在哪个环节发现假设不成立的
The quotation ends here. What is your view on it?
My interviewer asked how to roll back safely. How should I answer?
Please respond to the question on the card I just read.
I was reporting her question; now I want your answer too.
Skip the implementation details, but explain the motivation.
No need for a formal proof. Give me a practical explanation.
Don't answer the earlier question; tell me who owns the release instead.
You can stop waiting and begin your explanation.
If the inputs arrive out of order, how do you handle them?
Could you compare the normal case with the failure case?
What convinced you that the change was worthwhile?
The remaining one?	We evaluated three caching approaches and discussed the first two.
具体讲下这个 websocket 在断线后的重连过程
不用讲 tuning 细节，说说你怎么验证效果
我读完题了，解释一下这个 retry limit 的作用
如果没有 GPU，你会如何调整这条处理链
"""
ACCEPT_NEG = """
题目念完了，但还没到作答时间
上一位问你如何保证正确性，我只是复述他的话
照着刚才那道题讲思路，这是练习册上的要求，我在读练习册
面试官曾问我容灾怎么做，我后来把答案发给他了
团队怎么分配任务，这句是我从录音里抄下来的
我刚才转述的方案已经介绍结束了
引用结束了，这一段没有新的问题
这条留言我已经回复过
有人问过类似问题，我当时给了他解释
刚才念的那句话仅供引用，不需要回答
同样的问题昨天已经答复过了
面试稿里的这一问我已经打上了标记
他说为什么会超时，我只是把他的疑问读出来
那句话我是在复述，不是在要求你解释
报告要求阐明局限，这一条是我正在读的格式规范
我只是总结别人答案里补充了哪些看法
为什么选择这个结构，这段字是旧问卷的题干
请多举几个例子，这是观众当时说的话，现在我只是回放
The quotation ends here; that was not a question for you.
My interviewer asked how to roll back safely. I already answered her.
The card contains that question, but I am only transcribing it.
I was reporting her question and nothing more.
为什么要 retry，这句是日志注释里的问题
接着讲这个 websocket，是主持人昨天说的原话
先把回答停住，我需要核对材料
暂且不讨论任何方案
刚才那一问作废，你不用再组织答案
我先收回这个问题，等会换一个
不要继续解释，下一步先看屏幕
你先不必回应，我把题干改一下
目前既不需要细节，也不需要结论
等我发出开始的提示再作答
我不问原因了，先记到这里
技术和分工今天都先不展开
上面所有问题都先放下
先不要评价，让我把其他人的意见读完
我说暂停了，回答也请暂停
下一轮再说这个，现在先安静听
这个没必要回答，我们把它删掉
这一题我撤掉了，后面也暂时没有新题
先别讲可行性，风险也暂时不讲
我把这个提问收回，你先不用出声
Please hold off until I finish the setup.
Forget that entire question; there is nothing to answer now.
Stop explaining for a moment while I check my notes.
I withdraw both questions.
这个 workflow 的问题先撤销
不用再 explain，我还需要想想怎么问
我想了解你怎样在保证质量的同时把
请结合一次具体的返工，说明为什么要把
如果客户迟迟不给反馈，而且项目又
比较一下把处理放在客户端和
你的方法在遇到从没见过的输入时，假如
当依赖服务全部不可用时，我们要求
为什么要在提交之前先把
假如只能保留一个检查步骤，而另一个
刚才你提到重复处理，请结合
那个中间层你再讲细点，特别是当它
候选方案里剩下的那个，如果要让
我换一种说法，这个步骤究竟如何将
在这个假设下，假设还需要
以后谁接手呢，等等我还有一个条件
依据哪条证据，先别作答，我还在补题目
是怎么算的，这个我想等你看完材料后再问
如果完全没数据，并且我们
你个人干的那块，在另外一个
If the inputs arrive out of order and the client
Could you compare the normal case with
What convinced you that the change would be
Suppose the remaining approach cannot
这个 websocket 在断线之后如果
我想知道 retry limit 和
"""


def training_additions():
    result = []
    topics = [("任务调度", "任务调度如何保证公平"), ("日志采样", "为什么要进行日志采样"),
              ("资源回收", "资源回收是怎么实现的"), ("配置同步", "配置同步怎样处理冲突")]
    for category, pairs in [("reported", REPORT_PAIRS), ("withdrawn", CANCEL_PAIRS),
                            ("unfinished", PARTIAL_PAIRS), ("statement", STATEMENT_PAIRS)]:
        for i, pair in enumerate(pairs):
            for j, (topic, question) in enumerate(topics):
                for label, template in enumerate(pair):
                    history = [] if j % 2 == 0 else [turn("Them", "你最近负责哪些工作", True), turn("You", "最近负责服务的可靠性改造。")]
                    row = case(f"focus-{category}-{i}-{j}-{label}", f"focus-{category}-{i}",
                               template.format(t=topic, q=question), bool(label), history)
                    row["category"] = category
                    result.append(row)
    for i, pair in enumerate(EN_PAIRS):
        for j, (topic, question) in enumerate([("batching", "Why use batching?"), ("audit logging", "How does audit logging work?")]):
            for label, template in enumerate(pair):
                row = case(f"focus-en-{i}-{j}-{label}", f"focus-en-{i}", template.format(t=topic, q=question), bool(label))
                row["category"] = "english-contrast"
                result.append(row)
    # Further dialogue history perturbations keep current intent unchanged.
    for i, row in enumerate(list(result)):
        if i % 18 == 0:
            history = [turn("Them", "你如何设计测试环境", True),
                       turn("You", "我们先固定数据版本，再单独准备测试环境。" * 75)]
            result.append(case(row["id"] + "-long", row["family"], row["text"], row["respond"], history))
    return result


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--previous", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit("Refusing to overwrite frozen data")
    sys.path.insert(0, str(args.runtime / "source"))
    import laya_mlx
    worker = worker_module()
    agent = laya_mlx.load(args.runtime / "model", dtype="float16")
    previous = {s: json.loads((args.previous / f"{s}.json").read_text())
                for s in ("train", "calibration", "development", "acceptance", "regression")}
    fresh = manual("fresh-v3", ACCEPT_POS, ACCEPT_NEG)
    assert len(fresh) == 144, len(fresh)
    for row in fresh:
        i = int(row["id"].split("-")[-1])
        row["category"] = "request" if row["respond"] else ["reported", "withdrawn", "unfinished"][i // 24]
    old_texts = {c["text"] for rows in previous.values() for c in rows}
    assert not old_texts.intersection(c["text"] for c in fresh), "New acceptance must contain no old utterances"
    added = training_additions()
    cal = manual("calibration-v3", CAL_POS, CAL_NEG)
    splits = dict(train=previous["train"] + added, calibration=previous["calibration"] + cal,
                  development=previous["development"] + previous["acceptance"] + previous["regression"],
                  acceptance=fresh, regression=previous["regression"] + previous["acceptance"])
    train_texts = {r["text"] for r in splits["train"]}
    for split in ("calibration", "development", "acceptance"):
        assert not train_texts.intersection(r["text"] for r in splits[split]), f"Training utterance leak into {split}"
    random.Random(20261018).shuffle(splits["train"])
    args.out.mkdir(parents=True)
    manifest = dict(schema=1, created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    provenance="Local synthetic contrastive dialogue and ASR-prefix examples. No user transcripts or remote teacher.",
                    split_policy="Whole intent pairs remain in training. New acceptance independently authored and frozen before training. Previous acceptance now exposed development/regression only.",
                    question=worker.QUESTIONS, context_tokens=1024, threshold=.8, long_context_stride=2,
                    acceptance_gate=dict(recall_min=.95, false_positive_rate_max=.05, regression_accuracy_min=.95,
                                         require_swift_integration=True), splits={})
    for split, cases in splits.items():
        rows, counts = [], []
        for c in cases:
            state, count = worker.prepare_state(agent, c["text"], json.dumps(c["context"], ensure_ascii=False))
            rows.append(dict(state=state, questions=worker.QUESTIONS, expected=dict(needs_response=c["respond"])))
            counts.append(count)
        fixture = args.out / f"{split}.json"
        fixture.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n")
        data = args.out / f"{split}.jsonl"
        data.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows))
        manifest["splits"][split] = dict(count=len(cases), positive=sum(c["respond"] for c in cases),
                                        tokens_max=max(counts), sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                                        fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
