#!/usr/bin/env python3
"""Check a page's link preview the way the crawlers see it.

For each preview bot user agent: fetch the page HTML (no JavaScript, like the bots), read the OG and Twitter
tags from the first megabyte, fetch the image they point to, and report status, content type, dimensions,
bytes and Cache-Control against the limits every platform shares. Stdlib only.

Usage:
    check-og.py https://example.com/page [--bots facebook,twitter,...] [--json]

Exit code 1 when any error is found, 0 otherwise (warnings do not fail).
"""
import argparse
import json
import struct
import sys
import urllib.error
import urllib.parse
import urllib.request
from html.parser import HTMLParser

BOTS = {
    "facebook": "facebookexternalhit/1.1 (+http://www.facebook.com/externalhit_uatext.php)",
    "twitter": "Twitterbot/1.0",
    "telegram": "TelegramBot (like TwitterBot)",
    "whatsapp": "WhatsApp/2.23.20.0",
    "slack": "Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)",
    "discord": "Mozilla/5.0 (compatible; Discordbot/2.0; +https://discordapp.com)",
    "linkedin": "LinkedInBot/1.0 (compatible; Mozilla/5.0; Apache-HttpClient +http://www.linkedin.com)",
    "imessage": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_11_1) AppleWebKit/601.2.4 (KHTML, like Gecko) Version/9.0.1 Safari/601.2.4 facebookexternalhit/1.1 Facebot Twitterbot/1.0",
}
HTML_LIMIT = 1_000_000          # Facebook and iMessage stop reading the page here
BYTES_ERROR = 600_000           # WhatsApp's documented limit
BYTES_WARN = 300_000            # the safe target
TARGET = (1200, 630)
OK_TYPES = ("image/png", "image/jpeg")
TIMEOUT = 15


class MetaParser(HTMLParser):
    """Collects <meta property|name=... content=...> in document order, with the byte-ish offset of each."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.tags = []

    def handle_starttag(self, tag, attrs):
        if tag != "meta":
            return
        a = dict(attrs)
        key = a.get("property") or a.get("name")
        if key and "content" in a:
            self.tags.append((key.strip().lower(), (a.get("content") or "").strip(), self.getpos()))


def parse_meta(html):
    p = MetaParser()
    p.feed(html)
    meta = {}
    for key, value, _ in p.tags:
        meta.setdefault(key, value)  # the first occurrence wins, as for the crawlers
    return meta


def image_size(data):
    """(width, height, kind) from the first bytes of a PNG, JPEG, GIF or WebP; None when unknown."""
    if data[:8] == b"\x89PNG\r\n\x1a\n" and len(data) >= 24:
        w, h = struct.unpack(">II", data[16:24])
        return w, h, "png"
    if data[:6] in (b"GIF87a", b"GIF89a") and len(data) >= 10:
        w, h = struct.unpack("<HH", data[6:10])
        return w, h, "gif"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        chunk = data[12:16]
        if chunk == b"VP8X" and len(data) >= 30:
            w = 1 + int.from_bytes(data[24:27], "little")
            h = 1 + int.from_bytes(data[27:30], "little")
            return w, h, "webp"
        if chunk == b"VP8 " and len(data) >= 30:
            w, h = struct.unpack("<HH", data[26:30])
            return w & 0x3FFF, h & 0x3FFF, "webp"
        if chunk == b"VP8L" and len(data) >= 25:
            b = data[21:25]
            w = 1 + (((b[1] & 0x3F) << 8) | b[0])
            h = 1 + (((b[3] & 0x0F) << 10) | (b[2] << 2) | ((b[1] & 0xC0) >> 6))
            return w, h, "webp"
    if data[:2] == b"\xff\xd8":
        i = 2
        while i + 9 < len(data):
            if data[i] != 0xFF:
                i += 1
                continue
            marker = data[i + 1]
            if marker in (0xD8, 0x01) or 0xD0 <= marker <= 0xD7:
                i += 2
                continue
            length = struct.unpack(">H", data[i + 2:i + 4])[0]
            if marker in (0xC0, 0xC1, 0xC2, 0xC3, 0xC5, 0xC6, 0xC7, 0xC9, 0xCA, 0xCB, 0xCD, 0xCE, 0xCF):
                h, w = struct.unpack(">HH", data[i + 5:i + 9])
                return w, h, "jpeg"
            i += 2 + length
    return None


def fetch(url, ua, limit=None):
    req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "*/*"})
    try:
        with urllib.request.urlopen(req, timeout=TIMEOUT) as res:
            body = res.read(limit) if limit else res.read()
            return res.status, res.geturl(), res.headers, body
    except urllib.error.HTTPError as e:
        return e.code, url, e.headers, e.read(limit or 65536)


def check_page_meta(page_url, meta, html_bytes, findings):
    def err(msg):
        findings.append(("error", msg))

    def warn(msg):
        findings.append(("warn", msg))

    image = meta.get("og:image") or meta.get("og:image:url") or meta.get("og:image:secure_url")
    if not image:
        err("no og:image in the server HTML (client-side tags are invisible to crawlers)")
    elif not urllib.parse.urlparse(image).scheme:
        err(f"og:image is relative ({image}): crawlers need an absolute https URL (set metadataBase)")
    else:
        host = urllib.parse.urlparse(image).hostname or ""
        if not image.startswith("https://"):
            warn(f"og:image is not https: {image}")
        if host in ("localhost", "127.0.0.1") or host.endswith(".local"):
            err(f"og:image points to a local host ({host}): verify on the production domain")
        if host.endswith(".vercel.app"):
            warn(f"og:image is on {host}: a protected preview deployment answers 401 to bots; use the canonical origin")
    if meta.get("twitter:card") != "summary_large_image":
        warn(f"twitter:card is {meta.get('twitter:card')!r}, not 'summary_large_image' (X and Discord show a small thumbnail)")
    for key in ("og:title", "og:url", "og:image:alt", "og:image:width", "og:image:height"):
        if key not in meta:
            warn(f"missing {key}")
    if image:
        pos = html_bytes.find(b"og:image")
        if pos > HTML_LIMIT:
            err(f"og:image tag starts at byte {pos}, past the first megabyte Facebook and iMessage read")
    return image


def check_image(url, ua, meta, findings):
    def err(msg):
        findings.append(("error", msg))

    def warn(msg):
        findings.append(("warn", msg))

    status, final, headers, body = fetch(url, ua)
    info = {"url": url, "final_url": final, "status": status, "bytes": len(body),
            "content_type": headers.get("Content-Type", ""), "cache_control": headers.get_all("Cache-Control") or []}
    size = image_size(body[:65536])
    info["size"] = size
    if status != 200:
        err(f"image answers {status}: a crawler caches that as 'no preview'")
        return info
    ctype = info["content_type"].split(";")[0].strip().lower()
    if ctype not in OK_TYPES:
        warn(f"image content-type is {ctype!r}: PNG or JPEG render everywhere")
    if len(body) > BYTES_ERROR:
        err(f"image is {len(body) // 1000} KB: WhatsApp drops images over 600 KB")
    elif len(body) > BYTES_WARN:
        warn(f"image is {len(body) // 1000} KB: aim under 300 KB")
    if size:
        w, h, kind = size
        if (w, h) != TARGET:
            ratio = w / h if h else 0
            level = err if (w < 600 or abs(ratio - 1.91) > 0.2) else warn
            level(f"image is {w}x{h} ({kind}); expected 1200x630")
        if abs((w / h) - 1) < 0.06:
            err("image is near square: Signal and others draw it as an icon")
        try:
            dw, dh = int(meta.get("og:image:width", w)), int(meta.get("og:image:height", h))
            if (dw, dh) != (w, h):
                warn(f"og:image:width/height say {dw}x{dh}, the file is {w}x{h}")
        except ValueError:
            warn("og:image:width/height are not integers")
    else:
        warn("could not read the image dimensions")
    if len(info["cache_control"]) > 1:
        warn(f"{len(info['cache_control'])} Cache-Control headers: set it once (headers.set, not a spread)")
    return info


def run(url, bots):
    report = {"url": url, "bots": {}}
    worst = 0
    for name in bots:
        ua = BOTS[name]
        findings = []
        status, final, headers, body = fetch(url, ua, limit=HTML_LIMIT + 1)
        entry = {"status": status, "final_url": final}
        if status != 200:
            findings.append(("error", f"page answers {status} to this bot (bot protection, auth or a challenge?)"))
        else:
            html = body.decode(headers.get_content_charset() or "utf-8", errors="replace")
            meta = parse_meta(html)
            entry["meta"] = {k: v for k, v in meta.items() if k.startswith(("og:", "twitter:"))}
            image = check_page_meta(url, meta, body, findings)
            if image and urllib.parse.urlparse(image).scheme:
                entry["image"] = check_image(image, ua, meta, findings)
            tw = meta.get("twitter:image")
            if tw and tw != image and urllib.parse.urlparse(tw).scheme:
                entry["twitter_image"] = check_image(tw, ua, meta, findings)
        entry["findings"] = findings
        worst = max([worst] + [2 if lvl == "error" else 1 for lvl, _ in findings])
        report["bots"][name] = entry
    return report, worst


def print_report(report):
    print(f"\n{report['url']}")
    for name, entry in report["bots"].items():
        img = entry.get("image") or {}
        size = img.get("size")
        dims = f"{size[0]}x{size[1]} {size[2]}" if size else "?"
        line = f"  {name:9} page {entry['status']}"
        if img:
            line += f" | image {img['status']} {dims} {img['bytes'] // 1000} KB {img['content_type']}"
        print(line)
        for level, msg in entry["findings"]:
            print(f"      {'ERROR' if level == 'error' else 'warn '} {msg}")
    first = next(iter(report["bots"].values()), {})
    meta = first.get("meta") or {}
    if meta:
        print("\n  tags (first bot):")
        for k in sorted(meta):
            print(f"    {k} = {meta[k]}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("url")
    ap.add_argument("--bots", default=",".join(BOTS), help=f"comma list among {', '.join(BOTS)}")
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    bots = [b.strip() for b in args.bots.split(",") if b.strip()]
    unknown = [b for b in bots if b not in BOTS]
    if unknown:
        ap.error(f"unknown bot(s): {', '.join(unknown)}")
    report, worst = run(args.url, bots)
    if args.json:
        print(json.dumps(report, indent=2, default=list))
    else:
        print_report(report)
    sys.exit(1 if worst >= 2 else 0)


if __name__ == "__main__":
    main()
