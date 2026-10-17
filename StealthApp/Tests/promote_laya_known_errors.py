#!/usr/bin/env python3
"""Learn exposed known regressions, with new independent development selection.

Previously exposed dev cases are now explicitly training/known regression, never
claimed as unseen accuracy. The untouched fresh acceptance and calibration stay
isolated. No runtime sentence rules are created.
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
    for name in ['previous','development','known_audio','runtime','out']:
        p.add_argument('--'+name.replace('_','-'),type=Path,required=True)
    a=p.parse_args()
    if a.out.exists(): raise SystemExit('Refusing to overwrite data')
    old={s:json.loads((a.previous/f'{s}.json').read_text()) for s in ['train','calibration','development','acceptance','regression']}
    known=copy.deepcopy(old['development'])
    for c in known:c['training_provenance']='Exposed previous development; now known regression, not independent accuracy.'
    for r in json.loads(a.known_audio.read_text()):
        for field in ['spoken','text']:
            known.append(case('known-'+r['id']+'-'+field,'known-'+r['id'],r[field],r['respond'],r['context']['recentTurns']))
    for i,(text,label) in enumerate([
        ('我想了解这个系统在',False),('我想了解这个系统在断网时如何工作',True),
        ('请比较这个项目与',False),('请解释这个系统的实现，等等，先别回答',False),
        ('请解释这个系统的实现',True),('I would like to ask you about',False),
    ]):known.append(case(f'known-app-{i}',f'known-app-{i}',text,label))
    # Exact duplicate state/label adds no new information. Do not normalize away
    # real ASR casing or word substitutions that change tokenization.
    seen={}; train=[]
    for c in old['train']+known:
        key=(c['text'],json.dumps(c['context'],sort_keys=True))
        if key in seen:
            assert seen[key]==c['respond'];continue
        seen[key]=c['respond'];train.append(c)
    rng=random.Random(20261022)
    def long_copy(c,suffix):
        r=copy.deepcopy(c);r['id']+=suffix
        history=[turn('Them' if k%2 else 'You',('请回顾此前的任务。' if k%2 else '此前的任务已经回答完毕并存档。')*15,bool(k%2)) for k in range(10)]
        r['context']['recentTurns']=history+r['context']['recentTurns'];return r
    for label in [True,False]:
        for c in rng.sample([c for c in known if c['respond']==label],32): train.append(long_copy(c,'-known-long'))
    dev=json.loads(a.development.read_text())
    protected={normalized(c['text']) for c in old['calibration']+old['acceptance']+dev}
    assert not protected.intersection(normalized(c['text']) for c in train)
    assert not {normalized(c['text']) for c in dev}.intersection(normalized(c['text']) for c in old['acceptance']+old['calibration'])
    for label in [True,False]:
        for c in rng.sample([c for c in dev if c['respond']==label],16):dev.append(long_copy(c,'-dev-long'))
    rng.shuffle(train)
    splits=dict(train=train,development=dev)
    sys.path.insert(0,str(a.runtime/'source'));import laya_mlx
    worker=worker_module();agent=laya_mlx.load(a.runtime/'model',dtype='float16')
    a.out.mkdir(parents=True)
    shutil.copy2(a.previous/'label-audit.json',a.out/'label-audit.json')
    for s in ['calibration','acceptance','regression']:
        for ext in ['json','jsonl']:shutil.copy2(a.previous/f'{s}.{ext}',a.out/f'{s}.{ext}')
    manifest=json.loads((a.previous/'manifest.json').read_text())
    manifest.update(created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    split_policy='Exposed previous development promoted into training. New 128 independent dev cases plus 32 paired history stress tests. Fresh acceptance/calibration unchanged.',
                    regression_scope='Known training regressions, NOT unseen generalization accuracy.',
                    training_augmentation='Exposed known failures and prior synthetic ASR variants; no fresh acceptance inputs or scores used.',
                    previous_manifest_sha256=hashlib.sha256((a.previous/'manifest.json').read_bytes()).hexdigest())
    for s,rows in splits.items():
        prepared=[];counts=[]
        for c in rows:
            state,count=worker.prepare_state(agent,c['text'],json.dumps(c['context'],ensure_ascii=False))
            prepared.append(dict(state=state,questions=worker.QUESTIONS,expected=dict(needs_response=c['respond'])));counts.append(count)
        fixture=a.out/f'{s}.json';fixture.write_text(json.dumps(rows,ensure_ascii=False,indent=2)+'\n')
        data=a.out/f'{s}.jsonl';data.write_text(''.join(json.dumps(r,ensure_ascii=False)+'\n' for r in prepared))
        manifest['splits'][s]=dict(count=len(rows),positive=sum(c['respond'] for c in rows),tokens_max=max(counts),
                                  sha256=hashlib.sha256(data.read_bytes()).hexdigest(),fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    (a.out/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(manifest['splits'],indent=2))


if __name__=='__main__':main()
