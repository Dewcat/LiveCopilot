#!/usr/bin/env python3
"""Local-only full Laya fine-tuning using the pinned official training functions.

Explicit family-separated calibration/dev data; acceptance is never read here.
Checkpoints and optimizer state stay outside source control.
"""
import argparse
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import time

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
                  HF_HUB_DISABLE_TELEMETRY="1", TOKENIZERS_PARALLELISM="false")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--base", required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    p.add_argument("--epochs", type=int, default=4)
    p.add_argument("--pilot", action="store_true")
    p.add_argument("--freeze-encoder", action="store_true")
    p.add_argument("--encoder-lr", type=float, default=2.5e-5)
    p.add_argument("--head-lr", type=float, default=1e-4)
    p.add_argument("--seed", type=int, default=20261016)
    p.add_argument("--task-version", default="local-response-v1")
    p.add_argument("--durable-checkpoints", action="store_true")
    p.add_argument("--resume", action="store_true")
    p.add_argument("--consistency-weight", type=float, default=0.)
    args = p.parse_args()
    if args.consistency_weight and not args.durable_checkpoints:
        raise SystemExit("Paired consistency requires the durable trainer")
    if args.resume and (not args.durable_checkpoints or not (args.out / "resume.pt").exists()):
        raise SystemExit("Resume requires a durable local checkpoint")
    if args.out.exists() and not args.resume:
        raise SystemExit("Refusing to overwrite an existing run")
    if (args.out / "report.json").exists():
        raise SystemExit("Run is already complete")
    import torch
    from laya.train import (TrainConfig, load_checkpoint, items_from_rows, train_model,
                            calibration_records, evaluate_records, save_checkpoint, optimizer_updates,
                            calibration_report)
    from laya.calibrate import fit_temperature_map
    torch.set_num_threads(6)
    torch.manual_seed(args.seed)
    device = torch.device("mps")
    if not torch.backends.mps.is_available():
        raise SystemExit("MPS unavailable")
    model, tok, cfg = load_checkpoint(args.base)
    model.to(device)
    data_manifest = json.loads((args.data / "manifest.json").read_text())
    known_development = data_manifest.get("development_scope") == "known_training_regression"
    if known_development and (args.epochs != 1 or args.pilot):
        raise SystemExit("Promoted development requires one fixed epoch, never validation-based checkpoint selection")
    datasets = {}
    for split in ("train", "calibration", "development"):
        content = (args.data / f"{split}.jsonl").read_bytes()
        assert hashlib.sha256(content).hexdigest() == data_manifest["splits"][split]["sha256"]
        rows = [json.loads(line) for line in content.splitlines()]
        items, skipped = items_from_rows(tok, rows, 1024, 256, label_smoothing=.02 if split == "train" else 0)
        assert len(items) == len(rows), skipped
        datasets[split] = items
    config = TrainConfig(epochs=1 if args.pilot else args.epochs, micro_batch=2, grad_accum=4,
                         encoder_lr=args.encoder_lr, head_lr=args.head_lr, loss="soft-ce",
                         seed=args.seed, amp=False, gradient_checkpointing=True,
                         freeze_encoder=args.freeze_encoder, max_len=1024, head_max_len=256,
                         calib_frac=0, calib_max=0, log_every=10, label_smoothing=.02)
    if args.pilot:
        datasets["train"] = datasets["train"][:32]
        datasets["development"] = datasets["development"][:8]
    args.out.mkdir(parents=True, exist_ok=args.resume)
    manifest = dict(config=asdict(config), base=args.base, data_manifest=data_manifest,
                    torch=torch.__version__, pilot=args.pilot,
                    durable_checkpoints=args.durable_checkpoints,
                    updates=optimizer_updates(len(datasets["train"]), 2, 4, config.epochs),
                    selection=("single predeclared epoch; development is known training regression, not checkpoint selection"
                               if known_development else "lowest development cross-entropy at temperature 1; acceptance never read"))
    if args.consistency_weight:
        if not data_manifest.get('paired_consistency'):
            raise SystemExit('Dataset must declare independently reviewed equivalent adjacent pairs')
        manifest['consistency_weight'] = args.consistency_weight
    # Dataclass tuple fields become JSON lists on disk. Compare their serialized
    # representation so an identical configuration can actually resume.
    manifest = json.loads(json.dumps(manifest))
    if args.resume:
        if json.loads((args.out / "run.json").read_text()) != manifest:
            raise SystemExit("Resume manifest does not match original run")
    else:
        (args.out / "run.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps({k:v for k,v in manifest.items() if k != "data_manifest"}), flush=True)
    started = time.monotonic()
    selection = dict(best=float("inf"), epochs=[])

    def validate(epoch, loss):
        records = calibration_records(model, tok, datasets["development"], device, 1024, 256, batch_size=2)
        metrics = evaluate_records(records, [1., 1., 1.])
        entry = dict(epoch=epoch + 1, train_loss=loss, development=metrics,
                     development_scope=data_manifest.get("development_scope", "independent_selection"),
                     elapsed_seconds=time.monotonic() - started,
                     mps_allocated_mb=torch.mps.current_allocated_memory() / 1048576,
                     mps_driver_mb=torch.mps.driver_allocated_memory() / 1048576)
        selection["epochs"] = [e for e in selection["epochs"] if e["epoch"] != epoch + 1] + [entry]
        print("VALIDATION " + json.dumps(entry), flush=True)
        if metrics["loss"] < selection["best"]:
            selection["best"] = metrics["loss"]
            save_checkpoint(model, tok, dict(cfg, max_len=1024, head_max_len=256), str(args.out / "best"))
        (args.out / "epochs.json").write_text(json.dumps(selection["epochs"], indent=2) + "\n")
        # The official callback leaves model.eval() after dev inference.
        model.train()
        if args.freeze_encoder:
            model.encoder.eval()

    if args.durable_checkpoints:
        from laya_resumable_training import train_resumable
        fingerprint = dict(data_manifest_sha256=hashlib.sha256((args.data / "manifest.json").read_bytes()).hexdigest(),
                           base_weights_sha256=hashlib.sha256((Path(args.base) / "model.safetensors").read_bytes()).hexdigest(),
                           task_version=args.task_version)
        losses = train_resumable(model, tok, datasets["train"], config, device, 1024, 256,
                                 args.out / "resume.pt", fingerprint, selection,
                                 on_epoch_end=validate, resume=args.resume,
                                 consistency_weight=args.consistency_weight)
    else:
        losses = train_model(model, tok, datasets["train"], config, device, 1024, 256, on_epoch_end=validate)
    del model
    torch.mps.empty_cache()
    model, tok, best_cfg = load_checkpoint(str(args.out / "best"))
    model.to(device)
    records = calibration_records(model, tok, datasets["calibration"], device, 1024, 256, batch_size=2)
    fitted = fit_temperature_map(records)
    calibration = calibration_report(records, fitted["temperature"])
    best_cfg.update(max_len=1024, head_max_len=256, fine_tuned=True, temperature=fitted["temperature"])
    best_cfg.pop("temperature_by_options", None)
    if fitted["temperature_by_options"]:
        best_cfg["temperature_by_options"] = fitted["temperature_by_options"]
    best_cfg["training"] = dict(livecopilot=dict(config=asdict(config), calibration=calibration,
                                                data_hashes=data_manifest["splits"],
                                                task="needs_response", version=args.task_version))
    if args.consistency_weight:
        best_cfg['training']['livecopilot']['paired_consistency_weight']=args.consistency_weight
    save_checkpoint(model, tok, best_cfg, str(args.out / "calibrated"))
    (args.out / "calibrated/questions.json").write_text(json.dumps(data_manifest["question"], indent=2) + "\n")
    report = dict(losses=losses, epochs=selection["epochs"], calibration=calibration,
                  elapsed_seconds=time.monotonic() - started,
                  acceptance="not evaluated; must be evaluated separately after checkpoint selection")
    (args.out / "report.json").write_text(json.dumps(report, indent=2) + "\n")
    print("COMPLETE " + json.dumps(report), flush=True)


if __name__ == "__main__":
    main()
