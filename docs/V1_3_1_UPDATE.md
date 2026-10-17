# 1.3.1 — conversation refresh, spoken answers, and persistent keys

## Changes

- Header refresh discards current transcript, partial captions, draft, answer, and previous-question context, restoring compact height. Active listening reconnects a clean session and continues capture. Knowledge/settings/saved history remain; the discarded current session is not saved by this historical implementation.
- Answers use short paragraphs suitable for speaking, followed by separate evidence/notes. Documents support facts while relevant general knowledge, analogy, reasoning, and suggestions remain allowed. Personal experience, metrics, and citations must not be invented.
- Recap focuses on discussion, decisions, and open issues. Follow-up generates one directly askable question with its own task prompt. Language follows the actual question/conversation.
- Language & Appearance uses a palette icon.
- Keys persist in app-managed Keychain items. Startup/service changes read silently; inaccessible saved keys show **Saved · Authorization required**, without automatic prompts or pretending no key exists.

## Legacy credentials

Legacy `LiveCopilot-OpenAI` and similar items remain. When permitted, the app copies them to `LiveCopilot-Credentials-v1`; otherwise users explicitly choose **Authorize saved key**. Enter system passwords only in macOS dialogs. Removing an app-managed key does not automatically reimport its legacy copy.

Keychain persistence and signing continuity are separate issues. This build was still ad-hoc signed and could require one explicit authorization after upgrade. Distribution needs stable Developer ID signing, not plaintext keys or weaker ACLs.

## Acceptance

- Sixty deterministic checks passed, including all three task-prompt contracts.
- Twenty-four native tests passed: refresh during generation/listening and subsequent repeated questions; silent/explicit migration; restart, replacement, deletion without resurrection; provider/endpoint isolation; real Keychain synthetic-item silent access and interaction-policy restoration.
- Tests read no real keys and called no paid models; Mock preferences were restored.
- Installed **1.3.1 / 20260916.031556** at `~/Applications/LiveCopilot.app`, arm64/x86_64, signature valid. Executable SHA-256: `c446d6dd74229ba9b1e0c88360d03e5c42d06b366c003546674c8f40993f99a9`.
- UI confirmed refresh/palette icons and existing DeepSeek key awaiting authorization, without a startup prompt. Existing Paraformer/local-vector/DeepSeek settings remained.
- After user authorization, legacy DeepSeek migration and a full restart succeeded silently. A real `deepseek-flash` response streamed, first text about 4.3 seconds; conceptual answers used connected prose/general knowledge without invented personal experience.
- GUI refresh cleared an answer and multiline draft, shrinking 480 × 768 to 480 × 240. Switching OpenAI Live showed saved/authorization-required without prompting; Paraformer was restored.
- Changed temporary signing caused the installer to archive the old app and reset this app's ScreenCapture record. First listening still required user authorization; the relevant system settings were opened.
