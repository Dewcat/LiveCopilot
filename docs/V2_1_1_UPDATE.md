# LiveCopilot 2.1.1

## Changes

- Transparent Settings title bar removes the duplicate title and extends sidebar/content backgrounds to the top, retaining native controls, dragging, and resizing.
- Fresh installs enable automatic update checks; saved opt-outs remain. Download/installation still require user confirmation.
- Shortcuts adds Show/Hide Overlay, default Option + H, editable/resettable, immediate and persistent. Menus, tips, and onboarding show the actual binding.
- Recording a shortcut suspends this app's global hotkeys. Esc, outside click, or leaving the window cancels; duplicate combinations show an error and preserve the old setting.

## Validation

- Eighty-one XCTest cases ran; one real-Laya test skipped, all others passed.
- Added migration, visibility-shortcut persistence/reset/conflict, hotkey suspension/restoration, and default-on updates preserving explicit opt-out tests.
- Isolated preview checked continuous title/sidebar background, shortcut capture/conflict/reset/Esc/page navigation, and default-on updates without network access. Native key dispatch has separate test coverage.
- Universal Release passed: 2.1.1 / build 20260930.091834. Ten Mach-O components passed Developer ID, hardened-runtime, timestamp, and dual-architecture verification.
- App notarization `20aa3a20-137f-4b09-bef4-c23c3a46ad17` and DMG notarization `66f0fa1d-5b47-4c0a-95da-3b9d592631f8` were Accepted without issues. Both tickets stapled; Gatekeeper and final image integrity passed.
- DMG SHA-256: `63a3846eeda9c0209c12a7018d2087d646d87f08e9ef1894b579ce1c76aea3a9`.
- Delivered the package to Desktop for manual installation testing. Local 2.1.0 and settings remained. At this checkpoint, no GitHub/site publication had occurred.
