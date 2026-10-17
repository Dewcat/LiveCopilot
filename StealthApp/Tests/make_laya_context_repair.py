#!/usr/bin/env python3
"""Repair training coverage, not inference logic; reserve a second fresh holdout.

V3 acceptance is now exposed development evidence. None of its utterances is
copied into training. Balanced long-history augmentation preserves both labels.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import random
import sys

from make_laya_finetune_data import case, manual, turn, worker_module

# Negative and positive continuations share a stem. Short ASR-final prefixes can
# still be incomplete; finality is a transport property, not a semantic label.
PAIRS = [
    ("我想知道{t}如何把", "我想知道{t}如何把错误隔离开"),
    ("请分析{t}为什么要将", "请分析{t}为什么要将这两个步骤分开"),
    ("请结合{t}说明怎样在", "请结合{t}说明怎样在资源紧张时工作"),
    ("你能介绍{t}如何在保持性能的同时把", "你能介绍{t}如何在保持性能的同时把开销降下来"),
    ("介绍一下{t}，重点是它如何", "介绍一下{t}，重点是它如何处理失败"),
    ("比较一下{t}与它原来所", "比较一下{t}与它原来所用的实现"),
    ("请讲讲{t}，特别是当它", "请讲讲{t}，特别是当它没有足够权限时"),
    ("详细解释{t}，在这个过程中你", "详细解释{t}，在这个过程中你做了什么"),
    ("如果{t}来不及完成，并且", "如果{t}来不及完成，你会怎样安排"),
    ("为什么{t}必须先把", "为什么{t}必须先把数据做检查"),
    ("关于{t}，请结合", "关于{t}，请结合实际经历谈谈"),
    ("有关{t}，你给我分析一下当", "有关{t}，你给我分析一下当依赖失效时怎么办"),
    ("我想请教{t}究竟是如何将", "我想请教{t}究竟是如何将各部分连起来的"),
    ("假设{t}只能保留其中一项，那么你", "假设{t}只能保留其中一项，那么你选什么"),
    ("你会怎样让{t}在确保可用性的同时", "你会怎样让{t}在确保可用性的同时更便宜"),
    ("解释{t}为什么需要在执行前把", "解释{t}为什么需要在执行前把状态保存下来"),
    ("谈谈{t}从启动到", "谈谈{t}从启动到停止的整个过程"),
    ("你觉得{t}适合怎样的", "你觉得{t}适合怎样的业务"),
    ("我想问{t}能给使用者带来哪些", "我想问{t}能给使用者带来哪些改变"),
    ("如果{t}遇到我们之前从来没有", "如果{t}遇到我们之前从来没有见过的情况，该怎么办"),
    ("请比较{t}和", "请比较{t}和之前的版本"),
    ("介绍{t}的时候，尤其要说明为何会", "介绍{t}的时候，尤其要说明为何会选这种做法"),
    ("对{t}的这个判断你怎么能", "对{t}的这个判断你怎么能确定呢"),
    ("我想听{t}里的另一部分，如果要", "我想听{t}里的另一部分，如果要重做会怎样"),
    ("他说详细介绍{t}", "我想让你详细介绍{t}"),
    ("她说{t}这部分多讲讲", "请你把{t}这部分多讲讲"),
    ("对方要求把{t}解释清楚", "我要求你把{t}解释清楚"),
    ("评委问{t}有什么意义", "我问你{t}有什么意义"),
    ("他让我聊聊{t}", "麻烦你聊聊{t}"),
    ("人家问{t}怎么做", "我现在问{t}怎么做"),
    ("邮件问我{t}哪天完成", "我想知道{t}哪天完成"),
    ("朋友问过{t}为什么失败", "对于{t}为什么失败，你来回答一下"),
    ("{t}这一问是他当时提的", "{t}这一问是我现在向你提的，请回答"),
    ("刚才只是朗读{t}的题目", "刚才朗读的{t}题目你来回答"),
    ("{t}，这是他当时的发问", "{t}，这是我对你的发问，说说怎么做"),
    ("这个问题取消，{t}我也不问了", "之前那个取消，{t}我仍然想请你解答"),
    ("关于{t}，我不想知道答案了", "关于{t}，我不想知道理论，只想听实际做法"),
    ("不是要你解答{t}", "不是要你复述，是要你解答{t}"),
    ("我不要求你说明{t}", "我不要求你猜测，说说你实际做过的{t}"),
    ("{t}选哪一个，这句只是我复述的", "{t}只能选一个，你挑哪一个"),
]
EN_PAIRS = [
    ("Explain why {t} needs to be", "Explain why {t} needs to be repeated."),
    ("What convinced you that {t} would", "What convinced you that {t} would help?"),
    ("Can you compare {t} to", "Can you compare {t} to the original design?"),
    ("Describe {t}, particularly how it", "Describe {t}, particularly how it handles timeouts."),
    ("Tell me how {t} works when the", "Tell me how {t} works when the server is unavailable."),
    ("How would you keep {t} useful while", "How would you keep {t} useful while reducing its cost?"),
    ("Which part of {t} would you", "Which part of {t} would you change?"),
    ("Given {t}, suppose the other", "Given {t}, suppose the other option fails. What then?"),
    ("He told me to elaborate on {t}.", "I'd like you to elaborate on {t}."),
    ("Her question was how {t} works.", "My question for you is how {t} works."),
    ("I just read the question about {t}.", "Answer the question about {t} that I just read aloud."),
    ("I am not asking you about {t}.", "I am not asking for guesses; explain what you observed about {t}."),
]

FRESH_POS = """
刚才读的是题干，下面轮到你解答
题卡上写的那个难点，你给我示范一个回答
你先回答我引用的那段提问
虽然是同事最先问的，我现在也请你解答
下面这道题是向你提的：团队如何避免重复劳动
他要了解部署顺序，帮我准备一个口头回答
对刚才朗读的内容，你持什么意见
引文中的疑问你也给个解释
刚才那个问题作废，换成这个：异常发生后你先查哪里
我不是要你预测未来，描述已经发生的变化
不必分析所有原因，先说最有证据的那个
我不要求你马上下结论，先介绍收集到的信息
前一部分可以略过，这一部分请展开
不要再等条件了，现在开始解题
停止介绍沿革，改讲你的工作
其他问题暂停，这道题还需要你回答
你是如何让处理速度提高的同时减少资源消耗的
请从最近一次返工说起，描述如何找到遗漏
为什么这个操作需要在发送请求前完成
这一步如何把临时数据变成最终结果
把这两种排队方式的优劣说明一下
如果必须去掉一个模块，你会拿掉什么
这条路径在接收次序混乱时怎样恢复一致性
你会怎样安排第一次交付后的维护
遇到没有预期输出的样本，如何判断结果是否正确
没有额外预算的前提下，哪些改动最值得做
当外部系统返回一半结果就断开连接时，该怎么处理
假定其他条件相同，你为什么坚持这个选择
这组数字能支持什么结论
你们如何把几个人的修改整合到一起
这些步骤能不能颠倒顺序，为什么
是哪个假设限制了你们的方案
后面两项也谈谈	我刚列了监控、回滚和限流三项措施，只讲完监控。
怎么测出来的	我们发现优化后耗时缩短到了原来的一半。
你本人呢	大家分别承担了资料整理、建模和验证。
碰上峰值呢	在正常流量时我们逐条处理。
还有哪一条路	现阶段我们依赖外部托管组件。
为何非它不可	最后我们选用了一个新增的中间层。
那代价是什么	我们采用了双写来降低迁移风险。
出错以后谁处理	这条流程已经交给另一个团队运营。
第二段的经历再细说说
把一次意见不一致的决策过程讲给我听
你挑最熟悉的细节往下讲
这项改动对日常使用者有什么影响
请说明哪些前提一旦改变结论就会失效
用身边的事情类比一下这个机制
讲一个你主动缩小需求范围的例子
从用户点击开始，把请求经过的环节逐个说明
The text I read is the question. It is your turn to answer.
He originally raised it, but I would like your explanation as well.
Please answer the last question from the interview script.
Forget the earlier topic; explain how the failure was detected.
I am not asking for a forecast. Describe what you actually saw.
Leave the dates out and focus on the sequence of decisions.
If exactly one safeguard had to go, which would you remove?
How did you speed this up without increasing memory use?
What happens when the upstream sends only half the payload?
Take us through a disagreement that changed your design.
Why does the check have to happen before the write?
Explain how the result depends on the starting assumptions.
把问题里提到的 backpressure 工作方式讲给我听
不必展开配置，解释一下这段 retry 为什么存在
如果 ack 一直收不到，你具体怎么恢复
那个 payload 不完整的案例，你从头复盘一遍
"""
FRESH_NEG = """
他当时问我为何没选另一种实现
对方让我们把第一阶段讲清楚
面试官说先详细介绍自己的职责
他的原话是请解释每个模块的用途
有人曾向我打听迁移的风险
这页会议纪要记录了别人提出的疑问
同事问过我测试方法，我已经回复了
我正在复述老师让我解释论据的那句话
刚才念的是往年的提问记录
为什么要缓存是这篇文章的小标题
She asked me to go into the first task in detail.
He wanted to know what I had contributed.
Those were the questions from yesterday's rehearsal.
The paragraph quotes a request to explain the design.
他当时让我 explain 一下 backpressure
材料里写着请比较两种 retry 方案，这是我念的原文
刚才的提问不作数，先不用答
现在停止作答，我还要调整题目
这个答案暂时不需要了
那两道题都先撤掉，今天不聊这个
你先不用说，我还没交代完背景
之前让你解释的部分可以跳过了
等我确认问题以后再回答
别继续讲了，这一段到这里
当我没有提出这道题，先暂停
我把刚才那句话收回，稍后换一道
Please disregard that question for now.
Stop there; I need to change what I am asking.
I no longer need an answer to either question.
Wait until I finish setting the problem up.
这个 backpressure 的问题撤掉吧
先别解释 payload，我先把条件说齐
你是如何让处理速度提高的同时减少
请从最近一次返工说起，描述如何找到
为什么这个操作需要在发送请求前将
这一步如何把临时数据变成
把这两种排队方式与我们之前的
如果必须去掉一个模块，而其他模块都
这条路径在接收次序混乱时怎样才能
你会怎样安排第一次交付后的
遇到没有预期输出的样本，而且它又
没有额外预算的前提下，我们希望你能
当外部系统返回一半结果就断开连接时，假设我们
假定其他条件相同，而你所选择的
这组数字能支持什么结论，以及如何把
你们如何把几个人的修改整合到
这些步骤能不能颠倒顺序，特别是在它
是哪个假设限制了你们把
后面两项也谈谈，先等等，我还想加一个前提
怎么测出来的，先别答，我还没把数据给全
你本人呢，我是想具体问你在其中的
碰上峰值呢，假如它需要
还有哪一条路，如果不允许把
为何非它不可，尤其是当
那代价是什么，我还想知道如果我们把
出错以后谁处理，以及怎样将
How did you speed this up without increasing
What happens when the upstream sends only half the
Take us through a disagreement that changed how you
Why does the check have to happen before we can
Explain how the result depends on whether the
If exactly one safeguard had to go, and the remaining
把问题里提到的 backpressure 和
那个 payload 不完整的案例，如果我们要把
"""


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--previous', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit('Refusing to replace frozen data')
    sys.path.insert(0, str(args.runtime / 'source'))
    import laya_mlx
    worker = worker_module()
    agent = laya_mlx.load(args.runtime / 'model', dtype='float16')
    old = {s: json.loads((args.previous / f'{s}.json').read_text())
           for s in ['train', 'calibration', 'development', 'acceptance', 'regression']}
    additions = []
    for prefix, pairs, topics in [('zh', PAIRS, ['版本管理', '任务恢复', '数据校验']),
                                  ('en', EN_PAIRS, ['request routing', 'incremental updates'])]:
        for i, pair in enumerate(pairs):
            for j, topic in enumerate(topics):
                for label, template in enumerate(pair):
                    additions.append(case(f'v4-{prefix}-{i}-{j}-{label}', f'v4-{prefix}-{i}',
                                          template.format(t=topic), bool(label)))
    pool = old['train'] + additions
    rng = random.Random(20261019)
    for label in [False, True]:
        candidates = [c for c in pool if c['respond'] == label and not c['id'].endswith('-long')]
        selected = rng.sample(candidates, 128)
        for i, c in enumerate(selected):
            # Alternate last historical speaker/handled status. Both labels get
            # the exact same distribution of long background, before true context.
            older = [turn('Them' if k % 2 else 'You',
                          ('请谈谈前面那个已完成任务的经验。' if k % 2 else '那个任务已经完成，我记录了背景、过程和结果。') * (6 if i % 2 else 16),
                          bool(k % 2)) for k in range(9 if i % 2 else 10)]
            additions.append(case(c['id'] + '-balanced-long', c['family'], c['text'], label,
                                  older + c['context']['recentTurns'], c['context']['currentSpeaker']))
    fresh = manual('fresh-v4', FRESH_POS, FRESH_NEG)
    assert len(fresh) == 128, len(fresh)
    for row in fresh:
        i = int(row['id'].split('-')[-1])
        row['category'] = 'request' if row['respond'] else ('reported' if i < 16 else 'withdrawn' if i < 32 else 'unfinished')
    splits = dict(train=old['train'] + additions, calibration=old['calibration'],
                  development=old['development'] + old['acceptance'], acceptance=fresh,
                  regression=old['regression'] + old['acceptance'])
    all_old = {c['text'] for rows in old.values() for c in rows}
    assert not all_old.intersection(c['text'] for c in fresh)
    train_text = {c['text'] for c in splits['train']}
    for s in ['calibration', 'development', 'acceptance']:
        assert not train_text.intersection(c['text'] for c in splits[s]), s
    assert not {c['text'] for c in fresh}.intersection(c['text'] for c in splits['calibration'])
    rng.shuffle(splits['train'])
    args.out.mkdir(parents=True)
    manifest = dict(schema=1, created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    provenance='Synthetic local examples only; no remote teacher or user recordings.',
                    split_policy='All prior acceptance is now exposed development/regression. New holdout frozen before training. No failed test utterances copied into training.',
                    question=worker.QUESTIONS, context_tokens=1024, threshold=.8, long_context_stride=2,
                    acceptance_gate=dict(recall_min=.95, false_positive_rate_max=.05, regression_accuracy_min=.95,
                                         require_swift_integration=True), splits={})
    for s, cases in splits.items():
        rows, counts = [], []
        for c in cases:
            state, count = worker.prepare_state(agent, c['text'], json.dumps(c['context'], ensure_ascii=False))
            rows.append(dict(state=state, questions=worker.QUESTIONS, expected=dict(needs_response=c['respond'])))
            counts.append(count)
        fixture = args.out / f'{s}.json'
        fixture.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n')
        data = args.out / f'{s}.jsonl'
        data.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        manifest['splits'][s] = dict(count=len(cases), positive=sum(c['respond'] for c in cases), tokens_max=max(counts),
                                    sha256=hashlib.sha256(data.read_bytes()).hexdigest(), fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (args.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(manifest, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
