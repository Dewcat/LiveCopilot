#!/usr/bin/env python3
"""Build an isolated, receipt-verified test installation; never changes production.

The staged resources intentionally have no download manifest. They are only for
opt-in XCTest/worker acceptance, not an application distribution or model update.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import sys

os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--out", type=Path, required=True)
    args = p.parse_args()
    if args.out.exists():
        raise SystemExit("Refusing to replace a staged installation")
    sys.path.insert(0, str(args.runtime / "source"))
    from laya_mlx.convert import convert
    current = args.out / "runtime/current"
    current.mkdir(parents=True)
    convert(args.model.resolve(), current / "model", dtype="float16")
    shutil.copytree(args.runtime / "source", current / "source", ignore=shutil.ignore_patterns("__pycache__", ".git"))
    (current / "venv").symlink_to((args.runtime / "venv").resolve(), target_is_directory=True)
    hashes = {str(p.relative_to(current)): hashlib.sha256(p.read_bytes()).hexdigest()
              for folder in ("model", "source") for p in (current / folder).rglob("*") if p.is_file()}
    identifier = "local-response-candidate-" + hashes["model/model.safetensors"][:16]
    receipt = dict(schema=1, pin_id=identifier, files=hashes)
    (current / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    resources = args.out / "resources"
    resources.mkdir()
    production = Path(__file__).resolve().parents[1] / "Resources/LayaRuntime/worker.py"
    shutil.copy2(production, resources / "worker.py")
    (resources / "pins.json").write_text(json.dumps(dict(id=identifier, test_only=True)) + "\n")
    print(json.dumps(dict(root=str((args.out / "runtime").resolve()), resources=str(resources.resolve()),
                          model_sha256=hashes["model/model.safetensors"], test_only=True)))


if __name__ == "__main__":
    main()
