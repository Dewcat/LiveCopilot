#!/usr/bin/env python3
"""Independent artifact/row audit before packaging an accepted Laya candidate.

Recomputes frozen release criteria rather than trusting a report's pass flag.
Does not train, relabel, change thresholds, or install the candidate.
"""
import argparse
from collections import Counter
import datetime
import hashlib
import json
import math
from pathlib import Path
import re


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def read(path):return json.loads(Path(path).read_text())
def require(ok,why):
    if not ok:raise ValueError(why)


def audit_development_groups(report, cases):
    """Recompute group gates independently of the evaluation implementation."""
    by_id={c['id']:c for c in cases}
    require(len(by_id)==len(cases),'Duplicate development fixture ids')
    require(Counter(r['id'] for r in report['rows'])==Counter(by_id.keys()),'Missing/duplicate development rows')
    require(report['threshold']==.8,'Development threshold drift')
    for r in report['rows']:
        c=by_id[r['id']];score=r['score']
        require(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1,'Invalid development score')
        require(type(r['expected']) is bool and r['expected']==c['respond'],'Development label changed')
        require(r['development_group']==c['development_group'] and r['context_condition']==c.get('context_condition','short'),'Development group changed')
        require(r['triggered']==(score>=.8) and r['passed']==((score>=.8)==c['respond']),'Development decision inconsistent')
        require(type(r['tokens']) is int and 0<r['tokens']<=1024,'Development token budget violated')
        if r['context_condition']=='long':require(r['tokens']>=950,'Development long context not saturated')
    summaries={};passed=True
    for group in sorted({c['development_group'] for c in cases}):
        summaries[group]={}
        for condition in ['short','long']:
            rows=[r for r in report['rows'] if r['development_group']==group and r['context_condition']==condition]
            pos=[r for r in rows if r['expected']];neg=[r for r in rows if not r['expected']]
            require(pos and neg,'Incomplete development group/context')
            fn=sum(r['score']<.8 for r in pos);fp=sum(r['score']>=.8 for r in neg)
            value=dict(total=len(rows),passed=len(rows)-fn-fp,accuracy=(len(rows)-fn-fp)/len(rows),
                       recall=(len(pos)-fn)/len(pos),false_positive_rate=fp/len(neg),missed_requests=fn,false_triggers=fp)
            for key,v in value.items():require(math.isclose(report['development_groups'][group][condition][key],v,abs_tol=1e-12),'Development group summary mismatch')
            summaries[group][condition]=value;passed &= value['recall']>=.95 and value['false_positive_rate']<=.05
    require(set(report['development_groups'])==set(summaries),'Development group missing or extra')
    require(report['semantic_gate_passed'] and passed,'Development subgroup gate failed')
    return summaries


def main():
    p=argparse.ArgumentParser()
    for key in ['model','data','evidence','output']:p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--version',choices=['v12','v13','v14','v15','v16','v17','v18','v19','v20','v21','v22','v23'],default='v12')
    a=p.parse_args()
    if a.output.exists():raise SystemExit('Refusing to overwrite audit evidence')
    def evidence(suffix):return a.evidence/('candidate-'+a.version+'-'+suffix+'.json')
    manifest=read(a.data/'manifest.json');plan=read(a.evidence/('frozen-plan-'+a.version+'.json'))
    frozen=read(evidence('frozen-selection'))
    acceptance=read(evidence('acceptance'));integration=read(evidence('integration'))
    audio=read(evidence('fresh-audio'));probe=read(a.evidence/'fresh-audio-probe.json')
    model_files={str(f.relative_to(a.model)):sha(f) for f in a.model.rglob('*') if f.is_file()}
    weight=model_files['model.safetensors'];worker=Path('StealthApp/Resources/LayaRuntime/worker.py');worker_sha=sha(worker)
    limits=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True)
    require(manifest['threshold']==.8 and acceptance['threshold']==.8 and audio['threshold']==.8,'Threshold drift')
    require(manifest['acceptance_gate']==limits and plan['gate']==limits,'Acceptance gate drift')
    require(manifest['context_tokens']==1024 and acceptance['config']['max_len']==1024,'Context budget drift')
    require(acceptance['config']==read(a.model/'rl_agent_config.json'),'Model config differs from accepted checkpoint')
    require(acceptance['manifest']==manifest,'Acceptance manifest differs from current dataset')
    require(frozen['final_scores_seen'] is False and frozen['plan']==plan,'Final freeze metadata changed')
    require(frozen['model_files']==model_files and integration['model_files']==model_files,'Model files differ between freeze/evaluation/integration')
    for name,record in [('freeze',frozen),('acceptance',acceptance),('integration',integration),('audio',audio)]:
        require(record['model_sha256']==weight and record['worker_sha256']==worker_sha,name+' uses different model/worker')
    require(plan['worker_sha256']==worker_sha,'Runtime worker changed from frozen training plan')
    require(sha(evidence('development'))==frozen['development_sha256'],'Development evidence changed')
    development_groups={}
    if manifest.get('development_group_gate'):
        dev=read(evidence('development'));entry=manifest['splits']['development']
        require(dev['model_sha256']==weight and dev['worker_sha256']==worker_sha,'Development checkpoint mismatch')
        require(sha(a.data/'development.json')==entry['fixture_sha256'] and sha(a.data/'development.jsonl')==entry['sha256'],'Development fixture changed')
        development_groups=audit_development_groups(dev,read(a.data/'development.json'))
    datasets={}
    for split in ['acceptance','regression']:
        entry=manifest['splits'][split];file=a.data/(split+'.json')
        require(sha(file)==entry['fixture_sha256'],'Fixture hash changed: '+split)
        require(sha(a.data/(split+'.jsonl'))==entry['sha256'],'Prepared fixture changed: '+split)
        cases=read(file);require(len(cases)==entry['count'],'Fixture count differs')
        require(len({c['id'] for c in cases})==len(cases),'Duplicate fixture ids')
        datasets[split]=cases
    require(len(datasets['acceptance'])==160 and sum(c['respond'] for c in datasets['acceptance'])==plan.get('final_positive',81),'Final class counts differ from frozen plan')
    if 'fresh_fixture_sha256' in plan:
        require(sha(a.data/'acceptance.json')==plan['fresh_fixture_sha256'],'Final differs from pre-training frozen fixture')
    datasets['long_context']=[dict(c,id=c['id']+':long-history') for c in datasets['acceptance']]
    require(manifest['long_context_stride']==1,'Not all final cases have long-history coverage')
    require(set(r['split'] for r in acceptance['rows'])==set(datasets),'Unexpected or missing evaluation split')
    summaries={};gates={}
    for split,cases in datasets.items():
        by_id={c['id']:c for c in cases};rows=[r for r in acceptance['rows'] if r['split']==split]
        require(Counter(r['id'] for r in rows)==Counter(by_id.keys()),'Missing/duplicate evaluation rows: '+split)
        for r in rows:
            c=by_id[r['id']];score=r['score']
            require(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1,'Invalid score')
            require(type(r['expected']) is bool and r['expected']==c['respond'],'Expected label changed')
            require(r['triggered']==(score>=.8) and r['passed']==((score>=.8)==c['respond']),'Decision fields inconsistent')
            require(type(r['tokens']) is int and 0<r['tokens']<=1024,'Input exceeds real token budget')
            if split=='long_context':require(r['tokens']>=950,'Long-context stress input is not saturated')
        positives=[r for r in rows if r['expected']];negatives=[r for r in rows if not r['expected']]
        misses=sum(r['score']<.8 for r in positives);false=sum(r['score']>=.8 for r in negatives)
        value=dict(total=len(rows),passed=len(rows)-misses-false,accuracy=(len(rows)-misses-false)/len(rows),
            recall=(len(positives)-misses)/len(positives),false_positive_rate=false/len(negatives),missed_requests=misses,false_triggers=false)
        for k,v in value.items():require(math.isclose(acceptance['summaries'][split][k],v,abs_tol=1e-12),'Summary does not match rows: '+split+'/'+k)
        summaries[split]=value
        gates[split]=value['accuracy']>=.95 if split=='regression' else value['recall']>=.95 and value['false_positive_rate']<=.05
    require(acceptance['semantic_gate_passed']==all(gates.values()),'Semantic pass flag does not match recomputed gates')
    methods=['testInstalledLayaEndToEndWithMockReasoning','testRealLayaContextFollowupQueueAndRevisionPreserveStreamingAnswer',
             'testRealLayaReportedWithdrawnAndIncompleteASR','testRealLayaImplicitRequestUsesConversationContext','testRealLayaEnglishCaptionIntentAndRevision']
    require(set(integration['tests'])==set(methods),'Missing required real-model integration test')
    log=Path(integration['log_path']);require(sha(log)==integration['log_sha256'],'Integration log changed')
    output=log.read_text();observed={m:bool(re.search(r"Test Case '-\[LiveCopilotTests.LayaCoordinatorTests "+m+r"\]' passed",output)) for m in methods}
    require(observed==integration['tests'],'Integration report differs from raw test log')
    for field,value in [('observed_pins',integration['pin_id']),('observed_checkpoints',integration['checkpoint_id'])]:
        require(len(integration[field])==5 and set(integration[field])=={value},'Integration checkpoint identity coverage incomplete')
    dispatch=integration['first_dispatch_ms'];require(len(dispatch)==1 and 0<dispatch[0]<1500,'First dispatch delay gate fails')
    integration_passed=integration['exit_code']==0 and all(observed.values())
    require(integration['passed']==integration_passed,'Integration pass flag inconsistent')
    require(audio['fixture_sha256']==sha(a.evidence/'fresh-audio-probe.json'),'Audio fixture changed')
    require(len(probe)==32 and Counter(r['id'] for r in audio['rows'])==Counter(r['id'] for r in probe),'Audio probe exclusions or duplicates')
    probe_map={r['id']:r for r in probe};audio_summary={}
    for field,text_field in [('spoken','spoken'),('asr','text')]:
        for row in audio['rows']:
            c=probe_map[row['id']];require(row['expected']==c['respond'] and row[field]==c[text_field],'Audio label/text changed')
            require(row[field+'_passed']==((row[field+'_score']>=.8)==c['respond']),'Audio pass flag inconsistent')
        missed=sum(r['expected'] and r[field+'_score']<.8 for r in audio['rows']);false=sum(not r['expected'] and r[field+'_score']>=.8 for r in audio['rows'])
        audio_summary[field]=dict(passed=32-missed-false,missed_requests=missed,false_triggers=false)
        require(audio[field+'_passed']==32-missed-false,'Audio total mismatch')
    report=dict(audited_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifact_consistency_passed=True,
        model_sha256=weight,worker_sha256=worker_sha,summaries=summaries,semantic_gates=gates,integration_passed=integration_passed,
        development_groups=development_groups,
        semantic_and_integration_passed=all(gates.values()) and integration_passed,audio_summary=audio_summary,
        audio_failures_require_review=audio_summary['asr']['passed']!=32,
        installation_authorized_by_audit=False,scope='Exact candidate evidence audit. Packaging, signing, installed-artifact and behavior checks remain required.')
    a.output.write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))
    if not report['semantic_and_integration_passed']:raise SystemExit(1)

if __name__=='__main__':main()
