# LiveCopilot 1.4.1 — Developer ID & Apple notarization

> Release gate: both the application and final DMG must be Accepted by Apple, with validated stapled tickets and successful Gatekeeper assessments before publication. Submission receipts accompany the GitHub Release.

## Changes

- Developer ID signing for the app and all bundled inference binaries, with secure timestamps and hardened runtime enabled for both Apple Silicon and Intel.
- Separate Apple notarization and stapled tickets for the application and final disk image.
- Retains 1.4.0 functionality and user data. The first migration from ad-hoc signing can require renewed recording or Keychain permission; subsequent builds preserve the developer team and bundle identity without bypassing macOS policy.
- Release tooling verifies every binary, app/DMG tickets and Gatekeeper, then recalculates checksums after stapling. The former self-signed-root setup is now read-only.

## Validation

- Universal Release build passed; 24 native XCTest cases passed, with zero failures.
- All 5 bundled Mach-O binaries / 10 architecture slices passed Developer ID, team consistency, timestamp and hardened-runtime verification. No debug, unsigned-memory or library-validation exception was added.
- Real signed local runtime passed Paraformer Chinese/English streaming, question triggers, silence/flush checks and BGE-M3 retrieval/index persistence. No paid API or physical microphone/system-audio capture was used.
- Signing continuity check passed: changing the build and re-signing with this Developer ID preserved the Apple-anchored designated requirement used by the local installer.
- Application notarization: Accepted, submission `f751b64b-f701-4f4c-8b9c-ef7da17ecf54`. The final DMG submission and distribution verification are recorded in `NotarizationInfo.txt` alongside the published download and checksums.
