# 1.2.1 — overlay expansion and LIVE icon

## Behavior

- Automatic content height and right-edge hiding default on; other existing settings remain.
- Empty overlay is about 480 × 240 pt. Transcripts/answers expand it downward while preserving top/width. Transcript scrolls; answers expand to screen height then scroll. Very short screens allow the whole panel to scroll to controls.
- Hover within 3 pt of the right edge for roughly 0.16 s to reveal; leave for about 0.9 s to hide. Menu-bar/Dock corners are excluded, other displays supported, and typing/dragging keeps it open.
- Pinning disables edge hiding; unpinning collapses. `⌥H`, Dock, and menu bar always reveal. Manual answer shortcuts reveal; automatic suggestions do not force open a hidden window.
- Dragging top/bottom enters manual height; restore automatic height in General → Overlay. A pinned window moves from its header.
- Animations respect Reduce Motion. Hiding does not stop listening or generation.

## Icon

The rear bubble uses a pink gradient, with a blue foreground and ceramic base. A smaller waveform sits beside larger uppercase **LIVE**, outlined from Avenir Next Heavy Italic. The pink recording dot has radial glow/highlight. All text is vector outlines; SVG has no font dependencies or embedded bitmap.

Assets: `assets/brand/LiveCopilot.svg`, `LiveCopilot-mark.svg`, `LiveCopilot-preview.png`; regenerated app icon: `StealthApp/Resources/AppIcon.icns`.

## Validation

- Universal Release, 55 core checks, and 17 native tests passed.
- Tests cover negative-coordinate displays, bounds, hover/leave delay, typing visibility, hidden growth, manual resize superseding queued growth, and manual versus automatic reveal.
- Isolated Mock UI checked compact empty state, simulated transcription, long Chinese/English answers, sources, and settings, without real audio or API requests.
- Fixed NSHostingView default constraints preventing hidden growth and initial sizing callbacks arriving before the window was assigned.
- Still ad-hoc signed; no certificate migration or permission reset. macOS may request renewed Keychain/system-audio permission after updating.
- No GitHub Release was published for this UI update.
