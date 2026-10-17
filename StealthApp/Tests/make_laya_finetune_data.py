#!/usr/bin/env python3
"""Offline, synthetic task data. No user transcripts or teacher API calls.

Training varies topic/context around explicitly labelled utterance families.
Calibration/dev/acceptance are independently authored, not random row splits.
This is a small engineering benchmark, not a population accuracy estimate.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import random
import sys


ROOT = Path(__file__).resolve().parents[1]


def worker_module():
    spec = importlib.util.spec_from_file_location("worker", ROOT / "Resources/LayaRuntime/worker.py")
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    return worker


def turn(speaker, text, handled=False):
    return dict(speaker=speaker, text=text, handled=handled)


def case(identifier, family, text, respond, history=(), speaker="Room"):
    return dict(id=identifier, family=family, text=text, respond=respond,
                context=dict(currentSpeaker=speaker, recentTurns=list(history)))


TOPICS = ["缓存淘汰策略", "订单处理流程", "数据权限设计", "告警系统", "跨团队协作", "离线评估", "毕业论文", "职业规划"]
EN_TOPICS = ["cache eviction", "order processing", "access control", "alert delivery", "team collaboration", "offline evaluation", "your thesis", "career planning"]

POSITIVE = [
    "说说你对{t}的理解", "请用一个例子说明{t}", "麻烦介绍一下{t}", "你可以解释一下{t}吗",
    "详细讲讲{t}吧", "展开谈谈{t}", "我想听听你如何看待{t}", "关于{t}，请说一下你的实际经验",
    "从头梳理一遍{t}", "先讲{t}，重点说你负责的部分", "给我们介绍下{t}的背景和结果",
    "你为什么这样做{t}", "{t}遇到的困难是什么", "{t}还有什么改进空间",
    "你当时怎么推进{t}的", "假如重新做{t}，你会改变什么", "{t}的收益有多大",
    "{t}有几种替代方案", "你能对比一下{t}的不同实现吗", "请补充{t}的细节",
    "我没听清{t}这一段，能再说一遍吗", "不用讲所有经历，只讲{t}", "别展开背景，直接解释{t}",
    "先不讨论预算，讲讲{t}的技术方案", "用英文解释{t}", "把{t}总结成三点", "请反驳一下关于{t}的这个观点",
    "{t}呢", "那{t}这块呢", "我想问的是{t}如何落地", "请继续，{t}还没讲完", "{t}这里你再具体一点",
    "Walk me through {e}.", "Could you elaborate on {e}?", "Explain {e} with an example.", "What went wrong with {e}?",
    "Tell me how you handled {e}.", "I'd like to hear your reasoning about {e}.", "And what about {e}?",
    "Don't cover the timeline; just describe {e}.", "Please summarize {e}.", "为什么{e}会成为瓶颈",
    "讲一下{e}的 trade-off", "先 explain 一下{t}的实现", "How would you improve {e}?",
]
NEGATIVE = [
    "我来介绍一下{t}", "{t}我可以展开说说", "我当时主要负责{t}", "{t}已经做完了",
    "刚才我已经解释了{t}", "我们采用的{t}比较简单", "关于{t}，我的回答是先做验证再上线",
    "我认为{t}还有改进空间", "今天我们讨论了{t}", "接下来由我讲解{t}", "{t}暂时不用介绍",
    "不需要再讲{t}了", "先别回答{t}，等我把题目说完", "关于{t}的问题撤回了", "我刚想问{t}，不过现在不问了",
    "他昨天让我讲一下{t}", "报告里写着：请解释{t}", "刚才那句话是‘介绍一下{t}’，我在复述",
    "我准备问他的题目是‘{t}有什么风险’", "{t}，嗯……", "我想请你解释{t}和",
    "关于{t}，如果我们", "请说明{t}，具体要求是", "我来讲{t}的原因，因为",
    "{t}的问题我稍后再提，现在先听我介绍背景", "行，{t}的解释我听明白了", "谢谢，你刚才把{t}讲清楚了",
    "不用回答，我只是自言自语：{t}真的有必要吗", "{t}为什么成功？因为我们先验证了需求",
    "{t}做得不错", "对，{t}就是这样", "目前没有关于{t}的新问题", "等一下，让我看一下{t}的材料",
    "I'll explain {e} myself.", "We implemented {e} last year.", "No need to explain {e}.",
    "She asked me to describe {e} yesterday.", "The document says 'Explain {e}'.",
    "I'd like to ask about {e}, but first let me finish the setup.", "For {e}, if we were to",
    "Thanks, that answers my question about {e}.", "Let me explain {e}.", "我们做了{e}，效果符合预期", "刚才的{e}问题已经结束了",
]


def training():
    result = []
    rng = random.Random(20261016)
    for label, patterns in [(True, POSITIVE), (False, NEGATIVE)]:
        for i, pattern in enumerate(patterns):
            for j, (topic, english) in enumerate(zip(TOPICS, EN_TOPICS)):
                text = pattern.format(t=topic, e=english)
                history = []
                if j % 3:
                    history = [turn("Them", "先介绍一下你最近做的工作", True),
                               turn("You", f"我的工作涉及{topic}，进行了需求分析、实现和测试。")]
                if j == 6 and i % 5 == 0:
                    history = [turn("Room", "这次讨论的背景资料较多。" + "我们上周完成了需求整理和文档归档，今天按计划交流进展。" * 90)] + history
                if j == 7 and i % 4 == 0:
                    history += [turn("Them", f"说说{topic}的思路", True), turn("You", "先小范围验证，再逐步扩大。")]
                result.append(case(f"train-{int(label)}-{i}-{j}", f"train-{int(label)}-{i}", text, label, history,
                                   rng.choice(["Room", "Them"])))
    # Same current text with different surrounding dialogue: learn intent, not punctuation.
    context_pairs = [
        ("然后呢", "我们先完成了数据采集。", "我把他的话逐字复述给你听：", True, False),
        ("第二种", "有两种实现方案。你想让我讲哪一种？", "我选择了第二种方案，具体名称是：", True, False),
        ("为什么", "线上性能比测试环境慢了很多。", "我在逐字读题，最后三个字是：", True, False),
        ("比如呢", "我用过一些缓解办法。", "接下来我复述别人当时的追问：", True, False),
        ("具体一点", "我会先做性能优化。", "评语只有四个字，我读一下：", True, False),
        ("能", "这个问题我可以先解释方案，也可以讲风险。你希望我讲风险吗？", "我能完成这个任务吗？我自己回答：", True, False),
    ]
    for i, (text, positive_context, negative_context, _, __) in enumerate(context_pairs):
        for j in range(8):
            for label, previous in [(True, positive_context), (False, negative_context)]:
                history = [turn("Room", f"本次讨论主题是{TOPICS[j]}。"), turn("You" if label else "Room", previous)]
                result.append(case(f"train-context-{i}-{j}-{int(label)}", f"train-context-{i}", text, label, history))
    rng.shuffle(result)
    return result


def manual(split, positive, negative):
    """Each nonempty line: current utterance [TAB immediate prior turn]."""
    result = []
    for label, block in [(True, positive), (False, negative)]:
        for i, line in enumerate(block.strip().splitlines()):
            parts = line.split("\t")
            history = [turn("You", parts[1])] if len(parts) == 2 else []
            result.append(case(f"{split}-{int(label)}-{i}", f"{split}-{int(label)}-{i}", parts[0], label, history))
    return result


CAL_POS = """
挑一段你最熟悉的经历聊聊
这项改造的动机是什么
请把逻辑再捋顺一些
用通俗的话描述一下向量检索
你如何确认测试结果可信
这套系统由谁维护
对比传统做法有什么不同
如果只给你两周，你打算怎么做
你对这份岗位有什么期待
能不能补充一个失败的例子
刚才提到的准确率怎么算出来的
按照时间顺序，把排查过程复盘一下
那你自己的贡献呢	我们团队做了从需求到上线的全部工作。
如果数据量翻倍呢	现在一百万条记录可以正常运行。
另外一种怎么做	我比较过两种部署方式，第一种是直接部署。
为什么选它	我最终用了关系型数据库。
要多少人	这项任务需要专门组建团队。
结果如何	后来我们调整了采样参数。
Could you unpack that last point?
Give me the reasoning behind your decision.
How did you measure success?
Describe the hardest part in a few sentences.
Which option would you pick and why?
Can you illustrate that with numbers?
Your own role?	The team delivered the entire migration.
What happened next?	We switched off the failing component.
你能讲一下 distributed lock 的边界条件吗
这个 pipeline 怎么避免重复消费
不用重讲原理，告诉我你怎么测试的
不要只报数字，解释它的含义
我问的是上线以后，不是开发阶段，请重新回答
你没说清楚失败后的处理，再补充一下
"""
CAL_NEG = """
这一段由我来补充
稍等，我还没说完
这项改造是为了降低成本
向量检索能够查找语义相似内容
我们用人工标注的样本验证结果
维护工作交给了平台团队
下面先给你看背景，暂时不用回答
先打住，这道题跳过
我已经了解你的岗位期待
刚才的例子已经很清楚了
准确率是正确样本数除以总样本数
我现在复盘一下排查过程
那你自己的贡献呢，这是上次考官问我的原话
数据量翻倍的问题，我们已经答过了
另外一种怎么做，这个问题我不问了
我打算问原因，但先让我把背景交代完
要多少人由负责人再决定
结果如何需要等下周的数据
I'll unpack that last point now.
The reason was lower maintenance cost.
Don't answer yet; I'm still framing the question.
That was a quote from the interview script.
We picked the second option.
The numbers are in the appendix.
Your own role? That is the question printed on this card.
Next, we rolled back the deployment.
这个 distributed lock 是同事写的
pipeline 已经做了消费去重
不用重讲，也不需要补充了
不要解释，继续听我讲
我问的是上线以后……算了，跳过吧
你没说清楚的地方我回头再看，目前不用回答
"""
DEV_POS = """
把你排查过的一次生产故障讲给我听
这件事最难在哪儿
我想知道你怎样协调不同意见
按你的经验，哪个环节最容易出错
先举例，再解释概念
说一个你不赞同的团队决定
可不可以换一种讲法
这个取舍你是怎么想的
再往下讲	我完成了问题定位，然后准备上线修复。
后面两个也过一下	一共有三个阶段，第一个是调研。
假设预算减半呢	原计划需要购买两台服务器。
那谁负责回滚	发布任务由值班工程师执行。
你的结论是什么	我比较了两组实验结果。
还有没有更轻的方案	目前方案需要独立运行一个服务。
What did you personally own?
Please take me through the failure investigation.
Can you make that more concrete?
How would this behave under load?
And its limitations?	The algorithm works well on short inputs.
What about the other team?	Our team finished early.
详细解释一下 backpressure
你如何选择 chunk size
别复述论文了，谈谈你的判断
不要求推导，说明直觉就可以
"""
DEV_NEG = """
我排查过一次生产故障，现在给你介绍
最难的是协调发布窗口
我正在整理不同意见
这个环节容易出错，已经加了监控
先举例再解释概念，是这篇文章的结构
我对当时的团队决定有些不同意见
可不可以换一种讲法，这是观众昨天给我的留言
这个取舍暂且不谈
再往下讲，是录音中出现的四个字
后面两个就略过吧
假设预算减半……等一下，我换个条件
谁负责回滚不用在这里讨论
你的结论我已经记录好了
还有没有更轻的方案，我会自己去调研
I owned the release pipeline.
I'll describe the failure investigation shortly.
That makes it more concrete, thanks.
It handled the load well.
And its limitations? That was the last question on the survey.
The other team finished later.
backpressure 负责抑制过快的生产速度
chunk size 是根据离线评估选的
不用谈你的判断了，到此为止
我想知道这段推导的
"""
TEST_POS = """
把你最有成就感的那次交付复述给大家听
就拿刚才那个例子，给我画一遍数据流
我想听的不只是结论，谈谈中间怎么做的
站在接手人的角度，你会从哪里读代码
假设突然来了十倍流量，你第一步做什么
给这个设计找两个潜在问题
结合一次真实经历说明你怎么处理分歧
这部分由你来补充说明吧
把论证中最关键的一步说透
挑一个你亲手优化的地方展开
我不熟悉这个缩写，解释给我听
你提到做过实验，具体的数据能分享一下吗
用一句话概括你的方案价值
说一说从这次失败中学到什么
不谈实现，只说明采用它的理由
原理先放一边，先回答为何没有用现成服务
别列一堆选项，推荐一个并说明原因
再来个不一样的例子
就这一点多说几句	我们把热数据与冷数据分开存储。
中间那项呢	我做过推荐、搜索和结算三个模块。
为什么不反过来	我先清洗数据，然后再进行去重。
做到什么程度了	去年我们开始做架构迁移。
凭什么这么说	我觉得这个实现更稳定。
再后面发生了什么	我们完成第一轮试运行。
万一没赶上呢	我打算在周五前交付。
你倾向哪个	一个方案成本低，另一个方案延迟更小。
两者差别在哪里	我们还评估了另一种索引。
能量化吗	效果有明显提升。
Tell me about a time you changed your mind.
Make the case for this architecture.
Help me understand the bottleneck.
Talk us through one concrete tradeoff.
What evidence supports that conclusion?
Please revisit the second point in more depth.
Why not the simpler alternative?
What would you do differently today?
How so?	This made the system easier to operate.
For instance?	There were several unexpected edge cases.
And the downside?	We moved everything to local storage.
Which one was yours?	There were four separate deliverables.
这个 retry policy 的风险你解释下
用中文把 eventual consistency 讲明白
What if 网络一直不恢复
latency budget 是怎么分配的
把 CPU 和 GPU 两条链路比较一下
先解释评估方法，然后说结果
我换个问法，你在这个项目里到底解决了什么
不需要重新自我介绍，只讲离职原因
"""
TEST_NEG = """
我把最有成就感的那次交付复述给大家听
刚才那个例子的数据流我已经画在白板上了
不只是结论，中间过程我也记录了
站在接手人的角度，我会先读入口代码
十倍流量的情况先不用考虑
这个设计有两个潜在问题，我接着讲
我处理分歧通常会先听取双方意见
这部分由我补充说明
论证中最关键的一步我稍后再说
亲手优化的地方主要在数据访问层
这个缩写我去查一下，你先不用解释
实验数据在报告里，我们继续看下一页
我知道方案价值了，可以停在这里
从这次失败中学到了先做小规模验证
不谈实现，也先不谈采用理由
现成服务的限制是我自己发现的
别列选项了，现在不需要建议
不用再举例，我明白了
就这一点多说几句，这是我复述的审稿意见
中间那项不用展开了
为什么不反过来……我先把完整题干念完
做到什么程度由明天的评审决定
凭什么这么说，我当时就在心里想这句话
再后面发生的事我自己来讲
万一没赶上……让我想一下要问什么
我倾向第一个方案
两者差别主要是内存开销
量化数据我稍后自己补上
I changed my mind after reviewing the logs.
I'll make the case for this architecture.
The bottleneck was disk access.
No need to talk through the tradeoff now.
The evidence is included in the appendix.
The second point has been covered already.
Why not the simpler alternative? That's a line from yesterday's notes.
Today I'd start with a smaller deployment.
How so? I was reading that phrase aloud, not asking you.
For instance, the input can be empty.
The downside is extra disk usage.
The fourth deliverable was mine.
retry policy 的风险我刚刚说过了
eventual consistency 指的是最终会收敛
网络不恢复的话我会切到离线模式
latency budget 已经分配好了
CPU 和 GPU 两条链路我在附录里比较了
先解释评估方法，然后……等等，先不回答
我换个问法，你在这个项目里到底
离职原因不必回答，我们继续别的话题
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to rewrite frozen data")
    sys.path.insert(0, str(args.runtime / "source"))
    import laya_mlx
    agent = laya_mlx.load(args.runtime / "model", dtype="float16")
    worker = worker_module()
    splits = dict(train=training(), calibration=manual("calibration", CAL_POS, CAL_NEG),
                  development=manual("development", DEV_POS, DEV_NEG),
                  acceptance=manual("acceptance", TEST_POS, TEST_NEG))
    # Known challenges remain regression-only; none are training examples.
    splits["regression"] = []
    for name in ("laya_rolling_samples.json", "laya_official_audit_holdout.json"):
        for c in json.loads((ROOT / "Tests" / name).read_text()):
            splits["regression"].append(dict(c, family="exposed-regression", id=name + ":" + c["id"]))
    seen = {}
    manifest = dict(schema=1, provenance="Locally authored synthetic data; no user transcripts or external teachers.",
                    split_policy="Independently authored utterance families; no random row split. Regression is previously exposed.",
                    limitations="Small synthetic engineering benchmark; not an estimate of real conversation accuracy.",
                    question=worker.QUESTIONS, context_tokens=1024, threshold=0.8,
                    acceptance_gate=dict(recall_min=.95, false_positive_rate_max=.05,
                                         regression_accuracy_min=.95, require_swift_integration=True), splits={})
    args.output.mkdir(parents=True)
    for split, cases in splits.items():
        rows, lengths = [], []
        for c in cases:
            state, length = worker.prepare_state(agent, c["text"], json.dumps(c["context"], ensure_ascii=False))
            signature = hashlib.sha256(state.encode()).hexdigest()
            if signature in seen and seen[signature] != split and split != "regression":
                raise ValueError(f"cross-split duplicate {c['id']}")
            seen[signature] = split
            lengths.append(length)
            rows.append(dict(state=state, questions=worker.QUESTIONS, expected={"needs_response": c["respond"]}))
        fixture = args.output / f"{split}.json"
        fixture.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + "\n")
        data = args.output / f"{split}.jsonl"
        data.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows))
        manifest["splits"][split] = dict(count=len(cases), positive=sum(c["respond"] for c in cases),
                                        tokens_max=max(lengths), sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                                        fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (args.output / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
