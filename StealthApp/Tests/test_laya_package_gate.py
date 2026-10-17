"""A passing text/integration model must not bypass failed native-ASR acceptance."""
import copy,importlib.util,unittest
from pathlib import Path
spec=importlib.util.spec_from_file_location('laya_bundle',Path(__file__).resolve().parents[1]/'scripts/bundle-laya-response-model.py')
bundle=importlib.util.module_from_spec(spec);spec.loader.exec_module(bundle)

class PackageGateTests(unittest.TestCase):
    def report(self):
        return dict(artifact_consistency_passed=True,full_audio_gate_passed=True,model_sha256='weights',worker_sha256='worker',
                    summaries={c:dict(positive=80,negative=80,missed_requests=4,false_triggers=4,recall=.95,false_positive_rate=.05) for c in ['asr','asr_long']})
    def test_exact_boundary_passes(self):bundle.require_full_audio(self.report(),'weights','worker')
    def test_failed_audio_cannot_be_packaged(self):
        r=self.report();r['full_audio_gate_passed']=False
        with self.assertRaisesRegex(ValueError,'must pass'):bundle.require_full_audio(r,'weights','worker')
    def test_wrong_weights_or_worker_cannot_reuse_a_passing_audit(self):
        for weight,worker in [('different','worker'),('weights','different')]:
            with self.assertRaises(ValueError):bundle.require_full_audio(self.report(),weight,worker)
    def test_forged_pass_flag_does_not_hide_long_context_failure(self):
        r=self.report();r['summaries']['asr_long'].update(missed_requests=5,recall=75/80)
        with self.assertRaisesRegex(ValueError,'per-context'):bundle.require_full_audio(r,'weights','worker')

if __name__=='__main__':unittest.main()
