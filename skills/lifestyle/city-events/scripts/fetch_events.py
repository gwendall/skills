#!/usr/bin/env python3
"""fetch_events.py - Collect a city's events for "this week", normalize them,
dedupe and pre-score by an art+tech+culture taste.

Philosophy (see wallet-analysis): the script does the mechanical work
(pull N sources, merge, dedup, numeric score); the agent does the judgment
(final curation, "why you", diversity, writing). See SKILL.md.

Everything is API-KEY-FREE. Each source is best-effort: a dead or erroring
source is skipped silently (never a crash), and logged to stderr.

Usage:
    python3 fetch_events.py --city paris --json out.json
    python3 fetch_events.py --city paris --start 2026-06-24 --end 2026-06-30
    python3 fetch_events.py --city paris --only luma_discover,ra,qfap
    python3 fetch_events.py --city paris --offi        # also enable Offi (fragile HTML)

Output: JSON {window, counts, events:[...]} on --json (or stdout), summary on stderr.
The source registry (Luma IDs, RA area, etc.) is at the bottom: SOURCES_PARIS.
For another city: duplicate the registry with the city's IDs, reuse the same
fetchers.
"""
import argparse
import datetime as dt
import html
import json
import os
import re
import sys
import urllib.request
import urllib.parse
import urllib.error

try:
    from zoneinfo import ZoneInfo
except Exception:  # py<3.9
    ZoneInfo = None

UA_BROWSER = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36")
UA_SOCIAL = "facebookexternalhit/1.1"


# --------------------------------------------------------------------------- #
# HTTP
# --------------------------------------------------------------------------- #
def http(url, data=None, headers=None, ua=UA_BROWSER, timeout=30, method=None):
    """GET (data=None) or POST. data can be bytes or str. Returns the text."""
    h = {"User-Agent": ua, "Accept-Language": "fr-FR,fr;q=0.9"}
    if headers:
        h.update(headers)
    if isinstance(data, str):
        data = data.encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=h, method=method)
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read().decode("utf-8", "replace")


def http_json(url, **kw):
    return json.loads(http(url, **kw))


def log(msg):
    print(msg, file=sys.stderr, flush=True)


# --------------------------------------------------------------------------- #
# Dates
# --------------------------------------------------------------------------- #
PARIS_TZ = ZoneInfo("Europe/Paris") if ZoneInfo else dt.timezone(dt.timedelta(hours=2))


def parse_dt(s):
    """Parse a heterogeneous ISO 8601 (Z, +02:00, milliseconds) -> UTC-aware datetime.
    Returns None if not parsable."""
    if not s:
        return None
    s = s.strip()
    # epoch?
    if re.fullmatch(r"\d{9,13}", s):
        v = int(s)
        if v > 1e12:
            v //= 1000
        return dt.datetime.fromtimestamp(v, tz=dt.timezone.utc)
    s = s.replace("Z", "+00:00")
    s = re.sub(r"\.\d+", "", s)  # strip the milliseconds
    try:
        d = dt.datetime.fromisoformat(s)
    except ValueError:
        m = re.match(r"(\d{4}-\d{2}-\d{2})", s)
        if not m:
            return None
        d = dt.datetime.fromisoformat(m.group(1))
    if d.tzinfo is None:
        d = d.replace(tzinfo=PARIS_TZ)
    return d.astimezone(dt.timezone.utc)


def week_window(start=None, end=None, today=None):
    """Return (week_start, week_end) in UTC. By default: the current Monday..Sunday
    (Europe/Paris). start/end overrides in YYYY-MM-DD format."""
    if start and end:
        ws = dt.datetime.fromisoformat(start).replace(tzinfo=PARIS_TZ)
        we = dt.datetime.fromisoformat(end).replace(hour=23, minute=59, second=59, tzinfo=PARIS_TZ)
        return ws.astimezone(dt.timezone.utc), we.astimezone(dt.timezone.utc)
    now = (today and dt.datetime.fromisoformat(today).replace(tzinfo=PARIS_TZ)) \
        or dt.datetime.now(PARIS_TZ)
    monday = (now - dt.timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
    sunday = (monday + dt.timedelta(days=6)).replace(hour=23, minute=59, second=59)
    return monday.astimezone(dt.timezone.utc), sunday.astimezone(dt.timezone.utc)


def in_week(d, ws, we):
    return d is not None and ws <= d <= we


# --------------------------------------------------------------------------- #
# Normalized schema
# --------------------------------------------------------------------------- #
def _as_str(v):
    """Coerce possible lists/dicts (e.g. QFAP 'locations') into a clean string."""
    if v is None or isinstance(v, str):
        return v
    if isinstance(v, list):
        parts = [p for p in (_as_str(x) for x in v) if p]
        return ", ".join(parts) or None
    if isinstance(v, dict):
        return v.get("name") or v.get("title") or v.get("address") or None
    return str(v)


def _as_url(v):
    """Coerce a cover_url into a URL string (some sources return a media object)."""
    if isinstance(v, str):
        return v
    if isinstance(v, dict):
        u = v.get("url") or v.get("src") or v.get("href")
        return u if isinstance(u, str) else None
    if isinstance(v, list):
        return _as_url(v[0]) if v else None
    return None


def ev(title, start, source, tier, **kw):
    """Build a normalized event. start = aware datetime or ISO str."""
    if isinstance(start, str):
        start = parse_dt(start)
    end = kw.get("end")
    if isinstance(end, dt.datetime):
        end = end.isoformat()
    return {
        "title": (title or "").strip(),
        "start": start.isoformat() if start else None,
        "_start_dt": start,
        "end": end,
        "venue": _as_str(kw.get("venue")),
        "address": _as_str(kw.get("address")),
        "lat_lon": kw.get("lat_lon"),
        "url": kw.get("url"),
        "cover_url": _as_url(kw.get("cover_url")),
        "price": kw.get("price"),
        "source": source,
        "source_tier": tier,
        "tags": [t.lower() for t in (kw.get("tags") or [])],
        "access": kw.get("access", "public"),
        "host": kw.get("host"),
        "artists": kw.get("artists") or [],
        "popularity": kw.get("popularity"),      # number of registered/going if available
        "sold_out": kw.get("sold_out", False),
        "near_capacity": kw.get("near_capacity", False),
        "waitlist": kw.get("waitlist", False),
    }


# --------------------------------------------------------------------------- #
# Fetchers Luma
# --------------------------------------------------------------------------- #
def _luma_geo_city(e):
    g = e.get("geo_address_info") or {}
    return (g.get("city") or g.get("city_state") or "")


def fetch_luma_calendar(src, ws, we):
    """api.lu.ma/calendar/get-items?calendar_api_id=cal-XXX (key-free).
    Events sorted ascending -> early-exit as soon as start_at > week_end."""
    cal = src["cal"]
    out, cursor, pages = [], None, 0
    period = src.get("period", "future")
    while pages < 8:
        pages += 1
        q = {"calendar_api_id": cal, "period": period, "pagination_limit": 50}
        if cursor:
            q["pagination_cursor"] = cursor
        url = "https://api.lu.ma/calendar/get-items?" + urllib.parse.urlencode(q)
        data = http_json(url, headers={"accept": "application/json"})
        entries = data.get("entries", [])
        stop = False
        for it in entries:
            e = it.get("event") or {}
            sd = parse_dt(e.get("start_at"))
            if src.get("city_filter") and src["city_filter"].lower() not in _luma_geo_city(e).lower():
                continue
            if period == "future" and sd and sd > we:
                stop = True
                continue
            if in_week(sd, ws, we):
                out.append(ev(
                    e.get("name"), sd, src["source"], src["tier"],
                    end=e.get("end_at"), url=_luma_url(e.get("url")),
                    cover_url=e.get("cover_url"), tags=src.get("tags"),
                    venue=(e.get("geo_address_info") or {}).get("address"),
                    address=_luma_geo_city(e), **_luma_pop(it),
                ))
        if stop or not data.get("has_more") or not entries:
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return out


def fetch_luma_discover(src, ws, we):
    """api.lu.ma/discover/get-paginated-events?place_api_id=discplace-XXX (key-free).
    Sorted ascending -> early-exit. This is the niche/cool VOLUME source, already geo-filtered."""
    out, cursor, pages = [], None, 0
    while pages < 10:
        pages += 1
        q = {"place_api_id": src["place"], "pagination_limit": 50}
        if cursor:
            q["pagination_cursor"] = cursor
        url = "https://api.lu.ma/discover/get-paginated-events?" + urllib.parse.urlencode(q)
        data = http_json(url, headers={"accept": "application/json"})
        entries = data.get("entries", [])
        stop = False
        for it in entries:
            e = it.get("event") or {}
            sd = parse_dt(e.get("start_at"))
            if sd and sd > we:
                stop = True
                continue
            if in_week(sd, ws, we):
                out.append(ev(
                    e.get("name"), sd, src["source"], src["tier"],
                    end=e.get("end_at"), url=_luma_url(e.get("url")),
                    cover_url=e.get("cover_url"), tags=src.get("tags"),
                    **_luma_pop(it),
                ))
        if stop or not data.get("has_more") or not entries:
            break
        cursor = data.get("next_cursor")
        if not cursor:
            break
    return out


def _luma_pop(entry):
    """Popularity signals at the Luma entry level (discover AND calendar)."""
    ti = entry.get("ticket_info") or {}
    return {"popularity": entry.get("guest_count"),
            "sold_out": bool(ti.get("is_sold_out")),
            "near_capacity": bool(ti.get("is_near_capacity")),
            "waitlist": bool(entry.get("waitlist_active"))}


def _luma_url(slug):
    if not slug:
        return None
    return slug if slug.startswith("http") else "https://luma.com/" + slug


# --------------------------------------------------------------------------- #
# Que Faire à Paris (City of Paris open data, Opendatasoft v2.1) - culture base
# --------------------------------------------------------------------------- #
def fetch_qfap(src, ws, we):
    base = ("https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/"
            "que-faire-a-paris-/records")
    d0 = ws.astimezone(PARIS_TZ).strftime("%Y-%m-%d")
    d1 = we.astimezone(PARIS_TZ).strftime("%Y-%m-%d")
    # Events that START this week (a "new" signal, avoids permanent exhibitions).
    where = (f"date_start >= date'{d0}' AND date_start <= date'{d1}' "
             f"AND address_city='Paris'")
    sel = ("title,lead_text,url,date_start,date_end,occurrences,locations,"
           "address_zipcode,lat_lon,price_type,price_detail,access_link,"
           "qfap_tags,audience,cover_url")
    out, offset = [], 0
    while offset < 400:
        q = {"where": where, "select": sel, "order_by": "date_start",
             "limit": 100, "offset": offset}
        url = base + "?" + urllib.parse.urlencode(q)
        data = http_json(url)
        results = data.get("results", [])
        for r in results:
            tags = []
            qt = r.get("qfap_tags")
            if isinstance(qt, list):
                tags = qt
            elif isinstance(qt, str):
                tags = [x.strip() for x in qt.split(",") if x.strip()]
            ll = r.get("lat_lon") or {}
            latlon = [ll.get("lat"), ll.get("lon")] if isinstance(ll, dict) and ll.get("lat") else None
            out.append(ev(
                r.get("title"), r.get("date_start"), src["source"], src["tier"],
                end=r.get("date_end"), url=r.get("url"),
                venue=r.get("locations"), address=r.get("address_zipcode"),
                lat_lon=latlon, cover_url=r.get("cover_url"),
                price=r.get("price_type"),
                tags=(src.get("tags") or []) + [t.lower() for t in tags],
            ))
        if len(results) < 100:
            break
        offset += 100
    return out


# --------------------------------------------------------------------------- #
# Resident Advisor (GraphQL keyless) - nightlife
# --------------------------------------------------------------------------- #
RA_QUERY = ("query GET_EVENT_LISTINGS($filters: FilterInputDtoInput, $pageSize: Int, $page: Int) "
            "{ eventListings(filters: $filters, pageSize: $pageSize, page: $page) "
            "{ data { id listingDate event { id title date startTime contentUrl "
            "attending images { filename } "
            "venue { id name area { name country { name } } } artists { id name } } } "
            "totalResults } }")


def fetch_ra(src, ws, we):
    d0 = ws.astimezone(PARIS_TZ).strftime("%Y-%m-%d")
    d1 = we.astimezone(PARIS_TZ).strftime("%Y-%m-%d")
    out, page = [], 1
    while page <= 4:
        payload = json.dumps({
            "operationName": "GET_EVENT_LISTINGS",
            "variables": {
                "filters": {"areas": {"eq": src["area"]},
                            "listingDate": {"gte": d0, "lte": d1}},
                "pageSize": 100, "page": page},
            "query": RA_QUERY})
        data = http_json("https://ra.co/graphql", data=payload,
                         headers={"Content-Type": "application/json",
                                  "Origin": "https://ra.co"})
        listings = (((data.get("data") or {}).get("eventListings") or {}).get("data")) or []
        for li in listings:
            e = li.get("event") or {}
            v = e.get("venue") or {}
            artists = [a.get("name") for a in (e.get("artists") or []) if a.get("name")]
            imgs = e.get("images") or []
            out.append(ev(
                e.get("title"), e.get("startTime") or li.get("listingDate"),
                src["source"], src["tier"],
                venue=v.get("name"),
                url="https://ra.co" + e.get("contentUrl", "") if e.get("contentUrl") else None,
                cover_url=(imgs[0].get("filename") if imgs else None),
                tags=src.get("tags"), artists=artists,
                popularity=e.get("attending"),
            ))
        total = (((data.get("data") or {}).get("eventListings") or {}).get("totalResults")) or 0
        if page * 100 >= total or not listings:
            break
        page += 1
    return out


# --------------------------------------------------------------------------- #
# Shotgun (JSON-LD via a social-crawler UA) - cool nightlife
# --------------------------------------------------------------------------- #
def fetch_shotgun(src, ws, we, max_events=40):
    lst = http(f"https://shotgun.live/fr/cities/{src['slug']}?page=1", ua=UA_SOCIAL)
    slugs = sorted(set(re.findall(r"/fr/events/([a-z0-9-]+)", lst)))[:max_events]
    out = []
    for s in slugs:
        try:
            h = http(f"https://shotgun.live/fr/events/{s}", ua=UA_SOCIAL)
        except Exception:
            continue
        for blk in re.findall(r'<script type="application/ld\+json">(.*?)</script>', h, re.S):
            try:
                j = json.loads(html.unescape(blk))
            except Exception:
                continue
            for it in (j if isinstance(j, list) else [j]):
                if not (isinstance(it, dict) and it.get("@type") == "MusicEvent"):
                    continue
                sd = parse_dt(it.get("startDate"))
                if not in_week(sd, ws, we):
                    continue
                loc = it.get("location") or {}
                out.append(ev(
                    it.get("name"), sd, src["source"], src["tier"],
                    end=it.get("endDate"), venue=loc.get("name"),
                    url=it.get("url") or f"https://shotgun.live/fr/events/{s}",
                    cover_url=_ld_image(it), tags=src.get("tags"),
                ))
    return out


# --------------------------------------------------------------------------- #
# Dice (__NEXT_DATA__ SSR) - indie live / clubs
# --------------------------------------------------------------------------- #
def fetch_dice(src, ws, we):
    out = []
    for path in src.get("paths", ["music/gig", "music/party"]):
        url = f"https://dice.fm/browse/{src['slug']}/{path}"
        try:
            h = http(url, ua=UA_BROWSER)
        except Exception:
            continue
        m = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', h, re.S)
        if not m:
            continue
        try:
            pp = json.loads(m.group(1)).get("props", {}).get("pageProps", {})
        except Exception:
            continue
        for e in pp.get("events", []):
            dates = e.get("dates") or {}
            sd = parse_dt(str(e.get("date_unix"))) or parse_dt(dates.get("event_start_date"))
            if not in_week(sd, ws, we):
                continue
            venues = e.get("venues") or []
            out.append(ev(
                e.get("name"), sd, src["source"], src["tier"],
                venue=(venues[0].get("name") if venues else None),
                url="https://dice.fm/event/" + e.get("perm_name", "") if e.get("perm_name") else None,
                cover_url=(e.get("images") or {}).get("landscape"),
                tags=src.get("tags"),
            ))
    return out


# --------------------------------------------------------------------------- #
# GDG Paris (Bevy API) - community tech
# --------------------------------------------------------------------------- #
def fetch_gdg_bevy(src, ws, we):
    url = f"https://gdg.community.dev/api/event/?chapter={src['chapter']}&page_size=500"
    data = http_json(url, ua=UA_BROWSER)
    out = []
    for r in data.get("results", []):
        if r.get("status") != "Published":
            continue
        sd = parse_dt(r.get("start_date"))
        if not in_week(sd, ws, we):
            continue
        out.append(ev(r.get("title"), sd, src["source"], src["tier"],
                      end=r.get("end_date"), url=r.get("url"), tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# Palais de Tokyo (headless keyless WP-REST) - VIP art / institutional clubbing
# --------------------------------------------------------------------------- #
def fetch_palais_tokyo(src, ws, we):
    out, page = [], 1
    while page <= 6:
        url = f"https://admin.palaisdetokyo.com/wp-json/wph/v1/query/event?wpml_language=fr"
        try:
            data = http_json(url, data=json.dumps({"page": page}),
                             headers={"Content-Type": "application/json"})
        except Exception:
            break
        lst = data.get("list") or {}
        items = []
        if isinstance(lst, dict):
            for v in lst.values():
                items.extend(v if isinstance(v, list) else [v])
        elif isinstance(lst, list):
            items = lst
        for it in items:
            meta = it.get("meta") or {}
            sd = _parse_fr_datetime(meta.get("schedule_start"))
            if not in_week(sd, ws, we):
                continue
            link = it.get("link") or it.get("path")
            if link and link.startswith("/"):
                link = "https://palaisdetokyo.com" + link
            tg = meta.get("tag")
            extra = ["clubbing"] if (isinstance(tg, str) and "club" in tg.lower()) else []
            out.append(ev(it.get("post_title") or it.get("title") or it.get("name"),
                          sd, src["source"], src["tier"], url=link,
                          end=_parse_fr_datetime(meta.get("schedule_end")),
                          cover_url=meta.get("image_desktop"),
                          tags=(src.get("tags") or []) + extra))
        if data.get("nextPage") in (None, False) or not items:
            break
        page += 1
    return out


def _parse_fr_datetime(s):
    """'DD/MM/YYYY HH:MM' or 'DD/MM/YYYY' -> UTC datetime."""
    if not s:
        return None
    m = re.match(r"(\d{2})/(\d{2})/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?", s.strip())
    if not m:
        return None
    dd, mm, yy, hh, mi = m.groups()
    d = dt.datetime(int(yy), int(mm), int(dd), int(hh or 0), int(mi or 0), tzinfo=PARIS_TZ)
    return d.astimezone(dt.timezone.utc)


# --------------------------------------------------------------------------- #
# Slash-Paris (RSS of gallery openings/exhibitions) - niche/VIP art
# --------------------------------------------------------------------------- #
_MONTHS = {m: i for i, m in enumerate(
    ["january", "february", "march", "april", "may", "june", "july",
     "august", "september", "october", "november", "december"], 1)}


def _parse_slash_range(desc):
    """Extract (start, end) from a description like 'June 10 → July 25, 2026'.
    Returns (datetime, datetime) UTC or (None, None)."""
    txt = re.sub(r"<[^>]+>", " ", html.unescape(desc or ""))
    m = re.search(r"([A-Z][a-z]+)\s+(\d{1,2})(?:,\s*(\d{4}))?\s*(?:→|->|–|-)\s*"
                  r"([A-Z][a-z]+)\s+(\d{1,2}),\s*(\d{4})", txt)
    if not m:
        return None, None
    m1, d1, y1, m2, d2, y2 = m.groups()
    y1 = y1 or y2
    try:
        s = dt.datetime(int(y1), _MONTHS[m1.lower()], int(d1), tzinfo=PARIS_TZ)
        e = dt.datetime(int(y2), _MONTHS[m2.lower()], int(d2), 23, 59, tzinfo=PARIS_TZ)
        return s.astimezone(dt.timezone.utc), e.astimezone(dt.timezone.utc)
    except Exception:
        return None, None


def fetch_slash_paris(src, ws, we):
    xml = http(src.get("rss", "https://slash-paris.com/en/exhibs/rss.xml"), ua=UA_BROWSER)
    out = []
    for item in re.findall(r"<item>(.*?)</item>", xml, re.S):
        title = _xml_field(item, "title")
        link = _xml_field(item, "link")
        desc = _xml_field(item, "description")
        s, e = _parse_slash_range(desc)
        # An exhibition "covers" the week if its interval overlaps [ws, we].
        if s and e and s <= we and e >= ws:
            # best-effort Paris/IDF filter
            if re.search(r"(Paris|75\d{3})", desc or "") or "paris" in (link or "").lower():
                out.append(ev(title, s, src["source"], src["tier"],
                              end=e.isoformat(), url=link, tags=src.get("tags"),
                              venue=_slash_gallery(desc)))
    return out


def _slash_gallery(desc):
    txt = re.sub(r"<[^>]+>", " ", html.unescape(desc or ""))
    m = re.search(r"—\s*([^—]+?)\s*—", txt) or re.search(r"-\s*([^-]+?)\s*-", txt)
    return m.group(1).strip() if m else None


def _xml_field(blk, tag):
    m = re.search(rf"<{tag}>(?:<!\[CDATA\[)?(.*?)(?:\]\]>)?</{tag}>", blk, re.S)
    return html.unescape(m.group(1).strip()) if m else None


# --------------------------------------------------------------------------- #
# Ten Days in Paris (WordPress RSS) - insider fashion/art/design/party radar.
# Curated, low volume, high affinity. pubDate = the event date (day-level
# granularity, these posts announce evening openings). No structured time/venue.
# --------------------------------------------------------------------------- #
def fetch_tendays(src, ws, we):
    """WP RSS (30 items/page, reverse-chronological). We PAGINATE (?paged=N) until
    passing below the window start: guarantees completeness even if the feed is
    capped or the window is in the past (side-events drill-down of a tentpole)."""
    from email.utils import parsedate_to_datetime
    out, page, stop = [], 1, False
    while page <= 10 and not stop:
        url = "https://www.tendaysinparis.com/feed/" + (f"?paged={page}" if page > 1 else "")
        try:
            xml = http(url, ua=UA_BROWSER)
        except Exception:
            break
        items = re.findall(r"<item>(.*?)</item>", xml, re.S)
        if not items:
            break
        for item in items:
            title = _xml_field(item, "title")
            pub = re.search(r"<pubDate>([^<]+)</pubDate>", item)
            if not (title and pub):
                continue
            try:
                d = parsedate_to_datetime(pub.group(1)).astimezone(dt.timezone.utc)
            except Exception:
                continue
            if d > we:                 # too recent for the window, skip it
                continue
            if d < ws:                 # reverse-chronological -> everything else is older
                stop = True
                break
            day = d.astimezone(PARIS_TZ).date()
            sd = dt.datetime(day.year, day.month, day.day, 19, 0,
                             tzinfo=PARIS_TZ).astimezone(dt.timezone.utc)  # approx time (evening)
            content = re.search(r"<content:encoded>(.*?)</content:encoded>", item, re.S)
            img = None
            if content:
                mi = re.search(r'<img[^>]+src="([^"]+)"', content.group(1))
                img = mi.group(1) if mi else None
            out.append(ev(title, sd, src["source"], src["tier"],
                          url=_xml_field(item, "link"), cover_url=img,
                          tags=(src.get("tags") or []) + _tendays_tags(title)))
        page += 1
    return out


def _tendays_tags(title):
    t = (title or "").lower()
    pairs = [("party", "party"), ("after party", "party"), ("opening", "vernissage"),
             ("launch", "art"), ("exhibition", "expo"), ("pop up", "art"), ("pop-up", "art"),
             ("pfw", "fashion"), ("fashion", "fashion"), ("dinner", "supper"),
             ("bar ", "food"), ("show", "art"), ("collection", "fashion")]
    tags = [tag for kw, tag in pairs if kw in t]
    return tags or ["art"]


# --------------------------------------------------------------------------- #
# Eventbrite (JSON-LD ItemList, date filter via slug) - art+tech volume
# --------------------------------------------------------------------------- #
EVENT_TYPES = {"Event", "MusicEvent", "ExhibitionEvent", "TheaterEvent", "Festival",
               "SocialEvent", "DanceEvent", "VisualArtsEvent", "BusinessEvent",
               "ScreeningEvent", "EducationEvent"}


def _ldjson_walk(node, out):
    if isinstance(node, list):
        for x in node:
            _ldjson_walk(x, out)
        return
    if not isinstance(node, dict):
        return
    t = node.get("@type")
    types = set(t) if isinstance(t, list) else {t}
    if "@graph" in node:
        _ldjson_walk(node["@graph"], out)
    if "itemListElement" in node:
        for li in node["itemListElement"]:
            _ldjson_walk(li.get("item", li) if isinstance(li, dict) else li, out)
    if types & EVENT_TYPES and node.get("startDate"):
        out.append(node)


def _ld_image(node):
    img = node.get("image") if isinstance(node, dict) else None
    if isinstance(img, list):
        img = img[0] if img else None
    if isinstance(img, dict):
        img = img.get("url") or img.get("contentUrl")
    return img if isinstance(img, str) else None


def _ldjson_from_html(h):
    out = []
    for raw in re.findall(r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>', h, re.S):
        try:
            _ldjson_walk(json.loads(html.unescape(raw.strip())), out)
        except Exception:
            continue
    return out


def fetch_eventbrite(src, ws, we):
    out = []
    for slug in src.get("slugs", ["arts-events--this-week", "tech-events--this-week",
                                  "music-events--this-week"]):
        url = f"https://www.eventbrite.fr/d/france--paris/{slug}/"
        try:
            h = http(url, ua=UA_BROWSER)
        except Exception:
            continue
        for e in _ldjson_from_html(h):
            sd = parse_dt(e.get("startDate"))
            if not in_week(sd, ws, we):
                continue
            loc = e.get("location") or {}
            loc = loc[0] if isinstance(loc, list) else loc
            addr = loc.get("address") if isinstance(loc, dict) else {}
            addr = addr if isinstance(addr, dict) else {}
            city = addr.get("addressLocality") or ""
            pc = str(addr.get("postalCode") or "")
            if city and city != "Paris" and not pc.startswith("75"):
                continue
            # NB: the Eventbrite category slug is unreliable (the same generic event
            # resurfaces across arts/tech/music) -> we do NOT use it as an axis tag;
            # the axis comes from title inference (infer_tags).
            out.append(ev(e.get("name"), sd, src["source"], src["tier"],
                          end=e.get("endDate"),
                          venue=loc.get("name") if isinstance(loc, dict) else None,
                          address=city, url=e.get("url"), cover_url=_ld_image(e),
                          tags=src.get("tags")))
    return out


# Generic JSON-LD fetcher (reusable for any server-rendered art site).
def fetch_jsonld(src, ws, we):
    out = []
    for url in src.get("urls", [src.get("url")]):
        if not url:
            continue
        try:
            h = http(url, ua=UA_BROWSER)
        except Exception:
            continue
        for e in _ldjson_from_html(h):
            sd = parse_dt(e.get("startDate"))
            if not in_week(sd, ws, we):
                continue
            loc = e.get("location") or {}
            loc = loc[0] if isinstance(loc, list) else loc
            out.append(ev(e.get("name"), sd, src["source"], src["tier"],
                          end=e.get("endDate"),
                          venue=loc.get("name") if isinstance(loc, dict) else None,
                          url=e.get("url") or url, tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# AFJV - Paris video game agenda (data-vocabulary microdata, HTML scrape)
# --------------------------------------------------------------------------- #
def fetch_afjv(src, ws, we):
    h = http("https://afjv.com/agenda_jeu_video/", ua=UA_BROWSER)
    out = []
    for b in re.split(r'<a [^>]*class="ag_lign"', h)[1:]:
        sd = re.search(r'itemprop="startDate"[^>]*datetime="([^"]+)"', b) \
            or re.search(r'datetime="([^"]+)"', b)
        title = re.search(r'itemprop="name"[^>]*>(.*?)<', b, re.S)
        loc = re.search(r'itemprop="location"[^>]*>(.*?)<', b, re.S)
        if not (sd and title):
            continue
        place = re.sub(r"<[^>]+>", "", loc.group(1)).strip() if loc else ""
        if "paris" not in place.lower() and "75" not in place:
            continue
        d = parse_dt(sd.group(1))
        if not in_week(d, ws, we):
            continue
        href = re.search(r'href="([^"]+)"', b)
        url = href.group(1) if href else None
        if url and url.startswith("/"):
            url = "https://afjv.com" + url
        out.append(ev(re.sub(r"<[^>]+>", "", title.group(1)).strip(), d,
                      src["source"], src["tier"], url=url, venue=place,
                      tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# Generic Meetup ICS (some groups have a live ICS, e.g. Game Dev IDF)
# --------------------------------------------------------------------------- #
def _parse_ics_dt(raw, is_utc):
    raw = raw.strip()
    is_utc = is_utc or raw.endswith("Z")
    raw = raw.rstrip("Z")
    try:
        d = dt.datetime.strptime(raw[:15], "%Y%m%dT%H%M%S")
    except ValueError:
        try:
            d = dt.datetime.strptime(raw[:8], "%Y%m%d")
        except ValueError:
            return None
    d = d.replace(tzinfo=dt.timezone.utc if is_utc else PARIS_TZ)
    return d.astimezone(dt.timezone.utc)


def fetch_meetup_ics(src, ws, we):
    txt = http(src["ics"], ua=UA_BROWSER)
    out = []
    for ve in re.findall(r"BEGIN:VEVENT(.*?)END:VEVENT", txt, re.S):
        m = re.search(r"DTSTART([^:\r\n]*):([0-9TZ]+)", ve)
        if not m:
            continue
        d = _parse_ics_dt(m.group(2), "Z" in m.group(2))
        if not in_week(d, ws, we):
            continue
        summ = re.search(r"SUMMARY:(.*)", ve)
        u = re.search(r"URL[^:]*:(.*)", ve)
        out.append(ev(summ.group(1).strip() if summ else "(untitled)", d,
                      src["source"], src["tier"],
                      url=(u.group(1).strip() if u else None),
                      venue=src.get("venue_default"), tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# Bevy (communities.unrealengine.com) - Level UP Unreal Engine Paris
# --------------------------------------------------------------------------- #
def fetch_bevy_unreal(src, ws, we):
    url = f"https://communities.unrealengine.com/api/event_slim/for_chapter/{src['chapter']}/"
    data = http_json(url, ua=UA_BROWSER)
    out = []
    for r in data.get("results", []):
        d = parse_dt(r.get("start_date"))
        if not in_week(d, ws, we):
            continue
        out.append(ev(r.get("title"), d, src["source"], src["tier"],
                      end=r.get("end_date"), url=r.get("static_url"),
                      venue=src.get("venue_default"), tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# datacinesindes - "event" screenings (film clubs, Q&As, previews) from Paris
# independent cinemas. We take ONLY the _exists_:evenement ones
# (otherwise ~300 screenings/week pollute the shortlist).
# --------------------------------------------------------------------------- #
def fetch_datacines(src, ws, we):
    d0 = ws.astimezone(PARIS_TZ).strftime("%Y-%m-%d")
    d1 = we.astimezone(PARIS_TZ).strftime("%Y-%m-%d")
    qs = f'cineville:"Paris" AND showstart:[{d0} TO {d1}] AND _exists_:evenement'
    params = {"qs": qs, "sort": "showstart", "size": 100, "count": "false",
              "select": "filmtitle,filmdirector,evenement,showstart,showurl,cinenom,cineadresse"}
    url = ("https://datacinesindes.fr/data-fair/api/v1/datasets/"
           "programmation-cinemas/lines?" + urllib.parse.urlencode(params))
    data = http_json(url, ua=UA_BROWSER)
    out = []
    for r in (data.get("results") or data.get("data") or []):
        d = parse_dt(r.get("showstart"))
        if not in_week(d, ws, we):
            continue
        ev_label = r.get("evenement") or "Special screening"
        title = f"{ev_label} : {r.get('filmtitle')}"
        out.append(ev(title, d, src["source"], src["tier"], url=r.get("showurl"),
                      venue=r.get("cinenom"), address=r.get("cineadresse"),
                      tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# start.gg - Paris grassroots esport tournaments (GraphQL, free token required).
# Silent skip if $STARTGG_TOKEN is absent (the skill stays "key-free" by default).
# --------------------------------------------------------------------------- #
def fetch_startgg(src, ws, we):
    token = os.environ.get("STARTGG_TOKEN")
    if not token:
        return []
    q = ("query($after:Timestamp,$before:Timestamp){ tournaments(query:{perPage:50,"
         "filter:{location:{distanceFrom:\"48.8566,2.3522\",distance:\"50km\"},"
         "afterDate:$after,beforeDate:$before,upcoming:true}}){ nodes{ name startAt slug } } }")
    payload = json.dumps({"query": q, "variables": {
        "after": int(ws.timestamp()), "before": int(we.timestamp())}})
    data = http_json("https://api.start.gg/gql/alpha", data=payload,
                     headers={"Content-Type": "application/json",
                              "Authorization": "Bearer " + token})
    nodes = (((data.get("data") or {}).get("tournaments") or {}).get("nodes")) or []
    out = []
    for n in nodes:
        d = dt.datetime.fromtimestamp(n["startAt"], tz=dt.timezone.utc) if n.get("startAt") else None
        if not in_week(d, ws, we):
            continue
        out.append(ev(n.get("name"), d, src["source"], src["tier"],
                      url="https://start.gg/" + n.get("slug", ""), tags=src.get("tags")))
    return out


# --------------------------------------------------------------------------- #
# Déduplication
# --------------------------------------------------------------------------- #
def _slugify(s):
    s = (s or "").lower()
    s = re.sub(r"^paris\s*:?\s*", "", s)
    s = re.sub(r"[^\w\s]", "", s, flags=re.U)
    return re.sub(r"\s+", " ", s).strip()


TIER_RANK = {"vip": 4, "cool": 3, "niche": 2, "mainstream": 1}


def dedup(events):
    """Key = (start day) + title slug. Merges by keeping the richest version,
    the max tier, and the union of tags/sources."""
    by_key = {}
    for e in events:
        if not e["_start_dt"]:
            continue
        day = e["_start_dt"].astimezone(PARIS_TZ).strftime("%Y-%m-%d")
        key = (day, _slugify(e["title"]))
        if not key[1]:
            key = (day, (e.get("url") or "").lower())
        if key not in by_key:
            e["sources"] = [e["source"]]
            by_key[key] = e
            continue
        cur = by_key[key]
        cur["sources"] = sorted(set(cur.get("sources", [cur["source"]]) + [e["source"]]))
        cur["tags"] = sorted(set(cur["tags"]) | set(e["tags"]))
        if TIER_RANK.get(e["source_tier"], 0) > TIER_RANK.get(cur["source_tier"], 0):
            cur["source_tier"] = e["source_tier"]
        for f in ("cover_url", "venue", "address", "host", "price", "url", "lat_lon", "end"):
            if not cur.get(f) and e.get(f):
                cur[f] = e[f]
        if e.get("artists") and not cur.get("artists"):
            cur["artists"] = e["artists"]
        # popularity: keep the max registered count, OR the boolean signals
        if e.get("popularity") and (e["popularity"] or 0) > (cur.get("popularity") or 0):
            cur["popularity"] = e["popularity"]
        for f in ("sold_out", "near_capacity", "waitlist"):
            cur[f] = cur.get(f) or e.get(f)
    return list(by_key.values())


# --------------------------------------------------------------------------- #
# Pre-scoring (see the rubric in SKILL.md). The numeric score is a PRIOR;
# the agent does the final judgment.
# --------------------------------------------------------------------------- #
AXIS_TECH = {"tech", "ai", "ml", "llm", "web3", "crypto", "blockchain", "startup",
             "dev", "developers", "data", "product", "hackathon", "deeptech", "agents",
             "automation", "no-code", "saas", "vc", "founders", "deep-tech", "genai"}
AXIS_ART = {"art", "gallery", "galerie", "vernissage", "expo", "exposition", "exhibition",
            "contemporary", "art-contemporain", "design", "performance", "fashion", "mode",
            "photo", "photographie", "nft-art", "generative", "sculpture", "peinture",
            "visual-arts", "musee", "musée"}
AXIS_CULT = {"culture", "music", "musique", "concert", "techno", "house", "electronic",
             "clubbing", "nightlife", "rave", "theatre", "théâtre", "danse", "dance",
             "festival", "cinema", "cinéma", "film", "jazz", "classique", "live", "party",
             "spectacle", "opera", "opéra", "arthouse", "cine-club", "avant-premiere"}
AXIS_GAMING = {"gaming", "jeu-video", "jeu vidéo", "gamedev", "esport", "esports", "tournoi",
               "fgc", "smash", "tekken", "speedrun", "arcade", "retrogaming", "unreal",
               "real-time-3d", "indie-game", "game-design", "game-music"}
AXIS_FOOD = {"food", "food-and-drink", "restaurant", "restaurant-opening", "brunch",
             "wine-tasting", "vin", "gastro", "gastronomie", "supper", "popup-dinner",
             "dégustation", "apéro", "food-festival", "food-tour"}
ICONIC_VENUES = {"station f", "palais de tokyo", "lafayette anticipations", "silencio",
                 "bourse de commerce", "fondation cartier", "rex", "la machine", "concrete",
                 "nft factory", "petit bain", "la villette", "philharmonie", "gaîté lyrique"}


# Keywords (FR/EN) searched in the TITLE to infer real content tags,
# independently of the source's (sometimes catch-all) tags. This is what lets us
# tell a real art×tech event from a generic "networking afterwork".
TITLE_KEYWORDS = {
    # tech
    "ai": "ai", "a.i": "ai", "ia": "ai", "intelligence artificielle": "ai",
    "llm": "llm", "machine learning": "ml", "agent": "agents", "genai": "genai",
    "startup": "startup", "founder": "founders", "hackathon": "hackathon",
    "crypto": "crypto", "web3": "web3", "blockchain": "blockchain", "nft": "nft-art",
    "data": "data", "dev": "dev", "product": "product", "design": "design",
    "robot": "tech", "deeptech": "deeptech", "saas": "saas", "pitch": "startup",
    # art
    "art": "art", "expo": "expo", "exhibition": "exhibition", "vernissage": "vernissage",
    "galerie": "galerie", "gallery": "galerie", "sculpture": "sculpture",
    "photo": "photo", "peinture": "art", "fashion": "fashion", "mode": "fashion",
    "performance": "performance", "installation": "art",
    # culture / music / night
    "concert": "concert", "techno": "techno", "house": "house", "dj": "electronic",
    "club": "clubbing", "rave": "rave", "soirée": "party", "party": "party",
    "festival": "festival", "cinéma": "cinema", "cinema": "cinema", "film": "film",
    "théâtre": "theatre", "theatre": "theatre", "danse": "danse", "jazz": "jazz",
    "live": "live", "warehouse": "rave", "open air": "rave",
    # gaming (IRL)
    "esport": "esport", "esports": "esports", "gaming": "gaming", "jeu video": "jeu-video",
    "jeu vidéo": "jeu-video", "video game": "jeu-video", "gamedev": "gamedev",
    "game dev": "gamedev", "game jam": "gamedev", "smash": "smash", "tekken": "tekken",
    "speedrun": "speedrun", "arcade": "arcade", "unreal": "unreal", "godot": "gamedev",
    "japan expo": "gaming", "retrogaming": "arcade",
    # food
    "brunch": "brunch", "degustation": "dégustation", "dégustation": "dégustation",
    "wine": "wine-tasting", "vin": "vin", "food": "food", "resto": "restaurant",
    "restaurant": "restaurant", "diner": "supper", "dîner": "supper", "supper": "supper",
    "apero": "apéro", "apéro": "apéro", "gastro": "gastro", "gastronomie": "gastro",
    "cocktail": "food", "spritz": "food", "tasting": "wine-tasting", "oenologie": "vin",
    "chef": "gastro", "accord mets": "vin", "street food": "food", "bistrot": "restaurant",
    # cinema
    "cine-club": "cine-club", "ciné-club": "cine-club", "avant-premiere": "avant-premiere",
    "avant-première": "avant-premiere", "projection": "cinema",
}


_KW_RE = {kw: re.compile(r"\b" + re.escape(kw).replace(r"\ ", r"\s+") + r"\b")
          for kw in TITLE_KEYWORDS}


def infer_tags(title, venue=None):
    """Tags inferred by word boundary (avoids 'ai' in 'brain', 'art' in 'quartet')."""
    s = (title or "").lower() + " " + (venue or "").lower()
    return {tag for kw, tag in TITLE_KEYWORDS.items() if _KW_RE[kw].search(s)}


def axes_hit(tags):
    t = set(tags)
    hit = []
    if t & AXIS_TECH:
        hit.append("tech")
    if t & AXIS_ART:
        hit.append("art")
    if t & AXIS_CULT:
        hit.append("culture")
    if t & AXIS_GAMING:
        hit.append("gaming")
    if t & AXIS_FOOD:
        hit.append("food")
    return hit


def score(e, ws, we, now):
    b = {}
    # Enrich with tags inferred from the title (real content signal) before scoring.
    e["tags"] = sorted(set(e["tags"]) | infer_tags(e["title"], e.get("venue")))
    ax = axes_hit(e["tags"])
    b["A_taste"] = min(len(ax) * 2, 6) + (1 if ("art" in ax and "tech" in ax) else 0)
    b["B_tier"] = {"vip": 4, "cool": 3, "niche": 2, "mainstream": 1}.get(e["source_tier"], 1)
    q = 0
    if e.get("artists"):
        q += 2
    if (e.get("venue") or "").lower() in ICONIC_VENUES or any(
            v in (e.get("venue") or "").lower() for v in ICONIC_VENUES):
        q += 1
    if e.get("host"):
        q += 1
    b["C_quality"] = min(q, 4)
    r = 0
    acc = (e.get("access") or "").lower()
    price = (e.get("price") or "").lower()
    if acc in ("invite", "waitlist") or "waitlist" in price:
        r += 2
    if "sold" in price or acc == "sold-out":
        r += 1
    b["D_rarity"] = min(r, 3)
    f = 0
    sd = e["_start_dt"]
    if sd and sd >= ws:
        f += 1
    if sd and sd <= now + dt.timedelta(days=3):
        f += 1
    b["E_freshness"] = f
    # F. Buzz / popularity ("is there a crowd?") - real attendance signals.
    buzz = 0
    if e.get("sold_out") or e.get("waitlist"):
        buzz += 3
    elif e.get("near_capacity"):
        buzz += 2
    pop = e.get("popularity") or 0
    buzz += 3 if pop >= 200 else (2 if pop >= 80 else (1 if pop >= 30 else 0))
    b["F_buzz"] = min(buzz, 5)
    pen = 0
    if len(ax) <= 1 and e["source_tier"] == "mainstream" and not e.get("popularity"):
        pen -= 3
    if not e.get("url") and not e.get("venue"):
        pen -= 1
    b["penalty"] = pen
    e["score"] = max(0, sum(b.values()))
    e["score_breakdown"] = b
    e["axes"] = ax
    return e


# --------------------------------------------------------------------------- #
# Source registry - PARIS
# --------------------------------------------------------------------------- #
SOURCES_PARIS = [
    # --- Volume / Luma aggregators (niche+cool+vip, already geo-filtered Paris) ---
    # General aggregator: no axis tag at the source level (otherwise every event maxes
    # the taste). The real tags are inferred from the title by infer_tags() at scoring.
    {"id": "luma_paris", "fn": fetch_luma_discover, "source": "luma:paris", "tier": "cool",
     "place": "discplace-NdLrh1xJfeotJZC", "tags": ["paris"]},

    # --- Dedicated Luma tech/AI/web3 calendars ---
    {"id": "tech_europe", "fn": fetch_luma_calendar, "source": "luma:tech-europe", "tier": "cool",
     "cal": "cal-qyEpCltsspbMoJR", "city_filter": "Paris", "tags": ["tech", "ai", "hackathon", "deeptech"]},
    {"id": "ai_tinkerers", "fn": fetch_luma_calendar, "source": "luma:ai-tinkerers", "tier": "cool",
     "cal": "cal-qFg6R8OBKsMjMhr", "tags": ["ai", "builders", "hackathon", "ml", "dev"]},
    {"id": "air_street", "fn": fetch_luma_calendar, "source": "luma:air-street", "tier": "vip",
     "cal": "cal-zUWmkxeBGlQQenp", "city_filter": "Paris", "tags": ["ai", "ml", "vc", "research"]},
    {"id": "paris_ai_club", "fn": fetch_luma_calendar, "source": "luma:paris-ai-club", "tier": "cool",
     "cal": "cal-4Z4CD0wNw9dJT0H", "tags": ["ai", "demo-night", "startup", "talks"]},
    {"id": "n8n", "fn": fetch_luma_calendar, "source": "luma:n8n", "tier": "niche",
     "cal": "cal-rKZGvZjZWgFjKWW", "city_filter": "Paris", "tags": ["ai", "automation", "no-code", "agents"]},
    {"id": "langchain", "fn": fetch_luma_calendar, "source": "luma:langchain", "tier": "niche",
     "cal": "cal-mvNH1VHlaFtSMFx", "city_filter": "Paris", "tags": ["ai", "llm", "agents", "dev"]},
    {"id": "start_paris", "fn": fetch_luma_calendar, "source": "luma:start", "tier": "cool",
     "cal": "cal-0ZNQSVv8v4NanIC", "city_filter": "Paris", "tags": ["startup", "entrepreneurship", "deeptech"]},
    # Seasonal (often empty out of season; left active, silent skip):
    {"id": "ai_engineer", "fn": fetch_luma_calendar, "source": "luma:ai-engineer", "tier": "cool",
     "cal": "cal-U6ogeqZ4xvrThp6", "seasonal": "sept", "tags": ["ai", "ml", "llm", "conference"]},
    {"id": "vivatech", "fn": fetch_luma_calendar, "source": "luma:vivatech", "tier": "mainstream",
     "cal": "cal-MHbFyEBUOYhAcFC", "city_filter": "Paris", "seasonal": "juin", "tags": ["tech", "startup", "vc"]},
    {"id": "pbw", "fn": fetch_luma_calendar, "source": "luma:paris-blockchain-week", "tier": "vip",
     "cal": "cal-qa6Y6Yw2zOujPwF", "seasonal": "avril", "tags": ["web3", "crypto", "blockchain"]},

    # --- Community tech ---
    {"id": "gdg", "fn": fetch_gdg_bevy, "source": "gdg-paris", "tier": "mainstream",
     "chapter": 942, "tags": ["tech", "developers", "google", "ai", "cloud"]},

    # --- Official culture (base) ---
    {"id": "qfap", "fn": fetch_qfap, "source": "que-faire-paris", "tier": "mainstream",
     "tags": ["culture", "officiel-ville"]},

    # --- Nightlife ---
    {"id": "ra", "fn": fetch_ra, "source": "resident-advisor", "tier": "cool",
     "area": 44, "tags": ["techno", "house", "electronic", "clubbing", "nightlife", "underground", "music"]},
    {"id": "shotgun", "fn": fetch_shotgun, "source": "shotgun", "tier": "cool",
     "slug": "paris", "tags": ["clubbing", "electronic", "techno", "rave", "nightlife", "concerts", "underground", "music"]},
    {"id": "dice", "fn": fetch_dice, "source": "dice", "tier": "cool",
     "slug": "paris-5b23e8a0e63cc224a4c36a2d", "paths": ["music/gig", "music/party"],
     "tags": ["live-music", "concerts", "clubs", "indie", "electronic", "nightlife", "music"]},

    # --- Art / galleries / institutions ---
    {"id": "palais_tokyo", "fn": fetch_palais_tokyo, "source": "palais-de-tokyo", "tier": "vip",
     "tags": ["art", "contemporary", "exhibition", "performance", "clubbing", "vernissage"]},
    {"id": "slash_paris", "fn": fetch_slash_paris, "source": "slash-paris", "tier": "niche",
     "rss": "https://slash-paris.com/en/exhibs/rss.xml",
     "tags": ["art", "galerie", "vernissage", "expo", "art-contemporain"]},
    {"id": "tendays", "fn": fetch_tendays, "source": "tendaysinparis", "tier": "cool",
     "tags": ["insider", "fashion", "design"]},  # VIP fashion/art/party radar, day-level granularity

    # --- Ticketing / art+tech volume ---
    {"id": "eventbrite", "fn": fetch_eventbrite, "source": "eventbrite", "tier": "mainstream",
     "slugs": ["arts-events--this-week", "tech-events--this-week", "music-events--this-week"],
     "tags": ["workshops", "talks", "networking"]},

    # --- IRL Gaming (esport / gamedev / video games) ---
    {"id": "afjv", "fn": fetch_afjv, "source": "afjv", "tier": "niche",
     "tags": ["gaming", "jeu-video", "gamedev", "esport"]},
    {"id": "gamedev_idf", "fn": fetch_meetup_ics, "source": "game-dev-idf", "tier": "niche",
     "ics": "https://www.meetup.com/game-dev-idf/events/ical/",
     "venue_default": "Paris (venue on Discord)", "tags": ["gamedev", "indie", "game-design", "creative-coding"]},
    {"id": "unreal_paris", "fn": fetch_bevy_unreal, "source": "level-up-unreal", "tier": "niche",
     "chapter": 165, "venue_default": "Le Dernier Bar avant la Fin du Monde, 75001",
     "tags": ["gamedev", "unreal", "real-time-3d", "xr", "creative-coding"]},
    {"id": "startgg", "fn": fetch_startgg, "source": "start.gg", "tier": "niche",
     "tags": ["esport", "fgc", "tournoi", "gaming"]},  # skip if $STARTGG_TOKEN absent

    # --- Food & venues (dated food events) ---
    # unreliable category slug (non-food events promoted in it) -> provenance tag,
    # not an axis; the food axis comes from title inference.
    {"id": "eventbrite_food", "fn": fetch_eventbrite, "source": "eventbrite-food", "tier": "mainstream",
     "slugs": ["food-and-drink-events--this-week"], "tags": ["sortie"]},

    # --- Cinema ("event" screenings: film clubs, Q&As, previews) ---
    {"id": "cine_events", "fn": fetch_datacines, "source": "cines-indes", "tier": "niche",
     "tags": ["cinema", "arthouse", "cine-club", "culture"]},
]

REGISTRY = {"paris": SOURCES_PARIS}


# --------------------------------------------------------------------------- #
# ICS export - "option holds" for the calendar (no auth, importable anywhere)
# Events marked TENTATIVE + TRANSPARENT: they show up as suggestions
# without blocking your slots. [OPTION] prefix to spot/bulk-delete them.
# --------------------------------------------------------------------------- #
TIER_EMOJI = {"vip": "🔒", "cool": "🎯", "niche": "🧪", "mainstream": "🏛"}


def _ics_esc(s):
    return ((s or "").replace("\\", "\\\\").replace(";", "\\;")
            .replace(",", "\\,").replace("\n", "\\n"))


def _ics_dt(d):
    return d.astimezone(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def to_ics(events, limit, now):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//city-events//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:city-events (options)"]
    stamp = _ics_dt(now)
    n = 0
    for i, e in enumerate(events):
        if limit and n >= limit:
            break
        sd = parse_dt(e.get("start"))
        if not sd:
            continue
        ed = parse_dt(e.get("end")) or (sd + dt.timedelta(hours=2))
        if ed <= sd:
            ed = sd + dt.timedelta(hours=2)
        n += 1
        emoji = TIER_EMOJI.get(e.get("source_tier"), "")
        loc = ", ".join(x for x in (e.get("venue"), e.get("address")) if x)
        desc = []
        if e.get("tags"):
            desc.append("Tags: " + ", ".join(e["tags"][:6]))
        if e.get("sources"):
            desc.append("Sources: " + ", ".join(e["sources"]))
        desc.append(f"Score {e.get('score')} ({e.get('source_tier')})")
        if e.get("url"):
            desc.append(e["url"])
        uid = f"{_slugify(e.get('title')) or 'event'}-{_ics_dt(sd)}-{i}@city-events"
        lines += ["BEGIN:VEVENT", "UID:" + uid, "DTSTAMP:" + stamp,
                  "DTSTART:" + _ics_dt(sd), "DTEND:" + _ics_dt(ed),
                  "SUMMARY:" + _ics_esc(f"[OPTION] {emoji} {e.get('title')}".strip()),
                  "STATUS:TENTATIVE", "TRANSP:TRANSPARENT"]
        if loc:
            lines.append("LOCATION:" + _ics_esc(loc))
        if e.get("url"):
            lines.append("URL:" + e["url"])
        lines.append("DESCRIPTION:" + _ics_esc("\n".join(desc)))
        lines.append("END:VEVENT")
    lines.append("END:VCALENDAR")
    return "\r\n".join(lines) + "\r\n"


# --------------------------------------------------------------------------- #
# main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(description="Collect a city's events for this week.")
    ap.add_argument("--city", default="paris")
    ap.add_argument("--start", help="YYYY-MM-DD (override window start)")
    ap.add_argument("--end", help="YYYY-MM-DD (override window end)")
    ap.add_argument("--today", help="YYYY-MM-DD (simulate 'today' for the current week)")
    ap.add_argument("--only", help="comma-separated list of source ids")
    ap.add_argument("--skip", help="list of ids to exclude")
    ap.add_argument("--json", help="JSON output file (otherwise stdout)")
    ap.add_argument("--ics", help=".ics file of 'option' holds (top events, tentative/transparent)")
    ap.add_argument("--ics-limit", type=int, default=8, help="number of holds in the ICS (def 8)")
    ap.add_argument("--limit", type=int, default=0, help="keep only the top N after scoring")
    ap.add_argument("--min-score", type=int, default=0, help="cut the noise: keep score >= N")
    args = ap.parse_args()

    sources = REGISTRY.get(args.city.lower())
    if not sources:
        log(f"Unknown city: {args.city}. Available: {', '.join(REGISTRY)}")
        sys.exit(2)

    ws, we = week_window(args.start, args.end, args.today)
    now = dt.datetime.now(dt.timezone.utc)
    only = set(filter(None, (args.only or "").split(",")))
    skip = set(filter(None, (args.skip or "").split(",")))

    all_events, stats = [], []
    for src in sources:
        if only and src["id"] not in only:
            continue
        if src["id"] in skip:
            continue
        try:
            got = src["fn"](src, ws, we) or []
            all_events.extend(got)
            stats.append((src["id"], len(got), None))
            log(f"  {src['id']:16} {len(got):3} events")
        except urllib.error.HTTPError as ex:
            stats.append((src["id"], 0, f"HTTP {ex.code}"))
            log(f"  {src['id']:16}   0  (HTTP {ex.code}, skip)")
        except Exception as ex:
            stats.append((src["id"], 0, str(ex)[:80]))
            log(f"  {src['id']:16}   0  ({type(ex).__name__}: {str(ex)[:60]}, skip)")

    merged = dedup(all_events)
    for e in merged:
        score(e, ws, we, now)
    merged.sort(key=lambda x: (-x["score"], x["start"] or "z"))
    if args.min_score:
        merged = [e for e in merged if e["score"] >= args.min_score]
    if args.limit:
        merged = merged[:args.limit]

    for e in merged:
        e.pop("_start_dt", None)

    payload = {
        "city": args.city,
        "window": {"start": ws.astimezone(PARIS_TZ).isoformat(),
                   "end": we.astimezone(PARIS_TZ).isoformat()},
        "counts": {"collected": len(all_events), "deduped": len(merged),
                   "sources_active": sum(1 for _, n, _ in stats if n > 0),
                   "sources_total": len(stats)},
        "source_stats": [{"id": i, "n": n, "error": e} for i, n, e in stats],
        "events": merged,
    }
    out = json.dumps(payload, ensure_ascii=False, indent=2)
    if args.json:
        with open(args.json, "w", encoding="utf-8") as f:
            f.write(out + "\n")
        log(f"\n{len(merged)} unique events ({payload['counts']['collected']} collected, "
            f"{payload['counts']['sources_active']}/{len(stats)} active sources) -> {args.json}")
    elif not args.ics:
        print(out)

    if args.ics:
        with open(args.ics, "w", encoding="utf-8") as f:
            f.write(to_ics(merged, args.ics_limit, now))
        log(f"ICS: {min(args.ics_limit or len(merged), len(merged))} 'option' holds -> {args.ics}")


if __name__ == "__main__":
    main()
