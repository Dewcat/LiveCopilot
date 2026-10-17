# 1.4.2 local development build

This checkpoint was developed/validated locally, without Apple notarization, a public Release, GitHub push, or website deployment. Public version remained 1.4.1.

## UI and interaction

- Removed the transcript show/hide bubble; show text when present and stay compact when empty.
- Renamed the answer action to **Generate answer** across overlay, shortcuts, and menu bar.
- Added independent Recap/Follow-up switches and descriptions in General, initially on. Disabling hides the button, unregisters its global shortcut, and cancels that tool's active generation; reenabling restores the shortcut.
- Defaults: `⌃⌥Space` answer, `⌃⌥S` recap, `⌃⌥X` follow-up, `⌥H` visibility. Existing custom bindings remain; per-action reset uses new defaults. Empty-state/help text reads actual bindings.
- Knowledge import uses a large blue dashed rounded target with click/drop, hover/busy state, and format guidance. Validate the entire batch before indexing, rejecting folders, web links, and unsupported files; deduplicate URLs within a batch.
- Brand titles use Avenir Next Heavy Italic, matching the icon's LIVE lettering, in overlay, sidebar, and About.

## Local installation and data

- `~/Applications/LiveCopilot Dev.app`, `1.4.2 Dev (20260919.002)`.
- Identity `com.livecopilot.development`; production `com.livecopilot.app` and its path remain.
- Signed with the existing Developer ID, without notarization or a new public download.
- Independent Dev preferences/history/knowledge under `~/Library/Application Support/LiveCopilot/Development`. A local knowledge snapshot was copied and its source paths rewritten to Dev locations.
- Shared `LiveCopilot/Models` download cache avoids large repeat downloads. Mock keeps independent `LiveCopilot/Mock` data/preferences.
- First real Dev use may require recording/system-audio/Keychain permission for **LiveCopilot Dev**. Existing keys need not be reentered; startup reads silently and the user handles system authorization.
- Do not run Dev and production simultaneously because global shortcuts overlap.

## Validation

- Twenty-eight Debug native tests passed, zero failures: migration, independent toggles, shortcut disable/restore/custom/reset, and cancellation when disabling an active tool.
- Finder transfer tests used real NSItemProvider URL/Data representations, Chinese/space-containing filenames, sorted/deduplicated batches, unsupported-file rejection, and Mock vector indexing.
- Mock GUI checked both languages, brand font, removed bubble, names/default shortcuts/live help, disabled tool controls/shortcuts, click-to-import indexing, continuous captions, and recap shortcut with the input focused.
- Final Debug build and installation signature passed; normal launch showed the stated Dev version and production executable hash was unchanged.
- No paid APIs, exposed/committed keys, or physical audio capture. Actual cross-window Finder drag gestures were not automated; transfer decoding/indexing were tested separately.

Further changes accumulate locally; update the public version, notarize, and synchronize GitHub/site when the user moves to release.
