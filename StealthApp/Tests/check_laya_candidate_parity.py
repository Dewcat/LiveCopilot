#!/usr/bin/env python3
"""Record official/MLX predictions on frozen development inputs for export parity."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import sys

os.environ.update(USE_TF="0", HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
p = argparse.ArgumentParser()
p.add_argument("--backend", choices=["torch", "mlx"], required=True)
p.add_argument("--source", type=Path, required=True)
p.add_argument("--model", type=Path, required=True)
p.add_argument("--data", type=Path, required=True)
p.add_argument("--out", type=Path, required=True)
args = p.parse_args()
if args.out.exists():
    raise SystemExit("Refusing to replace parity evidence")
sys.path.insert(0, str(args.source))
if args.backend == "torch":
    import laya
    from laya.common import build_sequence, QTYPES
    agent = laya.load(str(args.model), device="mps")
else:
    import laya_mlx
    agent = laya_mlx.load(args.model, dtype="float16")
result = []
for i, line in enumerate(args.data.read_text().splitlines()):
    row = json.loads(line)
    if args.backend == "torch":
        internal = agent._to_internal(row["questions"]["needs_response"])
        ids, markers = build_sequence(agent.tok, row["state"], internal, 1024, 256)
        prepared = dict(ids=ids, markers=markers, qtype=QTYPES[internal["t"]])
    else:
        items, _ = agent.prepare(row["state"], row["questions"])
        prepared = {key: items[0][key] for key in ("ids", "markers", "qtype")}
    score = agent.predict(row["state"], row["questions"])["answers"]["needs_response"]["noul"]
    result.append(dict(index=i, score=score, prepared_sha256=hashlib.sha256(json.dumps(prepared, sort_keys=True).encode()).hexdigest()))
args.out.write_text(json.dumps(dict(backend=args.backend, model_sha256=hashlib.sha256((args.model / "model.safetensors").read_bytes()).hexdigest(),
                                    data_sha256=hashlib.sha256(args.data.read_bytes()).hexdigest(), rows=result), indent=2) + "\n")
print(json.dumps(dict(backend=args.backend, rows=len(result))))
