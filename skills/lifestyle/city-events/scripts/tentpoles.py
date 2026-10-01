#!/usr/bin/env python3
"""tentpoles.py - The calendar of the BIG dates (art fairs, biennials,
design/fashion shows, gaming/esport cons, major AI/tech confs, festivals).

Horizon = months in advance (not "this week"), multi-city, with a
`paris` vs `worth-travel` flag: to plan around Art Basel, Frieze, Gamescom,
GDC, NeurIPS... Many of these events have a near-fixed annual date -> a
CURATED LIST re-verified periodically is more reliable than a fragile scrape
(see references/sources-paris.md). The --artsy flag enriches art fairs live
via the public Artsy API (Metaphysics GraphQL, key-free).

Usage:
    python3 tentpoles.py                          # next 180 days, all
    python3 tentpoles.py --horizon-days 365
    python3 tentpoles.py --where paris            # paris | travel | all (def all)
    python3 tentpoles.py --artsy                  # + live refresh of art fairs
    python3 tentpoles.py --json out.json --md out.md

The TENTPOLES list below is verified as of 2026-06-24. Re-verify ~every
quarter (the N+1 editions get firmed up over the year).
"""
import argparse
import datetime as dt
import json
import os
import subprocess
import sys
import urllib.request


# (name, category, start, end, city, tier, paris|worth-travel|both, url, dates_text)
TENTPOLES = [
    # --- Art fairs & biennials ---
    ("Art Basel Paris", "art-fair", "2026-10-23", "2026-10-25", "Paris (Grand Palais)", "vip", "paris", "https://www.artbasel.com/paris", "23-25 Oct 2026 (preview 21-22)"),
    ("Paris Photo", "art-fair", "2026-11-12", "2026-11-15", "Paris (Grand Palais)", "mainstream", "paris", "https://www.parisphoto.com", "12-15 Nov 2026"),
    ("Fine Arts Paris", "art-fair", "2026-09-19", "2026-09-23", "Paris", "mainstream", "paris", "https://www.fineartsparis.com", "19-23 Sep 2026"),
    ("Art Basel in Basel", "art-fair", "2027-06-17", "2027-06-20", "Basel (Messe Basel)", "vip", "worth-travel", "https://www.artbasel.com/basel", "17-20 Jun 2027 (preview 15-16)"),
    ("Art Basel Hong Kong", "art-fair", "2027-03-25", "2027-03-27", "Hong Kong (HKCEC)", "vip", "worth-travel", "https://www.artbasel.com/hong-kong", "25-27 Mar 2027"),
    ("Art Basel Qatar", "art-fair", "2027-01-28", "2027-01-30", "Doha", "vip", "worth-travel", "https://www.artbasel.com/qatar", "28-30 Jan 2027"),
    ("Art Basel Miami Beach", "art-fair", "2026-12-04", "2026-12-06", "Miami Beach", "vip", "worth-travel", "https://www.artbasel.com/miami-beach", "4-6 Dec 2026"),
    ("Frieze London + Masters", "art-fair", "2026-10-14", "2026-10-18", "London (Regent's Park)", "mainstream", "worth-travel", "https://www.frieze.com/fairs", "14-18 Oct 2026"),
    ("Frieze Seoul", "art-fair", "2026-09-02", "2026-09-05", "Seoul (COEX)", "mainstream", "worth-travel", "https://www.frieze.com/fairs/frieze-seoul", "2-5 Sep 2026"),
    ("Frieze Los Angeles", "art-fair", "2027-02-25", "2027-02-28", "Los Angeles", "mainstream", "worth-travel", "https://www.frieze.com/fairs/frieze-los-angeles", "~25-28 Feb 2027"),
    ("Frieze New York", "art-fair", "2027-05-12", "2027-05-16", "New York (The Shed)", "mainstream", "worth-travel", "https://www.frieze.com/fairs/frieze-new-york", "~12-16 May 2027"),
    ("The Armory Show", "art-fair", "2026-09-24", "2026-09-27", "New York (Javits)", "mainstream", "worth-travel", "https://www.thearmoryshow.com", "24-27 Sep 2026"),
    ("TEFAF Maastricht", "art-fair", "2027-03-13", "2027-03-18", "Maastricht (MECC)", "mainstream", "worth-travel", "https://www.tefaf.com/fairs/tefaf-maastricht", "13-18 Mar 2027 (preview 11-12)"),
    ("TEFAF New York", "art-fair", "2027-05-14", "2027-05-18", "New York (Park Ave Armory)", "mainstream", "worth-travel", "https://www.tefaf.com/fairs/tefaf-new-york", "14-18 May 2027"),
    ("Biennale di Venezia - Arte", "biennial", "2026-05-09", "2026-11-22", "Venice (Giardini + Arsenale)", "mainstream", "worth-travel", "https://www.labiennale.org/en/art/2026", "9 May - 22 Nov 2026 (ongoing)"),
    ("documenta 16", "biennial", "2027-06-12", "2027-09-19", "Kassel", "vip", "worth-travel", "https://documenta.de", "12 Jun - 19 Sep 2027"),
    ("Les Rencontres d'Arles", "art-fair", "2026-07-06", "2026-10-04", "Arles", "mainstream", "worth-travel", "https://www.rencontres-arles.com", "6 Jul - 4 Oct 2026 (Opening Week 6-12 Jul)"),
    # --- Design / Fashion ---
    ("Paris Design Week", "design", "2026-09-10", "2026-09-19", "Paris (city-wide)", "mainstream", "paris", "https://www.maison-objet.com/en/paris-design-week", "10-19 Sep 2026"),
    ("Maison&Objet", "design", "2027-01-14", "2027-01-18", "Paris Nord Villepinte", "mainstream", "paris", "https://www.maison-objet.com", "14-18 Jan 2027"),
    ("Salone del Mobile (Milan Design Week)", "design", "2027-04-13", "2027-04-18", "Milan", "mainstream", "worth-travel", "https://www.salonemilano.it", "13-18 Apr 2027"),
    # --- Gaming / Esports ---
    ("gamescom", "gaming-con", "2026-08-26", "2026-08-30", "Cologne (Koelnmesse)", "mainstream", "worth-travel", "https://www.gamescom.global/en", "26-30 Aug 2026 (ONL 25 Aug)"),
    ("Tokyo Game Show", "gaming-con", "2026-09-17", "2026-09-21", "Chiba/Tokyo (Makuhari Messe)", "mainstream", "worth-travel", "https://expo.tgs.jp", "17-21 Sep 2026"),
    ("Paris Games Week", "gaming-con", "2026-10-22", "2026-10-25", "Paris Expo Porte de Versailles", "mainstream", "paris", "https://www.parisgamesweek.com/fr", "22-25 Oct 2026"),
    ("GDC (Game Developers Conf)", "gaming-con", "2027-03-01", "2027-03-05", "San Francisco (Moscone)", "mainstream", "worth-travel", "https://gdconf.com", "1-5 Mar 2027"),
    ("EGX @ MCM London Comic Con", "gaming-con", "2026-10-23", "2026-10-25", "London (ExCeL)", "mainstream", "worth-travel", "https://www.egx.net", "23-25 Oct 2026"),
    # --- Tech / AI confs ---
    ("VivaTech", "tech-conf", "2026-06-17", "2026-06-20", "Paris Expo Porte de Versailles", "mainstream", "paris", "https://vivatech.com", "17-20 Jun 2026 (public Sat 20)"),
    ("SIGGRAPH 2026", "tech-conf", "2026-07-19", "2026-07-23", "Los Angeles (LACC)", "niche", "worth-travel", "https://www.siggraph.org", "19-23 Jul 2026"),
    ("Ars Electronica Festival", "tech-conf", "2026-09-09", "2026-09-13", "Linz (city-wide)", "cool", "worth-travel", "https://ars.electronica.art/festival/en/", "9-13 Sep 2026"),
    ("Web Summit", "tech-conf", "2026-11-09", "2026-11-12", "Lisbon (MEO Arena)", "mainstream", "worth-travel", "https://websummit.com", "9-12 Nov 2026"),
    ("NeurIPS 2026 (Paris satellite)", "ai-conf", "2026-12-06", "2026-12-12", "Sydney + Atlanta & Paris satellites", "niche", "both", "https://neurips.cc", "6-12 Dec 2026 (Paris satellite TBC)"),
    ("CES", "tech-conf", "2027-01-06", "2027-01-09", "Las Vegas (LVCC)", "mainstream", "worth-travel", "https://www.ces.tech", "6-9 Jan 2027"),
    ("SXSW", "tech-conf", "2027-03-15", "2027-03-21", "Austin, Texas", "mainstream", "worth-travel", "https://sxsw.com", "15-21 Mar 2027"),
    ("SIGGRAPH 2027", "tech-conf", "2027-08-08", "2027-08-12", "Anaheim (ACC)", "niche", "worth-travel", "https://www.siggraph.org", "8-12 Aug 2027"),
    # --- Film / Culture ---
    ("Festival de Cannes", "film-festival", "2027-05-11", "2027-05-22", "Cannes (Palais des Festivals)", "vip", "worth-travel", "https://www.festival-cannes.com/en/", "11-22 May 2027 (80th ed.)"),
]


def http_post_json(url, payload, timeout=30):
    req = urllib.request.Request(
        url, data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8", "replace"))


def artsy_fairs(horizon_end):
    """Live refresh of art fairs via Artsy Metaphysics (GraphQL, key-free).
    The city is not exposed cleanly -> inferred from the name."""
    q = "{ fairs(sort: START_AT_ASC, size: 40) { name startAt endAt } }"
    try:
        data = http_post_json("https://metaphysics-production.artsy.net/v2", {"query": q})
    except Exception as ex:
        print(f"  artsy: skip ({type(ex).__name__})", file=sys.stderr)
        return []
    out = []
    for f in (((data.get("data") or {}).get("fairs")) or []):
        sa, ea = (f.get("startAt") or "")[:10], (f.get("endAt") or "")[:10]
        if not sa:
            continue
        name = f.get("name") or ""
        city = "Paris" if "paris" in name.lower() else "?"
        loc = "paris" if city == "Paris" else "worth-travel"
        out.append((name, "art-fair", sa, ea or sa, city, "mainstream", loc,
                    "https://www.artsy.net/art-fairs", f"{sa} -> {ea}"))
    return out


def side_events(name_query, today):
    """Drill-down: find the tentpole, and for a PARIS tentpole, run the weekly
    engine over its window (start-2d -> end+1d) to surface the side-events
    (openings, parties, side-confs). The feeds (Luma/RA/Shotgun) only fill up
    at T-2/4 weeks: sparse far from the date, rich as it approaches."""
    q = name_query.lower()
    match = next((t for t in TENTPOLES if q in t[0].lower()), None)
    if not match:
        print(f"No tentpole matches '{name_query}'. Try: "
              + ", ".join(sorted({t[0] for t in TENTPOLES})[:8]) + "...", file=sys.stderr)
        return
    name, cat, start, end, city, tier, loc, url, dates_text = match
    s = (dt.date.fromisoformat(start) - dt.timedelta(days=2)).isoformat()
    e = (dt.date.fromisoformat(end) + dt.timedelta(days=1)).isoformat()
    weeks_out = (dt.date.fromisoformat(start) - today).days // 7
    print(f"# Side-events of {name} ({dates_text}) - {city}")
    print(f"Scanned window: {s} -> {e}  (T-{weeks_out} weeks)\n")
    if loc not in ("paris", "both"):
        print(f"Tentpole outside Paris ({city}). Side-events need that city's sources "
              f"(multi-city roadmap) or the event's official Luma calendar. "
              f"Pull it manually for now.")
        return
    fetch = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fetch_events.py")
    tmp = os.path.join(os.path.dirname(os.path.abspath(__file__)), ".side.json")
    try:
        subprocess.run([sys.executable, fetch, "--city", "paris", "--start", s,
                        "--end", e, "--json", tmp], check=True, capture_output=True, timeout=180)
        with open(tmp) as f:
            d = json.load(f)
        os.remove(tmp)
    except Exception as ex:
        print(f"(pull failed: {ex})", file=sys.stderr)
        return
    evs = d.get("events", [])
    print(f"{len(evs)} side-events found ({d['counts'].get('sources_active')} active sources).")
    if weeks_out > 4:
        print(f">> Still far out (T-{weeks_out}w): parties/openings are published "
              f"mostly at T-2/4 weeks. Re-run this drill-down toward late "
              f"{dt.date.fromisoformat(start) - dt.timedelta(weeks=3):%b}.")
    print()
    for e2 in evs[:20]:
        when = (e2.get("start") or "")[:10]
        print(f"  [{e2.get('score')}|{e2.get('source_tier')}] {when} "
              f"{(e2.get('title') or '')[:48]:48} <{','.join(e2.get('sources') or [])[:16]}>")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--horizon-days", type=int, default=180)
    ap.add_argument("--where", choices=["paris", "travel", "all"], default="all")
    ap.add_argument("--today", help="YYYY-MM-DD (simulate today)")
    ap.add_argument("--artsy", action="store_true", help="live refresh of art fairs (Artsy)")
    ap.add_argument("--side-events", dest="side", help="drill-down side-events of a tentpole (name)")
    ap.add_argument("--json", help="JSON output")
    ap.add_argument("--md", help="Markdown output")
    args = ap.parse_args()

    if args.side:
        side_events(args.side, dt.date.fromisoformat(args.today) if args.today else dt.date.today())
        return

    today = dt.date.fromisoformat(args.today) if args.today else dt.date.today()
    horizon = today + dt.timedelta(days=args.horizon_days)

    rows = list(TENTPOLES)
    if args.artsy:
        seen_names = {r[0].lower()[:12] for r in rows}
        for a in artsy_fairs(horizon):
            if a[0].lower()[:12] not in seen_names:
                rows.append(a)

    items = []
    for name, cat, start, end, city, tier, loc, url, dates_text in rows:
        sd = dt.date.fromisoformat(start)
        ed = dt.date.fromisoformat(end)
        upcoming = today <= sd <= horizon
        ongoing = sd <= today <= ed
        if not (upcoming or ongoing):
            continue
        if args.where == "paris" and loc not in ("paris", "both"):
            continue
        if args.where == "travel" and loc not in ("worth-travel", "both"):
            continue
        items.append({"name": name, "category": cat, "start": start, "end": end,
                      "city": city, "tier": tier, "where": loc, "url": url,
                      "dates_text": dates_text, "status": "ongoing" if ongoing else "upcoming",
                      "days_until": (sd - today).days})
    items.sort(key=lambda x: x["start"])

    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            json.dump({"today": today.isoformat(), "horizon_days": args.horizon_days,
                       "count": len(items), "tentpoles": items}, f, ensure_ascii=False, indent=2)

    md = _to_md(items, today, args.horizon_days)
    if args.md:
        with open(args.md, "w", encoding="utf-8") as f:
            f.write(md)
    if not args.json and not args.md:
        print(md)
    print(f"{len(items)} tentpoles over {args.horizon_days}d", file=sys.stderr)


EMOJI = {"paris": "📍", "worth-travel": "✈️", "both": "📍✈️"}
CAT_LABEL = {"art-fair": "Art fair", "biennial": "Biennial", "design": "Design/Fashion",
             "gaming-con": "Gaming/Esport", "tech-conf": "Tech/AI", "ai-conf": "AI",
             "film-festival": "Film"}


def _to_md(items, today, horizon_days):
    lines = [f"# Tentpoles - next {horizon_days} days (from {today.isoformat()})", ""]
    for it in items:
        em = EMOJI.get(it["where"], "")
        cat = CAT_LABEL.get(it["category"], it["category"])
        tag = "🔒" if it["tier"] == "vip" else ("🎯" if it["tier"] == "cool" else "")
        when = it["dates_text"]
        cd = f" · D-{it['days_until']}" if it["status"] == "upcoming" and it["days_until"] >= 0 else " · ongoing"
        lines.append(f"- {em} **{it['name']}** {tag} ({cat}) - {when}{cd}")
        lines.append(f"  {it['city']} · {it['url']}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
