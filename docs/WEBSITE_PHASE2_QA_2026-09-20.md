# Website phase 2 acceptance — 2026-09-20

## Scope

Following phase-2 requirements and feedback about inaccurate product depictions, changed only the site while retaining the static build, two locales, Pages, downloads, and installation guidance.

- Removed invented traffic-light title bar, knowledge sidebar, generic answer card, and persistent edge handle from product visuals.
- `site/components/product-ui.html`, `product-transcript.html`, and `product-answer.html` now share rendering across Hero, feature cards, workflow endpoint, and scenarios.
- Matched actual toolbar/status/suggestions, transcript following, answer/recap/follow-up, answer sections, individual sources, input/context, and footer.
- Separate `product.css` follows source 16 px corners, 14 px padding, 12/14 px typography, and native-material direction rather than website glass styling.
- Document cards, retrieval lines, stage labels, and playback controls sit outside the product and are identified as website illustrations.
- Hero uses one 13.5-second timeline with phrase-wise transcript/answer changes, individual source expansion, and fixed outer height.
- Edge demo uses the actual idle panel fading to fully hidden; edge/web button restores it, without an invented handle.
- Workflow plays about six seconds after 45% viewport entry, ending in the same product component.
- Added Listen / Find / Answer overview before detailed service comparison; retained dark privacy section.
- Updated social preview with the shared product component.

## Product reference

Source commit: `064692ec15a3fbc537af41aef2bcd21219f48629`. Reviewed `OverlayView.swift`, `OverlayWindow.swift`, `OverlayLayout.swift`, `WindowBackgroundView.swift`, `AppBrandTitle.swift`, `SuggestionMode.swift`, `Localization.swift`, `AppCoordinator.swift`, and real repository screenshots.

An isolated fixture rendered unmodified SwiftUI views/materials/brand/layout/localization for comparison. It is actual source rendering, not a user's session or installed-release acceptance, and reads no production credentials/documents/audio.

Comparison: `../LiveCopilot-website-backups/phase2-qa-20260920/product-comparison.html`.

Browser material/fonts/control glyphs differ; pixel identity is not promised. Website animation reserves fixed dimensions while the app can grow. Source targets are at least 24 px on the web. Visual toolbar/switches do not pretend to start recording/open settings. Source `tuckAway` fades and calls `orderOut`; that behavior takes precedence over generic slide/handle diagrams.

## Validation

- Production build, locale-key parity, unique IDs, anchors, and local assets passed.
- Chrome macOS and Playwright WebKit: both languages at 375, 390, 430, 768, 1024, 1280, 1440, 1728 px, 32 cases.
- No horizontal overflow/pageerror; fixed a WebKit ResizeObserver loop warning.
- All sizes exercised scenarios, sources, edge control; also Escape, arrows/Home/End, install/service deep links, complete no-JS content, and native disclosures.
- Hero cycle/phrase updates/pause/sources/fixed height, final workflow, and Reduce Motion passed. Final outer height stayed 645.296875 px; CLS about 0.000004, no external requests.
- axe-core at Chinese/English 390/1440 px: no WCAG 2 A/AA or 2.1 AA violations. Expanded source targets flagged by Lighthouse.
- Inspected both Heroes, Bento, workflow, service overview, mobile layout, and 1200 × 630 social image.

## Local Lighthouse

| Configuration | Performance | Accessibility | Best Practices | SEO | LCP | CLS |
| --- | --- | --- | --- | --- | --- | --- |
| Desktop | 100 | 100 | 100 | 100 | 0.4 s | 0 |
| Emulated mobile | 99 | 100 | 100 | 100 | 1.7 s | 0 |

Normal animation stayed enabled. These are laboratory results, not field Core Web Vitals; real-user INP was not measured. Readable sources retain compression/cache optimization opportunities.

## Limits

- WebKit automation is not actual Safari/iOS hardware acceptance.
- Safari 26.6.2 WebDriver was blocked: `You must enable 'Allow remote automation' in the Developer section of Safari Settings`. Browser settings were not changed and Safari hardware acceptance was not claimed.
- No paid API, real audio, or native-app regression; this scope publishes only the site.
- Existing service prices were retained, not freshly audited.

## Backup and publication

Before changes, site/build script/Pages configuration were archived to `../LiveCopilot-website-backups/website-before-phase2-20260920-080712.tar.gz`, with SHA-256 inventory and readable-archive verification. Earlier backups remain.

Publish from an independent website branch containing only site, build script, and this record, excluding app-development commits. Then verify Pages workflow, online asset hashes, and downloads.

Screenshots, native fixture, browser results, and Lighthouse/axe JSON: `../LiveCopilot-website-backups/phase2-qa-20260920/`.
