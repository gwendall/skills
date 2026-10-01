#!/usr/bin/env python3
"""render_html.py - Standalone HTML page (single file, inline CSS+JS, no
dependency, no framework) built from the JSON outputs of fetch_events.py,
tentpoles.py and extras.py.

View: the week's events GROUPED BY DAY/TIME, type chips, type FILTER
(vanilla JS), thumbnails when a cover is available. + Upcoming / Extras sections.

    python3 fetch_events.py --city paris --json /tmp/ev.json
    python3 tentpoles.py --json /tmp/tp.json
    python3 extras.py --json /tmp/ex.json
    python3 render_html.py --events /tmp/ev.json --tentpoles /tmp/tp.json \
        --extras /tmp/ex.json --out /tmp/digest.html
"""
import argparse
import datetime as dt
import html
import json

DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
MONTHS = ["", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

TIER = {"vip": ("VIP", "#b388ff"), "cool": ("cool", "#40c4ff"),
        "niche": ("niche", "#69f0ae"), "mainstream": ("mainstream", "#9aa4b2")}

# (key, label, color, matching tag keywords)
TYPE_DEF = [
    ("nightlife", "Nightlife", "#ff4081", {"clubbing", "techno", "house", "rave", "nightlife", "party", "electronic", "underground"}),
    ("concert", "Concerts", "#ff9100", {"concert", "live", "jazz", "gig", "live-music"}),
    ("art", "Art & exhibitions", "#b388ff", {"art", "expo", "exposition", "vernissage", "galerie", "exhibition", "art-contemporain", "photo", "sculpture", "installation", "fashion", "mode", "performance"}),
    ("design", "Design", "#00bfa5", {"design"}),
    ("tech", "Tech & AI", "#40c4ff", {"tech", "ai", "ml", "llm", "web3", "crypto", "blockchain", "startup", "dev", "data", "product", "deeptech", "agents", "genai"}),
    ("gaming", "Gaming", "#69f0ae", {"gaming", "esport", "esports", "gamedev", "jeu-video", "smash", "tekken", "arcade", "unreal", "real-time-3d"}),
    ("food", "Food", "#ffd54f", {"food", "brunch", "wine-tasting", "vin", "gastro", "supper", "apéro", "dégustation", "restaurant"}),
    ("cinema", "Film", "#80d8ff", {"cinema", "cinéma", "film", "cine-club", "arthouse", "avant-premiere"}),
    ("talk", "Talks & confs", "#7c4dff", {"talk", "conference", "conférence", "meetup", "workshop", "networking", "demo-night", "hackathon", "talks"}),
    ("scene", "Culture", "#90a4ae", {"theatre", "théâtre", "danse", "dance", "festival", "spectacle", "opera", "opéra", "culture", "atelier"}),
]
TYPE_LABEL = {k: lab for k, lab, _, _ in TYPE_DEF}
TYPE_COLOR = {k: c for k, _, c, _ in TYPE_DEF}
SOURCE_TYPE = {"resident-advisor": "nightlife", "shotgun": "nightlife", "dice": "concert",
               "cines-indes": "cinema", "slash-paris": "art", "palais-de-tokyo": "art",
               "afjv": "gaming", "level-up-unreal": "gaming", "game-dev-idf": "gaming",
               "start.gg": "gaming", "eventbrite-food": "food"}


def load(path):
    if not path:
        return None
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def esc(s):
    return html.escape(str(s)) if s is not None else ""


def classify(e):
    tags = set(e.get("tags") or [])
    found = [k for k, _, _, kws in TYPE_DEF if tags & kws]
    st = SOURCE_TYPE.get(e.get("source"))
    if st and st not in found:
        found.insert(0, st)
    for src in (e.get("sources") or []):
        st = SOURCE_TYPE.get(src)
        if st and st not in found:
            found.append(st)
    return found or ["scene"]


def parse_dt(iso):
    try:
        return dt.datetime.fromisoformat((iso or "").replace("Z", "+00:00"))
    except Exception:
        return None


def card(e):
    types = classify(e)
    label, color = TIER.get(e.get("source_tier"), ("", "#888"))
    d = parse_dt(e.get("start"))
    hhmm = f"{d:%H:%M}" if d else ""
    title = esc(e.get("title") or "(untitled)")
    url = e.get("url")
    title_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{title}</a>' if url else title
    venue = esc(e.get("venue") or "")
    cover = e.get("cover_url")
    primary = types[0] if types else "scene"
    pcolor = TYPE_COLOR.get(primary, "#888")
    if cover and str(cover).startswith("http"):
        thumb = f'<img class="thumb" loading="lazy" src="{esc(cover)}" alt="">'
    else:  # type-tinted placeholder -> keeps the same height, uniform layout
        thumb = (f'<div class="thumb ph" style="--c:{pcolor}">'
                 f'<span>{esc(TYPE_LABEL.get(primary, primary))}</span></div>')
    chips = "".join(f'<span class="chip" style="--c:{TYPE_COLOR.get(t, "#888")}">{esc(TYPE_LABEL.get(t, t))}</span>'
                    for t in types[:3])
    score = e.get("score") or 0
    pop = e.get("popularity") or 0
    hype = bool(e.get("sold_out") or e.get("near_capacity") or pop >= 50)
    gem = score >= 8 or hype
    bits = []
    if e.get("sold_out"):
        bits.append("Sold out")
    elif e.get("near_capacity"):
        bits.append("Near capacity")
    elif e.get("waitlist"):
        bits.append("Waitlist")
    if pop:
        bits.append(f"{pop} registered")
    buzz = ""
    if bits:
        cls = "buzz hot" if hype else "buzz"
        flame = "🔥 " if hype else ""
        buzz = f'<div class="{cls}">{flame}{esc(" · ".join(bits))}</div>'
    return f"""<article class="card" data-types="{esc(' '.join(types))}" data-tier="{esc(e.get('source_tier') or '')}" data-gem="{1 if gem else 0}">
  {thumb}
  <div class="body">
    <div class="row"><span class="time">{hhmm}</span>
      <span class="note" title="score /20">{score}</span>
      <span class="badge" style="--c:{color}">{label}</span></div>
    <h3>{title_html}</h3>
    <div class="venue">{venue}</div>
    {buzz}
    <div class="chips">{chips}</div>
  </div>
</article>"""


def events_section(events):
    evs = [e for e in events.get("events", []) if parse_dt(e.get("start"))]
    evs.sort(key=lambda e: e.get("start") or "")
    week_start = (events.get("window") or {}).get("start", "")[:10]

    def is_gem(e):
        pop = e.get("popularity") or 0
        return (e.get("score") or 0) >= 8 or e.get("sold_out") or e.get("near_capacity") or pop >= 50

    gems = sum(1 for e in evs if is_gem(e))
    seen = set()
    for e in evs:
        seen.update(classify(e))
    present = [(k, lab) for k, lab, _, _ in TYPE_DEF if k in seen]
    grid_ico = ('<svg viewBox="0 0 16 16" width="15" height="15"><rect x="0" y="0" width="7" height="7" rx="1"/>'
                '<rect x="9" y="0" width="7" height="7" rx="1"/><rect x="0" y="9" width="7" height="7" rx="1"/>'
                '<rect x="9" y="9" width="7" height="7" rx="1"/></svg>')
    list_ico = ('<svg viewBox="0 0 16 16" width="15" height="15"><rect x="0" y="1" width="16" height="2.6" rx="1"/>'
                '<rect x="0" y="6.7" width="16" height="2.6" rx="1"/><rect x="0" y="12.4" width="16" height="2.6" rx="1"/></svg>')
    views = (f'<div class="views"><button class="view on" data-view="grid" title="Grid">{grid_ico}</button>'
             f'<button class="view" data-view="list" title="List">{list_ico}</button></div>')
    filters = (f'<button class="gem on" id="gemtoggle">🔥 Gems <b>{gems}</b></button>'
               '<span class="sep"></span>'
               '<button class="filter on" data-filter="all">All</button>' + "".join(
                   f'<button class="filter" data-filter="{k}" style="--c:{TYPE_COLOR[k]}">{esc(lab)}</button>'
                   for k, lab in present) + views)

    # Events that started BEFORE the week (ongoing exhibitions) have no day of
    # their own -> "ongoing all week" bucket, rendered at the end.
    dated, ongoing = {}, []
    for e in evs:
        day = (e.get("start") or "")[:10]
        if week_start and day < week_start:
            ongoing.append(e)
        else:
            dated.setdefault(day, []).append(e)

    days_html = []
    for day in sorted(dated):
        try:
            dd = dt.date.fromisoformat(day)
            head = f"{DAYS[dd.weekday()]} {dd.day} {MONTHS[dd.month]}"
        except Exception:
            head = day
        cards = "".join(card(e) for e in dated[day])
        days_html.append(f'<div class="day"><h2 class="dayhead">{esc(head)} '
                         f'<span class="count">{len(dated[day])}</span></h2>'
                         f'<div class="grid">{cards}</div></div>')
    if ongoing:
        ongoing.sort(key=lambda e: -(e.get("score") or 0))
        cards = "".join(card(e) for e in ongoing)
        days_html.append(f'<div class="day"><h2 class="dayhead">Ongoing all week '
                         f'<span class="count">{len(ongoing)}</span></h2>'
                         f'<div class="grid">{cards}</div></div>')

    c = events.get("counts", {})
    return (f'<section id="events"><div class="filters">{filters}</div>'
            f'<p class="stat">{gems} gems · {len(evs)} events total · '
            f'{c.get("collected", "?")} collected · {c.get("sources_active", "?")} active sources '
            f'<span class="dim">(gems = score ≥ 8, sold out/near capacity, or &gt;50 registered)</span></p>'
            + "".join(days_html) + "</section>")


def tentpoles_section(tp):
    tps = tp.get("tentpoles", [])
    if not tps:
        return ""
    rows = []
    for t in tps:
        where = {"paris": "📍 Paris", "worth-travel": "✈️ travel", "both": "📍✈️"}.get(t.get("where"), "")
        cd = "ongoing" if t.get("status") == "ongoing" else f"D-{t.get('days_until')}"
        url = t.get("url")
        name = esc(t.get("name"))
        name_html = f'<a href="{esc(url)}" target="_blank" rel="noopener">{name}</a>' if url else name
        rows.append(f'<li><span class="tp-when">{esc(t.get("dates_text") or t.get("start"))}</span> '
                    f'<b>{name_html}</b> <span class="tp-cd">{cd}</span><br>'
                    f'<span class="tp-city">{where} · {esc(t.get("city"))}</span></li>')
    return (f'<section id="tentpoles"><h2 class="sechead">Upcoming <span class="count">{len(tps)}</span></h2>'
            f'<ul class="tps">' + "".join(rows) + "</ul></section>")


def extras_section(ex):
    cols = []
    for key, title in (("restos", "🍽 New restaurants"), ("cinema", "🎬 Film releases"),
                       ("escapes", "🚄 TGVmax €0 getaways")):
        rows = ex.get(key) or []
        if not rows:
            continue
        lis = []
        for r in rows[:10]:
            if key == "restos":
                lis.append(f'<li><a href="{esc(r.get("url"))}" target="_blank">{esc(r.get("title"))}</a> '
                           f'<span class="dim">{esc(r.get("price") or "")}</span></li>')
            elif key == "cinema":
                lis.append(f'<li><a href="{esc(r.get("url"))}" target="_blank">{esc(r.get("title"))}</a> '
                           f'<span class="dim">{esc(r.get("release") or "")}</span></li>')
            else:
                lis.append(f'<li><b>{esc(r.get("destination"))}</b> '
                           f'<span class="dim">dep. {esc(r.get("depart"))}</span></li>')
        cols.append(f'<div class="xcol"><h3>{title}</h3><ul>' + "".join(lis) + "</ul></div>")
    if not cols:
        return ""
    return '<section id="extras"><h2 class="sechead">Extras</h2><div class="grid3">' + "".join(cols) + "</div></section>"


def build(events, tentpoles, extras):
    gen = dt.datetime.now().strftime("%Y-%m-%d %H:%M")
    window = ""
    if events and events.get("window"):
        w = events["window"]
        window = f"Week of {w['start'][:10]} to {w['end'][:10]}"
    body = [f'<header><h1>Paris · your week</h1><p class="sub">{esc(window)} · generated on {gen}</p></header>']
    if events and events.get("events"):
        body.append(events_section(events))
    if tentpoles:
        body.append(tentpoles_section(tentpoles))
    if extras:
        body.append(extras_section(extras))
    return PAGE.replace("{{BODY}}", "\n".join(body))


PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Paris · your week</title>
<style>
:root{color-scheme:dark}
*{box-sizing:border-box}
body{margin:0;background:#0d0f14;color:#e6e8ee;font:15px/1.5 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif}
header{padding:28px 20px 6px;max-width:1180px;margin:0 auto}
h1{margin:0;font-size:26px;letter-spacing:-.5px}
.sub{color:#8b93a7;margin:.3em 0 0}
section{padding:8px 20px;max-width:1180px;margin:0 auto}
.filters{position:sticky;top:0;z-index:10;background:#0d0f14e6;backdrop-filter:blur(8px);display:flex;flex-wrap:wrap;gap:8px;padding:14px 0;border-bottom:1px solid #1e2330}
.filter{cursor:pointer;border:1px solid #2b3140;background:#151823;color:#cfd5e3;font-size:13px;padding:5px 12px;border-radius:999px}
.filter:hover{border-color:var(--c,#40c4ff)}
.filter.on{background:var(--c,#39414f);color:#0d0f14;border-color:transparent;font-weight:600}
.gem{cursor:pointer;border:1px solid #ff7043;background:#1c1410;color:#ffab91;font-size:13px;padding:5px 12px;border-radius:999px}
.gem b{font-weight:700}
.gem.on{background:#ff7043;color:#0d0f14;border-color:transparent;font-weight:600}
.sep{width:1px;align-self:stretch;background:#2b3140;margin:0 2px}
.views{margin-left:auto;display:flex;gap:4px}
.view{cursor:pointer;display:flex;align-items:center;justify-content:center;width:32px;height:30px;border:1px solid #2b3140;background:#151823;color:#6b7488;border-radius:8px;padding:0}
.view:hover{color:#cfd5e3}
.view.on{background:#222a39;color:#e6e8ee;border-color:#39414f}
.view svg{fill:currentColor}
.stat{color:#5b6478;font-size:12px;margin:10px 0}
.stat .dim{color:#454c5e}
.dayhead{font-size:16px;margin:18px 0 12px;position:sticky;top:52px;z-index:5;background:rgba(13,15,20,.66);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);padding:10px 14px;border:1px solid #222a36;border-radius:10px}
.sechead{font-size:18px;border-bottom:1px solid #232733;padding-bottom:8px;margin-top:24px}
.count{font-size:12px;color:#6b7488;font-weight:400}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px}
.card{background:#151823;border:1px solid #222736;border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.thumb{width:100%;height:130px;object-fit:cover;display:block;background:#1c2130}
.thumb.ph{display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,color-mix(in srgb,var(--c) 26%,#141823),#141823)}
.thumb.ph span{color:var(--c);opacity:.65;font-size:12px;text-transform:uppercase;letter-spacing:1.5px;font-weight:600}
.body{padding:11px 13px 13px}
.row{display:flex;justify-content:space-between;align-items:center;gap:8px}
.time{font-size:13px;color:#aeb6c7;font-variant-numeric:tabular-nums}
.badge{font-size:10px;text-transform:uppercase;letter-spacing:.5px;color:#0d0f14;background:var(--c);padding:2px 7px;border-radius:999px;font-weight:700}
.note{margin-left:auto;font-size:12px;font-weight:700;color:#cfd5e3;background:#222a39;border-radius:6px;padding:1px 7px;font-variant-numeric:tabular-nums}
.card h3{font-size:14px;margin:7px 0 3px;line-height:1.3}
.card a{color:#e6e8ee;text-decoration:none;border-bottom:1px solid #39414f}
.card a:hover{border-color:#40c4ff}
.venue{color:#8b93a7;font-size:12px}
.buzz{font-size:11px;color:#8b93a7;margin-top:6px}
.buzz.hot{color:#ffab91;font-weight:600}
.chips{margin-top:8px;display:flex;flex-wrap:wrap;gap:5px}
.chip{font-size:10px;color:var(--c);border:1px solid var(--c);border-radius:999px;padding:1px 7px;opacity:.85}
/* --- list mode (compact, clean rows) --- */
.mode-list .grid{grid-template-columns:1fr;gap:6px}
.mode-list .card{flex-direction:row;align-items:stretch;min-height:74px}
.mode-list .thumb{width:74px;height:auto;min-height:100%;align-self:stretch;flex:0 0 74px}
.mode-list .thumb.ph span{font-size:9px;letter-spacing:.5px}
.mode-list .body{flex:1;min-width:0;padding:9px 14px;display:grid;column-gap:14px;row-gap:1px;
  align-content:center;grid-template-columns:1fr auto;
  grid-template-areas:"title meta" "venue meta" "buzz meta"}
.mode-list .row{grid-area:meta;align-self:center;justify-content:flex-end;gap:8px;width:auto}
.mode-list .note{margin-left:0}
.mode-list h3{grid-area:title;margin:0;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mode-list .venue{grid-area:venue;white-space:nowrap;overflow:hidden;text-overflow:ellipsis}
.mode-list .buzz{grid-area:buzz;margin-top:1px}
.mode-list .chips{display:none}
.tps{list-style:none;padding:0;margin:14px 0;display:grid;gap:10px}
.tps li{background:#151823;border:1px solid #222736;border-radius:10px;padding:10px 14px}
.tp-when{color:#8b93a7;font-size:12px;margin-right:8px}.tp-cd{color:#69f0ae;font-size:12px;margin-left:6px}
.tp-city{color:#7d8598;font-size:12px}.tps a{color:#e6e8ee;text-decoration:none;border-bottom:1px solid #39414f}
.grid3{display:grid;grid-template-columns:repeat(auto-fit,minmax(250px,1fr));gap:16px;margin-top:12px}
.xcol h3{font-size:14px;margin:0 0 8px}.xcol ul{list-style:none;padding:0;margin:0;display:grid;gap:6px}
.xcol li{font-size:13px}.xcol a{color:#cfd5e3;text-decoration:none;border-bottom:1px solid #2a3140}.dim{color:#5b6478;font-size:11px}
footer{max-width:1180px;margin:24px auto;padding:16px 20px;color:#4b5366;font-size:12px;border-top:1px solid #1a1e29}
</style></head>
<body>
{{BODY}}
<footer>city-events · aggregated without any API key · regenerate every week to stay up to date</footer>
<script>
(function(){
  var active=new Set();
  var btns=[].slice.call(document.querySelectorAll('.filter'));
  var allBtn=document.querySelector('.filter[data-filter="all"]');
  var gemBtn=document.getElementById('gemtoggle');
  function apply(){
    var gemOnly=gemBtn&&gemBtn.classList.contains('on');
    document.querySelectorAll('.card').forEach(function(c){
      var ts=(c.dataset.types||'').split(' ');
      var typeOk=active.size===0||ts.some(function(t){return active.has(t)});
      var gemOk=!gemOnly||c.dataset.gem==='1';
      c.style.display=(typeOk&&gemOk)?'':'none';
    });
    document.querySelectorAll('.day').forEach(function(d){
      var any=[].slice.call(d.querySelectorAll('.card')).some(function(c){return c.style.display!=='none'});
      d.style.display=any?'':'none';
    });
  }
  if(gemBtn){gemBtn.addEventListener('click',function(){gemBtn.classList.toggle('on');apply();});}
  var sec=document.getElementById('events');
  [].slice.call(document.querySelectorAll('.view')).forEach(function(v){
    v.addEventListener('click',function(){
      document.querySelectorAll('.view').forEach(function(x){x.classList.remove('on')});
      v.classList.add('on');
      sec.classList.toggle('mode-list', v.dataset.view==='list');
    });
  });
  btns.forEach(function(b){
    b.addEventListener('click',function(){
      if(b.dataset.filter==='all'){active.clear();btns.forEach(function(x){x.classList.remove('on')});b.classList.add('on');apply();return;}
      allBtn.classList.remove('on');
      b.classList.toggle('on');
      active.clear();
      document.querySelectorAll('.filter.on').forEach(function(x){if(x.dataset.filter!=='all')active.add(x.dataset.filter)});
      if(active.size===0){allBtn.classList.add('on')}
      apply();
    });
  });
  apply();
})();
</script>
</body></html>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--events")
    ap.add_argument("--tentpoles")
    ap.add_argument("--extras")
    ap.add_argument("--out", default="digest.html")
    args = ap.parse_args()
    page = build(load(args.events), load(args.tentpoles), load(args.extras))
    with open(args.out, "w", encoding="utf-8") as f:
        f.write(page)
    print(f"-> {args.out}")


if __name__ == "__main__":
    main()
