# Model release readiness — 2026-10-17

The accepted response checkpoint was uploaded on 2026-10-17. Application publication and notarization are recorded separately in the release validation report.

## Accepted fine-tuned Laya checkpoint

The locally installed app and integration checkout use:

- Weight SHA-256: `e505137a5e1bfa8392618c7f62e1733ed995deb66c2883882c0677150129ed9a`.
- Receipt ID: `livecopilot-needs-response-e505137a5e1bfa83`.
- Runtime pin: `laya-multilingual-20260921-1`.
- Context budget: 1,024 tokens.
- Tracked acceptance receipt: `StealthApp/Resources/LayaRuntime/response-model.json`; downloaded weights live in application support, not the app bundle.

### Immutable distribution and build checks

- Repository: `careybk/livecopilot-model-assets`.
- Directory: `laya/response/v2.5.0`.
- Revision: `32a060912987d9823a1e3d1f4c573f21ca581a39`.
- Receipt SHA-256: `f88d0668265188a12630a3beed24ed142700699dd6284af63338cafc07436566`.
- Weight size: 643,835,426 bytes.
- Source manifest: `StealthApp/Resources/LayaRuntime/response-model-source.json`.

`build.sh` validates download metadata without fetching weights. Packaging rejects any bundled `ResponseModel/` directory and limits Laya resources to 2 MiB. The onboarding/Services installer downloads the nine accepted model files from this immutable ModelScope directory and verifies each SHA-256 before atomic installation.

The new installation ID is `livecopilot-laya-response-2.5.0-e505137a5e1bfa83`; the underlying runtime compatibility ID remains `laya-multilingual-20260921-1`. Existing old installations are detected as needing the new model. The worker checks the new installation ID, acceptance prompt hash, context budget and all model file hashes; it cannot silently use the old checkpoint. Previous version directories remain on disk during installation. The old upstream ModelScope revision remains available for old clients and was not overwritten.

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

The latest GitHub Release was verified as `v2.3.0` (published 2026-10-12). The integration source now declares `MARKETING_VERSION = 2.5.0`.

1. Select the next public version in `StealthApp/Version.xcconfig`; do not reuse 2.3.0 for a new public update.
2. Validate immutable download metadata in a clean checkout; ensure the app contains no Laya weights.
3. Validate model preparation, actual load/self-check, and the downloaded response model using the final signed candidate’s resources.
4. Complete app/DMG notarization and ticket validation, then publish matching release notes and checksums.
5. Mirror the identical finalized DMG, sign the Sparkle feed, and verify the real update flow. See [RELEASING.md](RELEASING.md).
