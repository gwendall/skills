#!/usr/bin/env python3
"""extras.py - The "richer life" feeds that are NOT dated events and therefore
do not fit the fetch_events.py engine (data_shape != dated-event):

  1. restos   - new addresses added to the Le Fooding guide (openings)
  2. cinema   - this week's cinema releases (AlloCiné)
  3. escapes  - weekend getaways from Paris via TGVmax €0 (SNCF Open Data)

All key-free. Best-effort: a source that errors is skipped, never a crash.

Usage:
    python3 extras.py                      # all 3 feeds, Markdown output
    python3 extras.py --only restos,cinema
    python3 extras.py --restos-days 21     # restaurants added in the last 21 days
    python3 extras.py --escape-date 2026-06-27   # target Saturday (def: next Saturday)
    python3 extras.py --json out.json
"""
import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
import urllib.parse

UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"


def http(url, timeout=30):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "fr-FR,fr;q=0.9"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def http_json(url, **kw):
    return json.loads(http(url, **kw))


def log(m):
    print(m, file=sys.stderr)


# --------------------------------------------------------------------------- #
# 1. Le Fooding - new addresses (openings) in Paris
# --------------------------------------------------------------------------- #
def restos(days=30, today=None):
    today = today or dt.date.today()
    cutoff = today - dt.timedelta(days=days)
    try:
        data = http_json("https://lefooding.com/wp-json/api/v1/fr/places/restaurant/index?page=1")
    except Exception as ex:
        log(f"  restos: skip ({type(ex).__name__})")
        return []
    posts = data.get("data") or data.get("posts") or data.get("results") or \
        (data if isinstance(data, list) else [])
    out = []
    for p in posts:
        cities = p.get("city") or []
        is_paris = any((c.get("slug") == "paris") for c in cities if isinstance(c, dict))
        if not is_paris:
            continue
        created = (p.get("createdAt") or "")[:10]
        try:
            cd = dt.date.fromisoformat(created)
        except ValueError:
            continue
        if cd < cutoff:
            continue
        addr = p.get("address") or {}
        out.append({"title": p.get("title"), "added": created,
                    "url": p.get("permalink"),
                    "price": (p.get("price") or {}).get("name"),
                    "address": addr.get("address") if isinstance(addr, dict) else None})
    out.sort(key=lambda x: x["added"], reverse=True)
    return out


# --------------------------------------------------------------------------- #
# 2. AlloCiné - this week's cinema releases
# --------------------------------------------------------------------------- #
def cinema(today=None):
    today = today or dt.date.today()
    wednesday = today - dt.timedelta(days=(today.weekday() - 2) % 7)
    url = f"https://www.allocine.fr/film/agenda/sem-{wednesday.isoformat()}/"
    try:
        h = http(url)
    except Exception as ex:
        log(f"  cinema: skip ({type(ex).__name__})")
        return []
    dates = re.findall(r'"releaseDate":"([^"]+)"', h)
    anchors = re.findall(r'<a class="meta-title-link" href="(/film/fichefilm_gen_cfilm=\d+\.html)">(.*?)</a>', h, re.S)
    out = []
    for i, (href, title) in enumerate(anchors):
        rd = dates[i][:10] if i < len(dates) else None
        out.append({"title": re.sub(r"<[^>]+>", "", title).strip(),
                    "release": rd, "url": "https://www.allocine.fr" + href})
    return out


# --------------------------------------------------------------------------- #
# 3. SNCF TGVmax - €0 weekend getaways departing from Paris
# --------------------------------------------------------------------------- #
def escapes(date=None, today=None):
    today = today or dt.date.today()
    if not date:
        date = today + dt.timedelta(days=(5 - today.weekday()) % 7)  # next Saturday
        if date == today:
            date = today + dt.timedelta(days=7)
    ds = date.isoformat() if isinstance(date, dt.date) else date
    where = (f"date=date'{ds}' AND od_happy_card='OUI' AND origine='PARIS (intramuros)'")
    params = {"where": where, "select": "destination,heure_depart,heure_arrivee,train_no",
              "order_by": "heure_depart", "limit": 100}
    url = ("https://data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/records?"
           + urllib.parse.urlencode(params))
    try:
        data = http_json(url)
    except Exception as ex:
        log(f"  escapes: skip ({type(ex).__name__})")
        return []
    seen, out = set(), []
    for r in data.get("results", []):
        dest = r.get("destination")
        if dest in seen:
            continue
        seen.add(dest)
        out.append({"destination": dest, "depart": r.get("heure_depart"),
                    "arrivee": r.get("heure_arrivee"), "train": r.get("train_no"),
                    "date": ds})
    return out


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--only", help="restos,cinema,escapes")
    ap.add_argument("--restos-days", type=int, default=30)
    ap.add_argument("--escape-date", help="YYYY-MM-DD (target Saturday)")
    ap.add_argument("--today", help="YYYY-MM-DD")
    ap.add_argument("--json", help="JSON output")
    args = ap.parse_args()
    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    want = set(filter(None, (args.only or "restos,cinema,escapes").split(",")))

    res = {}
    if "restos" in want:
        res["restos"] = restos(args.restos_days, today)
    if "cinema" in want:
        res["cinema"] = cinema(today)
    if "escapes" in want:
        ed = dt.date.fromisoformat(args.escape_date) if args.escape_date else None
        res["escapes"] = escapes(ed, today)

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump(res, f, ensure_ascii=False, indent=2)
        log(f"-> {args.json}")
        return

    if "restos" in res:
        print(f"\n## 🍽  New restaurants in Paris ({len(res['restos'])}, Le Fooding, {args.restos_days}d)")
        for r in res["restos"][:12]:
            price = f" · {r['price']}" if r.get("price") else ""
            print(f"- **{r['title']}** (added {r['added']}){price}\n  {r.get('address') or ''} · {r['url']}")
    if "cinema" in res:
        print(f"\n## 🎬  This week's cinema releases ({len(res['cinema'])}, AlloCiné)")
        for c in res["cinema"][:15]:
            print(f"- **{c['title']}** (release {c['release'] or '?'}) · {c['url']}")
    if "escapes" in res:
        e = res["escapes"]
        d = e[0]["date"] if e else "?"
        print(f"\n## 🚄  TGVmax €0 getaways from Paris on {d} ({len(e)} destinations)")
        for x in e[:15]:
            print(f"- **{x['destination']}** - departure {x['depart']}, arrival {x['arrivee']} (train {x['train']})")


if __name__ == "__main__":
    main()
