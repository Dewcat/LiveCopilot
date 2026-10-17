#!/usr/bin/env python3
"""Score frozen synthetic speech and actual local-ASR captions via NDJSON worker."""
import argparse
import hashlib
import json
from pathlib import Path
from reproduce_trigger_asr import Worker

p = argparse.ArgumentParser()
for name in ['installation', 'resources', 'fixtures', 'output']:
    p.add_argument('--' + name, type=Path, required=True)
p.add_argument('--long-context', action='store_true')
args = p.parse_args()
if args.output.exists():
    raise SystemExit('Refusing to replace probe results')
rows = json.loads(args.fixtures.read_text())
worker = Worker([str(args.installation / 'venv/bin/python3'), '-I', '-B',
                 str(args.resources / 'worker.py'), '--installation', str(args.installation)])
results = []
try:
    for row in rows:
        values = {field: worker.call(op='predict', text=row[field], context=json.dumps(row['context']))
                  for field in ['spoken', 'text']}
        result=dict(id=row['id'], spoken=row['spoken'], asr=row['text'], expected=row['respond'],
                            spoken_score=values['spoken']['score'], asr_score=values['text']['score'],
                            spoken_tokens=values['spoken'].get('input_tokens'),asr_tokens=values['text'].get('input_tokens'),
                            spoken_passed=(values['spoken']['score'] >= .8) == row['respond'],
                            asr_passed=(values['text']['score'] >= .8) == row['respond'])
        if args.long_context:
            old=[dict(speaker='Them' if i%2 else 'You',handled=bool(i%2),
                      text=('请解释上周测试数据的来源。' if i%2 else '测试数据来自合成样本，已经归档。')*16) for i in range(40)]
            context=dict(row['context'],recentTurns=old+row['context']['recentTurns'])
            value=worker.call(op='predict',text=row['text'],context=json.dumps(context))
            if not 950<=value.get('input_tokens',0)<=1024:raise ValueError('ASR long context is not saturated within the 1024 token budget')
            result.update(asr_long_score=value['score'],asr_long_passed=(value['score']>=.8)==row['respond'],asr_long_tokens=value['input_tokens'])
        results.append(result)
finally:
    worker.close()
def summarize(field):
    positive = [r for r in results if r['expected']]
    negative = [r for r in results if not r['expected']]
    missed = sum(r[field + '_score'] < .8 for r in positive)
    false = sum(r[field + '_score'] >= .8 for r in negative)
    return dict(positive=len(positive), negative=len(negative),
                missed_requests=missed, false_triggers=false,
                recall=(len(positive) - missed) / len(positive) if positive else None,
                false_positive_rate=false / len(negative) if negative else None)

manifest = args.resources / 'response-model.json'
model = args.resources / 'ResponseModel' if manifest.exists() else args.installation / 'model'
checkpoint = json.loads((manifest if manifest.exists() else args.installation / 'receipt.json').read_text())
report = dict(fixture_sha256=hashlib.sha256(args.fixtures.read_bytes()).hexdigest(),
              pin_id=json.loads((args.installation / 'receipt.json').read_text())['pin_id'],
              checkpoint_id=checkpoint.get('id', checkpoint.get('pin_id')),
              model_sha256=hashlib.sha256((model / 'model.safetensors').read_bytes()).hexdigest(),
              worker_sha256=hashlib.sha256((args.resources / 'worker.py').read_bytes()).hexdigest(),
              threshold=.8, rows=results, total=len(results),
              spoken_passed=sum(r['spoken_passed'] for r in results),
              asr_passed=sum(r['asr_passed'] for r in results),
              summaries={field: summarize(field) for field in ['spoken', 'asr']+(['asr_long'] if args.long_context else [])},
              scope='Synthetic TTS -> real local Zipformer captions -> real Laya worker. Excludes live mic and answer network.')
args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
print(json.dumps({k: v for k, v in report.items() if k != 'rows'}, indent=2))
