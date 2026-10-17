# Website redesign acceptance — 2026-09-19

## Delivery

Implemented visual specification v1.1 while retaining the Python static builder, Chinese/English routes, Pages, and v1.4.1 download. Includes glass navigation, animated Hero, sequential workflow, four behavior cards, four scenarios, local-processing architecture, dark privacy section, download/install guidance, services, and 1200 × 630 social image. No new site dependencies or real API calls. P3 decorative parallax was not added.

Publication used an independent worktree from origin/main `5aa62342faf248f1adf7b930f4434aeb48e1cf54`, committing only website files/this record rather than app-development commits. User-supplied specification remained outside the publication commit.

## Backup

- `../LiveCopilot-website-backups/website-before-redesign-20260919-225100.tar.gz`
- SHA-256: `b8ebb446c8411d4249507f2c3cb4dfa2b546a3df0fce5776a774e14a25d423ed`.
- Contains `site/`, `StealthApp/scripts/build-site.py`, `.github/workflows/pages.yml`.
- Source-worktree HEAD at backup: `064692ec15a3fbc537af41aef2bcd21219f48629`. Site files matched then-current origin/main; archive readability verified.
- Adjacent JSON inventory retained. Restore those files in an independent worktree and redeploy through Pages; do not overwrite unrelated app work.

## Content checks

- `DocumentParser.supportedExtensions` supports PDF, DOCX, Markdown, TXT; the defense example's XLSX became exported PDF.
- Markdown sources use sections; PDFs use page numbers.
- Local speech/BGE-M3, SQLite, and Keychain claims checked against source.
- Answer requests explicitly send questions, relevant conversation, and excerpts to the selected analysis provider. Cloud speech/embeddings send their respective data; no fully offline promise.
- Download kept the existing signed/notarized v1.4.1 universal DMG; asset name/public URL verified through GitHub API. No new app release.
- Retained services, costs, Apple limits, installation/signing notes. Third-party price copy was not freshly audited.

## Local validation

- `python3 StealthApp/scripts/build-site.py` and locale-key parity passed.
- No duplicate IDs, missing local anchors, or missing assets.
- Chrome macOS/Playwright WebKit: both languages at 375, 390, 430, 768, 1024, 1280, 1440, 1728 px, 32 layouts without overflow/missing images/pageerror.
- Both engines/languages at 375/390/768/1440 px passed four scenarios, Sources, arrows/Home/End, overlay button, mobile navigation, Escape, and `#install`/`#services`. Scenario-container height remained fixed.
- Without JavaScript, full question/answer/sources, navigation/download/language links, and native details remained usable; scenario section showed the meeting example.
- All phases of the 14-second Hero passed: streaming transcript, chunked answer, soft reset, pause, and dynamic Reduce Motion. Sources pauses the loop; demo input sends nothing.
- Recorded cycle made no external requests; layout shift about 0.00006. Answers/material are fictional examples, not internal model reasoning.
- axe-core WCAG 2 A/AA and 2.1 AA found no violations for both languages at 390/1440 px; corrected small file-type/workflow text contrast.
- Inspected desktop/mobile full pages, Hero/scenarios, local path, and social image.

## Lighthouse

Final local production build in headless Chrome/macOS, desktop and mobile emulation, with normal animation/scripts enabled:

| Configuration | Performance | Accessibility | Best Practices | SEO | LCP | CLS |
| --- | --- | --- | --- | --- | --- | --- |
| Desktop | 100 | 100 | 100 | 100 | 0.3 s | 0 |
| Emulated mobile | 100 | 100 | 100 | 100 | 1.4 s | 0 |

Laboratory data is not field Core Web Vitals; no real-user INP measurement. Lighthouse/axe JSON, screenshots, and scripts: `../LiveCopilot-website-backups/qa-20260919/`. Tools are development-only, not website dependencies.

## Limits

- WebKit desktop/mobile coverage is not macOS Safari or physical iOS Safari acceptance; those were not run.
- No paid model requests, actual audio capture, or repeated native-app tests.
- Lightweight CSS/JS retained; cache/uncompressed-resource improvements remain despite meeting all four score targets. Pages controls production caching.

## Publication

Targets: `https://carey-bk.github.io/LiveCopilot/` and `/en/`. Publish through `.github/workflows/pages.yml`; verify remote workflow success, live/local asset equality, and download reachability separately at delivery.
