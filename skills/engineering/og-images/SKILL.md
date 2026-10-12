---
name: og-images
description: Design, build and verify Open Graph / Twitter card images and shareable result cards that read well as a phone thumbnail and unfurl everywhere (X, iMessage, WhatsApp, Telegram, Slack, Discord, LinkedIn, Facebook, Bluesky). Covers composition (big type, few words, a real image, safe zones, the square crop), Next.js `opengraph-image.tsx` / `twitter-image.tsx` / `ImageResponse` (Satori) and every pitfall that breaks them, fonts, byte budgets, crawler access, caching, the Web Share button, and a verification checklist with scripts. Use whenever you create or change an OG image, a social card, a share image, link previews or metadata images. Triggers on "OG image", "opengraph-image", "twitter-image", "og:image", "social card", "share card", "link preview", "unfurl", "ImageResponse", "next/og", "Satori", "partager l'image", "aperçu du lien".
compatibility: The design and verification parts apply to any stack. The implementation part targets Next.js App Router 14-16 with `next/og`. Scripts need python3 (stdlib only for check-og.py, Pillow for thumb-sheet.py) and network access.
metadata: {"version":"1.0.0","openclaw":{"requires":{"bins":["python3"]},"emoji":"framed_picture"}}
---

# OG images that read as a thumbnail and render everywhere

An OG image is not a poster. It is read **as a thumbnail, in a feed, on a phone, in under a second**, and it is fetched by a dozen crawlers that execute no JavaScript, cache it for weeks and fail silently. Every rule below comes from one of those two facts, or from a production incident.

Work in this order: **compose for the thumbnail, build it generated (never static), then verify from the real HTML in production.** Skipping the last step is how a card that looked perfect in dev ships broken.

## 1. The format

- **Link preview (OG / Twitter): 1200x630 PNG**, ratio 1.91:1. One size for every platform. Declare `og:image:width`, `og:image:height`, `og:image:type` and `og:image:alt` (Next.js does it from the exports).
- **Shareable file (the user posts the image itself): 1080x1080.** Instagram's profile grid crops every post to 1:1, and a square survives every feed. Add 1080x1350 (4:5) or 1080x1920 (story) only when there is a reason.
- **One component, several canvases.** The square and the OG are two layouts of the same card component, not two designs. The OG route and the file route call the same function with a `format` argument.
- **Generated per route, never a static file.** `opengraph-image.tsx` + `twitter-image.tsx` per route that has its own content. A static `public/og.png` goes stale the day the product changes and says nothing about the page.

## 2. Composition: design for 343 px wide

A phone shows the card about **343 to 500 CSS px wide**, so the canvas is shrunk by **0.3 to 0.4**. Some surfaces show a **~100 px thumbnail cut from the centre**. Design for those, then check at full size.

| Rule | Value on the 1200x630 canvas | Why |
| --- | --- | --- |
| Headline | **80 to 140 px**, 1 or 2 lines | At 0.29 it reads 23 to 40 px: legible at a glance |
| Any other text | **at least 40 px**, never under 36 | 36 px becomes 10 px on the phone: the floor of legibility |
| Words | **3 to 6 words, 42 characters max** for the hook | Read in one glance; more is a paragraph nobody reads |
| Image | A real subject (face, product, object, result) on **40 to 60 % of the canvas** | Feeds are scanned by image first; text-only cards are skipped |
| Safe zone | **60 px** from every edge for anything meaningful | Rounded corners, borders and overlays eat the edge |
| Centre square | The **630x630 centre** holds what must survive a square crop (the face, the score, the core of the hook) | Chat apps and compact previews show a centred square or a small thumb |
| Bottom-left | Keep it free of meaning | X draws the domain over the bottom-left of the card |
| Contrast | **4.5:1** minimum (WCAG 1.4.3); never text on a busy photo without a solid band | Thumbnails blur; low contrast vanishes first |

What to **leave out**: descriptions, eyebrows and category labels, capability footers, fine print, screenshots of UI, the URL (the link preview already shows the domain), more than one idea, em dashes or middle dots as separators. A shared *file* is the exception for the URL: it travels without a link, so put the domain on it, small and last.

What makes a card worth sharing (practitioner consensus, not measured science): a **personal result** ("me as X", a score, a rank), a **face**, a **short loud headline**, strong contrast, brand present but secondary. Spotify Wrapped, Duolingo streaks and Strava's Year in Sport all share that shape: the person's own data, big, on a bold field.

**Measure the headline, never guess it.** Satori wraps text but never shrinks it. A long title either overflows or wraps into a 4-line block at the wrong size. Pick the size and the line breaks before rendering, from the font's real advance widths: try every split of the words into 1..N lines, keep the largest size that fits the box. Recipe in `references/satori-recipes.md`. For pixel fonts, snap the size to the font's grid (multiple of 8 for an 8 px design) so every font pixel lands on whole device pixels.

**Look at every glyph you will draw.** A display font can be broken on one letter: a bold pixel font rendered its "W" as a solid blot, its "%" as a "Z" and its "#" as a smudge. Render the full alphabet, the digits and your symbols once in the target font and size, and look. Swap the font for the glyphs that fail.

## 3. Building it in Next.js (App Router, `next/og`)

The file convention, with the exports Next.js turns into tags:

```tsx
// app/thing/[id]/opengraph-image.tsx
import { ImageResponse } from 'next/og';

export const alt = 'Short description of the image';
export const size = { width: 1200, height: 630 };
export const contentType = 'image/png';

export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;              // params is a Promise since Next 16
  const data = await loadPublicThing(id);   // time-boxed, never throws: see "Never fail" below
  return new ImageResponse(<Card data={data} format="og" />, { ...size, fonts: await cardFonts() });
}
```

```tsx
// app/thing/[id]/twitter-image.tsx - must exist too, and re-export every field, or X gets no size/alt
export { default, alt, size, contentType } from './opengraph-image';
```

Route segment config (`runtime`, `dynamic`, `revalidate`) is read statically: **write it literally in each file**, never re-export it.

### Satori (the renderer) - what breaks it

`next/og` vendors its own Satori (Next 16.2 ships `@vercel/og` 0.11 with Satori 0.25 on Yoga). The Satori README on GitHub describes a newer version (grid, block layout); **trust only what the vendored version does.**

- **Flexbox only.** Every element with more than one child needs `display: 'flex'`. No `grid`, no `float`, no `position: sticky`, no animations. `position: absolute` inside a `position: relative` parent works and is how badges and overlaps are placed.
- **An `undefined` style value throws** (`Cannot read properties of undefined (reading 'toString')`). Never write `textShadow: cond ? x : undefined`; spread conditionally: `...(cond ? { textShadow: x } : {})`.
- **Mixed text nodes split.** `{pct}% match` is three children: wrapping and spacing go wrong. Build one string: `` {`${pct}% match`} ``.
- **Missing glyphs.** Every character must exist in a font you passed; curly quotes, accents in a pixel font, emoji and symbols fall back to tofu or trigger a runtime font fetch. Normalise text before drawing.
- **Fonts: TTF, OTF or WOFF only. Never WOFF2.** Pass them as `ArrayBuffer` in `fonts: [{ name, data, weight, style }]`; one entry per weight actually used.
- **Images: PNG or JPEG only** inside `<img>` (WebP and AVIF fail with "Unsupported image type"; SVG only as a data URI). Give every `<img>` explicit `width` and `height`. **No `next/image`** in an OG component.
- **The renderer cannot reach what a browser can.** It does not have the user's cookies, cannot read files through your site's URL during build, and cannot fetch private storage. Load the bytes server side (fs, a service-key client, a signed URL) and pass a data URL or an `ArrayBuffer`.
- **Pixel art**: draw it at an exact multiple of its native size (24x24 at 240, 288, 480...) so nothing is resampled. Low-resolution photos blur when they fill a big panel: give them a smaller frame.
- **`objectFit: 'cover'`** on an `<img>` with explicit `width` and `height` is the reliable way to crop a photo into a frame.

### Fonts

- **Self-host the font files in the repo** and read them with `fs` (Node runtime, the default and the current Next docs' pattern). A font fetched over the network at build time fails builds; at request time it adds latency and a failure mode.
- **Tracing trap**: `readFile(join(process.cwd(), 'assets/font.ttf'))` can make Turbopack trace the whole project into the route (one route pulled in 1,146 files). Fix with a `/* turbopackIgnore: true */` comment on the path expression plus `outputFileTracingIncludes` listing the font folder for that route, then check the route's `.nft.json`.
- **Edge runtime: 500 KB bundle limit** including fonts and images. One display font and one text font, not a family.
- If you must load a Google Font at request time, request the CSS with a non-browser user agent (Google then serves TTF instead of WOFF2), parse the `src: url(...)`, fetch it, and fall back to a bundled font when anything fails.

### Metadata wiring

- **A child segment's `openGraph` object replaces the parent's**, images included (metadata merges shallowly). A page that sets `openGraph: { title }` silently loses the parent's image: spread a shared `openGraph` base, or give the segment its own `opengraph-image`.
- **Explicit `openGraph.images` win over the file convention.** Do not set both; one source per route.
- **`metadataBase` must be the canonical production origin.** Relative image URLs fail the build without it, and a fallback to `VERCEL_URL` points crawlers at a protected preview deployment (401 to every bot).
- **A param-less `opengraph-image` is prerendered at build.** If it reads live data (a featured item, a count), add `export const dynamic = 'force-dynamic'` or revalidate it.
- **Read `og:image` from the real HTML.** Under route groups and some layouts the generated image URL gets a hash suffix; never hardcode `/thing/opengraph-image` in a share URL or a test.
- **Privacy**: the OG URL is public and cached by third parties forever. Render private or unlisted content only behind the same gate as the page, and serve a generic card otherwise.

### Never fail, and serve every crawler

- **A 500 or a timeout is cached as "no preview".** Time-box every data fetch (2 to 3 s), and on any failure return a generic branded card with status 200, never an error.
- **Crawlers must get a 200 `image/png` without cookies, JavaScript or a challenge.** Allowlist preview bots past bot protection and auth middleware: `facebookexternalhit`, `Facebot`, `Twitterbot`, `Slackbot`, `Slack-ImgProxy`, `TelegramBot`, `WhatsApp`, `Discordbot`, `LinkedInBot`, `Applebot`, `Bluesky Cardyb`, `Mastodon`, `Pinterestbot`, `redditbot`, `SkypeUriPreview`. Allow the OG routes in `robots.txt`.
- **The tags must be in the server HTML**, in the first megabyte (Facebook stops reading there, iMessage caps the page at 1 MB). Never add OG tags client side.
- **Absolute `https://` URLs**, no redirects to a login page. iMessage follows HTTP redirects, not meta refresh.
- **Byte budget: aim under 300 KB, never above 600 KB** (WhatsApp's documented limit; it drops larger images). Facebook allows 8 MB, X and LinkedIn 5 MB, Bluesky link thumbnails about 1 MB. Photo-heavy PNG cards easily reach 500 to 900 KB: measure, and if needed serve a JPEG (re-encode the `ImageResponse` with sharp in a route handler and point `openGraph.images` at it).
- **Cache-Control**: set it once with `headers.set` (spreading headers produced a duplicate header that some proxies reject). Long and immutable for content that never changes, short (minutes) for live data. Check what is actually sent with `curl -I`.
- **Version the image URL when the card changes** (`?v=2`). Facebook, LinkedIn, Telegram and chat apps cache the first fetch per URL; a new URL is the only reliable refresh. Facebook's Sharing Debugger, LinkedIn's Post Inspector and Telegram's @WebpageBot force a re-scrape; X has no validator anymore (post the link in a draft to see it).
- **Dev lies.** In development the OG URLs resolve to localhost and no crawler can reach them. Verify on the production domain.

## 4. The share button (image file or link)

Two different products, offer both:

1. **Share the image file** (mobile): fetch the square PNG from a server route, wrap it in a `File`, test `navigator.canShare({ files: [file] })`, then `navigator.share({ files: [file] })` inside the click handler (a user gesture is required; HTTPS only). `canShare` can run ahead of time to decide which button to show.
2. **Share the link**: `navigator.share({ url })` where supported; the link unfurls the OG card. Fallback on desktop: copy link, download the PNG (`<a download>`), and an X intent `https://x.com/intent/tweet?text=...&url=...` (280 characters after expansion).

Pitfalls: Firefox desktop has no Web Share; iOS Safari has shared only `text` when `text` and `url` were both given (WebKit bug 203221): put the URL in `url` alone, or inside `text`, and test on a device. Fetch the PNG before the tap (when the card appears): a slow `await fetch()` between the click and `share()` can outlive the user gesture, and `share()` then rejects with `NotAllowedError`.

## 5. Verify before calling it done

Run all of it; each line caught a real incident.

1. **Render with real data locally**, the worst cases included: the longest title, a one-word title, non-ASCII input, a missing image, a private item. Check every PNG is exactly 1200x630 (or 1080x1080) and under the byte budget.
2. **Look at it at phone size**: `scripts/thumb-sheet.py card-og.png [card-square.png]` builds the 343 px card, the 120 px centre-square crop and the 375 px square side by side. If the headline is not readable there, it is too small.
3. **Check the production HTML and every crawler**: `scripts/check-og.py https://example.com/page` reads the real HTML with several bot user agents, resolves `og:image` and `twitter:image`, and reports status, content type, dimensions, bytes, Cache-Control and every rule above that fails.
4. **Have a model judge it** when the card is generated from user content: a vision model scores legibility at thumbnail size and catches broken glyphs; include negative controls (a deliberately bad card) so a judge that says yes to everything is caught.
5. **Unit-test the fit**: random titles through the headline fitter never overflow the box and never go below the minimum size.
6. **Paste the link** in X (draft), iMessage, WhatsApp, Telegram, Slack and Discord once the page is live; re-scrape with the debuggers when a cached preview is stale.

## References

- `references/platform-specs.md` - every platform's documented limits, with sources and confidence (what is official, what is folklore).
- `references/satori-recipes.md` - the code: headline fitting, font loading, image inlining, never-fail data loading, the share button.
- `scripts/check-og.py` - production check of a page's OG tags and image across crawler user agents (stdlib only).
- `scripts/thumb-sheet.py` - phone-size legibility sheet of a card (needs Pillow).
