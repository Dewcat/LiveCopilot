#!/usr/bin/env python3
"""Opt-in real-model Swift integration with a mock answer provider; no paid API.

Capture exact checkpoint identity and files. A skipped test is not a pass.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys


def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()


def main():
    p = argparse.ArgumentParser()
    for name in ['root', 'resources', 'model', 'output', 'log']:
        p.add_argument('--' + name, type=Path, required=True)
    a = p.parse_args()
    if a.output.exists() or a.log.exists(): raise SystemExit('Refusing to overwrite integration evidence')
    root, resources, model = a.root.resolve(), a.resources.resolve(), a.model.resolve()
    pin = json.loads((resources / 'pins.json').read_text())['id']
    receipt = json.loads((root / 'current/receipt.json').read_text())
    assert receipt['pin_id'] == pin
    manifest = resources / 'response-model.json'
    checkpoint = json.loads(manifest.read_text())['id'] if manifest.exists() else pin
    selected_model = resources / 'ResponseModel' if manifest.exists() else root / 'current/model'
    if selected_model.resolve() != model:
        raise SystemExit('The recorded model must be the actual model selected by this worker')
    methods = ['testInstalledLayaEndToEndWithMockReasoning',
               'testRealLayaContextFollowupQueueAndRevisionPreserveStreamingAnswer',
               'testRealLayaReportedWithdrawnAndIncompleteASR',
               'testRealLayaImplicitRequestUsesConversationContext',
               'testRealLayaEnglishCaptionIntentAndRevision']
    cmd = ['xcodebuild', '-project', 'StealthApp/LiveCopilot.xcodeproj', '-scheme', 'LiveCopilot',
           '-configuration', 'Debug', '-derivedDataPath', 'StealthApp/build', 'CODE_SIGNING_ALLOWED=NO']
    cmd += ['-only-testing:LiveCopilotTests/LayaCoordinatorTests/' + name for name in methods]
    cmd += ['test']
    environment = dict(os.environ, LIVECOPILOT_TEST_REAL_LAYA='1', LIVECOPILOT_TEST_LAYA_ROOT=str(root),
                       LIVECOPILOT_TEST_LAYA_RESOURCES=str(resources))
    with a.log.open('w') as log:
        result = subprocess.run(cmd, env=environment, stdout=log, stderr=subprocess.STDOUT)
    output = a.log.read_text()
    passed_methods = {name: bool(re.search(r"Test Case '-\[LiveCopilotTests.LayaCoordinatorTests " + name + r"\]' passed", output)) for name in methods}
    seen_pins = re.findall(r'JEV_REAL_MODEL_PIN_ID=([^\s]+)', output)
    seen_checkpoints = re.findall(r'JEV_REAL_CHECKPOINT_ID=([^\s]+)', output)
    dispatches = [int(x) for x in re.findall(r'JEV_REAL_FIRST_DISPATCH_MS=(\d+)', output)]
    passed = (result.returncode == 0 and all(passed_methods.values()) and len(seen_pins) == len(methods)
              and set(seen_pins) == {pin} and len(seen_checkpoints) == len(methods) and set(seen_checkpoints) == {checkpoint}
              and len(dispatches) == 1 and dispatches[0] < 1500)
    report = dict(passed=passed, exit_code=result.returncode, tests=passed_methods,
                  model_sha256=sha(model / 'model.safetensors'),
                  model_files={str(f.relative_to(model)): sha(f) for f in model.rglob('*') if f.is_file()},
                  worker_sha256=sha(resources / 'worker.py'), pin_id=pin, checkpoint_id=checkpoint,
                  observed_pins=seen_pins, observed_checkpoints=seen_checkpoints, first_dispatch_ms=dispatches,
                  log_path=str(a.log), log_sha256=sha(a.log),
                  scope='Real local Laya worker + Swift trigger/controller/queue + mock reasoning stream; no live microphone or paid model.')
    a.output.write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps({k:v for k,v in report.items() if k != 'model_files'}, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == '__main__': main()
