"""Opt-in offline acceptance with the installed model. No microphone or paid API.
Synthetic development/held-out cases, not a population accuracy benchmark.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys
import statistics
import time

parser = argparse.ArgumentParser()
parser.add_argument('--installation', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
os.environ.update(HF_HUB_OFFLINE='1', TRANSFORMERS_OFFLINE='1', HF_HUB_DISABLE_TELEMETRY='1')
resources = Path(__file__).resolve().parents[1] / 'Resources/LayaRuntime'
spec = importlib.util.spec_from_file_location('worker', resources / 'worker.py')
worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)
worker.verify_installation(args.installation)
sys.path.insert(0, str(args.installation / 'source'))
import laya_mlx
agent = laya_mlx.load(args.installation / 'model', dtype='float16')
worker.predict(agent, 'The meeting starts at nine.', '')
rows = []
for case in json.loads(Path(__file__).with_name('laya_rolling_samples.json').read_text()):
    context = json.dumps(case['context'], ensure_ascii=False)
    start = time.monotonic()
    score, tokens = worker.predict(agent, case['text'], context)
    rows.append(dict(id=case['id'], split=case['split'], expected=case['respond'], score=score,
                     triggered=score >= 0.8, passed=(score >= 0.8) == case['respond'],
                     input_tokens=tokens, ms=round((time.monotonic() - start) * 1000, 1)))
# Actual-tokenizer checks: current text is retained, oldest history expires first,
# Unicode and JSON remain valid, and encoded input never silently exceeds 1024.
latest = '第一个项目仔细讲一下吧'
turns = [{'speaker':'Them','text':f'Old turn {i} ' + '历史内容 '*80,'handled':True} for i in range(50)]
turns += [{'speaker':'You','text':'Recent context: first project uses RAG.', 'handled':False}]
state, count = worker.prepare_state(agent, latest, json.dumps({'currentSpeaker':'Room','recentTurns':turns},ensure_ascii=False))
parsed = json.loads(state)
assert count <= 1024 and parsed['current_utterance'] == latest
assert len(parsed['previous_turns']) < len(turns)
assert parsed['previous_turns'][-1]['text'] == turns[-1]['text']
state, count = worker.prepare_state(agent, '超长转写🌟'*2500 + latest, '')
assert count <= 1024 and json.loads(state)['current_utterance'].endswith(latest)
# A single long previous answer must retain its recent tail for contextual follow-ups.
long_turn = {'speaker':'You','text':'很长的项目介绍。'*1500+'The second project uses a local speech model.', 'handled':False}
state, count = worker.prepare_state(agent, '那第二个呢', json.dumps({'currentSpeaker':'Them','recentTurns':[long_turn]},ensure_ascii=False))
parsed = json.loads(state)
assert count <= 1024 and parsed['current_utterance'] == '那第二个呢'
assert parsed['previous_turns'][0]['text'].endswith('The second project uses a local speech model.')
# Near the transport limit: measure packing separately from model inference.
stress_context = json.dumps({'currentSpeaker':'Them','recentTurns':[
    {'speaker':'You','text':f'Historical turn {i}: '+('历史内容 '*35), 'handled':False} for i in range(80)
]}, ensure_ascii=False)
packing_ms = []
for _ in range(5):
    start = time.monotonic()
    state, count = worker.prepare_state(agent, latest, stress_context)
    packing_ms.append((time.monotonic() - start) * 1000)
    assert count <= 1024 and json.loads(state)['current_utterance'] == latest
thresholds = []
for threshold in (0.8, 0.7, 0.6, 0.5, 0.4):
    thresholds.append({'threshold':threshold,
        'missed_requests':sum(r['expected'] and r['score'] < threshold for r in rows),
        'false_triggers':sum(not r['expected'] and r['score'] >= threshold for r in rows)})
report = {'threshold':0.8, 'context_limit':1024, 'questions':worker.QUESTIONS,
          'worker_sha256':hashlib.sha256((resources / 'worker.py').read_bytes()).hexdigest(),
          'samples_sha256':hashlib.sha256(Path(__file__).with_name('laya_rolling_samples.json').read_bytes()).hexdigest(),
          'model_config':agent.cfg, 'precision':'float16', 'threshold_sweep':thresholds,
          'packing_stress_bytes':len(stress_context.encode()),
          'packing_stress_median_ms':round(statistics.median(packing_ms), 1),
          'packing_stress_max_ms':round(max(packing_ms), 1),
          'token_budget_checks_passed':True, 'rows':rows,
          'passed':sum(r['passed'] for r in rows), 'total':len(rows),
          'release_acceptance_passed':all(r['passed'] for r in rows)}
args.output.parent.mkdir(parents=True, exist_ok=True)
args.output.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
print(json.dumps({k:report[k] for k in ['passed','total','release_acceptance_passed','token_budget_checks_passed']}))
for row in rows:
    if not row['passed']: print(json.dumps(row))
sys.exit(0 if report['release_acceptance_passed'] else 1)
