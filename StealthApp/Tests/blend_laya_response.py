#!/usr/bin/env python3
"""Materialize one predeclared midpoint of adjacent Laya fine-tuning weights.

This is a single model, not an inference ensemble. Only the original calibration
split is read; development and final acceptance remain separate commands.
"""
import argparse,datetime,hashlib,json,os
from pathlib import Path
os.environ.update(USE_TF='0',HF_HUB_OFFLINE='1',TRANSFORMERS_OFFLINE='1',
                  HF_HUB_DISABLE_TELEMETRY='1',TOKENIZERS_PARALLELISM='false')

def main():
    p=argparse.ArgumentParser()
    for n in ['left','right','data','plan','out']:p.add_argument('--'+n,type=Path,required=True)
    a=p.parse_args()
    if a.out.exists():raise SystemExit('Refusing to overwrite a midpoint candidate')
    sha=lambda f:hashlib.sha256(f.read_bytes()).hexdigest()
    plan=json.loads(a.plan.read_text());manifest=json.loads((a.data/'manifest.json').read_text())
    assert plan['checkpoint_method']=='adjacent_midpoint' and plan['right_weight']==.5
    assert plan['parent_weights_sha256']==[sha(a.left/'model.safetensors'),sha(a.right/'model.safetensors')]
    assert plan['manifest_sha256']==sha(a.data/'manifest.json')
    import torch
    from safetensors.torch import load_file
    from laya.train import load_checkpoint,items_from_rows,calibration_records,calibration_report,save_checkpoint
    from laya.calibrate import fit_temperature_map
    torch.set_num_threads(6)
    model,tok,cfg=load_checkpoint(str(a.left));right=load_file(str(a.right/'model.safetensors'))
    state=model.state_dict();assert state.keys()==right.keys()
    with torch.no_grad():
        for key,value in state.items():
            other=right[key];assert value.shape==other.shape
            # The official loader promotes saved float16 weights to float32.
            # Average in float32; the official saver controls output precision.
            if value.is_floating_point():
                assert other.is_floating_point()
                value.copy_((value.float()+other.float())*.5)
            else:assert torch.equal(value,other)
    del right,state
    device=torch.device('mps');assert torch.backends.mps.is_available();model.to(device)
    content=(a.data/'calibration.jsonl').read_bytes()
    assert sha(a.data/'calibration.jsonl')==manifest['splits']['calibration']['sha256']
    rows=[json.loads(line) for line in content.splitlines()]
    items,skipped=items_from_rows(tok,rows,1024,256,label_smoothing=0);assert len(items)==127 and not skipped
    records=calibration_records(model,tok,items,device,1024,256,batch_size=2)
    fitted=fit_temperature_map(records);calibration=calibration_report(records,fitted['temperature'])
    cfg.update(max_len=1024,head_max_len=256,fine_tuned=True,temperature=fitted['temperature'])
    cfg.pop('temperature_by_options',None)
    if fitted['temperature_by_options']:cfg['temperature_by_options']=fitted['temperature_by_options']
    cfg.setdefault('training',{}).setdefault('livecopilot',{}).update(version=plan.get('candidate_version','local-response-midpoint-v19'),checkpoint_method='adjacent_midpoint',
        parent_weights_sha256=plan['parent_weights_sha256'],right_weight=.5,calibration=calibration,data_hashes=manifest['splits'])
    save_checkpoint(model,tok,cfg,str(a.out/'calibrated'))
    (a.out/'calibrated/questions.json').write_text(json.dumps(manifest['question'],indent=2)+'\n')
    report=dict(finished_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),checkpoint_method='adjacent_midpoint',
        right_weight=.5,parent_weights_sha256=plan['parent_weights_sha256'],calibration=calibration,
        model_sha256=sha(a.out/'calibrated/model.safetensors'),final_scores_seen=False,
        acceptance='Not evaluated; fixed midpoint selected before any final score.')
    (a.out/'report.json').write_text(json.dumps(report,indent=2)+'\n');print(json.dumps(report,indent=2))

if __name__=='__main__':main()
