#!/usr/bin/env python3
"""Offline annotation migration, never imported by the app or inference worker.

Decisions are by frozen example/family ID, not runtime sentence matching.
Old files and scores remain immutable. Scores are not inputs to this review.
"""
import argparse
import collections
import copy
import datetime
import hashlib
import json
from pathlib import Path
import sys
import unicodedata

from make_laya_finetune_data import case, worker_module

READY = 'The main request is understandable now; trailing grammar or an optional elaboration does not revoke it.'
AMBIGUOUS = 'Without prosody or additional context, both a request and continued setup are plausible; exclude from binary training and gating.'
KEEP_POS = 'An explicit invitation or contextual follow-up requests a response now; perfect syntax and a fully specified answer are unnecessary.'
KEEP_NEG = 'No current invitation to respond, explicit wait/withdrawal, or essential requested action/object is still unknown.'

# Review by source annotation family. Only formerly negative members change;
# positive continuations and context-sensitive pairs retain their own labels.
READY_FAMILIES = {
    'train-0-20', 'train-0-22',
    *{f'focus-unfinished-{i}' for i in [3, 4, 6, 19]},
    'focus-en-7', 'focus-en-9',
    *{f'v4-zh-{i}' for i in [4, 5, 6, 7, 11, 13, 16, 17, 18, 21, 23]},
    *{f'v4-en-{i}' for i in [3, 4, 5]},
}
AMBIGUOUS_FAMILIES = {
    'train-0-19', 'focus-unfinished-8', 'v4-zh-3', 'v4-zh-8', 'v4-zh-14', 'v4-zh-22',
    'aug-v2-0-97', 'focus-en-10',
}
READY_IDS = {
    'calibration-v3-0-11', 'calibration-v3-0-22',
    'laya_rolling_samples.json:unfinished',
    'fresh-v3-0-57',
    *{f'fresh-v4-0-{i}' for i in [32,33,37,38,39,44,45,46,50,51,52,53,54,55,56,57,58,61]},
}
AMBIGUOUS_IDS = {
    'calibration-v3-0-27', 'development-0-23',
    'laya_official_audit_holdout.json:audit-fresh-22',
    *{f'fresh-v3-0-{i}' for i in [48,50,52,53,55,58,64,65,66,69,70]},
    *{f'fresh-v4-0-{i}' for i in [36,40,42,59,60,63]},
}


def audit(c):
    if c['respond']:
        return True, KEEP_POS
    if c['family'] in READY_FAMILIES or c['id'] in READY_IDS:
        return True, READY
    if c['family'] in AMBIGUOUS_FAMILIES or c['id'] in AMBIGUOUS_IDS:
        return None, AMBIGUOUS
    return False, KEEP_NEG


def normalized(text):
    return ''.join(c.lower() for c in unicodedata.normalize('NFKC', text)
                   if not unicodedata.category(c).startswith(('P', 'Z')))


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--previous', type=Path, required=True)
    p.add_argument('--runtime', type=Path, required=True)
    p.add_argument('--fresh', type=Path, required=True)
    p.add_argument('--out', type=Path, required=True)
    a = p.parse_args()
    if a.out.exists():
        raise SystemExit('Refusing to overwrite frozen data')
    old = {s: json.loads((a.previous / f'{s}.json').read_text())
           for s in ['train', 'calibration', 'development', 'acceptance', 'regression']}
    reviewed, ledger = {}, []
    for split, rows in old.items():
        reviewed[split] = []
        for c in rows:
            label, reason = audit(c)
            ledger.append(dict(split=split, id=c['id'], family=c['family'], text=c['text'],
                               old_label=c['respond'], new_label=label, reason=reason))
            if label is not None:
                r = copy.deepcopy(c)
                r.update(respond=label, annotation_reason=reason)
                if label and not c['respond']:
                    r['category'] = 'clear_intent_incomplete_grammar'
                reviewed[split].append(r)
    # All previous acceptance is exposed. It is now dev/regression, never train.
    dev = reviewed['development'] + reviewed['acceptance']
    # The user-corrected example is a known regression, not a new blind sample.
    dev.append(case('user-resource-intent', 'user-resource-intent', '请你介绍当资源不足时怎样', True))
    fresh = json.loads(a.fresh.read_text())
    old_text = {normalized(c['text']) for rows in old.values() for c in rows}
    assert not old_text.intersection(normalized(c['text']) for c in fresh)
    assert len({c['id'] for c in fresh}) == len(fresh)
    splits = dict(train=reviewed['train'], calibration=reviewed['calibration'],
                  development=dev, acceptance=fresh, regression=dev)
    train_text = {normalized(c['text']) for c in splits['train']}
    for s in ['calibration', 'development', 'acceptance']:
        assert not train_text.intersection(normalized(c['text']) for c in splits[s]), s
    # Every retained pair with exactly the same observable state must agree.
    seen = {}
    for split, rows in splits.items():
        for c in rows:
            key = (c['text'], json.dumps(c['context'], sort_keys=True))
            if key in seen:
                assert seen[key] == c['respond'], (split, c['id'])
            seen[key] = c['respond']
    sys.path.insert(0, str(a.runtime / 'source'))
    import laya_mlx
    worker = worker_module()
    agent = laya_mlx.load(a.runtime / 'model', dtype='float16')
    a.out.mkdir(parents=True)
    (a.out / 'label-audit.json').write_text(json.dumps(ledger, ensure_ascii=False, indent=2) + '\n')
    manifest = dict(schema=1, created_at_utc=datetime.datetime.now(datetime.timezone.utc).isoformat(),
                    provenance='Synthetic local text only. Semantic annotation decisions frozen before any new model scores.',
                    annotation_task='Does the latest speaker need a response now? Clear intent is sufficient; grammatical completeness is not required.',
                    annotation_limit='Single annotator review; ambiguous items quarantined before scoring, not relabelled from model output.',
                    split_policy='All previous acceptance becomes development/regression. Fresh cases share no normalized utterance with any previous split.',
                    question=worker.QUESTIONS, context_tokens=1024, threshold=.8, long_context_stride=1,
                    acceptance_gate=dict(recall_min=.95, false_positive_rate_max=.05,
                                         regression_accuracy_min=.95, require_swift_integration=True), splits={})
    for s, cases in splits.items():
        rows, counts = [], []
        for c in cases:
            state, count = worker.prepare_state(agent, c['text'], json.dumps(c['context'], ensure_ascii=False))
            rows.append(dict(state=state, questions=worker.QUESTIONS, expected=dict(needs_response=c['respond'])))
            counts.append(count)
        fixture = a.out / f'{s}.json'
        fixture.write_text(json.dumps(cases, ensure_ascii=False, indent=2) + '\n')
        data = a.out / f'{s}.jsonl'
        data.write_text(''.join(json.dumps(r, ensure_ascii=False) + '\n' for r in rows))
        manifest['splits'][s] = dict(count=len(cases), positive=sum(c['respond'] for c in cases),
                                    tokens_max=max(counts), sha256=hashlib.sha256(data.read_bytes()).hexdigest(),
                                    fixture_sha256=hashlib.sha256(fixture.read_bytes()).hexdigest())
    manifest['audit'] = {s: dict(total=len(rows), changed=sum(r['new_label'] is not None and r['new_label'] != r['old_label'] for r in rows),
                                 quarantined=sum(r['new_label'] is None for r in rows))
                         for s in old for rows in [[r for r in ledger if r['split'] == s]]}
    manifest['audit_sha256'] = hashlib.sha256((a.out / 'label-audit.json').read_bytes()).hexdigest()
    (a.out / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    print(json.dumps(dict(splits=manifest['splits'], audit=manifest['audit']), indent=2))


if __name__ == '__main__':
    main()
