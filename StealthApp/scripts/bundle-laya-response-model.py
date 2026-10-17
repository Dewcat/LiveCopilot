#!/usr/bin/env python3
"""Package an accepted local Laya checkpoint before signing an app.

No downloads, settings edits or installed-model mutations. The signed app owns
the optional checkpoint; reverting the app also reverts model selection.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile


def sha(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1048576), b''):
            h.update(chunk)
    return h.hexdigest()


def require_full_audio(report, weight, worker_sha):
    if (report.get('artifact_consistency_passed') is not True
            or report.get('full_audio_gate_passed') is not True
            or report.get('model_sha256') != weight or report.get('worker_sha256') != worker_sha):
        raise ValueError('Exact-model exhaustive native-ASR acceptance must pass before packaging')
    for condition in ['asr', 'asr_long']:
        value = report['summaries'][condition]
        if (value['positive'] != 80 or value['negative'] != 80
                or type(value['missed_requests']) is not int or type(value['false_triggers']) is not int
                or not 0 <= value['missed_requests'] <= 4 or not 0 <= value['false_triggers'] <= 4
                or value['recall'] != (80 - value['missed_requests']) / 80
                or value['false_positive_rate'] != value['false_triggers'] / 80):
            raise ValueError('Exhaustive native-ASR per-context gate failed')


def main():
    p = argparse.ArgumentParser()
    for name in ['model', 'runtime', 'resources', 'acceptance', 'integration', 'full-audio']:
        p.add_argument('--' + name, type=Path, required=True)
    args = p.parse_args()
    acceptance = json.loads(args.acceptance.read_text())
    integration = json.loads(args.integration.read_text())
    weight = sha(args.model / 'model.safetensors')
    worker_sha = sha(args.resources / 'worker.py')
    require_full_audio(json.loads(args.full_audio.read_text()), weight, worker_sha)
    files = {str(f.relative_to(args.model)): sha(f) for f in args.model.rglob('*') if f.is_file()}
    if (acceptance.get('semantic_gate_passed') is not True
            or acceptance.get('model_sha256') != weight
            or integration.get('passed') is not True
            or integration.get('model_sha256') != weight
            or integration.get('model_files') != files
            or acceptance.get('worker_sha256') != worker_sha
            or integration.get('worker_sha256') != worker_sha
            or acceptance.get('config') != json.loads((args.model / 'rl_agent_config.json').read_text())):
        raise SystemExit('Model acceptance and real integration must pass for these exact weights')
    spec = importlib.util.spec_from_file_location('worker', args.resources / 'worker.py')
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    if acceptance['manifest']['question'] != worker.QUESTIONS or worker.CONTEXT_TOKENS != 1024:
        raise SystemExit('The accepted semantic task differs from this app')
    pins = json.loads((args.resources / 'pins.json').read_text())
    installed = worker.verify_installation(args.runtime)
    if installed['pin_id'] != pins['id']:
        raise SystemExit('Runtime pin differs from this app')
    destination = args.resources / 'ResponseModel'
    manifest = args.resources / 'response-model.json'
    if destination.exists() or manifest.exists():
        raise SystemExit('Refusing to replace an existing bundled checkpoint')
    with tempfile.TemporaryDirectory(prefix='laya-package-') as temporary:
        model = Path(temporary) / 'ResponseModel'
        shutil.copytree(args.model, model)
        config = json.loads((model / 'mlx_config.json').read_text())
        config['source'] = 'LiveCopilot local response-needed fine-tune'
        (model / 'mlx_config.json').write_text(json.dumps(config, indent=2) + '\n')
        for name in ['LICENSE', 'NOTICE']:
            shutil.copy2(args.runtime / 'model' / name, model / name)
        (model / 'FINETUNE-NOTICE.txt').write_text('Modified by LiveCopilot: local synthetic response-needed fine-tuning.\n'
                                                  'Uses the upstream Laya multilingual architecture and tokenizer.\n'
                                                  'Validation is a local engineering benchmark, not population accuracy.\n')
        receipt = dict(schema=1, id='livecopilot-needs-response-' + weight[:16],
                       runtime_pin_id=pins['id'], context_tokens=1024,
                       question_sha256=hashlib.sha256(json.dumps(worker.QUESTIONS, sort_keys=True, separators=(',', ':')).encode()).hexdigest(),
                       acceptance_sha256=sha(args.acceptance), integration_sha256=sha(args.integration),
                       full_audio_audit_sha256=sha(args.full_audio),
                       files={str(f.relative_to(model)): sha(f) for f in model.rglob('*') if f.is_file()})
        shutil.copytree(model, destination)
        manifest.write_text(json.dumps(receipt, indent=2) + '\n')
    worker.model_path(args.runtime, args.resources, installed)
    print(json.dumps(dict(id=receipt['id'], model_sha256=weight, resources=str(args.resources))))


if __name__ == '__main__':
    main()
