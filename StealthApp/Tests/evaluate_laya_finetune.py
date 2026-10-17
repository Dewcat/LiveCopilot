#!/usr/bin/env python3
"""Evaluate a frozen checkpoint through the exact production worker state builder.

Use development before selection. Acceptance is read only for a frozen candidate.
Nonzero exit means the predeclared semantic release gate has not passed.
"""
import argparse
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time

os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1")


def summarize(rows):
    positive = [r for r in rows if r["expected"]]
    negative = [r for r in rows if not r["expected"]]
    return dict(total=len(rows), passed=sum(r["passed"] for r in rows),
                accuracy=sum(r["passed"] for r in rows) / len(rows),
                recall=sum(r["triggered"] for r in positive) / max(1, len(positive)),
                false_positive_rate=sum(r["triggered"] for r in negative) / max(1, len(negative)),
                missed_requests=sum(not r["triggered"] for r in positive),
                false_triggers=sum(r["triggered"] for r in negative),
                median_ms=round(statistics.median(r["ms"] for r in rows), 2),
                max_ms=round(max(r["ms"] for r in rows), 2))


def development_context_gate(rows, limits):
    contexts = {}
    passed = True
    for condition in ["short", "long"]:
        subset = [r for r in rows if r["context_condition"] == condition]
        assert subset and any(r["expected"] for r in subset) and any(not r["expected"] for r in subset)
        if condition == "long":
            assert all(950 <= r["tokens"] <= 1024 for r in subset)
        value = summarize(subset)
        contexts[condition] = value
        passed &= value["recall"] >= limits["recall_min"] and value["false_positive_rate"] <= limits["false_positive_rate_max"]
    return contexts, passed


def development_group_gate(rows, limits):
    groups = {}
    passed = True
    for group in sorted({r['development_group'] for r in rows}):
        require_rows = [r for r in rows if r['development_group'] == group]
        values, valid = development_context_gate(require_rows, limits)
        groups[group] = values
        passed &= valid
    assert groups
    return groups, passed


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--model", type=Path, required=True)
    p.add_argument("--runtime", type=Path, required=True)
    p.add_argument("--data", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--split", choices=["development", "acceptance"], default="development")
    args = p.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to overwrite evaluation evidence")
    sys.path.insert(0, str(args.runtime / "source"))
    import laya_mlx
    resource = Path(__file__).resolve().parents[1] / "Resources/LayaRuntime/worker.py"
    spec = importlib.util.spec_from_file_location("worker", resource)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)
    manifest = json.loads((args.data / "manifest.json").read_text())
    assert manifest["question"] == worker.QUESTIONS
    agent = laya_mlx.load(args.model, dtype="float16")
    worker.predict(agent, "This is a warmup statement.", "")
    rows = []
    splits = [args.split] + (["regression"] if args.split == "acceptance" else [])
    for split in splits:
        path = args.data / f"{split}.json"
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest["splits"][split]["fixture_sha256"]
        for case in json.loads(path.read_text()):
            start = time.monotonic()
            score, tokens = worker.predict(agent, case["text"], json.dumps(case["context"], ensure_ascii=False))
            triggered = score >= manifest["threshold"]
            rows.append(dict(id=case["id"], split=split, expected=case["respond"], score=score,
                             category=case.get("category", "unspecified"),
                             context_condition=case.get("context_condition", "short"),
                             development_group=case.get("development_group", "existing"),
                             triggered=triggered, passed=triggered == case["respond"],
                             tokens=tokens, ms=(time.monotonic() - start) * 1000))
    if args.split == "acceptance":
        # Predeclared perturbations, not additional independent examples. Old
        # handled requests and long answers must not change the newest intent.
        cases = json.loads((args.data / "acceptance.json").read_text())
        stride = manifest.get("long_context_stride", 4)
        assert type(stride) is int and stride > 0
        selected = [c for i, c in enumerate(cases) if i % stride == 0]
        for case in selected:
            old_turns = [dict(speaker="Them" if i % 2 else "You", handled=bool(i % 2),
                              text=("请解释上周测试数据的来源。" if i % 2 else "测试数据来自合成样本，已经归档。") * 16)
                         for i in range(40)]
            context = dict(case["context"], recentTurns=old_turns + case["context"]["recentTurns"])
            start = time.monotonic()
            score, tokens = worker.predict(agent, case["text"], json.dumps(context, ensure_ascii=False))
            triggered = score >= manifest["threshold"]
            rows.append(dict(id=case["id"] + ":long-history", split="long_context", expected=case["respond"],
                             category=case.get("category", "unspecified"),
                             score=score, triggered=triggered, passed=triggered == case["respond"], tokens=tokens,
                             ms=(time.monotonic() - start) * 1000))
        splits.append("long_context")
    summaries = {split: summarize([r for r in rows if r["split"] == split]) for split in splits}
    categories = {category: summarize([r for r in rows if r["split"] == args.split and r["category"] == category])
                  for category in sorted({r["category"] for r in rows if r["split"] == args.split})}
    limits = manifest["acceptance_gate"]
    result = summaries[args.split]
    passed = result["recall"] >= limits["recall_min"] and result["false_positive_rate"] <= limits["false_positive_rate_max"]
    development_contexts = {}
    development_groups = {}
    if args.split == "development" and manifest.get("development_context_gate"):
        development_contexts, context_passed = development_context_gate(rows, limits)
        passed &= context_passed
    if args.split == "development" and manifest.get("development_group_gate"):
        development_groups, group_passed = development_group_gate(rows, limits)
        passed &= group_passed
    if "regression" in summaries:
        passed &= summaries["regression"]["accuracy"] >= limits["regression_accuracy_min"]
        passed &= summaries["long_context"]["recall"] >= limits["recall_min"]
        passed &= summaries["long_context"]["false_positive_rate"] <= limits["false_positive_rate_max"]
    report = dict(threshold=manifest["threshold"], model_sha256=hashlib.sha256((args.model / "model.safetensors").read_bytes()).hexdigest(),
                  worker_sha256=hashlib.sha256(resource.read_bytes()).hexdigest(), config=agent.cfg,
                  manifest=manifest, summaries=summaries, categories=categories, rows=rows, semantic_gate_passed=passed,
                  development_contexts=development_contexts,
                  development_groups=development_groups,
                  application_acceptance="not evaluated by this script")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(dict(summaries=summaries, semantic_gate_passed=passed), indent=2), flush=True)
    # Acceptance failures are stored for diagnosis, not converted to training data.
    if args.split == "development":
        print(json.dumps([r for r in rows if not r["passed"]], ensure_ascii=False, indent=2))
    sys.exit(0 if passed else 1)


if __name__ == "__main__":
    main()
