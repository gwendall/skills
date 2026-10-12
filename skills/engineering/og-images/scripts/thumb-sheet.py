#!/usr/bin/env python3
"""Show a card the way a phone shows it, to judge legibility before shipping.

Builds one sheet with: the 1200x630 card at 343 px wide (a link preview in a feed or a chat), its centre square
at 120 px (the compact thumbnail some apps cut), and, when given, the square card at 375 px (a post in a feed).
If the headline cannot be read on this sheet at 100 % zoom, it is too small.

Usage:
    thumb-sheet.py card-og.png [card-square.png] [-o sheet.png]

Needs Pillow (pip install pillow).
"""
import argparse
import sys

try:
    from PIL import Image
except ImportError:
    sys.exit("thumb-sheet.py needs Pillow: pip install pillow")

PAD = 24
CARD_W = 343
THUMB = 120
SQUARE_W = 375
BG = "#1c1c22"


def build(og_path, square_path=None):
    og = Image.open(og_path).convert("RGB")
    card = og.resize((CARD_W, round(CARD_W * og.height / og.width)), Image.LANCZOS)
    side = min(og.width, og.height)
    left = (og.width - side) // 2
    top = (og.height - side) // 2
    thumb = og.crop((left, top, left + side, top + side)).resize((THUMB, THUMB), Image.LANCZOS)
    tiles = []
    if square_path:
        sq = Image.open(square_path).convert("RGB")
        tiles.append(sq.resize((SQUARE_W, round(SQUARE_W * sq.height / sq.width)), Image.LANCZOS))
    tiles += [card, thumb]
    width = PAD + sum(t.width + PAD for t in tiles)
    height = PAD * 2 + max(t.height for t in tiles)
    sheet = Image.new("RGB", (width, height), BG)
    x = PAD
    for t in tiles:
        sheet.paste(t, (x, PAD))
        x += t.width + PAD
    return sheet


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("og")
    ap.add_argument("square", nargs="?")
    ap.add_argument("-o", "--out", default="thumb-sheet.png")
    args = ap.parse_args()
    build(args.og, args.square).save(args.out)
    print(args.out)


if __name__ == "__main__":
    main()
