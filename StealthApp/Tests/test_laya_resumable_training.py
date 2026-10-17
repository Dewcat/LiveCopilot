#!/usr/bin/env python3
"""Exercise exact optimizer/RNG continuation against the official training loop."""
import copy
from pathlib import Path
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch
import torch
import laya.train as upstream
from laya_resumable_training import train_resumable

class Tiny(torch.nn.Module):
    def __init__(self):
        super().__init__();self.encoder=torch.nn.Linear(4,7);self.drop=torch.nn.Dropout(.25);self.head=torch.nn.Linear(7,2)
    def forward(self, ids, *args, **kwargs):
        return self.head(self.drop(self.encoder(ids.float()))),None

def encode(tok,item,*args):return item

def collate(groups,pad):
    rows=groups[0];n=len(rows)
    return dict(input_ids=torch.tensor([r['ids'] for r in rows]),target=torch.tensor([r['target'] for r in rows]),
        attention_mask=torch.ones(n,4),marker_mask=torch.ones(n,2,dtype=torch.bool),marker_pos=torch.zeros(n,2,dtype=torch.long),qtype=torch.full((n,),2))

class ResumeTests(unittest.TestCase):
    def setUp(self):
        torch.set_num_threads(1);torch.manual_seed(42)
        self.initial=Tiny().state_dict();self.items=[dict(ids=[i%3,1,i%5,i/11],target=[.99,.01] if i%2 else [.01,.99],q={'t':'noul'},k=2) for i in range(19)]
        self.tok=SimpleNamespace(pad_token_id=0)
        self.config=upstream.TrainConfig(epochs=2,micro_batch=2,grad_accum=4,encoder_lr=.001,head_lr=.003,min_lr=.0001,loss='soft-ce',amp=False,gradient_checkpointing=False,seed=123,log_every=0)
    def model(self):
        m=Tiny();m.load_state_dict(self.initial);return m
    def verify(self,device):
        with tempfile.TemporaryDirectory() as d,patch.object(upstream,'encode_item',encode),patch.object(upstream,'collate_items',collate):
            cfg=self.config;dev=torch.device(device);m=self.model();events=[]
            expected=upstream.train_model(m,self.tok,self.items,cfg,dev,1024,256,on_epoch_end=lambda e,l:events.append(e))
            reference={k:v.cpu().clone() for k,v in m.state_dict().items()}
            continuous=self.model();selection={'epochs':[]}
            actual=train_resumable(continuous,self.tok,self.items,cfg,dev,1024,256,Path(d)/'continuous.pt',{'data':'fixture'},selection,checkpoint_every_updates=1)
            self.assertEqual(expected,actual)
            for k,v in continuous.state_dict().items():torch.testing.assert_close(v.cpu(),reference[k],rtol=0,atol=0)
            # Interrupt once mid-epoch and once exactly after the last optimizer
            # update but before epoch validation; includes a partial accumulation.
            for stop in [1,3,4]:
                path=Path(d)/f'resume-{stop}.pt';partial=self.model();selection={'epochs':[]}
                def callback(e,l):selection['epochs'].append(e)
                result=train_resumable(partial,self.tok,self.items,cfg,dev,1024,256,path,{'data':'fixture'},selection,on_epoch_end=callback,checkpoint_every_updates=1,stop_after_updates=stop)
                self.assertIsNone(result)
                resumed=self.model();selection={'should_be_replaced':True}
                actual=train_resumable(resumed,self.tok,self.items,cfg,dev,1024,256,path,{'data':'fixture'},selection,on_epoch_end=callback,resume=True,checkpoint_every_updates=1)
                self.assertEqual(expected,actual);self.assertEqual(selection['epochs'],[0,1])
                for k,v in resumed.state_dict().items():torch.testing.assert_close(v.cpu(),reference[k],rtol=0,atol=0)
                with self.assertRaisesRegex(ValueError,'configuration/data/base'):
                    train_resumable(self.model(),self.tok,self.items,cfg,dev,1024,256,path,{'data':'different'},selection,resume=True)
    def test_cpu_matches_official_and_resumes_exactly(self):self.verify('cpu')
    @unittest.skipUnless(torch.backends.mps.is_available(),'MPS unavailable')
    def test_mps_matches_official_and_resumes_exactly(self):self.verify('mps')

if __name__=='__main__':unittest.main()
