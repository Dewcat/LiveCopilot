# Knowledge model loading investigation — 2026-10-17

Two users reported a downloaded model failing to load on the Knowledge page. The screenshot shows v2.3.0 and the local BGE-M3 model identity. Hardware, OS and native diagnostics from those machines are unavailable; their specific root cause is **not confirmed**.

## Confirmed implementation issues

- All native initialization exceptions were converted to `model_load_failed`; Swift always recommended downloading again. The message did not establish that model files were corrupt.
- Each embedding worker allocated an 8192-token context/batch/microbatch at startup, even for a short query.
- Model and context initialization had no CPU retry after a recoverable GPU failure.

## Changes

- Start at 512 tokens and grow by powers of two up to the existing 8192-token input limit. Keep the entire bidirectional BGE input in one microbatch. Keep weights, pooling, normalization and index identity unchanged.
- Retry failed GPU model/context initialization with CPU devices only and both operation/KQV offloading disabled. Expose `embedding-cpu` as a native diagnostic mode.
- Preserve a fixed context-allocation failure code over IPC and show a specific retry message. General load failures no longer automatically blame the download. No document text, paths or raw native logs are added to UI diagnostics.
- Preserve installed models, knowledge data and settings.

## Local evidence and limits

On Apple M4 Max, with the existing real BGE-M3 weights and bundled llama.cpp b10955 framework:

- Startup compute buffers: previous GPU 341.54 MiB + CPU 224.09 MiB; updated GPU 17.94 MiB + CPU 6.51 MiB. Model mappings remain about 599 MiB. These are runtime-reported buffers, not total process memory or a promise for every Mac.
- Native helper compiles for arm64 and x86_64. Real execution was on Apple Silicon, including forced CPU; it does not establish Intel hardware compatibility.
- Temporary native test variants forced model-load failure or context creation failure on the GPU path. Both automatically retried on CPU and produced a 1024-dimensional vector.
- Universal Release app build passed after regenerating the local Xcode project. The rebuilt helper with bundle-relative runtime paths was placed into the isolated build and successfully generated a real 1024-dimensional embedding. The installed app was not replaced.
- 74 deterministic Swift checks passed, including startup error classification.
- `StealthApp/Tests/check_embedding_runtime.py WORKER MODEL_DIR [BASELINE]` exercises real GPU/CPU inference, context growth/reuse, finite unit vectors, bilingual retrieval ordering and old/new GPU vector compatibility. CPU/Metal quantized kernels are not bit-identical: observed minimum cosine on the initial fixtures was 0.99797746; old/new GPU cosine was 1.0. The regression requires CPU/GPU cosine >0.995 plus correct retrieval ordering, and old/new GPU cosine >0.9999.

Automatic CPU fallback handles initialization APIs returning failure. Native aborts, OS termination and process-level timeouts remain separate limitations. No signed release or user-machine acceptance is implied by these local checks.

## Follow-up differential diagnosis

- Checked the v2.3.0 tag: the screenshot's exact message is emitted when the child returns a non-ready JSON response during initialization. Missing executables, process launch errors, EOF/crashes/timeouts and per-input inference errors take different paths. This strongly narrows the screenshot to initialization; it does not identify which initialization stage failed.
- An isolated sparse file of exactly the legitimate GGUF size, paired with the installation receipt, passes the existing size-based installed check and reproduces `model_load_failed`. Downloads are SHA-256 checked before commit, so this is a demonstrated post-install integrity gap, not evidence that the downloader accepts corrupted payloads. Real local weights match the pinned SHA-256.
- Real model startup succeeds through a directory containing Chinese characters and spaces. Both download status and knowledge provider use the same model root in the coordinator; no root mismatch was found.
- The original universal worker executed successfully as x86_64 through Rosetta and generated 1024 dimensions. Rosetta does not validate physical Intel CPUs, Intel/AMD GPUs or older macOS drivers.
- Installed v2.3.0 llama framework and repository framework have identical unsigned arm64 and x86_64 slices. Their raw hashes differ because of Developer ID versus ad-hoc signing. This does not establish the provenance of either reporting user's app.
- A failed document's error is persisted in SQLite. Downloading/restarting does not automatically reindex it: a historical error can remain until Re-index is clicked. This can explain a continuing failure display after an underlying transient problem clears, but not the original initialization failure.
- A separate local bundle seal issue was observed: `LayaRuntime/__pycache__/worker.cpython-312.pyc` was added inside the installed app. It is unrelated to BGE initialization in the observed code path and should not be presented as the cause of these user reports.

Priority remains GPU/OS compatibility and resource allocation, followed by post-install model readability/integrity, with persisted historical errors as an explanation for apparent persistence. PDF content, cloud credentials/network and ordinary incomplete downloads do not fit the observed initialization error path. User-machine stage diagnostics are still required to establish root cause.

## Download self-check and diagnostic UI

Download completion now runs pinned SHA-256 verification and an actual local embedding of a built-in bilingual sentence. Only a finite, normalized 1024-dimensional result earns the Services card's green ready status. Paraformer uses a synthetic silent audio request; no microphone or document data is used. Reports are session-scoped: existing files without a current result show Downloaded / not checked, not verified readiness.

Services provides Run self-check and Copy diagnostics, and Knowledge links directly to the knowledge service. File, runtime, memory, initialization and inference failures have different recovery guidance. Successful checks explicitly explain that old failed document records require Re-index. Onboarding also reflects self-check status. Reports contain only app/OS/hardware/process architecture/physical-memory information, timestamp, model kind, checksum verdict and fixed failure code, never raw runtime logs, document text, paths or credentials. Cancel preserves installed files and never marks a check successful.

Validation on 2026-10-17:

- `scripts/test-model-health.sh <verified-bge-directory> <worker>` uses an isolated temporary install: verified install → actual inference → ready; diagnostic privacy and private-pasteboard roundtrip; simulated context allocation and missing-runtime failures; same-size corruption → explicit re-download advice → repaired install → ready; cancellation preserves files and never marks ready.
- 74 core checks passed. The final 20 onboarding XCTest cases passed with zero failures after the onboarding status presentation adjustment; the universal Release app/test build passed.
- An isolated native UI host built from the actual LocalModelCard source verified visible damaged-file failure, the Copy diagnostics → Copied button response, and an actual approximately 635 MB ModelScope download via the real installer followed automatically by a passing real inference check. Production model files and documents were not changed. UI feedback found and prompted fixes to download-status precedence and reset of the copied indicator on a new download.
- The UI host used the real rebuilt native worker. The app's bundled worker was also refreshed from the dual-architecture build with bundle-relative runtime linking.
- Tests were on Apple Silicon. Physical Intel hardware, older macOS versions, and real Paraformer self-check execution were not covered in this run. No release was published or installed over the user's production app.
