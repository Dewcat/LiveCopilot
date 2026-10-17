#!/usr/bin/env python3
"""Offline checkpointed equivalent of pinned Laya's soft-CE training loop.

Uses upstream encoding, forward pass, loss, accumulation and optimizer schedule.
Only local persistence is added; inference and checkpoint selection are unchanged.
Optional paired consistency training is an explicit offline extension; weight
zero retains the exact upstream-equivalent loop used by earlier runs.
"""
from dataclasses import asdict
import math
import os
from pathlib import Path
import random
import torch


def paired_consistency_loss(logits, mask):
    """Symmetric Jensen-Shannon loss for adjacent equivalent noul examples."""
    if logits.shape[0] % 2 or logits.shape[-1] != 2 or not bool(mask.all()):
        raise ValueError('Consistency requires complete pairs of binary options')
    logp = torch.log_softmax(logits, dim=-1).reshape(-1, 2, 2)
    logm = torch.logaddexp(logp[:, 0], logp[:, 1]) - math.log(2.)
    return (logp.exp() * (logp - logm[:, None, :])).sum(-1).mean()


def _cpu(value):
    if isinstance(value, torch.Tensor):
        return value.detach().cpu()
    if isinstance(value, dict):
        return {k: _cpu(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_cpu(v) for v in value]
    if isinstance(value, tuple):
        return tuple(_cpu(v) for v in value)
    return value


def train_resumable(model, tok, items, config, device, max_len, head_max_len,
                    checkpoint_path, fingerprint, selection, on_epoch_end=None,
                    resume=False, checkpoint_every_updates=64, stop_after_updates=None,
                    consistency_weight=0.):
    from laya.train import (encode_item, draw_option_order, collate_items, _forward,
                            soft_ce_loss, optimizer_updates)
    config.validate()
    if not items or config.loss != 'soft-ce' or config.amp not in (False, None):
        raise ValueError('Resumable local runner supports nonempty full-precision soft-CE only')
    if checkpoint_every_updates <= 0:
        raise ValueError('Checkpoint interval must be positive')
    if not math.isfinite(consistency_weight) or consistency_weight < 0:
        raise ValueError('Invalid consistency weight')
    if consistency_weight:
        if len(items) % 2 or config.micro_batch % 2:
            raise ValueError('Paired training requires even items and batch size')
        for a,b in zip(items[::2],items[1::2]):
            if a['q']['t'] != 'noul' or b['q'] != a['q'] or a['k'] != 2 or b['k'] != 2 or a['target'] != b['target']:
                raise ValueError('Paired rows must have the same noul task and target')
    if config.freeze_encoder:
        for p in model.encoder.parameters():
            p.requires_grad_(False)
    elif config.gradient_checkpointing and hasattr(model.encoder, 'gradient_checkpointing_enable'):
        model.encoder.gradient_checkpointing_enable(gradient_checkpointing_kwargs={'use_reentrant': False})
    model.head_checkpointing = bool(config.gradient_checkpointing)
    model.to(device).train()
    if config.freeze_encoder:
        model.encoder.eval()
    groups=[{'params':[p for n,p in model.named_parameters() if not n.startswith('encoder.') and p.requires_grad], 'lr':config.head_lr}]
    if not config.freeze_encoder:
        groups.insert(0,{'params':[p for n,p in model.named_parameters() if n.startswith('encoder.') and p.requires_grad], 'lr':config.encoder_lr})
    optimizer=torch.optim.AdamW(groups,weight_decay=config.weight_decay)
    scheduler=torch.optim.lr_scheduler.CosineAnnealingLR(optimizer,
        T_max=optimizer_updates(len(items),config.micro_batch,config.grad_accum,config.epochs),eta_min=config.min_lr)
    params=[p for g in groups for p in g['params']]
    steps_per_epoch=math.ceil(len(items)/config.micro_batch)
    path=Path(checkpoint_path)
    identity=dict(schema=1,fingerprint=fingerprint,config=asdict(config),items=len(items),max_len=max_len,head_max_len=head_max_len)
    if consistency_weight:identity['consistency_weight']=consistency_weight
    epoch0=0;start0=0;total0=0.;steps0=0;updates=0;history=[]
    torch.manual_seed(config.seed)
    order_rng=random.Random(config.seed)
    if resume:
        state=torch.load(path,map_location='cpu',weights_only=True)
        if state['identity']!=identity:
            raise ValueError('Resume configuration/data/base differs from saved checkpoint')
        model.load_state_dict(state['model']);optimizer.load_state_dict(state['optimizer']);scheduler.load_state_dict(state['scheduler'])
        epoch0=state['epoch'];start0=state['next_start'];total0=state['total'];steps0=state['steps'];updates=state['updates'];history=state['history']
        selection.clear();selection.update(state['selection'])
        torch.set_rng_state(state['cpu_rng'])
        if device.type=='mps':torch.mps.set_rng_state(state['device_rng'])
        order_rng.setstate(state['option_rng'])
        print(f'RESUMED epoch={epoch0+1} next_item={start0} updates={updates}',flush=True)
    elif path.exists():
        raise ValueError('Refusing to replace an existing resume checkpoint')

    def save(epoch,next_start,total,steps):
        path.parent.mkdir(parents=True,exist_ok=True)
        if device.type=='mps':torch.mps.synchronize()
        state=dict(identity=identity,model=_cpu(model.state_dict()),optimizer=_cpu(optimizer.state_dict()),scheduler=scheduler.state_dict(),
            epoch=epoch,next_start=next_start,total=total,steps=steps,updates=updates,history=list(history),selection=dict(selection),
            cpu_rng=torch.get_rng_state(),device_rng=torch.mps.get_rng_state() if device.type=='mps' else None,option_rng=order_rng.getstate())
        temporary=path.with_suffix('.partial')
        with temporary.open('wb') as stream:
            torch.save(state,stream);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)
        print(f'CHECKPOINT epoch={epoch+1} next_item={next_start} updates={updates}',flush=True)

    for epoch in range(epoch0,config.epochs):
        epoch_items=list(items)
        if consistency_weight:
            pairs=list(zip(epoch_items[::2],epoch_items[1::2]))
            random.Random(config.seed+epoch).shuffle(pairs)
            epoch_items=[item for pair in pairs for item in pair]
        else:
            random.Random(config.seed+epoch).shuffle(epoch_items)
        start_at=start0 if epoch==epoch0 else 0
        total=total0 if epoch==epoch0 else 0.;n_steps=steps0 if epoch==epoch0 else 0
        optimizer.zero_grad(set_to_none=True)
        for start in range(start_at,len(epoch_items),config.micro_batch):
            # Canonical binary option order must match across each pair. The
            # ordinary zero-weight path retains official option randomization.
            chunk=[encode_item(tok,it,max_len,head_max_len,None if consistency_weight else draw_option_order(it,order_rng,config.shuffle_options),False)
                   for it in epoch_items[start:start+config.micro_batch]]
            batch=collate_items([chunk],tok.pad_token_id)
            logits=_forward(model,batch,device,False,config.freeze_encoder)
            loss=soft_ce_loss(logits,batch['target'].to(device),batch['marker_mask'].to(device))
            if consistency_weight:
                loss=loss+consistency_weight*paired_consistency_loss(logits,batch['marker_mask'].to(device))
            window_start=(n_steps//config.grad_accum)*config.grad_accum
            window_size=min(config.grad_accum,steps_per_epoch-window_start)
            (loss/window_size).backward();n_steps+=1;total+=loss.item()
            if n_steps%config.grad_accum==0 or start+config.micro_batch>=len(epoch_items):
                torch.nn.utils.clip_grad_norm_(params,config.grad_clip)
                optimizer.step();scheduler.step();optimizer.zero_grad(set_to_none=True);updates+=1
                final_batch=start+config.micro_batch>=len(epoch_items)
                stop=stop_after_updates is not None and updates>=stop_after_updates
                if updates%checkpoint_every_updates==0 or final_batch or stop:
                    save(epoch,min(start+config.micro_batch,len(epoch_items)),total,n_steps)
                if stop:return None
            if config.log_every and n_steps%config.log_every==0:
                print(f'epoch {epoch+1}/{config.epochs} step {n_steps} loss {loss.item():.4f}',flush=True)
        mean=total/max(1,n_steps);history.append(mean)
        print(f'epoch {epoch+1}/{config.epochs} mean loss {mean:.4f}',flush=True)
        if on_epoch_end is not None:on_epoch_end(epoch,mean)
        save(epoch+1,0,0.,0)
    model.eval()
    return history
