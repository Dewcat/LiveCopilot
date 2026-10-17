"""Offline native regression: python3 check_embedding_runtime.py WORKER MODEL_DIR [BASELINE].
Uses synthetic text only; model files are read, never installed or changed.
"""
import json
import math
import subprocess
import sys


def vectors(worker, root, mode):
    # Exercise small context, context growth, then reuse for a short input.
    texts = ["Method B latency is 42 milliseconds.",
             "检索测试资料。" * 180,
             "Method B latency is 42 milliseconds.",
             "方法 B 的延迟是多少？", "Bananas are yellow fruit."]
    commands = "".join(json.dumps({"id": str(i), "op": "embed", "text": text}) + "\n"
                       for i, text in enumerate(texts))
    result = subprocess.run([worker, mode, root], input=commands, text=True,
                            capture_output=True, timeout=180)
    assert result.returncode == 0, result.stdout
    rows = [json.loads(line) for line in result.stdout.splitlines()]
    assert rows[0]["ready"] is True and len(rows) == len(texts) + 1, rows[0]
    output = []
    for i, row in enumerate(rows[1:]):
        assert row["id"] == str(i) and "error" not in row, row.get("error")
        value = row["vector"]
        assert len(value) == 1024 and all(math.isfinite(x) for x in value)
        assert abs(sum(x*x for x in value) - 1) < 1e-5
        output.append(value)
    assert cosine(output[0], output[2]) > 0.9999
    assert cosine(output[3], output[0]) > cosine(output[3], output[4]) + 0.1
    return output


def cosine(a, b):
    return sum(x*y for x, y in zip(a, b))


if __name__ == "__main__":
    worker, root = sys.argv[1:3]
    gpu = vectors(worker, root, "embedding")
    cpu = vectors(worker, root, "embedding-cpu")
    # Quantized CPU and Metal kernels need not be bit-identical; require close
    # direction plus the bilingual retrieval ordering checked above.
    similarity = min(cosine(a, b) for a, b in zip(gpu, cpu))
    assert similarity > 0.995, similarity
    print(f"PASS: CPU/GPU minimum cosine {similarity:.8f}; bilingual retrieval ordering")
    print("PASS: GPU and CPU: normalized 1024-dimensional vectors; context growth and reuse")
    if len(sys.argv) > 3:
        baseline = vectors(sys.argv[3], root, "embedding")
        similarity = min(cosine(a, b) for a, b in zip(gpu, baseline))
        assert similarity > 0.9999, similarity
        print(f"PASS: existing index compatibility; minimum cosine against baseline {similarity:.8f}")
