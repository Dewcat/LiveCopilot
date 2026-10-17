"""Protocol and installation checks; no model, network, or API credentials required."""
import importlib.util
import hashlib
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'Resources/LayaRuntime'
spec = importlib.util.spec_from_file_location('laya_worker', ROOT / 'worker.py')
worker = importlib.util.module_from_spec(spec); spec.loader.exec_module(worker)

class WorkerTests(unittest.TestCase):
    def test_strict_protocol_rejects_nonfinite_and_duplicate_keys(self):
        for value in ('{"score":NaN}', '{"id":"a","id":"b"}', '{"score":Infinity}'):
            with self.assertRaises(ValueError): worker.strict_loads(value)

    def test_score_is_positive_probability_not_confidence(self):
        self.assertEqual(worker.checked_score({'confidence': 0.99, 'answers': {'needs_response': {'noul': 0.1}}}), 0.1)
        for value in (True, -0.1, 1.01, float('nan'), '0.9'):
            with self.assertRaises(ValueError): worker.checked_score({'answers': {'needs_response': {'noul': value}}})
        with self.assertRaises(KeyError):
            worker.checked_score({'confidence': 0.99, 'answers': {'needs_response': {'probabilities': {'respond': 0.9}}}})

    def test_context_schema_preserves_turns_without_treating_history_as_current(self):
        value = {'currentSpeaker': 'Them', 'recentTurns': [
            {'speaker': 'Them', 'text': '介绍一下你的项目', 'handled': True},
            {'speaker': 'You', 'text': '我有三个项目。', 'handled': False}]}
        speaker, turns = worker.recent_context(json.dumps(value, ensure_ascii=False))
        self.assertEqual(speaker, 'Them')
        self.assertEqual(turns, value['recentTurns'])
        self.assertEqual(worker.recent_context(''), ('Room', []))
        self.assertEqual(worker.recent_context('legacy transcript')[1][0]['text'], 'legacy transcript')

    def test_context_rejects_malformed_or_unbounded_turns(self):
        turn = {'speaker': 'You', 'text': 'Synthetic', 'handled': False}
        valid = {'currentSpeaker': 'Room', 'recentTurns': [turn]}
        for changes in ({'recentTurns': [dict(turn, handled=1)]}, {'recentTurns': [dict(turn, extra=1)]},
                        {'recentTurns': [dict(turn, text=None)]}, {'currentSpeaker': 'x' * 33},
                        {'recentTurns': [turn] * 81}, {'recentTurns': None}, {'extra': 1}):
            with self.assertRaises(ValueError): worker.recent_context(json.dumps(dict(valid, **changes)))

    def test_request_limits_and_schema(self):
        valid = {'id': 'synthetic-1', 'op': 'predict', 'text': '为什么？', 'context': ''}
        worker.validate_request(valid)
        for changes in ({'text': ''}, {'text': '中' * 22000}, {'op': 'exec'}, {'id': '../path'}, {'extra': 1}):
            with self.assertRaises(ValueError): worker.validate_request(dict(valid, **changes))

    def test_receipt_detects_tampering_and_path_escape(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); sample = root / 'sample'; sample.write_bytes(b'synthetic')
            receipt = {'schema': 1, 'files': {'sample': hashlib.sha256(b'synthetic').hexdigest()}}
            (root / 'receipt.json').write_text(json.dumps(receipt))
            worker.verify_installation(root)
            sample.write_bytes(b'modified')
            with self.assertRaises(ValueError): worker.verify_installation(root)
            receipt['files'] = {'../escape': '0' * 64}
            (root / 'receipt.json').write_text(json.dumps(receipt))
            with self.assertRaises(ValueError): worker.verify_installation(root)

    def test_bundled_model_is_optional_but_incomplete_package_fails_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            self.assertEqual(worker.model_path(root, root, {'pin_id': 'base'}), root / 'model')
            (root / 'ResponseModel').mkdir()
            with self.assertRaises(FileNotFoundError):
                worker.model_path(root, root, {'pin_id': 'base'})

    def test_bundled_model_requires_exact_task_runtime_and_file_integrity(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); model = root / 'ResponseModel'
            files = {}
            for name in ['model.safetensors', 'rl_agent_config.json', 'mlx_config.json',
                         'encoder/config.json', 'tokenizer/tokenizer.json', 'tokenizer/tokenizer_config.json']:
                path = model / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'synthetic')
                files[name] = hashlib.sha256(b'synthetic').hexdigest()
            receipt = dict(schema=1, context_tokens=1024, runtime_pin_id='base', files=files,
                           question_sha256=hashlib.sha256(json.dumps(worker.QUESTIONS, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
            manifest = root / 'response-model.json'
            manifest.write_text(json.dumps(receipt))
            self.assertEqual(worker.model_path(root, root, {'pin_id': 'base'}), model)
            for changes in [dict(context_tokens=2048), dict(question_sha256='0' * 64),
                            dict(runtime_pin_id='other'), dict(files={}),
                            dict(files=dict(files, **{'../escape': '0' * 64}))]:
                manifest.write_text(json.dumps(dict(receipt, **changes)))
                with self.assertRaises(ValueError): worker.model_path(root, root, {'pin_id': 'base'})
            manifest.write_text(json.dumps(receipt))
            (model / 'model.safetensors').write_bytes(b'corrupt')
            with self.assertRaises(ValueError): worker.model_path(root, root, {'pin_id': 'base'})

    def test_downloaded_checkpoint_rejects_old_revision_and_modified_weights(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder); resources = root / 'resources'; resources.mkdir()
            model = root / 'model'; files = {}
            for name in ['model.safetensors', 'rl_agent_config.json', 'mlx_config.json',
                         'encoder/config.json', 'tokenizer/tokenizer.json', 'tokenizer/tokenizer_config.json']:
                path = model / name; path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'synthetic'); files[name] = hashlib.sha256(b'synthetic').hexdigest()
            manifest = dict(schema=1, context_tokens=1024, runtime_pin_id='base', files=files,
                            question_sha256=hashlib.sha256(json.dumps(worker.QUESTIONS, sort_keys=True, separators=(',', ':')).encode()).hexdigest())
            (resources / 'response-model.json').write_text(json.dumps(manifest))
            (resources / 'pins.json').write_text(json.dumps({'id':'new-response'}))
            receipt = {'pin_id':'new-response', 'runtime_pin_id':'base'}
            self.assertEqual(worker.model_path(root, resources, receipt), model)
            with self.assertRaises(ValueError): worker.model_path(root, resources, {'pin_id':'base'})
            (model / 'model.safetensors').write_bytes(b'old-model')
            with self.assertRaises(ValueError): worker.model_path(root, resources, receipt)

if __name__ == '__main__': unittest.main()
