# Satori / next/og recipes

Each recipe is the version that survived production. Adapt names; keep the shape.

## 1. Fit a headline before rendering

Satori never shrinks text. Choose the size and the line breaks from the font's advance widths.

Get the advance widths once (Python, fontTools):

```python
from fontTools.ttLib import TTFont
f = TTFont('Display.ttf'); upm = f['head'].unitsPerEm; cmap = f.getBestCmap(); hm = f['hmtx']
print({c: round(hm[cmap[ord(c)]][0] * 1000 / upm) for c in "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 %#'!?.,&-:/"})
```

Then fit (TypeScript, no dependency):

```ts
/** Advance widths per 1000 units of font size, measured from the TTF. A monospaced font is one constant. */
const ADVANCE: Record<string, number> = { /* paste the table */ };
const FALLBACK = 1000; // a glyph missing from the table counts as the widest, so a fitted line never overflows

export function textWidth(text: string, fontSize: number): number {
  return ([...text].reduce((sum, c) => sum + (ADVANCE[c] ?? FALLBACK), 0) / 1000) * fontSize;
}

export type Box = { maxWidth: number; maxHeight: number; maxLines: number; maxSize: number; minSize: number; lineHeight: number; grid?: number };

function splits(words: string[], count: number): string[][] {
  if (count === 1) return [[words.join(' ')]];
  const out: string[][] = [];
  for (let cut = 1; cut <= words.length - count + 1; cut++)
    for (const rest of splits(words.slice(cut), count - 1)) out.push([words.slice(0, cut).join(' '), ...rest]);
  return out;
}

/** The largest size the text reaches inside the box, and its lines at that size (fewer lines on a tie). */
export function fitHeadline(text: string, box: Box): { lines: string[]; fontSize: number } {
  const words = text.trim().split(/\s+/).filter(Boolean);
  let best = { lines: [words.join(' ')], fontSize: 0 };
  for (let count = 1; count <= Math.min(box.maxLines, words.length); count++) {
    const heightCap = box.maxHeight / (count * box.lineHeight);
    for (const lines of splits(words, count)) {
      const widest = Math.max(...lines.map(l => textWidth(l, 1)));
      let size = Math.min(box.maxSize, heightCap, box.maxWidth / widest);
      size = box.grid ? Math.floor(size / box.grid) * box.grid : Math.floor(size); // pixel fonts: snap to the grid
      if (size > best.fontSize) best = { lines, fontSize: size };
    }
  }
  return { lines: best.lines, fontSize: Math.max(box.minSize, best.fontSize) };
}
```

Render one `div` per line with `whiteSpace: 'nowrap'`, so Satori never re-wraps what you fitted. A single word longer than the box at `minSize` still overflows: truncate the input upstream (a nickname, a title) rather than shrinking below the floor.

Alternative when a font table is impractical: render candidate sizes with sharp, trim the ink, keep the largest that fits (slower, exact for any font).

## 2. Fonts, read from the repo

```ts
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';

const FONT_DIR = join(process.cwd(), /* turbopackIgnore: true */ 'src/app/og/fonts');
let cached: Promise<{ name: string; data: Buffer; weight: 400 | 700; style: 'normal' }[]> | undefined;

export function cardFonts() {
  cached ??= Promise.all([
    readFile(join(FONT_DIR, 'Display.ttf')).then(data => ({ name: 'Display', data, weight: 400 as const, style: 'normal' as const })),
    readFile(join(FONT_DIR, 'Text-Regular.ttf')).then(data => ({ name: 'Text', data, weight: 400 as const, style: 'normal' as const })),
  ]);
  return cached;
}
```

```ts
// next.config.ts - ship the fonts with the routes that read them, and only them
outputFileTracingIncludes: { '/thing/[id]/opengraph-image': ['./src/app/og/fonts/**'] },
```

## 3. Images as bytes, never as a URL the renderer must reach

```ts
async function asDataUrl(url: string, timeoutMs = 2500): Promise<string | null> {
  try {
    const res = await fetch(url, { signal: AbortSignal.timeout(timeoutMs) });
    if (!res.ok) return null;
    const type = res.headers.get('content-type') ?? '';
    if (!/^image\/(png|jpeg)$/.test(type)) return null; // Satori: PNG or JPEG only
    return `data:${type};base64,${Buffer.from(await res.arrayBuffer()).toString('base64')}`;
  } catch {
    return null;
  }
}
```

For private storage, fetch with the server key or a short signed URL, still inside this helper. For WebP sources, convert with sharp first.

## 4. Never fail: a generic card on any problem

```tsx
export default async function Image({ params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const thing = await loadThing(id).catch(() => null);           // time-boxed inside
  if (!thing || !thing.isPublic) return genericCard();           // privacy gate = the page's gate
  const photo = await asDataUrl(thing.photoUrl);
  if (!photo) return genericCard();
  return new ImageResponse(<Card thing={thing} photo={photo} format="og" />, { ...size, fonts: await cardFonts() });
}
```

## 5. Conditional styles

```tsx
// Satori throws on a key whose value is undefined: absent means no key.
<div style={{ display: 'flex', color, ...(shadow ? { textShadow: shadow } : {}) }}>{`${pct}% match`}</div>
```

## 6. A file route for the square card (Share button)

```ts
// app/thing/[id]/card/route.tsx
export async function GET(req: Request, { params }: { params: Promise<{ id: string }> }) {
  const { id } = await params;
  const format = new URL(req.url).searchParams.get('format') === 'og' ? 'og' : 'square';
  const res = new ImageResponse(<Card ... format={format} />, { ...SIZES[format], fonts: await cardFonts() });
  res.headers.set('Cache-Control', 'public, max-age=300, s-maxage=86400');
  res.headers.set('Content-Disposition', `inline; filename="thing-${id}.png"`);
  return res;
}
```

## 7. Share button

```tsx
'use client';
const fileRef = useRef<File | null>(null);

useEffect(() => { // fetch before the tap: share() must run inside the click's user activation
  fetch(`/thing/${id}/card?format=square`).then(r => r.blob())
    .then(b => { fileRef.current = new File([b], `thing-${id}.png`, { type: 'image/png' }); })
    .catch(() => {});
}, [id]);

async function shareCard() {
  const file = fileRef.current;
  if (file && navigator.canShare?.({ files: [file] })) {
    try { await navigator.share({ files: [file] }); return; }
    catch (e) { if ((e as Error).name === 'AbortError') return; } // the user closed the sheet
  }
  openFallbackSheet(); // download link, copy link, X intent
}
```

The link variant shares `{ url }` only (not `text` plus `url`, see the iOS bug) and relies on the OG card for the picture.

## 8. Test the page the way a crawler does

```bash
curl -sA 'facebookexternalhit/1.1' https://example.com/thing/1 | grep -o '<meta[^>]*og:image[^>]*>'
curl -sIA 'Twitterbot/1.0' "$(the og:image URL)"   # 200, content-type image/png, one cache-control
```

Or run `scripts/check-og.py`, which does both for several bots and checks the size and bytes.
