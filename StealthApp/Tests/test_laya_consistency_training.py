"""Loss and exact resume checks for the optional offline paired objective."""
import copy
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
import torch
import laya.train as upstream
from laya_resumable_training import paired_consistency_loss, train_resumable
from test_laya_resumable_training import ResumeTests, encode, collate

class ConsistencyTests(unittest.TestCase):
    def test_identical_predictions_have_zero_penalty(self):
        z=torch.tensor([[2.,-1.],[2.,-1.]],requires_grad=True)
        loss=paired_consistency_loss(z,torch.ones_like(z,dtype=torch.bool))
        self.assertAlmostEqual(loss.item(),0.,places=7)
        loss.backward();torch.testing.assert_close(z.grad,torch.zeros_like(z),atol=1e-7,rtol=0)
    def test_penalty_is_symmetric_and_pulls_disagreement_together(self):
        z=torch.tensor([[3.,-3.],[-3.,3.]],requires_grad=True);mask=torch.ones_like(z,dtype=torch.bool)
        loss=paired_consistency_loss(z,mask);self.assertGreater(loss.item(),.6)
        self.assertAlmostEqual(loss.item(),paired_consistency_loss(z.flip(0),mask).item(),places=7)
        loss.backward();self.assertGreater(z.grad[0,0].item(),0);self.assertLess(z.grad[1,0].item(),0)
    def test_incomplete_pairs_are_rejected(self):
        with self.assertRaises(ValueError):paired_consistency_loss(torch.ones(3,2),torch.ones(3,2,dtype=torch.bool))
    def verify_resume(self,device):
        helper=ResumeTests();helper.setUp();items=[]
        for row in helper.items[:9]:
            a=copy.deepcopy(row);b=copy.deepcopy(row);b['ids'][0]+=.1;items.extend([a,b])
        with tempfile.TemporaryDirectory() as d,patch.object(upstream,'encode_item',encode),patch.object(upstream,'collate_items',collate):
            dev=torch.device(device);full=helper.model()
            expected=train_resumable(full,helper.tok,items,helper.config,dev,1024,256,Path(d)/'full.pt',{}, {},consistency_weight=.5,checkpoint_every_updates=1)
            reference={k:v.cpu().clone() for k,v in full.state_dict().items()}
            for stop in [1,3,4]:
                path=Path(d)/f'partial-{stop}.pt';partial=helper.model()
                train_resumable(partial,helper.tok,items,helper.config,dev,1024,256,path,{}, {},consistency_weight=.5,stop_after_updates=stop)
                resumed=helper.model()
                actual=train_resumable(resumed,helper.tok,items,helper.config,dev,1024,256,path,{}, {},consistency_weight=.5,resume=True)
                self.assertEqual(expected,actual)
                for k,v in resumed.state_dict().items():torch.testing.assert_close(v.cpu(),reference[k],rtol=0,atol=0)
                with self.assertRaisesRegex(ValueError,'configuration/data/base'):
                    train_resumable(helper.model(),helper.tok,items,helper.config,dev,1024,256,path,{}, {},consistency_weight=.25,resume=True)
            bad=copy.deepcopy(items);bad[1]['target']=[.4,.6]
            with self.assertRaisesRegex(ValueError,'same noul task and target'):
                train_resumable(helper.model(),helper.tok,bad,helper.config,dev,1024,256,Path(d)/'bad.pt',{}, {},consistency_weight=.5)
    def test_cpu_resume_keeps_pairing_and_exact_weights(self):self.verify_resume('cpu')
    @unittest.skipUnless(torch.backends.mps.is_available(),'MPS unavailable')
    def test_mps_resume_keeps_pairing_and_exact_weights(self):self.verify_resume('mps')

if __name__=='__main__':unittest.main()
