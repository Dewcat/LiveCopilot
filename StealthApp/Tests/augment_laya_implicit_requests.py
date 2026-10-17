#!/usr/bin/env python3
"""Local synthetic training only; never used by the inference decision path.

Learn implicit invitations, contextual references and quotation boundaries.
All final examples are separately authored, frozen before training, and excluded
from training/calibration/development by normalized utterance.
"""
import argparse
import copy
import datetime
import hashlib
import json
from pathlib import Path
import random
import shutil
import sys

from make_laya_finetune_data import case, turn, worker_module
from review_laya_response_labels import normalized

# Each pair contrasts a current invitation with narration/withdrawal. These are
# labelled examples for learned weights, not a whitelist of production phrases.
PAIRS = [
    ('{t}这一节我还想听得更具体些', '{t}这一节我刚才听得很具体了'),
    ('我想再多了解一些{t}的细节', '我已经了解了一些{t}的细节'),
    ('{t}的过程你刚才带得有点快，我还想听', '{t}的过程我刚才讲得有点快，下面由我补充'),
    ('{t}这里还需要你展开一点', '{t}这里不需要你再展开了'),
    ('我期待的是{t}的实际操作，不是概念', '我记录的是{t}的实际操作，不是概念'),
    ('比起结论，我更想听{t}的推导', '比起结论，我刚才更注意了{t}的推导，现在听懂了'),
    ('{t}光说结果我还没明白', '{t}的结果我已经听明白了'),
    ('{t}这一步怎么来的，我还有疑问', '{t}这一步怎么来的我已没有疑问'),
    ('{t}这段还缺一个具体的案例', '{t}这段我会自己补一个案例，你先不用说'),
    ('如果有{t}的数字依据就更好了，想听你说', '如果有{t}的数字依据就更好了，这只是我的备忘'),
    ('我关心的是你本人如何推进{t}', '我当时关心的是自己如何推进{t}，现在已经办完了'),
    ('你在{t}里起的作用还没有讲到', '你在{t}里起的作用已经讲过，不必重复'),
    ('关于{t}，我需要一段能直接听懂的解释', '关于{t}，我写好了一段能直接听懂的解释'),
    ('我希望听到{t}中你的取舍理由', '我听到了{t}中你的取舍理由'),
    ('{t}的来龙去脉还没弄清，你接着说', '{t}的来龙去脉我已经弄清，你先停一下'),
    ('对{t}我还是有点困惑，想听你的理解', '对{t}我以前有点困惑，如今没有了'),
    ('我在等你对{t}的看法', '我在整理你对{t}的看法，不用回答'),
    ('{t}这一点需要一个说明', '{t}这一点已经附了说明'),
    ('{t}只讲到一半，我想继续听下去', '{t}我只讲到一半，我接着往下讲'),
    ('你的{t}经验，我想知道的还多一点', '你的{t}经验，我现在已经知道得够多了'),
    ('我们把话题拉回{t}，你接着讲', '我们的话题曾经是{t}，我在回顾记录'),
    ('{t}这个答案能不能落到一个动作上', '{t}这个答案已经落到一个动作上了'),
    ('我不是不要解释{t}，而是想听简短的解释', '我暂时不需要解释{t}，等我再问'),
    ('{t}不用讲那么多铺垫，直接说做法就好', '{t}不用讲了，做法我已经知道'),
    ('{t}无需考虑别的条件，就按目前的条件说', '{t}先不要说，我还要补充条件'),
    ('别误会，我还是想让你回答{t}', '别误会，我不是让你现在回答{t}'),
    ('{t}我不是在复述别人的问题，现在就是问你', '{t}我是在复述别人的问题，并不是现在问你'),
    ('刚读到的{t}这题，现在由你来作答', '刚读到的{t}这题，是昨天的试题记录'),
    ('题目虽然来自旧材料，但{t}现在请你答一下', '题目来自旧材料，{t}这句只是引文'),
    ('我需要你回应的是{t}的原因，而非数字本身', '我需要存档的是{t}的原因，而非数字本身'),
    ('我没有让你等，我是请你现在解释{t}', '我没有让你解释{t}，我是请你等一下'),
    ('{t}你按自己的理解答，背景不足也没关系', '{t}背景不足，所以你先别答'),
    ('{t}不用重新组织长答案，给我一句话就行', '{t}不用重新组织答案，今天不讨论了'),
    ('我只要你说明{t}的一个关键原因', '我只记下了{t}的一个关键原因'),
    ('{t}在我看来还需要你解释一下', '{t}在我看来已不需要你解释了'),
    ('我需要你把{t}的全程从开始说到结束', '我会把{t}的全程从开始说到结束'),
    ('用一次实际执行把{t}走一遍给我听', '我在笔记里写着用一次实际执行把{t}走一遍'),
    ('{t}的推演，我想从第一步听起', '{t}的推演，我自己会从第一步讲起'),
    ('这次你来当讲解者，把{t}讲给我', '这次我来当讲解者，讲的是{t}'),
    ('{t}想听你拆成几个步骤', '{t}我已拆成几个步骤了'),
    ('先向我解释{t}，再来', '我先解释{t}，再来'),
    ('请把{t}的经历讲出来，然后再', '我把{t}的经历讲出来，然后再'),
    ('{t}为何这样安排，我主要想', '{t}已经这样安排，我主要是'),
    ('{t}的理由你先说明，后续', '{t}的理由我先说明，后续'),
    ('{t}我希望听详细的，尤其是', '{t}我希望自己记录详细的，尤其是'),
    ('{t}请再讲清楚一点，下一步再', '{t}我再讲清楚一点，下一步再'),
    ("I'd appreciate more detail about {e}.", 'I appreciated the detail about {e}; that is enough.'),
    ('I was hoping to hear how {e} actually worked.', 'I have heard how {e} actually worked; no more is needed.'),
    ('What I need is your reasoning about {e}, not just the outcome.', 'I have recorded your reasoning about {e}, not just the outcome.'),
    ('I am still waiting for your account of {e}.', 'I was waiting for that account of {e}, but I no longer need it.'),
    ('There is still a gap in your explanation of {e}. Could you fill it?', 'I filled the gap in my explanation of {e} myself.'),
    ('More on {e} would help me understand.', 'Your account of {e} helped me understand. Thanks.'),
    ('The part about {e} could use an example from you.', 'The part about {e} now has an example; do not add more.'),
    ('I am interested in your own contribution to {e}.', 'I have finished noting your own contribution to {e}.'),
    ('I would rather hear the steps behind {e}.', 'I would rather describe the steps behind {e} myself.'),
    ('That was too brief about {e}; I need more.', 'That was brief about {e}, and it was enough.'),
    ('I am not asking you to stay silent; explain {e} briefly.', 'I am asking you to stay silent for now; do not explain {e}.'),
    ('You need not guess anything; explain {e} using what we have.', 'You need not explain {e}; just wait while I add information.'),
    ('The quoted question about {e} is now yours to answer.', 'The quoted question about {e} is from an old interview, not addressed to you.'),
    ('Do not skip {e}; just keep your answer short.', 'Skip {e}; I am not asking for an answer.'),
    ('I have not withdrawn the request about {e}. Please answer.', 'I have withdrawn the request about {e}. Please wait.'),
    ('Please take one {e} example from the start to the finish.', 'I took one {e} example from the start to the finish.'),
    ('Start with {e}, and then', 'I started with {e}, and then'),
    ('I want the explanation of {e}, especially when', 'I wrote down the explanation of {e}, especially when'),
]

# Identical newest utterances under an actual answer versus explicit recitation.
CONTEXT_PAIRS = [
    ('最开始那段我还想听详细些', '我做过需求澄清、方案实施和现场交付三个阶段。'),
    ('这部分不够具体', '我先用几个词概括一下：做过验证、找过原因、推进了修复。'),
    ('你的理由还没听到', '我最后选了第二个方案，结果符合预期。'),
    ('不止这些吧', '能想到的收获目前先讲这两个。'),
    ('后面发生的事我也想知道', '当时发现问题后，我们先把系统停了下来。'),
    ('细节还差一点', '整个过程就是先沟通，再实施，最后检查。'),
    ('最好有个你亲历的例子', '我认为应该先判断影响，再采取措施。'),
    ('第二步还没理解', '第一步是采集，第二步是过滤，第三步才是归档。'),
    ('换成更慢的设备', '目前在高性能电脑上，这段程序一秒就能执行完。'),
    ('对方没同意的情况', '正常情况下，我们会取得合作方的同意再操作。'),
    ('你自己那部分', '整个小组共同完成了这一轮交付。'),
    ('当时谁负责判断', '那次我们认为没有必要继续扩大试验。'),
    ('The middle part still feels vague.', 'I split the work into planning, execution, and review.'),
    ('I was hoping for an actual example.', 'The general approach is to communicate and then verify.'),
    ('Your own part is missing.', 'Our team completed the whole delivery together.'),
    ('And with nobody available?', 'Usually someone is on duty to handle the request.'),
]

# Quotation after the quoted imperative is as important as quotation before it.
QUOTES = [
    ('“{t}具体怎么做”是我现在给你的题目', '“{t}具体怎么做”是以前问卷上的标题，我只是在读标题'),
    ('“请解释{t}”这句话现在就是对你说的', '“请解释{t}”这句话写在历史记录里，我只是在念记录'),
    ('你需要回答的是“{t}为什么这样做”', '我念的是“{t}为什么这样做”，不是请你现在回答'),
    ('请给{t}一个例子，这是我现在的要求', '请给{t}一个例子，这是旧表格上的文字，与当前讨论无关'),
    ('Explain {e}. That is my question to you now.', 'Explain {e} is the heading on the archived questionnaire; I am only reading it.'),
    ('The words about {e} are quoted, but I want your answer to them now.', 'The words about {e} are quoted, and I do not want an answer to them now.'),
    ('I am now asking you to discuss {e}, not recounting someone else.', 'I am recounting that someone asked me to discuss {e}, not asking you.'),
    ('有人问过{t}的理由，现在我也想听你解释', '有人问过{t}的理由，这只是事件经过，无需你解释'),
]

TOPICS = [('流量预估', 'traffic forecasting'), ('文档审核', 'document review'),
          ('排班调整', 'shift planning'), ('设备巡检', 'equipment inspection')]


def additions():
    rows = []
    for family, pairs in [('implicit', PAIRS), ('quotation', QUOTES)]:
        for i, pair in enumerate(pairs):
            for j, (topic, english) in enumerate(TOPICS):
                history = [] if j % 2 == 0 else [turn('Them', f'说说{topic}。', True),
                         turn('You', f'{topic}从准备到执行再到检查，有几个主要步骤。')]
                for label, text in zip([True, False], pair):
                    rows.append(case(f'v9-{family}-{i}-{j}-{int(label)}', f'v9-{family}-{i}', text.format(t=topic, e=english), label, history))
    for i, (text, answer) in enumerate(CONTEXT_PAIRS):
        for j, (topic, _) in enumerate(TOPICS):
            for label in [True, False]:
                history = [turn('Them', f'我们之前讨论的是{topic}。', True)]
                if label:
                    history.append(turn('You', answer))
                else:
                    history += [turn('Them', '下面我逐字念出已经结束的访谈记录，所有句子都是引文，请先不要回答。'),
                                turn('Them', '记录中的下一句话是：')]
                rows.append(case(f'v9-context-{i}-{j}-{int(label)}', f'v9-context-{i}', text, label, history))
    return rows


def main():
    p=argparse.ArgumentParser()
    for name in ['previous','development','fresh','runtime','out']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise SystemExit('Refusing to overwrite frozen data')
    old={s:json.loads((a.previous/f'{s}.json').read_text()) for s in ['train','calibration','development','acceptance','regression']}
    development=json.loads(a.development.read_text()); fresh=json.loads(a.fresh.read_text())
    exposed=copy.deepcopy(old['acceptance'])
    for c in exposed: c['training_provenance']='V8 final test is exposed; this is training/known regression only.'
    new=additions(); rng=random.Random(20261024)
    # Paired long histories contain handled older requests, not current directives.
    for label in [True, False]:
        for i,c in enumerate(rng.sample([c for c in new+exposed if c['respond']==label],96)):
            row=copy.deepcopy(c);row['id']+='-long'
            history=[]
            for k in range(40):
                topic=TOPICS[k%4][0]
                text=(f'此前关于{topic}的处理已讨论完毕。我们已记录结果、结束复盘、完成归档。' if k%2==0 else f'请解释此前{topic}的流程，这个问题已经得到回答。')*12
                history.append(turn('You' if k%2==0 else 'Them',text,k%2==1))
            row['context']['recentTurns']=history+row['context']['recentTurns'];new.append(row)
    train=old['train']+exposed+new
    regression=old['regression']+exposed
    # Old development stays out of training as an additional retained check.
    regression+=copy.deepcopy(old['development'])
    past={normalized(c['text']) for rows in old.values() for c in rows}
    training_text={normalized(c['text']) for c in train}
    assert not past.intersection(normalized(c['text']) for c in fresh)
    assert not past.intersection(normalized(c['text']) for c in development)
    for name,rows in [('calibration',old['calibration']),('development',development),('acceptance',fresh)]:
        conflicts=training_text.intersection(normalized(c['text']) for c in rows)
        assert not conflicts,(name,conflicts)
    assert not {normalized(c['text']) for c in development}.intersection(normalized(c['text']) for c in fresh)
    assert len(fresh)==160 and sum(c['respond'] for c in fresh)==81
    seen={}
    for c in train+old['calibration']+development+fresh:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen: assert seen[key]==c['respond'],c['id']
        seen[key]=c['respond']
    rng.shuffle(train)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    a.out.mkdir(parents=True)
    shutil.copy2(a.previous/'label-audit.json',a.out/'label-audit.json')
    manifest=json.loads((a.previous/'manifest.json').read_text())
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        split_policy='V8 final is now exposed training/regression. New independently authored development and acceptance. No normalized utterance overlap. Old development retained only in known regression.',
        regression_scope='Exposed training and retained development regressions, not unseen acceptance.',
        training_augmentation='Implicit invitations, context-sensitive follow-ups, answer-format redirection, quoted imperatives, clear intent with dangling grammar and paired long histories. Offline examples only.')
    splits=dict(train=train,calibration=old['calibration'],development=development,acceptance=fresh,regression=regression)
    for split,rows in splits.items():
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        fixture=a.out/f'{split}.json';fixture.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        data=a.out/f'{split}.jsonl';data.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(data.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest['splits'],indent=2))


if __name__=='__main__':main()
