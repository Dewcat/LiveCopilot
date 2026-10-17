# LiveCopilot 1.3.0 — Apple Speech, window, and permission fixes

## Local delivery

Installed `~/Applications/LiveCopilot.app`, **1.3.0 / 20260915.153614** (UTC build). Executable SHA-256: `e4520b689b1de2546e3d3316983f0b4a3945fa8c70e8eb5011b019074c3c8131`. Universal arm64/x86_64 Release passed signature-integrity checks but remained ad-hoc signed, without Developer ID/notarization. No new GitHub Release.

Recognition/vector/DeepSeek choices and knowledge were preserved. Apple appeared under Services → Realtime service → Apple, with Mandarin/English selection on macOS 26 and supported hardware. Other local/OpenAI routes remained for macOS 14/15.

## Permissions and upgrades

`LiveCopilot.app.previous.20260914221600` was an old backup. Thirteen loose same-ID backups in Applications could be registered by LaunchServices/TCC as permission targets. Each ad-hoc build also changed code requirements, so old grants did not prove the new binary's identity.

The installer archived those 13 backups and replaced version, verified every file/symlink, then removed/unregistered loose bundles. Archives are under `~/Library/Application Support/LiveCopilot/Backups/Applications/`. Only canonical `~/Applications/LiveCopilot.app` remained registered; only its ScreenCapture grant was reset.

Future local upgrades use `StealthApp/scripts/install-local.py`. Same-signature dry-run confirmed no reset. Changed signing cleans old registrations and rebuilds this app's recording-permission record. **The script cannot grant macOS permission or change Keychain ACLs.** Stable Developer ID signing is needed for identity continuity.

General → System audio permission shows the running binary's current status and explicit request/settings actions. Missing permission produces guidance rather than prompting on every Start click. Other ScreenCaptureKit failures are no longer all labeled permission errors.

## Window clipping

Previously automatic height scrolled the whole card while size/edge animations overlapped, temporarily desynchronizing content/window geometry. The revised layout fixes header/input controls, scrolls only transcript/answer, and allocates space from actual height. Dynamic minimum height protects controls; size changes are atomic and edge reveal uses only opacity. Native/SwiftUI containers clip corners to actual bounds.

Native regression covered long content, automatic growth, manual resize, stop, hide/reveal, and hosting/content bounds. On 2026-09-16 installed screenshots confirmed intact header/input/footer/corners with long text. Manual resize regression passed; physical dragging was not repeatedly forced while the user worked.

## Apple versus FunASR measurements

Apple M4 Max / macOS 26.6.2, identical system-TTS fixtures, 16 kHz PCM in 250 ms chunks with 500 ms leading silence. Values are submitted audio duration at first result, with 250 ms granularity, **not strict end-to-end latency or accuracy benchmarks**. SenseVoice/Paraformer ran concurrently; Apple separately, so no fair hardware-speedup comparison is possible.

| Engine | First English preview | First Chinese preview | English final | Chinese final |
| --- | ---: | ---: | ---: | ---: |
| Apple SpeechTranscriber | 1.25 s | 1.25 s | 5.00 s | 8.75 s |
| Paraformer bilingual streaming INT8 | 1.00 s | 1.00 s | 4.50 s | 6.75 s |
| SenseVoiceSmall INT8 + VAD | No separate preview | No separate preview | 4.50 s | 6.75 s |

English speech ended at 3.572 s, Chinese at 5.868 s. Apple finalization lagged by about 1.4/2.9 s; SenseVoice/Paraformer about 0.9 s. Automatic suggestions consumed final text, so earlier captions did not imply earlier analysis.

- English reference: `Why did we choose method B, and what is its latency?` Apple/SenseVoice recognized it; Paraformer wrote “lency.”
- Chinese fixture asked why method B was chosen and its latency in milliseconds. SenseVoice retained method B; Apple/Paraformer substituted a Chinese homophone, while retaining latency/milliseconds. These are English descriptions of the original Chinese fixture.
- Apple produced 14 English/23 Chinese distinct previews; Paraformer 6/10. Revisable previews were not prematurely written to history/question context.
- None charges an ASR API fee. Apple manages shared assets and selects Mandarin/English explicitly; SenseVoice detects multiple languages with sentence output; Paraformer streams bilingual text. None supplies room-speaker separation or built-in language-model question understanding.
- Apple inference is system-managed; FunASR uses a helper process. No comparable peak-memory, energy, long-meeting, mixed-speech, accent, or noise study was run; no overall accuracy/resource superiority is claimed.

Apple + SpeechDetector used the then-existing local question rules/cooldown. Them/Room questions delegated once; You did not. Stop drained final results and preserved trailing words; silence produced no transcript. Repeated tests after asset installation required no download or real cloud calls. Offline behavior relied on Apple's API contract; the Mac was not physically disconnected for this test.

## Settings guidance and historical prices

UI explains local/cloud, streaming/sentence output, language limits, analysis credentials/thinking, embedding/reindex costs, modes/scenarios, and evidence count. Price cards identify USD, review date **2026-09-15**, and official sources. Unknown/custom models do not inherit unrelated prices.

| Service | Recorded official reference price on that date |
| --- | --- |
| GPT-Live-1 | $0.05/minute/stream, billed by second; system audio + microphone about $0.10/minute, connected silence included; backend models/tools extra |
| GPT-5.6 Sol | Per million tokens: input $4, cached input $0.40, output $20; then-advertised discount through at least 2026-11-21 |
| DeepSeek Flash | Per million tokens, off-peak/peak: input miss $0.15/$0.30, hit $0.003/$0.006, output $0.60/$1.20 |
| DeepSeek V4 Pro | Per million tokens, off-peak/peak: input miss $0.66/$1.32, hit $0.022/$0.044, output $1.98/$3.96 |
| text-embedding-3-small / large | $0.02 / $0.13 per million input tokens; indexing, reindexing, and queries count |
| Apple / FunASR / BGE-M3 | No API usage fee; local storage/memory/compute |

Recorded DeepSeek peak hours were weekdays 09–12 and 14–18 Beijing time. The fetched page still listed V4 Pro, so a cached retirement claim was not used. Prices depend on subsequent provider changes, account discounts, tax, and actual usage; this is not a current quote.

Sources: [Apple](https://developer.apple.com/videos/play/wwdc2025/277/), [GPT-Live-1](https://developers.openai.com/api/docs/models/gpt-live-1), [GPT-5.6 Sol](https://developers.openai.com/api/docs/models/gpt-5.6-sol), [OpenAI pricing](https://developers.openai.com/api/docs/pricing), [DeepSeek pricing](https://api-docs.deepseek.com/quick_start/pricing/).

## Acceptance and follow-up

- Fifty-nine deterministic checks and 19 native tests passed; final run 2026-09-15 23:55 local.
- Real Apple Chinese/English previews, stable text, triggers, no self-trigger, silence, and stop drain passed.
- SenseVoice/Paraformer transcription/trigger/stop regression passed, with accuracy limits above.
- Installer initially passed two tests; September 16 added a third for unregistering only same-production-ID development copies while excluding canonical/independent Debug apps.
- Universal build/signature/installed-byte checks passed. Models, knowledge, and API keys remained unchanged; no real analysis fees.
- Screen lock delayed September 15 UI acceptance; authorization/UI checks completed September 16 below.

## 2026-09-16 permission root cause and installed acceptance

Despite the user's recording grant, TCC logged `Failed to match existing code requirement ... kTCCServiceScreenCapture`. Comparing that requirement with `codesign -d -r-` showed the grant matched a **Debug test bundle**, not the installation: post-install native tests had registered a same-ID Debug app. This was a validation/install workflow bug, not an unenabled user switch.

- Debug now uses `com.livecopilot.development`, Release `com.livecopilot.app`. Built Debug plist confirmed separation; all 19 native tests passed again.
- Installer unregisters known same-production-ID build/dist/staging copies before registering the canonical app, without deleting artifacts or touching unrelated/Debug identities. Three installer tests passed.
- Reapplied registration cleanup/single-app ScreenCapture reset to unchanged **1.3.0 / 20260915.153614**. Executable hash/signature and API keys were unchanged; no rebuild/resign.
- Installed system capture then worked. Roughly five seconds of synthetic Chinese audio from a local browser appeared as Them through Apple Mandarin; microphone speech appeared as You. Stop/restart caused no renewed recording prompt.
- Screenshots confirmed empty Settings, ready Apple, DeepSeek price/credential status, and long transcript/streamed answer with intact controls/corners. Manual resize remained covered by native tests rather than interrupting user activity.
- DeepSeek was configured and a user-initiated answer with citations was visible. The assistant played only synthetic audio, made no additional paid request, and restored temporarily disabled automatic suggestions. No actual user transcript/answer/document content was recorded here.

Acceptance left Apple Mandarin and the user's active listening intact, with pinned automatic-height overlay. Pin can restore edge hiding. The test page and temporary HTTP server were closed. No permission blocker remained.
