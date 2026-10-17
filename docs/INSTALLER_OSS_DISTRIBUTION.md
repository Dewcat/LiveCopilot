# Hong Kong OSS installer distribution

## Historical rollout status

On 2026-10-09, created `livecopilot-downloads-hk` in Hong Kong, standard storage/local redundancy. Published 2.1.0 DMG and SHA256SUMS were uploaded under `releases/v2.1.0/`. Bucket ACL stays private; policy allows anonymous `oss:GetObject` only for `releases/*`. Anonymous listing returns 403.

Website download buttons use Hong Kong with GitHub fallback. Sparkle's enclosure uses the same object; the feed stays on GitHub Pages. Anonymous HEAD returned 200, a 1,024-byte Range returned 206, listing 403.

Local `curl --noproxy '*'` initially timed out after 90 seconds/22,625,735 bytes (about 251 KB/s); a 120-second resume transferred only 3,915,184 bytes (about 32.6 KB/s). A GitHub 1 MiB sample took 3.57 seconds. Egress location was not verified, so these results do not represent all mainland networks. The user subsequently reported acceptable speed with a screenshot showing about 1.1 MB/s on 2026-10-09, and approved the website download rollout.

## Configuration

- Website manifest: `site/download.json`. `mirror_url: null` uses GitHub; set an immutable HTTPS URL only after anonymous validation.
- With a mirror, both languages' header/footer retain GitHub fallback links.
- Upload only public release DMG/checksums, not old model directories, signing keys, or user data.
- Initial choice: Hong Kong standard pay-as-you-go, no acceleration/CDN. Account console pricing is authoritative.
- Use a dedicated bucket or versioned `releases/v<version>/` prefix. No anonymous writes/listing; read only release objects. Confirm permissions in the actual console.
- Billing alerts are not spending caps.

## First-rollout acceptance

1. Fetch the published GitHub artifact and verify size/GitHub SHA-256; do not substitute an unpublished local candidate.
2. Upload identical bytes under a version path with correct filename and Content-Type.
3. Verify anonymous HEAD, complete GET, Range, and downloaded SHA-256.
4. Test on a mainland network without proxies; a proxied local benchmark does not qualify.
5. Set `mirror_url`, build/check both languages' main/fallback links, then deploy Pages.
6. Separately verify Sparkle enclosure URL, length, signature, and actual update flow before switching updates. Do not repack a DMG merely to change its URL.

## Later releases

Publish GitHub first, mirror identical finalized bytes and verify, then update website/feed. Never overwrite an existing version. Upload credentials belong only in controlled local configuration or CI Secrets, never web pages or the app.

## Routing decision

Keep one download button. Direct Hong Kong OSS requires no custom domain; retain GitHub fallback. Strict mainland/international routing would need a reachable redirect service using client egress IP: CN → Hong Kong, other countries → GitHub, unknown → Hong Kong, with `Cache-Control: no-store`. It would redirect rather than proxy files. VPN/Private Relay changes apparent egress.

Do not infer region from browser language/timezone or depend on an unverified public IP lookup. No routing service or domain was created.

A complete OSS download matched SHA-256 `748a0414f159bb9f4898a2d0b88bdaec7ff704d5ea875293fd6198ac88bddb4d`. Parallel Range requests completed the tail; this proves integrity, not acceptable single-connection speed.

[Historical test download](https://livecopilot-downloads-hk.oss-cn-hongkong.aliyuncs.com/releases/v2.1.0/LiveCopilot-2.1.0-macOS-universal.dmg)

## Rollout scope

One direct Hong Kong button, no IP detection/domain/routing service, and GitHub fallback. Sparkle's enclosure switched to the same DMG and the feed was re-signed with the existing Keychain identity. Package signature/version/notes stayed unchanged; Hong Kong hash, original package signature, and new feed signature passed. The feed stayed on Pages. Public version remained 2.1.0; no artificial upgrade version was created. Real client installation/relaunch was deferred to the next genuine release.
