# First-run onboarding — phase 2

Historical status: local implementation and preview acceptance completed on 2026-09-29, not yet published. Extends the six-step guide with animation, scenario recommendations, and first-use tips.

## Animated demonstration

- A single-play sequence shows hearing a question → identifying a complete question → consulting context/material → suggesting an answer. Supports pause, resume, and replay.
- Interview, meeting, and academic-defense examples have distinct synthetic questions, material, and answers. Switching scenario updates the demo and reuses `ScenarioProfile` for the actual answer style.
- Demonstrations are independent of recording, documents, and service requests; leaving the page cancels their task.
- Reduce Motion displays the full static content. Native buttons retain keyboard/accessibility support; unrevealed content is not exposed early to accessibility.

## Scenario recommendations

The model page explains the rationale and proposed changes before **Apply recommended configuration**. Browsing scenarios does not apply recommendations.

| Scenario | Preparation |
| --- | --- |
| Interview | Local recognition and Jev Mode; prepare retrieval for resumes/project material. |
| Meeting | Local recognition and Jev Mode; retrieval optional, recap for reviewing discussion. |
| Academic defense | Local recognition and Jev Mode; prepare retrieval for papers/method notes. |

At this checkpoint, installed Apple assets for the selected language were reused first; otherwise Paraformer was recommended. Later releases recommend Zipformer for mixed Chinese/English. Supported devices recommend Jev Mode; others use manual answers. Typing-only does not alter speech/Jev Mode or add speech downloads. Recommendations preserve answer provider/model/endpoint/key, interface language, remote/in-person mode, and window preferences. They start neither downloads nor recording and cannot apply while listening, indexing, or preparing models.

Using personal materials remains an onboarding preparation preference; it does not delete or disable an existing knowledge library. Users can adjust individual settings; downloads use the existing explicit action.

## Overlay first-use tips

- Fresh installations show four tips: listen/type, generate an answer, show/hide the overlay, and capture/sharing exclusion.
- Tips highlight corresponding controls and read saved shortcuts. Controls remain usable; tip buttons do not start listening or answer requests.
- Progress is independent and skippable. Tips pause while onboarding is open and resume afterward; completing the guide again does not repeat completed tips.
- Existing users, including phase-1 users, are not interrupted. They can replay tips from Settings → General → Overlay tips or onboarding's final page.
- Auto-hide pauses during tips. A manually hidden panel remains recoverable from the screen edge. Onboarding suppresses edge-hover overlay activation; pin/edge preferences remain intact.

## Acceptance

- Debug build, preview signature, script syntax, and `git diff --check` passed.
- Native XCTest: 67 tests, one existing real-Laya integration test skipped, zero failures. Fourteen onboarding tests, including five new ones.
- Added coverage: tip persistence/pause/completion/replay, old-guide compatibility and unobtrusive upgrades, recommendation scope, no implicit download/listening, and guide/tip edge visibility.
- Actual UI checks: Chinese animation/replay/pause, explicit meeting recommendation, English defense/typing recommendations, replay from Settings/final page, collapse after tip completion, dark/compact layouts.
- The then-minimum sizes were 880 × 590 pt for onboarding and 400 pt overlay width; English text fit. The right-column scrolling layout was later superseded below.
- Log: `StealthApp/build/onboarding-phase2-tests.log`; screenshots: `StealthApp/build/onboarding-phase2-qa/`.

Isolated preview checks did not capture real audio, call paid APIs, download large models, or replace production.

## Visual transitions — 2026-09-29

- Pink/blue glows move between six steps with 1.2-second transitions and reduced brightness in dark mode. Background extends through the transparent title bar; title/separator are hidden, native window controls retained.
- Pages slide/fade for 0.38 seconds, reversing direction on back navigation. Brand/footer remain fixed; outgoing pages ignore clicks and accessibility.
- Bottom-left progress totals 206 pt wide × 7 pt tall: current segment 46 pt, others 26 pt. Width/color/step number animate together.
- **Set up later** sits left of Continue as borderless text, accent-colored and underlined on hover, dimmer when pressed. **Download later** shares the style.
- Reduce Motion disables page/background/progress animation. Preview-only `--onboarding-slow-motion` runs at one-fifth speed for intermediate-frame checks.
- All 14 onboarding tests, final Debug build, signing, and diff checks passed. Actual UI confirmed continuous title-bar background, forward/back intermediate frames, compact English dark appearance, and Reduce Motion. Automation did not reproduce hover events; hover color/underline were implemented in the view.
- Screenshots: `StealthApp/build/onboarding-motion-qa/`; log: `StealthApp/build/onboarding-motion-tests.log`.

## Single-screen layout — 2026-09-29

- Removed the right scrolling container. Default/minimum window is 1040 × 700 pt, initially constrained by available screen space. Immersive background, transitions, and fixed navigation remain.
- Scenario selection moved to the introduction's left column; the right column shows the full example, answer, replay, and explanation.
- Recommendations moved left. The right column contains speech, side-by-side retrieval/Jev Mode, and download/storage information. Cloud credentials use a separate popover instead of stacked editors.
- Advanced answer connection fields use a popover. Permission cards are tighter so remote microphone and system-audio permissions appear together.
- First experience uses Readiness / Examples / Try a question tabs in a shared region. Switching preserves question content; leaving Try cancels its request. Long answers paginate within available space without losing characters or vertical scrolling.
- Debug build/preview signature and 16 onboarding tests passed. New tests cover complete Chinese/English/emoji pagination, measured height, unspaced text, and resizing.
- Minimum-window checks covered Chinese examples, English Apple/Jev Mode, dual audio permissions, five readiness states, example/question tabs, dark/Reduce Motion, and retained question content. Preview made no real requests, permission prompts, or downloads.
- Log: `StealthApp/build/onboarding-no-scroll-tests.log`; screenshots: `StealthApp/build/onboarding-no-scroll-qa/`.

## Reproduce

```sh
bash StealthApp/scripts/preview-onboarding.sh
bash StealthApp/scripts/preview-onboarding.sh --onboarding-dark --onboarding-compact --onboarding-reduce-motion
```

Flags affect only the isolated preview, not system settings. Quit the running preview before rebuilding. Output remains `StealthApp/build/Onboarding/LiveCopilot Preview.app`.
