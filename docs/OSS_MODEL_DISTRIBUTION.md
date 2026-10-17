# Historical OSS model distribution

> **Disabled as of 2026-09-24.** The full model set is 1,639,227,742 bytes (about 1.64 GB). At the then-reviewed rate, each complete user download would incur about CNY 0.7 of internet egress, scaling without a cap. Alibaba OSS was therefore not selected for model distribution.
>
> Development moved to the [dedicated ModelScope repository](MODELSCOPE_MODEL_DISTRIBUTION.md) for 37 files, followed by applicable mirrors/upstream. The OSS instructions below are historical, not active routing.
>
> Release **2.0.0 embeds a public immutable ModelScope HTTPS revision**, with no OSS address or AccessKey. Dev `model-distribution.json` contains only ModelScope; the old OSS configuration was retained as `model-distribution.json.disabled`. Manifests, staging, and policies below remain reference material.

## Manifest and licenses

[`oss-model-manifest.json`](oss-model-manifest.json) records 37 required object keys, pinned sources, hashes, licenses, and known sizes. Generate with `python3 StealthApp/scripts/oss-manifest.py > docs/oss-model-manifest.json`; regenerate/review before uploading. Preserve manifest paths. A base URL may contain a prefix such as `https://<bucket>.oss-cn-hangzhou.aliyuncs.com/models`.

| Group | Objects | License | Source |
| --- | ---: | --- | --- |
| Paraformer INT8 encoder/decoder/tokens | 3 | Apache-2.0 | [Pinned model card](https://huggingface.co/csukuangfj/sherpa-onnx-streaming-paraformer-bilingual-zh-en/tree/8e40c43232a1c5c66c82111efc5820d3accca11b) |
| Silero VAD ONNX | 1 | MIT | [License](https://github.com/snakers4/silero-vad/blob/master/LICENSE) |
| BGE-M3 Q8 GGUF | 1 | MIT | [Quantized repository](https://huggingface.co/gpustack/bge-m3-GGUF/tree/2d48f1737679ad900d5c26c5aad5410e9c70fdca) |
| Laya CPython 3.12.14 | 1 | PSF-2.0 | Pinned archive in `pins.json` |
| laya-mlx source | 1 | Apache-2.0 | Pinned source commit; app retains LICENSE/NOTICE |
| Laya model including LICENSE/NOTICE | 11 | Apache-2.0 | Pinned revision; notices distributed with model |
| Python wheels | 19 | Per-file manifest | Versioned PyPI metadata; retain archive `.dist-info` licenses |

Only installer-required files are included, not whole repositories. Model licenses come from upstream declarations/distributed files; wheel composite licenses are governed by archive texts. Retain notices and never put user documents, conversations, or keys in the bucket.

## Historical bucket preparation

1. Created dedicated `livecopilot-models-cn-7b4f`, East China 2 (Shanghai), `oss-cn-shanghai`, standard/local redundancy/private ACL. Block Public Access stayed on. Storage, requests, and egress incur fees. [Console](https://oss.console.aliyun.com/), [billing](https://help.aliyun.com/zh/oss/billing-overview), [bucket creation](https://help.aliyun.com/zh/oss/user-guide/create-a-bucket-4).
2. `python3 StealthApp/scripts/oss-stage.py` stages under `StealthApp/build/oss-stage/objects/`, checks every SHA-256, and copies verified local BGE without changing installed models. All 37 files / 1,639,227,742 bytes passed local verification. `StealthApp/build/oss-stage/upload/models/` is a hard-linked console-upload tree. On 2026-09-24 the console reported 37 successes, zero failures, with only `models/` at root and `local/`/`laya/` beneath. Upload sources passed another size/hash check. Upload rights stayed in the administrator session, not the app. Anonymous remote verification still required a working policy.
3. Without an embedded AccessKey or URL-signing service, objects require anonymous read. The draft [policy](oss-bucket-policy.json) keeps bucket ACL private and permits only HTTPS `oss:GetObject` for `models/local/*` and `models/laya/*`, without list/write/delete/admin. [Policy documentation](https://help.aliyun.com/zh/oss/user-guide/use-bucket-policy-to-grant-permission-to-access-oss/). Block Public Access overrides that grant; changing it would make model URLs public and requests billable. No private data belongs here. [Block Public Access](https://help.aliyun.com/zh/oss/user-guide/block-public-access).
4. Verify credential-free `curl -I https://<bucket>.oss-<region>.aliyuncs.com/models/local/paraformer-tokens.txt` returns 200, missing paths return 403/404, anonymous listing is denied, and large objects support Range/206 for Laya chunks. Client hashes remain authoritative; mismatches fall back.

The console equivalent selects specified prefixes, all accounts, read-only without ListObject, narrows actions to `oss:GetObject`, and requires HTTPS. Exact UI depends on the current console.

## Disabled OSS configuration

The former proposed Dev override at `~/Library/Application Support/LiveCopilot/Development/model-distribution.json` was:

```json
{"ossBaseURL":"https://livecopilot-models-cn-7b4f.oss-cn-shanghai.aliyuncs.com/models"}
```

Do not replace the current ModelScope configuration with it. It contains only a public HTTPS base, no credentials/signatures/user data. The historical implementation read it per download, otherwise used mirrors. BGE/Paraformer/VAD and Laya Python/source/wheels/model route per file, with the same pinned hash across all sources; unreachable, truncated, or incorrect content advances to the next source.

| Order | Historical route |
| --- | --- |
| 1 | Configured public distribution base; the OSS example is disabled |
| 2 | File-specific mirror, e.g. BGE-M3 Q8 on ModelScope `gpustack/bge-m3-GGUF`, matching pinned bytes |
| 3 | Host mirrors: Hugging Face → hf-mirror; GitHub releases → gh-proxy / hk.gh-proxy / ghproxy.net; codeload → hk.gh-proxy; CPython prefers USTC/NJU github-release mirrors; PyPI → Tsinghua |
| 4 | Upstream |

Historical home-network tests without a proxy reported ModelScope 11.6 MB/s, hf-mirror 1.8–4.9 MB/s, USTC/NJU 12–15 MB/s, and gh-proxy 0.67 MB/s; direct GitHub did not finish the same file in 45.5 seconds and remained last fallback. Settings reports current-file percentage/bytes/speed; small files may show only initial/completed states. Cancellation/hash failure never replaces an installed model.

Local hashes passed for all 37 upload objects and the console reported success, but the bucket remained private with public access blocked; anonymous downloads were unavailable. See [ModelScope records](MODELSCOPE_MODEL_DISTRIBUTION.md) for actual active repository, revision, remote hashes, and download results.
