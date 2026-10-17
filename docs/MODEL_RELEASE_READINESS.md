# Model release readiness — 2026-10-17

This is a preparation check, not a publication receipt. No model upload or public release was performed as part of this check.

## Accepted fine-tuned Laya checkpoint

The locally installed app and integration checkout use:

- Weight SHA-256: `e505137a5e1bfa8392618c7f62e1733ed995deb66c2883882c0677150129ed9a`.
- Receipt ID: `livecopilot-needs-response-e505137a5e1bfa83`.
- Runtime pin: `laya-multilingual-20260921-1`.
- Context budget: 1,024 tokens.
- Resource locations: `StealthApp/Resources/LayaRuntime/ResponseModel/` and `response-model.json`.

These resources are currently untracked local packaging inputs. `worker.py` validates the receipt, prompt hash, runtime pin, paths, and every file hash before using the bundled checkpoint. If both resources are absent it uses the downloaded upstream model; a partially present or incompatible checkpoint is an error. Therefore a successful clean build alone does **not** prove that the accepted checkpoint is included.

The public ModelScope API reported the account repository's `laya/model/model.safetensors` as 643,835,426 bytes with SHA-256 `7fc5834af4d8fdfb268d272a9d1a66e5819a0daac98241651c4c888cc43adff1`. This differs from the accepted checkpoint. The existing release download remains pinned to revision `a5ba0b9be08e7d8f7438e3762791ac5b62c1e253`.

### Required release decision

For the current bundled-checkpoint design, a ModelScope upload is not required for end users to receive the checkpoint, **provided** release packaging explicitly stages and verifies the accepted files before signing. A durable, pinned model artifact is still needed for reproducible builds. Uploading the fine-tuned model as a separately versioned ModelScope artifact is recommended; retain upstream LICENSE/NOTICE, add the fine-tuning notice, include tokenizer/configuration files and receipt, and verify remote hashes. Do not overwrite the old pinned model.

If the goal is to download the fine-tuned model separately rather than bundle it, uploading alone is insufficient: update runtime download pins, installation/receipt checks, and the worker's selection path, then test a fresh installation and an upgrade. Preserve the existing base/runtime path until that migration is verified.

## Zipformer

The four primary runtime files are available from the upstream [ModelScope repository](https://modelscope.cn/models/pkufool/sherpa-onnx-streaming-zipformer-bilingual-zh-en-2023-02-20/files), pinned to `fe4123ca09cd7efaef00fe0ed88219211bc5b77e`:

| File | Bytes | SHA-256 |
| --- | ---: | --- |
| encoder-epoch-99-avg-1.int8.onnx | 181895032 | `8fa764187a261844f859d7143ebaa563af5d10adfece4c18a8f414c88cba2a9b` |
| decoder-epoch-99-avg-1.onnx | 13876452 | `2e3b5ec371f8899ee6acd829fd753ba45772df57a91bdf37cde3136354e7db7d` |
| joiner-epoch-99-avg-1.int8.onnx | 3228404 | `1ed689c5ed19dbaa725d9d191bb4822b5f4855a39e1ffd28cbc1f340d25b2ee0` |
| tokens.txt | 56317 | `a8e0e4ec53810e433789b54a5c0134a7eaa2ffca595a6334d54c00da858841d3` |

Remote API sizes/hashes matched `LocalModels.swift`. Anonymous HEAD checks on all four pinned URLs returned HTTP 200 with ETags equal to those SHA-256 values. The app tries this ModelScope route before Hugging Face. The 12,564-byte `bpe.vocab` is bundled and hash-verified, with Hugging Face as its download fallback. Silero VAD uses the existing shared distribution asset.

Zipformer is not mirrored in `careybk/livecopilot-model-assets` at the checked revision or current repository listing. Mirroring it there is optional for the current implementation; it is not a prerequisite for ModelScope downloads. Remote metadata verification is not a new full download or a guarantee of performance on every user's network.

## Packaging checklist

The latest GitHub Release was verified as `v2.3.0` (published 2026-10-12). The integration source still declares `MARKETING_VERSION = 2.3.0`; a new public update needs a new version.

1. Select the next public version in `StealthApp/Version.xcconfig`; do not reuse 2.3.0 for a new public update.
2. Make the accepted response-model artifact reproducibly available to the clean packaging checkout and verify its receipt/hashes.
3. Validate model preparation, actual load/self-check, and the bundled response model from the final signed candidate.
4. Complete app/DMG notarization and ticket validation, then publish matching release notes and checksums.
5. Mirror the identical finalized DMG, sign the Sparkle feed, and verify the real update flow. See [RELEASING.md](RELEASING.md).
