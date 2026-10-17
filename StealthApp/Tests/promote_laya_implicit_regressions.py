#!/usr/bin/env python3
"""Promote exposed development bugs for one fixed corrective epoch.

There is deliberately no independent development selection after this promotion.
The unchanged, never-scored final holdout is the only new acceptance evidence.
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


def main():
    p=argparse.ArgumentParser()
    for name in ['previous','short','runtime','out']:p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite frozen data')
    old={s:json.loads((a.previous/f'{s}.json').read_text()) for s in ['train','calibration','development','acceptance','regression']}
    exposed=copy.deepcopy(old['development'])
    for c in exposed:c['training_provenance']='V9/V10 development is exposed and promoted; it is known regression, not independent model selection.'
    short=json.loads(a.short.read_text())
    for c in short:c.update(family='known-'+c['id'],category='known_short_turn')
    supplemental=[]
    invitations=['你希望我继续讲下一步吗？','我可以再举一个例子，你要听吗？','你要我把其中的原因说明吗？']
    closings=['以上就是所有步骤，已经解释完了。','这个例子讲完了，没有别的要补充。','刚才你问的原因已经全部说明了。']
    for i,text in enumerate(['好','行','嗯','能']):
        for j,(yes,no) in enumerate(zip(invitations,closings)):
            for label,prior in [(True,yes),(False,no)]:
                supplemental.append(case(f'v11-short-{i}-{j}-{int(label)}',f'v11-short-{i}',text,label,[turn('You',prior)]))
    for c in list(supplemental):
        r=copy.deepcopy(c);r['id']+='-long'
        r['context']['recentTurns']=[turn('Them' if i%2 else 'You',('请解释过去的处理。这已经得到回答。' if i%2 else '过去的处理已经说明，任务已经结束。')*18,bool(i%2)) for i in range(40)]+r['context']['recentTurns']
        supplemental.append(r)
    train=old['train']+exposed+short+supplemental
    random.Random(20261026).shuffle(train)
    protected={normalized(c['text']) for s in ['calibration','acceptance'] for c in old[s]}
    assert not protected.intersection(normalized(c['text']) for c in train)
    seen={}
    for c in train:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen:assert seen[key]==c['respond'],c['id']
        seen[key]=c['respond']
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    a.out.mkdir(parents=True)
    for file in a.previous.iterdir():
        if file.name not in ['train.json','train.jsonl','regression.json','regression.jsonl','manifest.json']:shutil.copy2(file,a.out/file.name)
    manifest=json.loads((a.previous/'manifest.json').read_text())
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        development_scope='known_training_regression',
        selection_data_policy='V9/V10 development is now training/known regression. Exactly one predeclared epoch; no validation-driven checkpoint choice. Calibration and unseen final holdout unchanged.',
        regression_scope='All exposed prior regressions and V9/V10 development plus known short-turn probes; not unseen accuracy.',
        training_augmentation='Exposed development corrections plus contextual short-turn contrasts, offline data only.')
    manifest.pop('rehearsal',None)
    for split,rows in [('train',train),('regression',old['regression']+exposed+short)]:
        prepared=[];counts=[]
        for c in rows:
            state,n=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False));counts.append(n)
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])))
        fixture=a.out/(split+'.json');fixture.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        data=a.out/(split+'.jsonl');data.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][split]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),sha256=hashlib.sha256(data.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(dict(train=manifest['splits']['train'],regression=manifest['splits']['regression'],development_scope=manifest['development_scope']),indent=2))


if __name__=='__main__':main()
