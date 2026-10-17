"""Opt-in offline comparison using fixed synthetic text and existing weights.

Run with the installed Laya environment's Python. No downloads or answer API calls.
This measures worker prediction, not audio-to-answer latency or general accuracy.
"""

import argparse
import importlib.util
import json
import os
from pathlib import Path
import statistics
import sys
import time


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--worker", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--cache", action="store_true")
    args = parser.parse_args()
    os.environ.update(HF_HUB_OFFLINE="1", TOKENIZERS_PARALLELISM="false")
    sys.dont_write_bytecode = True
    sys.path.insert(0, args.source)
    spec = importlib.util.spec_from_file_location("worker", args.worker)
    worker = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(worker)

    started = time.perf_counter()
    import laya_mlx

    agent = laya_mlx.load(args.model, dtype="float16", cache_prompts=args.cache)
    loaded = time.perf_counter()
    worker.predict(agent, "The meeting starts at nine.", "")
    warmed = time.perf_counter()
    cases = json.loads(Path(__file__).with_name("laya_intent_samples.json").read_text())
    cases += [
        {"id": "mixed", "text": "请解释 React 的 useEffect 和 Vue watch 有什么区别？", "respond": True},
        {"id": "mixed-short", "text": "Redis 呢？", "respond": True},
        {
            "id": "long",
            "text": "我们正在设计一个多租户系统，需要兼顾权限隔离、数据库扩展、缓存失效和线上回滚。" * 30
            + "请说明你会如何设计 Redis 缓存失效和故障恢复方案？",
            "respond": True,
        },
        {
            "id": "multi-followup", "text": "那你会如何验证这个优化没有引入新的问题？",
            "context": "对方：为什么要使用 Redis？我：为了减少数据库查询。", "respond": True,
        },
        {
            "id": "multi-ack", "text": "明白了，谢谢。",
            "context": "对方：你能解释架构吗？我：用了微服务。", "respond": False,
        },
    ]
    rows = []
    for case in cases:
        times = []
        for _ in range(5):
            start = time.perf_counter()
            score, tokens = worker.predict(agent, case["text"], case.get("context", ""))
            times.append((time.perf_counter() - start) * 1000)
        rows.append(dict(case, score=score, tokens=tokens, times_ms=times,
                         matches=(score >= 0.8) == case["respond"]))
    result = dict(source=args.source, version=laya_mlx.__version__, cache=args.cache,
                  load_ms=(loaded - started) * 1000, warmup_ms=(warmed - loaded) * 1000, rows=rows)
    Path(args.output).write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(args.output, "mean_ms=", statistics.mean(t for row in rows for t in row["times_ms"]),
          "fixture_matches=", sum(row["matches"] for row in rows), "/", len(rows))


if __name__ == "__main__":
    main()
