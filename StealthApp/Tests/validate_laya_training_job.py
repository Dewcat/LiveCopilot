#!/usr/bin/env python3
"""Continue a specific local job into reproducible validation, never installation.

No weights/threshold/labels are selected using final acceptance. If development
fails, leave the final unscored. All output paths are single-attempt evidence.
"""
import argparse
import datetime
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def now():return datetime.datetime.now(datetime.timezone.utc).isoformat()

def main():
    p=argparse.ArgumentParser()
    for name in ['job','plan','data','training','candidate','runtime','evidence','status']:
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--version', choices=['v12','v13','v14','v15','v16','v17','v18','v20','v23'], default='v12')
    a=p.parse_args()
    if a.status.exists():raise SystemExit('Refusing to overwrite a validation attempt')
    state=dict(status='waiting_for_training',started_at=now(),commands=[])
    def write():
        f=a.status.with_suffix('.partial');f.write_text(json.dumps(state,indent=2)+'\n');f.replace(a.status)
    def call(name,command):
        log=a.evidence/(name+'.log')
        if log.exists():raise ValueError('Validation log already exists: '+str(log))
        state.update(status='running',step=name);write()
        with log.open('w') as output:
            process=subprocess.Popen(command,stdout=output,stderr=subprocess.STDOUT,stdin=subprocess.DEVNULL)
            state['child_pid']=process.pid;write();code=process.wait()
        state['commands'].append(dict(name=name,command=command,exit_code=code,log=str(log),log_sha256=sha(log)))
        state.pop('child_pid',None);write()
        return code
    write()
    try:
        while True:
            job=json.loads(a.job.read_text())
            if job['status'] in ['completed','failed']:break
            process=subprocess.run(['ps','-p',str(job['pid']),'-o','args='],capture_output=True,text=True)
            if process.returncode!=0 or 'train_laya_response.py' not in process.stdout:
                # Supervisor may be writing terminal state. Re-read once, do not
                # restart training based on a polling race.
                time.sleep(2);job=json.loads(a.job.read_text())
                if job['status'] not in ['completed','failed']:raise RuntimeError('Training process missing without terminal metadata')
                break
            time.sleep(30)
        if job.get('exit_code')!=0:raise RuntimeError('Training did not complete successfully')
        report=json.loads((a.training/'report.json').read_text());run=json.loads((a.training/'run.json').read_text())
        plan=json.loads(a.plan.read_text());manifest=json.loads((a.data/'manifest.json').read_text())
        if run['pilot'] or len(report['epochs'])!=plan['epochs']:raise ValueError('Incomplete or pilot training output')
        for key in ['epochs','seed','encoder_lr','head_lr']:
            if run['config'][key]!=plan[key]:raise ValueError('Training config drift: '+key)
        if run.get('consistency_weight',0.)!=plan.get('consistency_weight',0.):raise ValueError('Training objective drift')
        if manifest['threshold']!=.8 or manifest['context_tokens']!=1024 or manifest['acceptance_gate']!=plan['gate']:raise ValueError('Gate drift')
        if run['data_manifest']!=manifest:raise ValueError('Training data manifest drift')
        worker=Path('StealthApp/Resources/LayaRuntime/worker.py')
        if sha(worker)!=plan['worker_sha256']:raise ValueError('Worker changed during training')
        for path,digest in plan.get('training_sources',{}).items():
            if sha(path)!=digest:raise ValueError('Training/evaluation source changed: '+path)
        for split,value in manifest['splits'].items():
            if sha(a.data/(split+'.json'))!=value['fixture_sha256'] or sha(a.data/(split+'.jsonl'))!=value['sha256']:raise ValueError('Dataset drift: '+split)
        runtime_python=str(a.runtime/'venv/bin/python3')
        code=call(a.version+'-stage',[runtime_python,'StealthApp/Tests/stage_laya_candidate.py','--model',str(a.training/'calibrated'),'--runtime',str(a.runtime),'--out',str(a.candidate)])
        if code:raise RuntimeError('Candidate staging failed')
        model=a.candidate/'runtime/current/model';resources=a.candidate/'resources'
        def evaluate(split):
            return call(a.version+'-'+split,[runtime_python,'StealthApp/Tests/evaluate_laya_finetune.py','--model',str(model),'--runtime',str(a.runtime),'--data',str(a.data),'--split',split,'--output',str(a.evidence/('candidate-'+a.version+'-'+split+'.json'))])
        if evaluate('development'):
            state.update(status='development_failed_final_unscored',finished_at=now(),installed=False);write();return
        frozen=a.evidence/('candidate-'+a.version+'-frozen-selection.json')
        if frozen.exists():raise ValueError('Frozen candidate already exists')
        frozen.write_text(json.dumps(dict(frozen_at_utc=now(),model_sha256=sha(model/'model.safetensors'),worker_sha256=sha(worker),
            model_files={str(f.relative_to(model)):sha(f) for f in model.rglob('*') if f.is_file()},
            plan=plan,training_report_sha256=sha(a.training/'report.json'),development_sha256=sha(a.evidence/('candidate-'+a.version+'-development.json')),
            final_scores_seen=False,selection=plan['selection']),indent=2)+'\n')
        semantic_exit=evaluate('acceptance')
        integration_exit=call(a.version+'-integration',[sys.executable,'StealthApp/Tests/evaluate_laya_swift.py',
            '--root',str(a.candidate/'runtime'),'--resources',str(resources),'--model',str(model),
            '--output',str(a.evidence/('candidate-'+a.version+'-integration.json')),'--log',str(a.evidence/('candidate-'+a.version+'-integration-xcode.log'))])
        audio_exit=call(a.version+'-audio',[sys.executable,'StealthApp/Tests/evaluate_laya_audio_probe.py',
            '--installation',str(a.candidate/'runtime/current'),'--resources',str(resources),
            '--fixtures',str(a.evidence/'fresh-audio-probe.json'),'--output',str(a.evidence/('candidate-'+a.version+'-fresh-audio.json'))])
        full_audio_exit=full_audio_audit_exit=None
        if plan.get('full_audio_gate'):
            full_scores=a.evidence/('candidate-'+a.version+'-full-audio.json')
            full_audio_exit=call(a.version+'-full-audio',[sys.executable,'StealthApp/Tests/evaluate_laya_audio_probe.py',
                '--installation',str(a.candidate/'runtime/current'),'--resources',str(resources),
                '--fixtures',str(a.evidence/'full-audio-probe.json'),'--output',str(full_scores),'--long-context'])
            if full_audio_exit==0:
                full_audio_audit_exit=call(a.version+'-full-audio-audit',[sys.executable,'StealthApp/Tests/audit_laya_full_audio.py',
                    '--plan',str(a.plan),'--selection',str(frozen),'--original',str(a.data/'acceptance.json'),
                    '--fixtures',str(a.evidence/'full-audio-probe.json'),'--review',str(a.evidence/'full-audio-pre-score-review.json'),
                    '--scores',str(full_scores),'--model',str(model),'--resources',str(resources),
                    '--output',str(a.evidence/('candidate-'+a.version+'-full-audio-audit.json'))])
        state.update(status='validation_finished_requires_review',finished_at=now(),semantic_exit=semantic_exit,
            integration_exit=integration_exit,audio_exit=audio_exit,full_audio_exit=full_audio_exit,
            full_audio_audit_exit=full_audio_audit_exit,installed=False);write()
    except Exception as error:
        state.update(status='failed',finished_at=now(),error=str(error),installed=False);write();raise

if __name__=='__main__':main()
