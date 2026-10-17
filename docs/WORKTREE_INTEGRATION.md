# Onboarding and model-configuration integration — 2026-09-29

## Source of the differences

The model-distribution task's `de53` worktree and onboarding worktree `1cee` shared committed baseline `ada250f`. Default-model changes remained in eight uncommitted files in `de53`, so earlier `1cee` packages omitted them. Main-worktree commit `5aa6234` was already in the common baseline; there was no separate unmerged commit branch.

Imported those eight file diffs into `codex/onboarding-first-run`, preserving onboarding. Source worktree/uncommitted files were untouched; no push/publication.

| Item | Outcome |
| --- | --- |
| Preferred distribution source, fallback, hashes, progress | Already in common baseline; retained. |
| OpenAI language preference and no-language-hint request | Already in baseline; added missing onboarding access using the same four settings choices. |
| Official OpenAI logo | Existing asset reused in sample-question area. |
| Flash defaults / GLM thinking constraints | Imported uncommitted changes; added GLM Flash compatibility at the request layer. |
| Service guidance, pricing examples, core checks | Imported; OpenAI changed to GPT-6 Sol as requested at the time. |

## Defaults at this checkpoint

| Service | New-configuration model |
| --- | --- |
| OpenAI | `gpt-6-sol`, low reasoning |
| DeepSeek | `deepseek-flash`, low reasoning |
| Qwen | `qwen3.8-flash`, thinking off |
| GLM | `glm-5.3-flash`, model-default thinking |
| Kimi | `kimi-k2.6`, thinking off |

Normal upgrades retain saved models/endpoints/credentials. GLM Flash hides thinking-off and suppresses invalid legacy off parameters in requests.

OpenAI offers Chinese-first, English-first, mixed Chinese/English, and unrestricted recognition (no language guidance). Paraformer recognizes mixed Chinese/English; Apple requires explicit Mandarin/English selection, without claiming automatic switching.

## UI changes

- Onboarding/Settings booleans use right-aligned pill switches; overlay retains its existing switch style.
- Jev Mode reuses the branded Settings font and remains recommended.
- Try-a-question shows provider logo/name/model; custom endpoints use a generic icon. See [logo provenance](PROVIDER_LOGOS.md).
- Added fourth overlay tip for screenshot/sharing exclusion, showing current state and a Settings link without changing the privacy choice. Actual behavior depends on macOS/capture software.
- Retained 1040 × 700 single-screen layout, immersive title bar, pink/blue background, and transitions.

## Validation

- Seventy-three core checks passed without real API requests.
- Seventy-two native tests: one opt-in real-Laya test skipped, zero failures; 19 onboarding tests.
- Isolated preview checked compact no-scroll layout, switches/branding, four language options, DeepSeek logo/model, four overlay tips, and final-step General entry.
- Release built; five universal Mach-O components passed Developer ID/timestamp/hardened-runtime verification.
- Replaced local production 2.0.0 (`20260929.071457`); actual Chinese model-page switches/branding and sample-page DeepSeek/`deepseek-flash` were visible without vertical scrolling or obstruction.
- Per user request, local old factory defaults were updated; other preferences, credentials, and permissions remained. Preferences and old app were backed up. Model/Laya/knowledge file sizes and modification times were unchanged.
- New provider models were not evaluated with real audio or paid requests.

Logs: ignored `StealthApp/build/onboarding-merged-*.log`; source diff backup: `StealthApp/build/oss-worktree-changes.patch`.
