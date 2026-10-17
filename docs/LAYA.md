# Local Laya automatic triggering

Laya sits between transcription and answer generation: ASR text → local response-intent classification → speech completion/pause checks → the selected analysis service. It neither transcribes audio nor writes answers.

## Current development implementation

The accepted response checkpoint uses a 1,024-token context budget and a default threshold of 0.80. Semantic decisions belong to Laya; deterministic pause handling, deduplication, cancellation, and scheduling remain outside the classifier. The locally installed app carries the fine-tuned checkpoint in `LayaRuntime/ResponseModel`, verified by `response-model.json`. See [release readiness](MODEL_RELEASE_READINESS.md) before packaging from a clean checkout.

For local bilingual speech, Zipformer is the recommended default; Paraformer remains an option. Apple Speech is available on supported systems. Laya requires Apple Silicon and macOS 14+, plus internet for initial runtime preparation. It then classifies locally without another API key. Answer generation still uses the configured analysis service and can incur its API fees. GPT-Live-1 uses its own client-delegation decisions. Manual generation remains available when Laya is missing or fails; the app does not silently switch to a paid classifier.

## Historical development record: September 2026

The following records the earlier development implementation and its validation, not the current fine-tuned classifier's acceptance results.

The original setup was Settings → Services → Realtime service, using Paraformer or Apple and **Download and prepare**. Old speech-service/rule-trigger preferences were removed and ignored on upgrade. Local recognition providers emitted transcription and speech activity without independently delegating questions, avoiding duplicate generation.

The threshold ranged from 0.50 to 0.99, defaulting to 0.80. Lower values could increase both triggers and false positives; higher values could miss questions. Scores were respond-class probabilities, not calibrated meeting accuracy.

### Historical behavior and boundaries

- Evaluated the latest transcript at most roughly every 350 ms, with one inference request at a time.
- Partial text supported early classification; generation waited for final text and at least roughly 500 ms of silence across known speakers. Paraformer's Silero VAD additionally needed roughly 650 ms of silence to close a segment.
- The earlier implementation supplemented explicit questions within 0.10 below threshold with local question rules. It could add a question mark to classifier input when ASR omitted punctuation, while preserving displayed and analysis text. This is historical behavior, not the current semantic-classifier contract.
- When unpunctuated Chinese ASR merged a preceding question with a follow-up, the earlier implementation scored both the full segment and preceding question and used the higher score. Analysis still used the full original text; triggering still required the model threshold or the then-existing near-threshold rule.
- Remote mode excluded the local speaker. Local speech, manual questions, refresh, stop, and service changes discarded pending decisions.
- Questions were deduplicated; decisions arriving during generation were queued and rechecked afterward. Stale questions did not trigger late. Existing 7- or 12-second scenario cooldowns applied.
- In-person microphone audio did not reliably distinguish speakers. Laya provided no voice identification and could not repair ASR errors or source labels.
- The early classifier evaluated the current utterance only. Its 1,024-token budget included instructions/options and retained the tail of oversized input using actual tokenizer length. Conversation context was still provided to the downstream analysis model. This restriction was superseded by the later contextual response model.
- Classification requests traveled through local anonymous pipes and were not written to Laya logs. Session persistence remained a separate application feature.

### Installation and sources

Development resources use `~/Library/Application Support/LiveCopilot/Development/Laya`; production has a separate data directory. System Python is not modified.

Pins are in `StealthApp/Resources/LayaRuntime/pins.json`. Historical OSS staging and license/hash records are in [OSS_MODEL_DISTRIBUTION.md](OSS_MODEL_DISTRIBUTION.md); later public routing is documented in [MODELSCOPE_MODEL_DISTRIBUTION.md](MODELSCOPE_MODEL_DISTRIBUTION.md).

- [laya-mlx](https://github.com/mizorewww/laya-mlx), source commit `fc1df62828a3fedf4d8229fdac1cbd85f1cdf337`, Apache-2.0.
- [Laya multilingual MLX](https://huggingface.co/aac6fef/laya-multilingual-mlx), upstream revision `ba40c87fcb357f1643d04d71323af9cdc3b9e591`, retaining LICENSE/NOTICE.
- Isolated CPython 3.12.14, MLX 0.32.2, and all wheels have pinned URLs and SHA-256. The selected MLX wheel targets macOS 14 Apple Silicon.

Installation verifies an isolated directory before switching. Failure/cancellation preserves the preceding complete installation. Reload reads local files only. The original initial download included about 644 MB of weights, about 34 MB of tokenizer data, Python, and dependencies; caches were retained for retries.

### Validation tools

- `bash StealthApp/scripts/test-laya-trigger.sh`: model-free trigger-state checks.
- Python 3.12 with `StealthApp/Tests/test_laya_worker.py`: protocol and file verification.
- Native Debug XCTest: regression, coordinator events, runtime crashes/timeouts/cancellation, with Mock analysis.
- `StealthApp/Tests/LayaRealSmoke.swift`: installed-model probe with synthetic Chinese/English text and long context, without analysis API calls.

The early synthetic examples still produced false positives for reported questions and unfinished speech. Small synthetic sets cannot establish real-meeting false-trigger rates or API cost.

### Local acceptance (2026-09-21)

- All 43 native tests passed, including real Laya + Mock analysis for Chinese/English questions and statements; 28 state-machine checks and four Python protocol checks passed.
- Cold load took about 4.8 seconds; reload about 0.8 seconds. Short examples took roughly 6–10 ms per decision; a truncated long input about 41 ms. These are not continuous-audio latency guarantees.
- `StealthApp/Tests/laya_intent_samples.json` can be evaluated with installed Python and `evaluate_laya_intent.py --installation <Laya/current>`. The set influenced prompt selection, so it was not independent accuracy evaluation. Ten of twelve examples passed; one English reported question and one unfinished utterance remained false positives and were retained.
- Installed `LiveCopilot Dev 1.4.2 (20260921.001)` showed local Laya ready and threshold 0.80. Its Developer ID requirement matched the preceding Dev app; the production executable hash was unchanged.
- No human recording or paid analysis API integration was run. No publication, push, or notarization occurred.

### Settings and indexing (20260921.002)

Laya download/load/trigger/threshold controls moved together under Services → Realtime service. Models could be prepared before selecting the trigger. Knowledge indexing used a real batch-progress bar display; successful commit showed indexed, while failed rebuilding retained the previous index.

### Index-progress correction (20260921.003)

Local embeddings reported each completed chunk through the resident model and per-chunk IPC, without extra model loads. Dark blue showed completed work, light blue remaining work; moving highlights were removed. Cold loading and an in-flight chunk did not fabricate progress; 100% required successful index persistence. Cloud progress remained batch-based. All 45 native tests passed, including documents with fewer than 24 chunks and preservation of the previous index after failure.
