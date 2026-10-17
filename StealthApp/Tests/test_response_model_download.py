"""Offline integrity and atomic preparation tests for release model inputs."""
import hashlib
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('prepare', Path(__file__).parents[1] / 'scripts/prepare-response-model.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ResponseDownloadTests(unittest.TestCase):
    def test_real_manifest_matches_accepted_receipt(self):
        self.assertEqual(module.manifest()['revision'], '32a060912987d9823a1e3d1f4c573f21ca581a39')

    def test_atomic_download_reuse_corruption_and_missing_receipt(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            resource, target = root / 'source', root / 'output'
            resource.mkdir()
            (resource / 'response-model.json').write_bytes(b'receipt')
            source = {'receipt_sha256': hashlib.sha256(b'receipt').hexdigest(), 'base_url': 'https://example.com/',
                      'files': {'model.bin': {'size': 5, 'sha256': hashlib.sha256(b'model').hexdigest()}}}
            def download(args, **kwargs):
                Path(args[-1]).write_bytes(b'model')
            with patch.object(module, 'RESOURCE', resource), patch.object(module.subprocess, 'run', side_effect=download) as fetch:
                module.prepare(target, source)
                module.prepare(target, source)
                self.assertEqual(fetch.call_count, 1)
                (target / 'ResponseModel/model.bin').write_bytes(b'wrong')
                with self.assertRaises(ValueError): module.prepare(target, source)
                self.assertEqual(fetch.call_count, 1)
                self.assertEqual((target / 'ResponseModel/model.bin').read_bytes(), b'wrong')
                (target / 'response-model.json').unlink()
                with self.assertRaises(ValueError): module.verify(target, source)

    def test_bad_download_never_promotes_partial_model(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'response-model.json').write_bytes(b'receipt')
            source = {'receipt_sha256': hashlib.sha256(b'receipt').hexdigest(), 'base_url': 'https://example.com/',
                      'files': {'model.bin': {'size': 5, 'sha256': hashlib.sha256(b'model').hexdigest()}}}
            def download(args, **kwargs): Path(args[-1]).write_bytes(b'wrong')
            with patch.object(module, 'RESOURCE', root), patch.object(module.subprocess, 'run', side_effect=download):
                with self.assertRaises(ValueError): module.prepare(root / 'output', source)
            self.assertFalse((root / 'output/ResponseModel').exists())


if __name__ == '__main__': unittest.main()
