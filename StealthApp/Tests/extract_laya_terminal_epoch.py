#!/usr/bin/env python3
"""Calibrate an already trained terminal epoch without reading final cases.

The lowest uncalibrated development CE need not pass the deployed threshold.
This command extracts the other pre-existing epoch as a separately frozen
candidate, with the original calibration set and unchanged development gates.
"""
import argparse,datetime,hashlib,json,os
from pathlib import Path
os.environ.update(USE_TF='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                  HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')

def main():
    p=argparse.ArgumentParser()
    for n in ['training','data','plan','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite terminal candidate')
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    plan=json.loads(a.plan.read_text());manifest=json.loads((a.data/'manifest.json').read_text())
    assert plan['checkpoint_method']=='terminal_epoch' and plan['terminal_epoch']==2
    assert plan['checkpoint_sha256']==sha(a.training/'resume.pt')
    assert plan['manifest_sha256']==sha(a.data/'manifest.json')
    import torch
    from laya.train import load_checkpoint,items_from_rows,calibration_records,calibration_report,save_checkpoint
    from laya.calibrate import fit_temperature_map
    torch.set_num_threads(6)
    model,tok,cfg=load_checkpoint(str(a.training/'best'))
    checkpoint=torch.load(a.training/'resume.pt',map_location='cpu',weights_only=True)
    assert checkpoint['epoch']==2 and checkpoint['next_start']==0 and len(checkpoint['history'])==2
    assert checkpoint['identity']['fingerprint']['data_manifest_sha256']==plan['manifest_sha256']
    model.load_state_dict(checkpoint['model'],strict=True);del checkpoint
    device=torch.device('mps');assert torch.backends.mps.is_available();model.to(device)
    content=(a.data/'calibration.jsonl').read_bytes();assert sha(a.data/'calibration.jsonl')==manifest['splits']['calibration']['sha256']
    rows=[json.loads(line) for line in content.splitlines()]
    items,skipped=items_from_rows(tok,rows,1024,256,label_smoothing=0);assert len(items)==127 and not skipped
    records=calibration_records(model,tok,items,device,1024,256,batch_size=2)
    fitted=fit_temperature_map(records);calibration=calibration_report(records,fitted['temperature'])
    cfg.update(max_len=1024,head_max_len=256,fine_tuned=True,temperature=fitted['temperature'])
    cfg.pop('temperature_by_options',None)
    if fitted['temperature_by_options']:cfg['temperature_by_options']=fitted['temperature_by_options']
    cfg.setdefault('training',{})['livecopilot']=dict(version='local-response-terminal-v21',checkpoint_method='terminal_epoch',
        terminal_epoch=2,checkpoint_sha256=plan['checkpoint_sha256'],calibration=calibration,data_hashes=manifest['splits'],task='needs_response')
    save_checkpoint(model,tok,cfg,str(a.out/'calibrated'))
    (a.out/'calibrated/questions.json').write_text(json.dumps(manifest['question'],indent=2)+'\n')
    report=dict(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkpoint_method='terminal_epoch',
        terminal_epoch=2,checkpoint_sha256=plan['checkpoint_sha256'],calibration=calibration,
        model_sha256=sha(a.out/'calibrated/model.safetensors'),final_scores_seen=False,
        acceptance='Not evaluated; terminal epoch chosen for independent development gating only.')
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
