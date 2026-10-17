# First-run onboarding — phase 1

Historical status: local implementation and preview acceptance completed, not yet published. Based on `ada250f` (2.0.0).

## User flow

A separate native window has six steps: language → features/use mode → local capabilities → answer service → permissions → first experience.

| Step | Behavior |
| --- | --- |
| Language | System, Simplified Chinese, or English; changes apply immediately. |
| Features and mode | Examples explain transcription, Jev Mode, and suggestions; choose remote meeting, in-person, or typing first. |
| Local capabilities | Select Paraformer, Apple, or cloud recognition, optionally prepare retrieval/Jev Mode, detect existing resources, and show additional download size and available space. These were the options at this historical checkpoint. |
| Answer service | Reuse services and Keychain configuration; advanced connection fields, explicit testing, cancellation, and errors. Tests send only a synthetic question, without history/documents. |
| Permissions | Remote mode requests system audio/microphone as needed; in-person needs microphone only; typing needs neither. Authorization does not start recording. |
| First experience | Separate model, permission, and service status; sample questions, demos, and overlay entry. Installation, key storage, and successful validation are distinct states. |

Fresh installations open the guide automatically; existing settings/data do not force it. Closing preserves progress for the next launch. **Set up later** suppresses automatic reopening. Settings → General → First-run guide reopens it; a completed guide restarts at page one.

## Implementation boundaries

- Reuses `AppSettings`, `CredentialEditor`, model installers, Apple Speech, and Laya managers; no additional key store.
- `OnboardingState` stores navigation/choices, not proof of runtime readiness.
- Downloads require explicit action. Paraformer/BGE jobs are serialized/deduplicated; failures preserve reasons and allow the queue to continue. Cancellation clears pending jobs and preserves older models. Closing onboarding does not cancel an ongoing download.
- Local transcription/vectors do not imply local answer generation. UI explains data destinations and API usage.
- Connection-test results last only for the current run and are invalidated by provider, configuration, or credential changes.
- New installs default to local transcription/vectors and an independent answer service. Supported devices default to Jev Mode suggestions; existing settings are preserved. Model preparation still requires explicit action.

## Preview

From the repository root:

```sh
bash StealthApp/scripts/preview-onboarding.sh
```

Creates `StealthApp/build/Onboarding/LiveCopilot Preview.app`, reusable without launch arguments. A bundled preview marker selects mock services with an independent bundle ID, preferences, and data directory. Downloads, permissions, and real API calls are disabled. Production installation is not replaced.

```sh
bash StealthApp/scripts/preview-onboarding.sh --onboarding-dark --onboarding-compact
```

Preview progress persists, but reopening a completed preview starts at page one. Quit the preview before rebuilding to avoid multiple instances.

## Acceptance — 2026-09-28

- Debug build passed; `scripts/test-core.sh`: 72 checks passed.
- Native XCTest: 62 tests, one existing real-Laya integration test skipped, zero failures.
- Nine added onboarding tests cover fresh/existing data detection, resume/skip/finish, setting preservation, download queue/failure/cancellation, test-request content and invalidation, typing mode, and no preview downloads.
- Actual window checks covered all six Chinese pages, English switching, sample questions, reopening from Settings, resuming after defer/exit, and 880 × 590 compact dark appearance. A successful service test remained visible on the final page.
- Screenshots: `StealthApp/build/onboarding-qa/`; complete log: `StealthApp/build/onboarding-final-tests.log`.

Not validated here: real model downloads, physical microphone/system-audio authorization/capture, or paid service requests. Isolated end-to-end checks are required before release; mock preview acceptance does not establish those outcomes.
