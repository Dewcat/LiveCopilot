# 1.1.1 — window controls and application icon

Installed **1.1.1 / 20260914.191619** at `~/Applications/LiveCopilot.app`, with 1.1.0 backed up. Settings, models, knowledge, and Keychain items were neither migrated nor cleared. The public GitHub Release remained 1.1.0; this update was not separately published.

## Changes

- **Capture:** Settings/History now allow capture. General provides optional overlay exclusion from screenshots/sharing, initially enabled, independent of background and persisted.
- **Resize:** 12 pt edge targets and 28 × 28 pt corners preserve the opposite edge. Width is clamped to 400–700, height to 440–1000. Fixed bottom-right vertical direction; header/footer leave corner clearance while text remains editable/selectable.
- **Dock:** regular macOS activation restores the Dock icon. Clicking it reveals the overlay; menu-bar access and shortcuts remain.
- **Icon:** original conversation-card/waveform-to-text artwork with ceramic base, blue/green embossed cards, highlights, and shadows from editable SVG. Includes monochrome mark, transparent PNG, and full-size ICNS. See [brand assets](../assets/brand/README.md).

## Validation

- Native universal Release and strict installed signature validation passed.
- Fourteen native tests passed, including 43 core checks, eight-direction resizing, clamping, opposite-edge preservation, clear central content, migration, and capture-option persistence.
- Mock Settings screenshots and the Chinese capture toggle worked. Production version/preferences/new option and SVG/PNG/ICNS artwork were checked.
- Automated dragging did not yield reliable size-change evidence. Geometry tests do not establish real drag feel; Dock appearance and specific meeting-app exclusion still need local observation.
- No real model calls. Changed ad-hoc signing prompted Keychain confirmation; after user approval the existing item loaded at 19:18:57 and Services showed configured. No key replacement or transmission.
- Executable SHA-256: `20f8d93c13add4a456680a6ca80e6224fa59bf9fa2e7c4a6a4cce7b5b7c06d0a`. Final tests completed 19:18:27: 14 tests, zero failures.

## ASR direction

The working Live route was not replaced. Proposed next step: local ASR + complete-question detection + local retrieval + text model, rather than replacing semantic delegation with VAD pauses. See [ASR evaluation](ASR_DIRECTION.md) for model choice, English/mixed-language evaluation, and macOS packaging boundaries.
