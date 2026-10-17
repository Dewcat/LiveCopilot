# History and model-health integration acceptance — 2026-10-17

## Delivered behavior

The installed-version source baseline (including the accepted V23 Laya runtime) now includes:

- Light native three-column history, search across transcript/questions/answers/citation excerpts, Today/Yesterday/Earlier groups, metadata header, chronological lazy timeline, per-session reading bookmarks, individual/full copy, Markdown/TXT export and confirmed deletion.
- Green room speech, blue nearby speech, separate manual/recognized questions and Markdown answers. Evidence/notes and knowledge citations are collapsible.
- Optional schema-v2 JSON fields preserve questions, separate answers, lifecycle timestamps, warnings/errors, source fragment IDs and citation excerpts (no embedding vectors). Legacy files decode without rewriting or inventing answers. Stable ASR revisions retain their original fragments while updating one final transcript line. Archival storage is not truncated by the 400-line live UI limit.
- Answer completion after voice stop updates that answer's archived session. Async title/answer results never recreate deleted sessions. Failed saves prevent clearing the current session.
- Voice-session end invokes the selected analysis provider once for a title, using at most 12 evenly sampled 300-character transcript/question excerpts, no knowledge excerpts. A 30-second deadline and invalid-title checks retain the local preview on failure. Old sessions are not retrospectively sent to the API. Manual-only sessions use their question preview.
- Local model download performs checksum plus real loading/inference, with manual self-check, privacy-conscious copyable diagnostics and stage-specific recovery instructions. Embedding contexts start smaller and fall back to CPU when GPU initialization fails.
- The three overlay settings rows now share typography, spacing and separators.

## Validation

- Universal Release build: arm64 + x86_64.
- Final selected regression: **89 tests, 85 passed, 4 conditional skips, zero failures**. Includes legacy byte preservation, new JSON roundtrip, chronological multiple answers, post-stop completion, search, both export formats, deletion/late callback protection, 1,200-line ASR revision archive, title success/invalid response/timeout, and a native 3,000-message scrolling test.
- Five real installed Laya integration cases passed alongside model-health, native and onboarding regressions. This is regression coverage, not a replacement model benchmark or a claim about every user's hardware.
- One additional native settings rendering test passed. General settings image inspected for consistent overlay rows.
- Real title request: unsigned XCTest could not read the saved key (`-25293`). A Developer ID-signed acceptance runner with the existing app identity made one synthetic request through the configured analysis provider and returned `缓存优化与下周加载测试计划`. No credential ACL change and no real conversation was sent by this acceptance runner.
- Isolated native UI exercised content/source search, no-results state, source disclosure, long-session scrolling and session switching, whole-session copy feedback, Markdown save panel, delete confirmation and cancellation. Actual exported file was read back and contained timestamps, roles, AI text and citations. Delete persistence itself was exercised in isolated tests.
- Installed BGE-M3 self-check reported ready after real load/inference; copying diagnostics showed the copied confirmation. Final UI also restored the long-session reading bookmark after switching away and back.
- Installed at `/Applications/LiveCopilot.app`, version **2.3.0**, build **20261017.035022**. Ten embedded binaries passed Developer ID, secure timestamp and hardened-runtime validation. Installation retained the designated requirement and did **not** reset screen-capture permissions. Previous app archived by the installer.
- All 10 pre-existing history/knowledge files matched pre-install SHA-256 values after installation. The three real legacy sessions opened in the redesigned installed UI with an explicit transcript-only notice.

## Preserved Laya artifacts

- worker.py: `62118cc5889f8209925bb71e48e83549198d43756a302dd1e911c08df5cb8db5`
- response-model.json: `f88d0668265188a12630a3beed24ed142700699dd6284af63338cafc07436566`
- model.safetensors: `e505137a5e1bfa8392618c7f62e1733ed995deb66c2883882c0677150129ed9a`

The reported users' hardware and logs remain unknown. The fixes improve diagnosis and resilience; they do not prove which failure affected those machines. Native execution was tested on this Apple Silicon Mac; Intel was built but not run on physical Intel hardware.

## Local evidence

- `/tmp/history-final-regression.log`, `/tmp/history-render.log`
- `/tmp/livecopilot-title-check/result.json` (synthetic title only)
- `/tmp/history-ui-export.md`
- `/tmp/history-signing-final.log`, `/tmp/history-install-dry-run.json`, `/tmp/history-install.log`
- `/tmp/livecopilot-pre-history-backup/data-sha256.json`
