# LiveCopilot ModelScope distribution

## Release-preparation check: 2026-10-17

The public `careybk/livecopilot-model-assets` repository still contains the upstream Laya weight with SHA-256 `7fc5834af4d8fdfb268d272a9d1a66e5819a0daac98241651c4c888cc43adff1`. It is not the accepted fine-tuned response checkpoint. Zipformer is available from a separately pinned upstream ModelScope repository, not this account's asset repository. See [current model release readiness](MODEL_RELEASE_READINESS.md).

## Historical distribution validation

- OSS routing was disabled; the app contained no OSS address or AccessKey. The OSS bucket remained private, anonymous requests returned 403, and uploaded files were retained.
- Created public repository [careybk/livecopilot-model-assets](https://modelscope.cn/models/careybk/livecopilot-model-assets). The repository license is `other`; README and manifest specify each file's applicable license. All 40 uploaded paths, sizes, and SHA-256 values matched the local manifest through the ModelScope API, excluding the platform-generated `.gitattributes`.
- Pinned revision: `a5ba0b9be08e7d8f7438e3762791ac5b62c1e253`. Anonymous HEAD returned 200 for all 37 distribution files; `X-Linked-Etag` matched each manifest hash and Range returned 206. A full 634,553,760-byte BGE-M3 Q8 download matched SHA-256: 56.25 seconds / 11.28 MB/s with inherited proxy variables, and 51.02 seconds / 12.44 MB/s with `curl --noproxy '*'`. The 165,462,184-byte Paraformer and 24,981,445-byte Laya Python downloads passed installer-directory verification with intermediate percentage, byte, and speed callbacks. A 132,079-byte Laya wheel successfully fell back from a ModelScope 404 to Tsinghua and passed its hash.
- The distribution set contains 37 files totaling 1,639,227,742 bytes: Paraformer, Silero VAD, BGE, Laya model, and isolated Python dependencies. See the [per-file manifest](oss-model-manifest.json) for origins, licenses, hashes, and sizes.
- Dev `20260924.003` fixed numeric `size` parsing in the Laya Python pin; the entire entry cannot be cast to a string dictionary. A native regression covers the real structure. With the bundled installer and the app's isolated process environment, all 31 Laya dependency/model files downloaded from ModelScope and passed SHA-256 without fallback. The Python bootstrap archive had already passed a separate full download. A Dev receipt was created; the offline worker returned `ready` and predicted a synthetic question. General visibly showed `20260924.003`; desktop automation crashed while opening Services, so that page was not accepted visually.

## Staging uploads

Run `python3 StealthApp/scripts/modelscope-stage.py`. It reads existing verified staging sources and creates `StealthApp/build/modelscope-stage/`. Hard links reuse the 37 distribution files without altering installed models or user data. README lists origins, licenses, sizes, and hashes; `artifact-manifest.json` retains machine-readable metadata.

Use a dedicated public model repository with `local/` and `laya/` paths. Check visibility, content rules, and mixed-license declarations before uploading. Laya LICENSE/NOTICE accompany the model; wheels retain archive license metadata. The tokenizers 0.23.2 wheel metadata declares Apache Software License but lacks the full text, so staging adds `LICENSES/tokenizers-0.23.2-APACHE-2.0.txt`. Record the actual repository URL and immutable revision after upload, and compare every remote size/hash. Never upload user documents, conversations, keys, or private application configuration.

The official client supports [`ms-hub upload`](https://github.com/modelscope/modelscope_hub#ms-hub-upload) and individual downloads. An isolated Python 3.11 environment was prepared at `StealthApp/build/modelscope-tools-venv311/`. The account owner enters a write token interactively; never put it in the app, repository, chat, or command arguments. The repository uses license `other` because individual files have different licenses. Upload directory contents at the repository root:

```sh
ms-hub upload careybk/livecopilot-model-assets StealthApp/build/modelscope-stage/ '' --repo-type model
```

Availability, traffic policies, and speed depend on the platform and user network; one local benchmark is not a guarantee.

## Application routing

The historical Dev override was `~/Library/Application Support/LiveCopilot/Development/model-distribution.json`:

```json
{"modelScopeBaseURL":"https://modelscope.cn/models/careybk/livecopilot-model-assets/resolve/a5ba0b9be08e7d8f7438e3762791ac5b62c1e253"}
```

Release 2.0.0 uses this immutable revision by default, without user setup. An optional local `modelScopeBaseURL` overrides it; no AccessKey is embedded. Applicable `local/...` and `laya/...` files try this repository first, then configured mirrors/upstream. Every source must pass the pinned SHA-256. Settings show real current-file percentage, downloaded bytes, and speed. Zipformer was subsequently added with its own pinned route rather than this distribution prefix.

Historical local regression: Debug build, 70 core checks, 17 Python download checks, and 47 native tests (one skipped) passed; `git diff --check` passed. Installed `LiveCopilot Dev 1.4.2 (20260924.002)` passed strict Developer ID validation and matched the previous designated requirement; the old app was backed up. Version text was visually confirmed, while Services inspection was interrupted. Temporary probes were removed. Installed BGE/Paraformer and user data were unchanged; Laya had not been found at the expected installation path before that update.
