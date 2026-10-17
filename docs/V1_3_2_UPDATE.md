# LiveCopilot 1.3.2

2026-09-16

## Changes

- Overlay and Settings titles show the high-resolution app logo.
- About displays version/build and links to the author's GitHub, repository, bilingual guide, and Stealth attribution.
- Separate Chinese/English product pages have explicit language switching; the then-current README linked both language versions.
- Responsive desktop/mobile pages provide scripted answer examples, service comparison, privacy boundaries, and installation guidance. They record no audio, call no model API, and load no external fonts or tracking scripts.

## Cumulative public-release changes since 1.1.0

Includes Apple SpeechAnalyzer/SpeechTranscriber, Paraformer streaming, SenseVoiceSmall + VAD, and local BGE-M3 embeddings, plus soft-frost appearance, automatic height, edge hiding, refresh, spoken-answer prompts, independent services, cost guidance, and app-managed Keychain credentials.

Apple Speech requires macOS 26+ and supported devices/languages; the app supports macOS 14+ on Apple Silicon/Intel. Initial model downloads require internet. Local models have no API usage fee but consume local resources. Cloud analysis receives questions, relevant conversation, and retrieved passages.

## Validation

- Universal arm64/x86_64 Release passed.
- Twenty-four native tests, including 60 core checks, passed.
- Local Chinese/English navigation and example buttons worked at 390 px mobile and 1280 px desktop with no horizontal overflow/missing images.
- The same installed build visibly showed logos, About version, and three destination links; startup had no Keychain prompt.
- ASR, analysis protocols, and credential storage were unchanged; no repeated paid requests were made for this branding update.

## Installation and signing

The DMG contains the app, Applications shortcut, installation instructions, MIT license, and version/source information; checksums are separate. Quit before replacing and keep a consistent path.

This community build remained ad-hoc signed and unnotarized. Silent startup does not prompt, but a changed signature can require renewed permission when using keys/system audio. The development installer cleans old registrations and resets only this app's old ScreenCapture record; it cannot grant permission for the user.
