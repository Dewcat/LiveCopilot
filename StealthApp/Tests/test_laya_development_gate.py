"""Reject dilution of a long-context failure by easy short examples."""
import unittest
from evaluate_laya_finetune import development_context_gate, development_group_gate, summarize
from audit_laya_acceptance import audit_development_groups

class DevelopmentGateTests(unittest.TestCase):
    def setUp(self):
        self.limits=dict(recall_min=.95,false_positive_rate_max=.05)
        self.rows=[dict(context_condition=c,expected=i<64,triggered=i<64,passed=True,
                        tokens=1016 if c=='long' else 140,ms=10.)
                   for c in ['short','long'] for i in range(128)]
    def test_long_false_triggers_cannot_be_diluted(self):
        for r in self.rows[192:196]:r.update(triggered=True,passed=False)
        self.assertLess(summarize(self.rows)['false_positive_rate'],.05)
        contexts,passed=development_context_gate(self.rows,self.limits)
        self.assertGreater(contexts['long']['false_positive_rate'],.05)
        self.assertFalse(passed)
    def test_long_misses_cannot_be_diluted(self):
        for r in self.rows[128:132]:r.update(triggered=False,passed=False)
        self.assertGreater(summarize(self.rows)['recall'],.95)
        self.assertFalse(development_context_gate(self.rows,self.limits)[1])
    def test_saturated_inputs_required(self):
        self.rows[128]['tokens']=600
        with self.assertRaises(AssertionError):development_context_gate(self.rows,self.limits)
    def test_both_contexts_required(self):
        with self.assertRaises(AssertionError):development_context_gate(self.rows[:128],self.limits)
    def test_english_asr_failure_cannot_be_diluted_by_existing_development(self):
        rows=[dict(r,development_group='existing') for r in self.rows]
        extra=[dict(context_condition=c,expected=i<32,triggered=i<32,passed=True,
                    tokens=1016 if c=='long' else 140,ms=10.,development_group='english_asr')
               for c in ['short','long'] for i in range(64)]
        for r in extra[64:66]:r.update(triggered=False,passed=False)
        rows+=extra
        self.assertTrue(development_context_gate(rows,self.limits)[1])
        groups,passed=development_group_gate(rows,self.limits)
        self.assertEqual(groups['english_asr']['long']['recall'],30/32)
        self.assertFalse(passed)
    def test_each_development_group_requires_both_contexts(self):
        rows=[dict(r,development_group='existing') for r in self.rows]
        rows += [dict(r,development_group='english_asr') for r in self.rows[:128]]
        with self.assertRaises(AssertionError):development_group_gate(rows,self.limits)
    def test_independent_auditor_recomputes_group_failure(self):
        rows=[dict(r,id=str(i),score=.95 if r['expected'] else .05,development_group='english_asr') for i,r in enumerate(self.rows)]
        cases=[dict(id=r['id'],respond=r['expected'],context_condition=r['context_condition'],development_group=r['development_group']) for r in rows]
        groups,_=development_group_gate(rows,self.limits)
        report=dict(rows=rows,threshold=.8,development_groups=groups,semantic_gate_passed=True)
        self.assertIn('english_asr',audit_development_groups(report,cases))
        for r in rows[128:132]:r.update(score=.1,triggered=False,passed=False)
        report['development_groups'],_=development_group_gate(rows,self.limits)
        with self.assertRaisesRegex(ValueError,'subgroup gate failed'):audit_development_groups(report,cases)
    def test_independent_auditor_rejects_changing_group_membership(self):
        rows=[dict(r,id=str(i),score=.95 if r['expected'] else .05,development_group='english_asr') for i,r in enumerate(self.rows)]
        cases=[dict(id=r['id'],respond=r['expected'],context_condition=r['context_condition'],development_group=r['development_group']) for r in rows]
        groups,_=development_group_gate(rows,self.limits)
        rows[0]['development_group']='existing'
        with self.assertRaisesRegex(ValueError,'group changed'):
            audit_development_groups(dict(rows=rows,threshold=.8,development_groups=groups,semantic_gate_passed=True),cases)

if __name__=='__main__':unittest.main()
