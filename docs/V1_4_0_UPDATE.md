# LiveCopilot 1.4.0

## Changes

- Retires sentence-only SenseVoiceSmall in favor of Apple, Paraformer, and GPT-Live-1 streaming options. Legacy selections migrate to Paraformer without resetting preferences or deleting weights.
- Adds separate 11–28 pt transcript/answer font controls, with live previews and persisted settings. Large text reflows and remains scrollable.
- Adds Qwen, GLM, and Kimi analysis presets, configurable models/endpoints/thinking, vendor-specific request fields, and provider/endpoint-scoped credentials. Uses the existing streaming answer and RAG workflow.
- Replaces the bilingual site's collapsed technical disclosure with a visible service comparison. Local ASR also triggers automatic suggestions via text rules; GPT-Live-1 supplies semantic delegation decisions. Speech, embeddings, and analysis remain independent choices.

Historical preset models were `qwen-plus`, `glm-5.2`, and `kimi-k2.6`. Save a connection before adding its key in Services → Analysis. Provider account/region determines availability; Qwen regional keys are not interchangeable and GLM Coding Plan is not general API credit.

## Validation

- Universal arm64 + x86_64 Release build succeeded.
- 67 deterministic checks passed; 24 native XCTest cases passed with zero failures. Includes legacy ASR migration, independent font persistence/bounds, provider routing, credential isolation, vendor thinking parameters, SSE output/error handling and existing application regression checks.
- Real local runtime: Chinese/English Paraformer synthetic-audio fixtures produced 10/6 changing previews before audio ended, delegated once for the other speaker/room, and did not delegate for “You”. Silence suppression, final-tail flush and normal-endpoint equivalence passed. English “latency” remained imperfect; this is a functional test, not an accuracy benchmark.
- Real BGE-M3 cross-language retrieval passed, with persisted index reopening. No paid API request or physical microphone/system-audio capture was made for this update.
- Mock GUI checked: exactly three listening options; Qwen/GLM/Kimi defaults; independent font controls; maximum-size transcript and answer text with intact top/bottom controls and scrolling.
- Chinese/English site checked at desktop, 390px and 320px widths with no horizontal overflow. Service content is a normal section, installation remains a disclosure, language navigation and demo actions work.
- **Boundary:** real Qwen, GLM, and Kimi credentials were not supplied or used. Protocol/Mock validation does not verify account balance, model entitlement, real latency, or answer quality. Apple Speech and paid OpenAI/DeepSeek behavior were not re-exercised with live audio/API calls in this update.

This remains an ad-hoc signed, unnotarized community build. macOS may require permissions for a changed signature; no authorization or credential ACL bypass is introduced.
