# LiveCopilot 2.1.0

## Changes

- Six-step first-run guide covers language, scenario, local preparation, permissions, answer service, and readiness/experience. Skippable and reopenable; previews neither record nor call APIs.
- Pink/blue gradients, page transitions, larger progress indicator, single-window content, and small right-aligned switches.
- Settings places Open guide and Overlay tips together. **Download and continue** explicitly starts preparation; applying recommendations does not. Later steps show progress and allow remaining downloads. Downloading, queued, and failed states are distinct.
- System-audio permission is visible in all modes, marking required remote access versus skippable access. Completion reveals the overlay until the first pointer entry.
- General can hide/show the menu-bar icon. Overlay sharing-exclusion naming/explanation is consistent across Settings/tips.
- DMG uses pink/blue drag-to-install styling: Applications left, LiveCopilot right, large icons/left arrow, smaller instructions below.
- Jev Mode uses consistent branding and recommendation; overlay operation/capture tips explain OS/application-dependent exclusion.
- OpenAI recognition offers Mandarin, English, mixed, or unrestricted automatic recognition. Apple uses explicit supported language; Paraformer supports mixed speech.
- New-user analysis presets: OpenAI `gpt-6-sol`, DeepSeek `deepseek-flash`, Qwen `qwen3.8-flash`, GLM `glm-5.3-flash`, Kimi `kimi-k2.6`. Saved custom settings remain.
- Knowledge indexing has continuous overall progress, percentage, and completed/batch counts. Each document contributes equally, advancing by completed chunks. Rows show activity; completion requires persistence and failures never show 100%.
- Sparkle checks from About, app menu, or menu-bar menu. Automatic checks initially default off. Download/install require confirmation; current sessions are ended/saved before installation.
- Ed25519 verifies feed/package; production uses HTTPS. Packages retain Developer ID signing and Apple notarization.

## Upgrade

Versions 2.0 and earlier need one manual 2.1 DMG installation from GitHub Releases. Quit/replace the Applications app; later updates can be checked in-app. Models, documents, history, settings, and keys are retained.

Requires macOS 14+ on Apple Silicon/Intel. Apple Speech needs macOS 26+; Laya needs Apple Silicon. Service data/cost boundaries are unchanged.

## Release validation

- Version 2.1.0 / 20260929.144323, universal arm64/x86_64.
- Previous candidate passed 73 deterministic checks; core code was unchanged. This run: 78 XCTest cases, one opt-in real-Laya test skipped, zero failures.
- Isolated native SwiftUI rendering covered both languages, model choice, and final readiness at minimum settings width. No real model downloads/API calls or installed-app replacement.
- Added batch-progress coverage for intermediate reports, equal document weighting, excluding existing documents, failure, single retry, and full reindex; continuous bar rendered natively.
- App and all ten Mach-O components passed Developer ID, hardened runtime, secure timestamp, and architecture checks.
- Earlier signed candidates loaded/pinged Paraformer/BGE-M3. r4 indexed two synthetic documents with existing BGE-M3: 0%, 23%, 47%, 50%, 65%, 81%, 97%, 100%. Temporary knowledge only; no user-data changes/API calls. Runtime unchanged, so not retested in this final run.
- App notarization `d0f4a2af-6f98-44d7-8c15-b575216bd017`: Accepted, no issues.
- DMG notarization `c4d436cf-cd1c-46a5-9dea-b094eead1256`: Accepted, no issues.
- Both tickets stapled; Gatekeeper, image integrity, and checksums passed. Mounted/copied apps passed strict signature verification; packaging adds no FinderInfo to the app.
- Earlier Finder checks showed Applications left/app right, bottom three icons 56 pt and upper icons 128 pt, all without scrolling. Disk layout unchanged.
- Earlier isolated UI checked in-person system-audio visibility, automatic overlay reveal, menu-bar toggle, and consistent Settings/tip copy.
- DMG SHA-256: `748a0414f159bb9f4898a2d0b88bdaec7ff704d5ea875293fd6198ac88bddb4d`.
- Independent QA previously discovered build 101 from 100, downloaded, verified, installed, and relaunched. Executable matched the candidate and a subsequent check showed current.
- A tampered test feed was rejected with a signature error. Final production feed/DMG Ed25519 verification passed.
- About update entry and default-off toggle were exercised earlier; updater unchanged in this run.
- `site/updates/appcast.xml` contains the production feed; site building preserves signed bytes.

See [GitHub Release](https://github.com/carey-bk/LiveCopilot/releases/tag/v2.1.0) for package, checksums, and build information. Website/in-app update use identical signed bytes. Publication does not automatically replace the maintainer's app or clear user data.
