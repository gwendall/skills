# Platform specs for link previews (checked October 2026)

Confidence: **official** = the platform's own documentation; **code** = read from the client's source; **folklore** = blogs, forums and SEO guides, repeated everywhere, never confirmed. Design to the official numbers, treat folklore as a risk to test.

## Summary: what one image must satisfy

| Constraint | Value | Binding platform |
| --- | --- | --- |
| Size | 1200x630 (1.91:1) | Facebook, LinkedIn (min 1200x627), iMessage (min 900 wide), Google Discover (min 1200 wide) |
| Bytes | **under 600 KB**, aim under 300 KB | WhatsApp (official 600 KB; folklore says 300 KB) |
| Format | PNG or JPEG | all; WebP is accepted by some, rejected by others |
| Delivery | server HTML, no JS, tags in the first 1 MB, absolute https URL | Facebook, iMessage, every crawler |
| Not square | ratio clearly wider than 1:1 | Signal treats near-square images as an icon |

## Per platform

### Facebook / Meta (official)
- Minimum 200x200; under 600x315 the image shows small; **1200x630 recommended**; ratio as close to 1.91:1 as possible, same on desktop and mobile. Max 8 MB. ([developers.facebook.com/docs/sharing/webmasters/images](https://developers.facebook.com/docs/sharing/webmasters/images/))
- The first share of a URL triggers the scrape: the first sharer may see no image. Declaring `og:image:width` and `og:image:height` lets Facebook render immediately instead of downloading asynchronously. To change an image already shared, use a new URL; the Sharing Debugger's "Scrape Again" refreshes the cache.
- Crawler `facebookexternalhit/1.1` expects an answer within a few seconds, reads OG tags only in the first 1 MB of the page, wants gzip/deflate and `Range` support. ([crawler doc](https://developers.facebook.com/docs/sharing/webmasters/crawler))

### WhatsApp (official, with a disclaimer)
- **Under 600 KB**, at least 300 px wide, width/height ratio at most 4:1. Meta itself warns these rules "are not guaranteed to work (and to keep working)". ([developers.facebook.com/docs/whatsapp/link-previews](https://developers.facebook.com/docs/whatsapp/link-previews))
- Folklore: 300 KB max (contradicts the doc; staying under it is the safe side), square crop of the preview (unconfirmed).

### X / Twitter
- The Cards documentation was removed from docs.x.com; the Card Validator lost its preview in 2022 and is gone. Check a card by pasting the link in a draft post.
- Still true in practice: `twitter:card = summary_large_image`, image at least 300x157, 1200x630 or 1200x675 renders large, max 5 MB (the figure Next.js cites).
- X draws the domain over the bottom-left of the image and no longer shows the title under it: the image must carry the message alone.
- Share intent (official): `https://x.com/intent/tweet` with `text`, `url`, `hashtags`, `via`; 280 characters after expansion. ([web intent doc](https://docs.x.com/x-for-websites/post-button/guides/web-intent))
- Do not apply the Ads API Website Card numbers (3 MB, 800 px, 1:1 or 1.91:1) to organic links: different product.

### LinkedIn (official)
- Needs `og:title`, `og:image`, `og:description`, `og:url`. Image max 5 MB, minimum 1200x627, ratio 1.91:1. ([linkedin.com/help/linkedin/answer/46687](https://www.linkedin.com/help/linkedin/answer/46687))
- Post Inspector refreshes the cache. A post already published keeps the preview it was created with.

### iMessage / Apple (official, TN3156, 2024)
- Images **at least 900 px wide**; under 150 px wide they may be ignored or shown as an icon; square icons at least 108 px. The page itself is capped at 1 MB, all linked resources at 10 MB. ([TN3156](https://developer.apple.com/documentation/technotes/tn3156-create-rich-previews-for-messages))
- No JavaScript, no meta refresh; HTTP redirects are followed. Same metadata for mobile and desktop (no user agent sniffing).
- Falls back to `apple-touch-icon` when no usable `og:image`.
- Folklore: iOS 17 crops 1200x628 towards square (one developer forum report).

### Telegram
- No official spec. 1200x630 works. Previews are cached hard; @WebpageBot refreshes a URL. Some valid pages fail with no explanation: test the real link.

### Slack (official, partial)
- Reads standard OG and Twitter card tags. Unfurl can be disabled per message (`unfurl_links`, `unfurl_media`). Cache duration and byte limits are undocumented.

### Discord
- No official spec for link unfurls. 1200x630 renders; without `summary_large_image` Discord may show a small thumbnail. Keep under about 1 MB (folklore).

### Signal (code)
- Prefers `og:image`, falls back to touch icons. Shows the image large only if both sides are at least 200 px **and it is not near square** (within about 5 % of 1:1); otherwise it is drawn as an icon. Read from Signal Desktop's source at one point in time.

### Bluesky
- Uses the page's OG tags. External link thumbnails are capped at about 1 MB in the AT Protocol lexicon (blog reading of the lexicon; post images were raised to 2 MB in 2026). Keep the card under 1 MB.

### Threads, Mastodon, Reddit
- No official spec. Threads shares Meta's infrastructure (Sharing Debugger). Every Mastodon instance fetches the page and the image independently (a fan-out of requests on each post) and may crop closer to square. Reddit follows 1200x630 by convention.

### Google Discover (official)
- At least 1200 px wide, more than 300,000 pixels, 16:9 recommended, and the page needs `max-image-preview:large` in its robots meta or no large image is shown. Google may crop. ([google-discover doc](https://developers.google.com/search/docs/appearance/google-discover))

## Shareable files (not link previews)

- Instagram: post 1080x1080 (1:1) or 1080x1350 (4:5); the profile grid always crops to 1:1, so keep the subject centred. Story 1080x1920 with UI overlays at the top and bottom (keep about 250 px clear at each end). Third-party figures, consistent across guides.

## Web Share API (official specs and caniuse, October 2026)

- `navigator.share({ title, text, url, files })` returns a Promise; at least one field is required. Needs HTTPS and a user gesture; a cross-origin iframe needs `allow="web-share"`.
- `navigator.canShare(data)` tests file support and needs no gesture.
- Support about 94 % globally: Chrome full file sharing from 128, Safari `share` from 12.1 and `canShare` from 14, Samsung Internet from 8.2, Firefox Android recent versions; **Firefox desktop: none**.
- iOS Safari bug (WebKit 203221, reported 2019, not confirmed fixed): with both `text` and `url`, some targets (Copy) keep only the text.

## Readability references

- WCAG 2.1 SC 1.4.3: contrast 4.5:1 for normal text, 3:1 for large text.
- No controlled study ties font size on social cards to engagement. Practitioner heuristics: a headline of at least 60 to 72 px on a 1200x630 canvas because it is shown 300 to 400 px wide; 24 pt minimum, 32 pt for key information in social graphics. The 80 px headline / 40 px floor in SKILL.md comes from the 0.29 scale of a 343 px phone card.
