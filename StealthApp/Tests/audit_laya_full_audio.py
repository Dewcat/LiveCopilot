#!/usr/bin/env python3
"""Recompute exhaustive native-ASR release gates from immutable per-case evidence."""
import argparse,collections,datetime,hashlib,json,math
from pathlib import Path

def require(ok,why):
    if not ok:raise ValueError(why)

def audit_rows(report,captions,original):
    require(report['threshold']==.8,'Threshold changed')
    require(len(original)==160 and sum(r['respond'] for r in original)==80,'Final class counts changed')
    originals={r['id']:r for r in original};transcripts={r['id']:r for r in captions}
    require(len(originals)==160 and len(captions)==160 and len(transcripts)==160,'Missing/duplicate source rows')
    require(set(originals)==set(transcripts),'Caption IDs changed')
    require(collections.Counter(r['id'] for r in report['rows'])==collections.Counter(originals.keys()),'Missing/duplicate scored rows')
    require(report['total']==160,'Reported count changed')
    for r in report['rows']:
        o=originals[r['id']];c=transcripts[r['id']]
        require(type(r['expected']) is bool and r['expected']==o['respond']==c['respond'],'Label changed')
        require(r['spoken']==o['text']==c['spoken'] and r['asr']==c['text'],'Text changed')
        require(c['context']==o['context'],'Original context changed')
        for field in ['spoken','asr','asr_long']:
            score=r[field+'_score'];tokens=r[field+'_tokens']
            require(type(score) in (int,float) and math.isfinite(score) and 0<=score<=1,'Invalid score')
            require(type(tokens) is int and 0<tokens<=1024,'Input token budget violated')
            if field=='asr_long':require(tokens>=950,'Long context not saturated')
            require(r[field+'_passed']==((score>=.8)==r['expected']),'Decision flag inconsistent')
    def summarize(rows,field):
        positive=[r for r in rows if r['expected']];negative=[r for r in rows if not r['expected']]
        fn=sum(r[field+'_score']<.8 for r in positive);fp=sum(r[field+'_score']>=.8 for r in negative)
        return dict(positive=len(positive),negative=len(negative),missed_requests=fn,false_triggers=fp,
                    recall=(len(positive)-fn)/len(positive),false_positive_rate=fp/len(negative))
    summaries={};gates={}
    for field in ['spoken','asr','asr_long']:
        value=summarize(report['rows'],field);require(report['summaries'][field]==value,'Summary does not match rows')
        summaries[field]=value;gates[field]=value['recall']>=.95 and value['false_positive_rate']<=.05
    for field in ['spoken','asr']:
        require(report[field+'_passed']==sum(r[field+'_passed'] for r in report['rows']),'Correct total inconsistent')
    languages={}
    for language,chinese in [('zh',True),('en',False)]:
        rows=[r for r in report['rows'] if any('\u4e00'<=c<='\u9fff' for c in r['spoken'])==chinese]
        languages[language]={field:summarize(rows,field) for field in ['asr','asr_long']}
    return dict(summaries=summaries,language_breakdown=languages,gates=gates,
                full_audio_gate_passed=all(gates[field] for field in ['asr','asr_long']))

def main():
    p=argparse.ArgumentParser()
    for name in ['plan','selection','original','fixtures','review','scores','model','resources','output']:
        p.add_argument('--'+name,type=Path,required=True)
    a=p.parse_args()
    if a.output.exists():raise SystemExit('Refusing to replace audit evidence')
    read=lambda p:json.loads(p.read_text());sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
    plan=read(a.plan);selection=read(a.selection);review=read(a.review);report=read(a.scores)
    require(plan['threshold']==.8 and plan['context_tokens']==1024,'Frozen plan drift')
    require(plan['full_audio_gate']==dict(recall_min=.95,false_positive_rate_max=.05,short_and_long_separately=True,cases=160,no_exclusions=True),'Full audio gate drift')
    require(plan['fresh_fixture_sha256']==sha(a.original),'Original final fixture changed')
    require(selection['final_scores_seen'] is False and selection['plan']==plan,'Selection freeze drift')
    require(report['fixture_sha256']==sha(a.fixtures)==review['fixture_sha256'],'Caption fixture changed')
    require(review['scores_seen'] is False and review['total']==160 and review['exclusions']==[] and review['label_changes']==[],'Review exclusions or post-score changes')
    captions=read(a.fixtures)
    require(collections.Counter(review['reviewed_ids'])==collections.Counter(c['id'] for c in captions),'Incomplete caption review')
    require(all(c['fixture_sha256']==sha(a.original) for c in captions),'ASR originated from different final')
    model_files={str(f.relative_to(a.model)):sha(f) for f in a.model.rglob('*') if f.is_file()}
    require(selection['model_files']==model_files,'Candidate changed after freeze')
    require(report['model_sha256']==selection['model_sha256']==model_files['model.safetensors'],'Model identity mismatch')
    require(report['worker_sha256']==selection['worker_sha256']==plan['worker_sha256']==sha(a.resources/'worker.py'),'Worker identity mismatch')
    result=audit_rows(report,captions,read(a.original))
    result.update(audited_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),artifact_consistency_passed=True,
                  model_sha256=report['model_sha256'],worker_sha256=report['worker_sha256'],
                  scores_sha256=sha(a.scores),fixture_sha256=sha(a.fixtures),installed=False,
                  scope='160 paired synthetic speech/native ASR cases, original and saturated history. No live microphone or paid answer model. Packaging/install verification separate.')
    a.output.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
    if not result['full_audio_gate_passed']:raise SystemExit(1)

if __name__=='__main__':main()
