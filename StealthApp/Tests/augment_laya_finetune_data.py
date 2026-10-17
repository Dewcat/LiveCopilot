#!/usr/bin/env python3
"""Training-only diversity augmentation selected from development diagnostics.

No acceptance results were read when this was authored. Frozen non-training
splits are copied byte-for-byte. These are training examples, not runtime rules.
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import sys

from make_laya_finetune_data import manual, worker_module, turn, case

POSITIVE = """
请你接着讲
往下说吧
您给大家说两句
仔细说说这个
能再仔细些么
我没跟上，你从这儿重新讲
换个角度解释给我听
请以实际操作为例
给我演示一下
说出这个实现的缺陷
概括一下核心步骤
先谈背景再谈技术
先用简单的例子帮我理解，然后谈复杂的情况
先说设计目标，随后说怎么验证它
不用写代码，把算法过程描述出来
不必说全部步骤，挑关键部分说明
不要管性能，先给一个能工作的思路
你能不能用更容易理解的话介绍
方便讲讲你当时的考虑么
能否把其中的理由也交代一下
可以把这个术语换成日常用语来讲吗
可不可以从使用者的视角再讲一次
先把刚才的数字解释清楚
根据你的经历，给些可操作的建议
设身处地想一下，如果是你会怎么处理
让你来拍板，你选哪条路
说点自己动手做的事
聊个你最近遇到的挑战
复现步骤你描述一下
你的具体分工，麻烦讲明白
这些名词我不懂，给我解释一下
你能归纳一下吗
把关键区别列出来吧
这件事和你的研究有什么联系
为什么没采用开源版本
谁来批准这个变更
什么时候决定切换架构的
最后是否达到了目标
有没有衡量这种提升的指标
还有别的办法吗
你们试过把这一步省掉吗
你觉得哪个最值得做
这一点的依据在哪
最开始怎么发现异常的
这个限制能解除吗
现在最缺什么
这算哪种类型的问题
在什么条件下会失败
成本是不是太高了
除了时间，还有别的约束么
这段代码有什么用
具体是哪一步导致的
你能帮我理解这张图吗
对上面这句话，你同意还是不同意
从业务角度怎么看
我想请教一下，你怎样保证结果一致
你来说说看
你觉得呢
凭啥	我认为这个指标足够衡量质量。
怎么做到的	我们把启动时间缩短了一半。
何以见得	我觉得这个方案比较可靠。
多快	优化之后响应速度提升很多。
多少	我们花了一笔经费来做调研。
多久能完成	迁移需要分阶段实施。
什么时候	我们打算停止维护旧接口。
还有谁	主要由两个人一起负责。
你的部分	这是整个团队的成果。
其他人呢	我负责数据处理这一块。
展开这块	我们还做了容错处理。
细节呢	我加入了一个重试机制。
影响呢	我们暂时关掉了缓存。
然后怎么处理	线上出现了一批失败请求。
有备选么	我们想依赖第三方组件。
说点缺点	这套方案实现简单而且成本低。
那相反的情况	数据比较少时我们直接扫描。
剩下的也说说	我负责设计、开发、测试三个环节，设计部分已经介绍了。
最后一个多讲些	这个系统分成采集、清洗、索引三个阶段。
如果是在线的	这套流程目前只做离线计算。
改成串行会怎样	现在三个任务同时执行。
那换个场景呢	刚才以电商数据为例做了说明。
这个结论怎么验证	我认为压缩后效果不会有明显下降。
Keep going, please.
Go into more detail.
Try explaining it another way.
Break this down for me.
Put that in plain English.
Show me an example of the workflow.
Name a disadvantage.
Start with a small example, then generalize.
First outline the goal, then describe your implementation.
You can skip the math, but explain the intuition.
Don't list tools; describe what you built.
Would you mind clarifying the last sentence?
Can we hear more about your contribution?
I'd appreciate a more detailed explanation.
Could you expand upon the incident response?
Take us through the lifecycle of a request.
Suppose the database is down. What happens?
Is there any less expensive way to do it?
What else did you consider?
How much memory did that save?
Who made the final decision?
When did you notice the regression?
Where does the validation happen?
Does this work with multiple workers?
Would this still hold for smaller inputs?
Why was that necessary?
How can you tell?	The system seems more reliable now.
Any alternatives?	We chose a managed queue.
And then?	We first disabled the broken job.
Your contribution?	We collectively delivered three milestones.
How many?	Several users reported the problem.
In what way?	It improved the developer experience.
What changed?	The results were different in the second experiment.
Can you 给个例子
从 scalability 角度评价一下
这个 API 的 error handling 怎么安排的
请把失败时的 fallback 过程走一遍
分别讲一下 precision 和 recall
不用切英文，中文说下这个 bug 的根因
再讲讲你刚才提到的 load balancing
如果 CPU 忙不过来怎么处理
"""
NEGATIVE = """
我接着讲
我往下说
我给大家说两句
我仔细说说这个
我可以讲得再仔细一些
我刚才没讲清楚，现在重新解释
下面我换个角度解释
我以实际操作为例说明一下
我现在给你演示
这个实现有一些缺陷
核心步骤有三个
我先谈背景再谈技术
我先讲简单情况，再介绍复杂情况
设计目标后面会在文档里说明
代码可以不用写，我们先结束这一部分
不必继续说步骤了
现在不需要你提出思路
我能用更容易理解的话介绍
关于当时的考虑我自己说一下
其中的理由我稍后补充
文章把技术术语转换成了日常用语
使用者的视角这次先不讨论
刚才的数字没有问题，继续听我讲
根据我的经历，先做验证比较好
如果是我，会先找相关同事确认
让我来拍板的话，我会选便宜的
自己动手做的事主要是联调
我最近遇到的挑战是数据格式不统一
复现步骤已经给了开发人员
具体分工我记下了，不用再说
这些名词我待会自己查
归纳起来就是先试验后推广
关键区别在于是否需要联网
这件事和研究的联系我自己会补充
为什么没采用开源版本，我当时也是这样问他的
谁来批准变更这个问题留待下次再问
切换架构的决定是去年作出的
最后我们达到了目标
衡量指标已经放在页面上了
没有别的办法了，我只是感叹一下
我们已经试过省掉这一步
我觉得最值得做的是改进质量
这一点的依据在论文里
异常最早由告警发现
这个限制暂时不能解除
现在最缺测试数据
这是资源竞争问题
输入为空时会失败
成本确实偏高
除时间以外还有内存约束
这段代码负责释放资源
具体是哪一步导致的，我正在自己查
这张图我已经理解了
上面那句话暂时不需要表态
业务角度的问题以后再说
结果一致性我还在讲，先不要插话
你先别说
我的意思就是这些
凭啥，是那条评论的全部内容
怎么做到的？靠增加批量大小就做到了
何以见得，我先保留这个问题
多快还没有测出来
多少由财务去统计
多久能完成我还没有估出来
什么时候我想好了再说
还有谁参加我已经确认了
你的部分已经讲完了
其他人呢，我在读会议记录里的问题
这块不要展开
细节留在文档中就行
影响我已经了解了
然后怎么处理我会自己决定
备选暂时不用讨论
缺点不用再说了
相反的情况还没测过
剩下的不用说了
最后一个不必解释
在线的情况先放一放
串行的版本已经做过对照
换个场景之后我再提问
这个结论我自己验证过
I'll keep going.
No further detail is needed.
I'll try explaining it another way.
This breaks down into four steps.
The guide is written in plain English.
Let me show you an example of the workflow.
The disadvantage is increased complexity.
I started with a small example and generalized it.
The goal was lower latency, and the implementation used caching.
You can skip the rest of this answer.
I built a small command-line tool.
The last sentence is clear now, thanks.
Your contribution has been noted.
We don't need a more detailed explanation now.
The incident response was handled by another team.
The request lifecycle is documented here.
Suppose the database is down, and then if
There is a less expensive way to do it.
We considered several other options.
It saved roughly a third of the memory.
The lead made the final decision.
We noticed the regression yesterday.
Validation happens at the gateway.
It works with multiple workers.
This still holds for smaller inputs.
Why was that necessary? I'm quoting the question I was asked last time.
How can you tell, that's what the slide says.
The alternatives are listed in the proposal.
And then we restored the backup.
My contribution was implementing the client.
How many... wait, I haven't finished the question.
In what way, I will explain that next.
What changed is the input format.
这个 API 的 error handling 已经修好了
fallback 过程我来讲一遍
precision 和 recall 这两个指标我都统计了
这个 bug 的根因现在不用讲了
load balancing 是后面一页的标题
CPU 忙不过来时我们就限制并发数
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit("Refusing to rewrite data")
    sys.path.insert(0, str(args.runtime / "source"))
    import laya_mlx
    agent = laya_mlx.load(args.runtime / "model", dtype="float16")
    worker = worker_module()
    shutil.copytree(args.data, args.out)
    rows = json.loads((args.out / "train.json").read_text())
    additions = manual("aug-v2", POSITIVE, NEGATIVE)
    for row in additions:
        rows.append(row)
        # Context augmentation is training-only; whole utterance families stay together.
        for i in range(2):
            background = [turn("Them", "请谈谈你近期的工作。", True),
                          turn("You", "我最近完成了一个服务重构，做了监控、测试和发布。")]
            if i:
                background = [turn("Room", "上一阶段的讨论已经结束。" + "我们完成了访谈资料整理、问题分类和文档归档。" * 90)] + background
            rows.append(case(row["id"] + f"-context-{i}", row["family"], row["text"], row["respond"],
                             background + row["context"]["recentTurns"], "Them" if i else "Room"))
    heldout_texts = {c["text"] for split in ("calibration", "development", "acceptance")
                     for c in json.loads((args.data / f"{split}.json").read_text())}
    assert not heldout_texts.intersection(c["text"] for c in additions), "Exact held-out utterance leak"
    # Long-context augmentation on every family is expensive; include one in eight.
    rows = [r for i, r in enumerate(rows) if not r["id"].endswith("-context-1") or i % 8 == 0]
    import random
    random.Random(20261017).shuffle(rows)
    encoded, lengths = [], []
    for row in rows:
        state, length = worker.prepare_state(agent, row["text"], json.dumps(row["context"], ensure_ascii=False))
        encoded.append(dict(state=state, questions=worker.QUESTIONS, expected={"needs_response": row["respond"]}))
        lengths.append(length)
    fixture = args.out / "train.json"
    fixture.write_text(json.dumps(rows, ensure_ascii=False, indent=2) + "\n")
    data = args.out / "train.jsonl"
    data.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in encoded))
    manifest = json.loads((args.out / "manifest.json").read_text())
    manifest["augmentation"] = "v2: independently authored training dialogue diversity after development-only diagnostics; unchanged frozen non-training splits"
    manifest["splits"]["train"] = dict(count=len(rows), positive=sum(c["respond"] for c in rows), tokens_max=max(lengths),
                                        sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                                        fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (args.out / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(manifest["splits"]["train"]))


if __name__ == "__main__":
    main()
