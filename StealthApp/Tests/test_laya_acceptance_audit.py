#!/usr/bin/env python3
"""Fault-injection checks for the pre-package evidence auditor; no model scores."""
import copy
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import audit_laya_acceptance as audit

class AuditTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=Path.cwd();os.chdir(self.tmp.name)
        self.data=Path('data');self.evidence=Path('evidence');self.model=Path('model')
        for p in [self.data,self.evidence,self.model]:p.mkdir()
        worker=Path('StealthApp/Resources/LayaRuntime/worker.py');worker.parent.mkdir(parents=True);worker.write_text('# test fixture only\n')
        self.worker=audit.sha(worker);(self.model/'model.safetensors').write_bytes(b'audit fixture, not a model')
        self.write(self.model/'rl_agent_config.json',dict(max_len=1024));self.weight=audit.sha(self.model/'model.safetensors')
        self.files={str(f.relative_to(self.model)):audit.sha(f) for f in self.model.iterdir()}
        self.cases=[dict(id=str(i),respond=i<81) for i in range(160)];reg=[dict(id='reg',respond=True),dict(id='reg-negative',respond=False)]
        splits={}
        for name,cases in [('acceptance',self.cases),('regression',reg)]:
            self.write(self.data/(name+'.json'),cases);(self.data/(name+'.jsonl')).write_text('test fixture\n')
            splits[name]=dict(count=len(cases),fixture_sha256=audit.sha(self.data/(name+'.json')),sha256=audit.sha(self.data/(name+'.jsonl')))
        limits=dict(recall_min=.95,false_positive_rate_max=.05,regression_accuracy_min=.95,require_swift_integration=True)
        manifest=dict(threshold=.8,context_tokens=1024,acceptance_gate=limits,splits=splits,long_context_stride=1)
        self.write(self.data/'manifest.json',manifest);plan=dict(gate=limits,worker_sha256=self.worker)
        self.write(self.evidence/'frozen-plan-v12.json',plan);self.write(self.evidence/'candidate-v12-development.json',dict(fixture=True))
        frozen=dict(final_scores_seen=False,plan=plan,model_files=self.files,model_sha256=self.weight,worker_sha256=self.worker,development_sha256=audit.sha(self.evidence/'candidate-v12-development.json'))
        self.write(self.evidence/'candidate-v12-frozen-selection.json',frozen)
        rows=[]
        for split,cases in [('acceptance',self.cases),('regression',reg),('long_context',[dict(c,id=c['id']+':long-history') for c in self.cases])]:
            rows.extend(dict(id=c['id'],split=split,expected=c['respond'],score=.95 if c['respond'] else .05,triggered=c['respond'],passed=True,tokens=1016 if split=='long_context' else 140) for c in cases)
        self.acceptance=dict(threshold=.8,config=dict(max_len=1024),manifest=manifest,model_sha256=self.weight,worker_sha256=self.worker,rows=rows,semantic_gate_passed=True,summaries={})
        self.resummarize();self.write(self.evidence/'candidate-v12-acceptance.json',self.acceptance)
        names=['testInstalledLayaEndToEndWithMockReasoning','testRealLayaContextFollowupQueueAndRevisionPreserveStreamingAnswer','testRealLayaReportedWithdrawnAndIncompleteASR','testRealLayaImplicitRequestUsesConversationContext','testRealLayaEnglishCaptionIntentAndRevision']
        log=self.evidence/'xcode.log';log.write_text(''.join(f"Test Case '-[LiveCopilotTests.LayaCoordinatorTests {n}]' passed\n" for n in names))
        self.integration=dict(model_files=self.files,model_sha256=self.weight,worker_sha256=self.worker,tests={n:True for n in names},log_path=str(log),log_sha256=audit.sha(log),observed_pins=['fixture']*5,observed_checkpoints=['fixture']*5,pin_id='fixture',checkpoint_id='fixture',first_dispatch_ms=[180],exit_code=0,passed=True)
        self.write(self.evidence/'candidate-v12-integration.json',self.integration)
        probe=[dict(id=str(i),respond=i<16,spoken='synthetic fixture '+str(i),text='caption fixture '+str(i)) for i in range(32)];self.write(self.evidence/'fresh-audio-probe.json',probe)
        audio=dict(threshold=.8,model_sha256=self.weight,worker_sha256=self.worker,fixture_sha256=audit.sha(self.evidence/'fresh-audio-probe.json'),spoken_passed=32,asr_passed=32,rows=[dict(id=c['id'],expected=c['respond'],spoken=c['spoken'],asr=c['text'],spoken_score=.95 if c['respond'] else .05,asr_score=.95 if c['respond'] else .05,spoken_passed=True,asr_passed=True) for c in probe])
        self.write(self.evidence/'candidate-v12-fresh-audio.json',audio)
    def tearDown(self):os.chdir(self.old);self.tmp.cleanup()
    def write(self,path,value):path.write_text(json.dumps(value))
    def resummarize(self):
        for split in ['acceptance','regression','long_context']:
            rows=[r for r in self.acceptance['rows'] if r['split']==split];pos=[r for r in rows if r['expected']];neg=[r for r in rows if not r['expected']]
            misses=sum(r['score']<.8 for r in pos);fp=sum(r['score']>=.8 for r in neg)
            self.acceptance['summaries'][split]=dict(total=len(rows),passed=len(rows)-misses-fp,accuracy=(len(rows)-misses-fp)/len(rows),recall=1-misses/len(pos),false_positive_rate=fp/len(neg),missed_requests=misses,false_triggers=fp)
    def run_audit(self):
        args=['audit','--model',str(self.model),'--data',str(self.data),'--evidence',str(self.evidence),'--output','audit.json']
        with patch.object(sys,'argv',args):audit.main()
    def test_consistent_complete_evidence_passes(self):
        self.run_audit();self.assertTrue(json.loads(Path('audit.json').read_text())['semantic_and_integration_passed'])
    def test_missing_row_is_rejected(self):
        self.acceptance['rows'].pop();self.write(self.evidence/'candidate-v12-acceptance.json',self.acceptance)
        with self.assertRaisesRegex(ValueError,'Missing/duplicate'):self.run_audit()
    def test_fabricated_summary_is_rejected(self):
        self.acceptance['summaries']['acceptance']['recall']=.99;self.write(self.evidence/'candidate-v12-acceptance.json',self.acceptance)
        with self.assertRaisesRegex(ValueError,'Summary'):self.run_audit()
    def test_high_accuracy_cannot_hide_recall_failure(self):
        for r in self.acceptance['rows'][:5]:r.update(score=.1,triggered=False,passed=False)
        self.resummarize();self.acceptance['semantic_gate_passed']=False;self.write(self.evidence/'candidate-v12-acceptance.json',self.acceptance)
        with self.assertRaises(SystemExit) as e:self.run_audit()
        self.assertEqual(e.exception.code,1);self.assertFalse(json.loads(Path('audit.json').read_text())['semantic_and_integration_passed'])
    def test_over_budget_is_rejected(self):
        self.acceptance['rows'][0]['tokens']=1025;self.write(self.evidence/'candidate-v12-acceptance.json',self.acceptance)
        with self.assertRaisesRegex(ValueError,'token budget'):self.run_audit()
    def test_missing_real_method_is_rejected(self):
        self.integration['tests'].pop('testRealLayaEnglishCaptionIntentAndRevision');self.write(self.evidence/'candidate-v12-integration.json',self.integration)
        with self.assertRaisesRegex(ValueError,'required real-model'):self.run_audit()
    def test_changed_checkpoint_is_rejected(self):
        (self.model/'model.safetensors').write_bytes(b'different fixture')
        with self.assertRaisesRegex(ValueError,'Model files'):self.run_audit()

if __name__=='__main__':unittest.main()
