# V1.1 — language, appearance, and analysis services

After trying V1, the user requested Chinese UI, an optional white background, independent service configuration, and replaceable analysis providers. This update follows that scope; the original V1 requirements remain unchanged.

## Usage

1. Settings → General offers System, English, and Simplified Chinese, applied immediately. Documents, transcripts, and answers are not dictionary-translated; answers follow the question's language.
2. Choose translucent glass or solid white. White uses dark text/light native controls; capture exclusion is independent.
3. Services → Realtime service manages the OpenAI key, Live model, and embedding model. Configured credentials show status and a fixed mask. **Replace key** opens an empty secure field; the actual key is never filled back in.
4. Analysis service offers shared realtime OpenAI, independent OpenAI, DeepSeek, or compatible Chat Completions. The default reuses existing OpenAI configuration without changing models/knowledge.
5. DeepSeek has an independent key and editable model, initially `deepseek-v4-pro` with low reasoning. Compatible services require an HTTPS base URL, Chat Completions path, and model. Save the connection before configuring credentials; a new endpoint needs its own key.

At this release, realtime audio and embeddings still used OpenAI. Analysis receives questions, relevant conversation, and locally retrieved evidence. Independent analysis keys neither replace realtime keys nor send OpenAI credentials to another service. Changing only the analysis model needs no index rebuild.

## Capture exclusion

The overlay, Settings, and History retained `NSWindow.sharingType = .none`, requesting capture exclusion through a window property rather than an extra layer. Behavior varied across macOS/capture applications; shared previews still needed checking.

Only combined `--mock --ui-preview` allowed development capture, using isolated mock data/settings without production credentials. Normal launch or `--ui-preview` alone kept production policy.

## Implementation and validation

- Field-by-field migration preserved existing models, modes, scenarios, automatic suggestions, and retrieval settings; only new fields received defaults.
- All 43 deterministic checks passed, covering migration, language/source labels, HTTPS validation, endpoint-scoped keys, four analysis routes, credential isolation, and abnormal streams.
- All 12 native tests passed, including real URLSession/URLProtocol Chat Completions byte streams, underlying stream closure on cancellation, and independent-key deletion isolation. No real models or user keys were used.
- DeepSeek/compatible streaming displays only `delta.content`, not `reasoning_content`. Truncation, empty output, errors, and cancellation are handled without exposing raw server error bodies.
- Isolated Mock UI checks covered immediate language switching, Chinese windows/overlay, white background, separate service sections, DeepSeek, saved endpoint/model, and complete typed questions with streamed sources while listening was off. Production capture exclusion stayed enabled. Replacing native GroupBox with explicit SwiftUI groups resolved an automation-tool crash.
- Native Release compiled. DeepSeek/custom endpoints still needed validation with users' own credentials.

## Official references checked on 2026-09-14

- [OpenAI Responses streaming](https://developers.openai.com/api/docs/guides/streaming-responses): retained the accepted adapter.
- [DeepSeek Chat Completions](https://api-docs.deepseek.com/api/create-chat-completion/): streaming `choices[].delta.content`, `finish_reason`, and `[DONE]`; DeepSeek reasoning fields go only to DeepSeek.
- [DeepSeek model/pricing reference](https://api-docs.deepseek.com/quick_start/pricing/): historical default `deepseek-v4-pro`, editable by the user.

## Local checks

Switch languages across Settings, overlay, menus, and History; verify persistence after restart. Check white/glass over a dark wallpaper. Realtime credentials should show configured after loading; replacement begins empty and cancellation preserves the key. Shared OpenAI needs no duplicate entry; DeepSeek/new endpoints need their own credentials. With listening off, submit a sourced question and verify streaming after changing analysis providers.

## Local installation record

- Version **1.1.0 / 20260914.093932**, at `~/Applications/LiveCopilot.app`; installer backed up the previous version.
- Startup preserved remote-meeting/interview/model settings. System language displayed Chinese; solid white was selected.
- Strict signature verification passed. Executable SHA-256: `be701433349e126040b4f88e61eb8b2f0666dc7780223f4b8b4e34c9bdc4de01`.
- Final tests completed 2026-09-14 09:38:46: 12 native tests, zero failures, including 43 core checks.
- Changed ad-hoc signing prompted one Keychain authorization; existing credentials loaded at 09:41:09. UI showed configured/masked credentials. Replacement opened an empty secure field with Save disabled; cancellation preserved the configured state. The original Keychain item was unchanged.
- No additional real model requests. Acceptance covered encoding, routing, parsing, errors/cancellation, and UI, not live provider connectivity.
