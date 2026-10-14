# Event sources - Paris

Catalog verified live on 2026-06-24. Every source kept here is **alive**, **key-free**, and **filterable to "this week"**. Each source carries the `id` used by `scripts/fetch_events.py` (flags `--only` / `--skip`).

Tiers: `vip` (insider / invite / capped) · `cool` (in-the-know scene) · `niche` (sharp community) · `mainstream` (general public, the "well-known" base).

> The script implements this whole catalog. This file is the human doc: to do the pull by hand, understand a source, fix a broken one, or add one.

## Luma convention (applies to all `luma-api` sources)

1. Find the `calendar_api_id` in the raw HTML of the calendar page:
   `curl -sA "Mozilla/5.0" <url> | grep -oE '"api_id":"cal-[A-Za-z0-9]+"'` (ignore CSS false positives like `cal-padding`; the WebFetch markdown does NOT expose it, you need the raw HTML).
2. Pull without a key: `GET https://api.lu.ma/calendar/get-items?calendar_api_id=cal-XXX&period=future&pagination_limit=50` (header `accept: application/json`). `period` only accepts `future|past` (anything else = HTTP 400).
3. Response: `{entries:[{event:{name,start_at,end_at,timezone,url,geo_address_info:{city,city_state,...}}}], has_more, next_cursor}`. `start_at` = ISO 8601 UTC, already sorted ascending. Paginate via `&pagination_cursor=<next_cursor>`, stop as soon as `start_at > end of week` (early-exit).
4. Filter "this week" client-side; filter Paris on `geo_address_info.city == "Paris"` for **global calendars** (they are NOT pre-filtered). Event page = `https://luma.com/<event.url>`.

---

## 1. Tech / AI / Web3

Dedicated Luma calendars. Most are **monthly or seasonal**: on a given week, many return 0 (that is normal, silent skip).

| id | name | tier | access |
|---|---|---|---|
| `tech_europe` | {Tech: Europe} | cool | `cal-qyEpCltsspbMoJR` (global -> filter Paris). ICS alt: `https://api.lu.ma/ics/get?entity=calendar&id=cal-qyEpCltsspbMoJR`. Sub-calendars on the same endpoint: Alpic `cal-73DrqykM2XUzHje`, Auth0 Events Europe `cal-inLTbBIZPpPPkRP`. |
| `ai_tinkerers` | AI Tinkerers Paris | cool | `cal-qFg6R8OBKsMjMhr` (in the URL). AI builder demo nights, cadence ~1-2/month. Mirror: paris.aitinkerers.org. |
| `air_street` | Air Street (Paris AI) | **vip** | `cal-zUWmkxeBGlQQenp` (**global** calendar -> filter Paris, ~5 Paris out of 37). High-end VC/AI (Black Forest Labs, DeepMind). Very low frequency, very high signal. |
| `paris_ai_club` | Paris AI Club | cool | `cal-4Z4CD0wNw9dJT0H`. "Once a month, the best AI talents gather for a demo night." |
| `n8n` | Paris n8n Meetup | niche | `cal-rKZGvZjZWgFjKWW` (global -> filter "Paris, France"). Automation / no-code / agents. |
| `langchain` | LangChain Events | niche | `cal-mvNH1VHlaFtSMFx` (global, US-dominated -> filter Paris; Paris events prefixed "PARIS:"). Opportunistic. |

Pre-filtered AI Paris aggregator page (robust alternative, `__NEXT_DATA__` parsing):
- **Luma AI Events Paris** `https://luma.com/discover/paris/ai` [cool]. `GET` with a browser UA, extract `<script id="__NEXT_DATA__">`, walk the tree for `evt-*` objects. Pre-filtered AI + Paris server-side. GOTCHA: the `get-paginated-events` API IGNORES the `cat-ai` category filter (returns all of Paris) -> for strict AI, parse the `__NEXT_DATA__`, not the API. Brand parties (Anthropic, Cursor, Stripe) are often waitlisted -> VIP tint.

Community tech (outside Luma):
- **GDG Paris** `gdg.community.dev/gdg-paris/` [mainstream], id `gdg`. Bevy API (NOT Meetup, the Meetup ICS is empty): `GET https://gdg.community.dev/api/event/?chapter=942&page_size=500` (browser UA). `results[]` -> keep `status=='Published'` + date within the week (server date filter is ignored). Sibling chapters: GDG Cloud Paris, GDG Paris Android (different `chapter`).
- **Paris Machine Learning Group** `meetup.com/Paris-Machine-learning-applications-group/events/` [niche], not scripted. The Meetup ICS is DEAD (403). Scrape `<script id="__NEXT_DATA__">` (browser UA): `dateTime`, `title`, `eventUrl`, `venue.city`. Legendary group (7500+ members), monthly cadence.

## 2. Startup / Product / Design

| id | name | tier | access |
|---|---|---|---|
| `start_paris` | START Paris | cool | `cal-0ZNQSVv8v4NanIC` (global -> filter Paris). Tied to START Summit, bursts around hackathon cycles. |

Seasonal (left active, empty out of season):
- **AI Engineer Paris (side events)** `ai_engineer`, `cal-U6ogeqZ4xvrThp6`. Annual conf (~Sept @ Station F). The side-events calendar fills up as it approaches (vLLM/Mistral/Neo4j meetups). **Re-poll in September.**
- **VivaTech (side events)** `vivatech`, `cal-MHbFyEBUOYhAcFC`. Window ~mid-June only. During the edition, use `period=past` (the `future` empties out). Filter Paris (Berlin/Milan satellites).
- **Paris Blockchain Week** `pbw`, `cal-qa6Y6Yw2zOujPwF`. Industry week with many side events, ~April. Dormant the rest of the year.

## 3. Art / Galleries / Museums

| id | name | tier | access |
|---|---|---|---|
| `palais_tokyo` | Palais de Tokyo | **vip** | Headless keyless WP-REST: `POST https://admin.palaisdetokyo.com/wp-json/wph/v1/query/event?wpml_language=fr` (Content-Type json, body `{}` or `{"page":N}`). `list` keyed by `DD/MM/YYYY`; item: `post_title`, `link`, `meta.schedule_start`/`schedule_end` ("DD/MM/YYYY HH:MM"), `meta.tag` (`clubbing-en` = late-night parties). Exhibitions: same route `/wph/v1/query/expo`. Mix of well-known + VIP + institutional clubbing. |
| `slash_paris` | Slash-Paris (openings) | niche | Keyless RSS: `GET https://slash-paris.com/en/exhibs/rss.xml` (FR: `/fr/...`). **The reference calendar for contemporary art galleries** (Mennour, Continua, Xippas, Lelong). DATE GOTCHA: `pubDate` = publication date, NOT the event date; the real period is in free text in the 2nd CDATA block `<description>` (`June 10 -> July 25, 2026`, separator `→`). Filter Paris/IDF client-side (the feed includes provincial/foreign entries). |

Not scripted (low volume, fragile scrape; pull via WebFetch case by case):
- **Lafayette Anticipations** `lafayetteanticipations.com/fr/agenda` [cool]. Sharp contemporary art foundation (performances, experimental music, talks), single venue (9 rue du Plâtre, Marais). Scrape: `div.c-events-group` (one per day) > `h2.ft_h4` (date label "jeudi 25 juin 2026"), `div.c-block-event` > `h3.ft_h3` (title) + `a[href^="/fr/manifestation/"]`. Date filterable client-side (parse the day headers). ~5 events/week, high quality.
- Bourse de Commerce (Pinault), Fondation Cartier, Jeu de Paume, Lafayette: most expose JSON-LD `Event`/`ExhibitionEvent` -> try the generic JSON-LD fallback (see SKILL.md).

> The "gallery openings + digital art" layer: partially covered by `luma_paris` (which mixes openings, magazine launches, PFW parties, creative film clubs) and by `slash_paris`. The dedicated art-crypto Luma calendars (NFT Paris, Bright Moments, fxhash) are **dormant/off-season** (see discarded). For institutional art, `que-faire-paris` filtered on `qfap_tags` containing "Expo"/"Art contemporain".

## 4. Culture / Official (mainstream base)

| id | name | tier | access |
|---|---|---|---|
| `qfap` | Que Faire à Paris (City of Paris open data) | mainstream | Opendatasoft v2.1 API, no key. Base: `https://opendata.paris.fr/api/explore/v2.1/catalog/datasets/que-faire-a-paris-/records` (dataset_id = `que-faire-a-paris-`, **trailing dash required**). |

Two useful queries:
- Events that **start this week** (a "new" signal, avoids permanent exhibitions):
  `?where=date_start >= date'2026-06-24' AND date_start <= date'2026-06-30' AND address_city='Paris'&order_by=date_start&limit=100` (~367 results). That is what the script does.
- Events **active this week** (also catches long-running exhibitions still open):
  `?where=date_end >= now() AND date_start <= date'2026-07-01'&order_by=date_start&limit=100` (~1324).

Projection: `&select=title,lead_text,url,date_start,date_end,occurrences,locations,address_zipcode,lat_lon,price_type,price_detail,access_link,qfap_tags,audience,cover_url`. Pagination `limit=100` + `offset=N`, `total_count` returned. URL-encode spaces and quotes. Filterable by arrondissement (`address_zipcode` 75xxx) and by theme (`qfap_tags`: "Expo", "Concert", "Festival", "Théâtre", "Danse", "Atelier", "Art contemporain"...). **Does NOT cover** techno clubbing, private parties, confidential openings, tech meetups: complement with Luma + nightlife.

## 5. Nightlife / Music

| id | name | tier | access |
|---|---|---|---|
| `ra` | Resident Advisor | cool | Keyless GraphQL: `POST https://ra.co/graphql` (headers `Content-Type: application/json`, `User-Agent` **non-empty required**, `Origin: https://ra.co`). Paris = `areas.eq:44`. Date filter `listingDate` gte/lte (YYYY-MM-DD), **server-side**. Response: `data.eventListings.data[].event` -> `title, startTime, venue.name, artists[].name, contentUrl` (prefix `https://ra.co`). **The HTML page is DataDome-protected (curl -> 403); the GraphQL is not.** Unofficial endpoint, may break without notice. ~100 events/week, mix of mainstream + underground. |
| `shotgun` | Shotgun | cool | Keyless scrape + JSON-LD **with a trick**: a social-crawler UA is **mandatory** (`facebookexternalhit/1.1` or `Twitterbot/1.0`) to pass the "Vercel Security Checkpoint" (normal UA -> 429). Step 1: list slugs via `GET https://shotgun.live/fr/cities/paris?page=N` (regex `/fr/events/[a-z0-9-]+`). Step 2: date per event via JSON-LD `MusicEvent` on `/fr/events/<slug>` (`startDate` ISO, client-side filter). City URL = `/fr/cities/paris` (NOT `/city/paris`). `api.shotgun.live/events` = organizer API (key required), unusable. |
| `dice` | Dice | cool | Keyless `__NEXT_DATA__` scrape, browser UA required. Keyless city id via `https://api.dice.fm/cities` (Paris = `5b23e8a0e63cc224a4c36a2d`). Pages: `dice.fm/browse/paris-5b23e8a0e63cc224a4c36a2d/music/gig` (concerts) and `.../music/party` (clubs). Events SSR in `<script id="__NEXT_DATA__">` -> `props.pageProps.events` (21/page) + `nextCursor`. Date: `date_unix` (epoch) or `dates.event_start_date` (ISO). Strong indie live/club curation (Supersonic, L'International, Petit Bain). |

## 6. Ticketing / art+tech volume

| id | name | tier | access |
|---|---|---|---|
| `eventbrite` | Eventbrite Paris | mainstream | Keyless JSON-LD scrape. **Date+category filter via the path slug**: `https://www.eventbrite.fr/d/france--paris/<slug>/` with slug ∈ `arts-events--this-week`, `tech-events--this-week`, `music-events--this-week`, `science-and-tech-events--this-week`. Browser UA. JSON-LD #0 = `ItemList` -> `itemListElement[].item`. `startDate` ISO + address. Filter Paris (`addressLocality=='Paris'` or `postalCode` 75xxx). **Limits**: capped at ~68 events; category slug unreliable (the same business event resurfaces across several slugs) -> the script does NOT use it as an axis tag, the axis comes from the title. Large mainstream/business share. |

Not scripted:
- **Offi.fr (L'Officiel des spectacles)** [mainstream]. Reference agenda since 1946, ultra-exhaustive (concerts, theater, exhibitions, classical, jazz, cinema). **Server-side date filter to the day** -> perfect for the week. AJAX: `POST https://www.offi.fr/concerts/programme.html` (same for `/theatre/`, `/expositions-musees/`...). Headers `X-Requested-With: XMLHttpRequest`, `Content-Type: application/x-www-form-urlencoded`, browser UA. Body: `values=<url-encoded query string DateDebut=24/06/2026&DateFin=01/07/2026&NbDay=7>`, `tri=`, `npage=1`, `update=1`. Response = HTML fragment split on the literal delimiter `########`. Ideal "well-known" base, no underground.

## 7. Cool aggregators

- **Time Out Paris** [cool] `https://www.timeout.fr/paris/que-faire-a-paris/les-meilleurs-plans-de-la-semaine`. Editorial "what to do this week" selection (art, exhibitions, restaurants, concerts). Scrape: `article > h3 > a.tileImageLink` (~18 tiles/week), date at the article level (JSON-LD `Article` + "semaine du X"). **Canonical domain = `.fr`** (the `.com/paris/things-to-do` is dead 404). Good for "well-known + cool", little underground.

---

## 8. IRL Gaming (esport / gamedev / video games)

| id | name | tier | access |
|---|---|---|---|
| `afjv` | AFJV - video game agenda | niche | Microdata (HTML scrape, NOT JSON-LD): `GET https://afjv.com/agenda_jeu_video/` (browser UA). Events in `<a class="ag_lign" itemtype="data-vocabulary.org/Event">`; date = `<time itemprop="startDate" datetime="...">`, title = `itemprop="name"`, venue = `itemprop="location"` (filter "Paris"/"75"). URLs `/news/*.htm` to prefix with `https://afjv.com`. 124 events/year of which 25 are in Paris (BnF, game-music colloquia, Paris Games Week, Japan Expo). `rss.xml` = news, NOT the agenda. |
| `gamedev_idf` | Game Dev IDF (Meetup) | niche | Keyless ICS (a rare live Meetup one): `https://www.meetup.com/game-dev-idf/events/ical/`. Per VEVENT: `DTSTART;TZID=Europe/Paris`, `SUMMARY`, `URL`. `LOCATION` empty (venue is on Discord) -> "Paris (TBA)". First Thursday of the month, ~1/month. The HTML hydrates client-side -> take the ICS, not the scrape. |
| `unreal_paris` | Level UP - Unreal Engine Paris | niche | Keyless Bevy API (same family as GDG): `GET https://communities.unrealengine.com/api/event_slim/for_chapter/165/`. `results[]`: `title`, `start_date`/`end_date` (ISO UTC), `static_url`. IRL at Le Dernier Bar avant la Fin du Monde (75001), 3rd Wednesday of the month. |
| `startgg` | start.gg - esport tournaments | niche | GraphQL `POST https://api.start.gg/gql/alpha`, **free token required** (`Authorization: Bearer $STARTGG_TOKEN`, created in 30s at start.gg/admin/profile/developer). Filter `location.distanceFrom:"48.8566,2.3522" distance:"50km"` + `afterDate`/`beforeDate` (UNIX). FGC/Smash scene. **Silent skip if no token** (the skill stays key-free by default). |

## 9. Food & venues

| id | name | tier | access |
|---|---|---|---|
| `eventbrite_food` | Eventbrite Paris Food & Drink | mainstream | Reuses the Eventbrite fetcher (JSON-LD `ItemList`), slug `food-and-drink-events--this-week`. Brunches, wine tastings, food tours. Re-filter Paris client-side. |

Separate module (outside the events engine, see `scripts/extras.py`):
- **Le Fooding - restaurants** [cool]. New openings: `GET https://lefooding.com/wp-json/api/v1/fr/places/restaurant/index?page=1` (the `/index` suffix is mandatory, otherwise 404). Sorted DESC by `createdAt` (= addition to the guide). Keep `city[].slug=="paris"` + recent `createdAt`. `data_shape=ongoing` (openings, not dated events).

## 10. Cinema

| id | name | tier | access |
|---|---|---|---|
| `cine_events` | Indie cinemas - "event" screenings | niche | Keyless Koumoul data-fair: `GET https://datacinesindes.fr/data-fair/api/v1/datasets/programmation-cinemas/lines?qs=cineville:"Paris" AND showstart:[D0 TO D1] AND _exists_:evenement`. Take ONLY the `_exists_:evenement` ones (film clubs, Q&As, previews) to avoid 300 screenings/week. Fields: `filmtitle`, `evenement`, `showstart`, `cinenom`, `showurl`. |

Separate module (release, see `scripts/extras.py`):
- **AlloCiné - this week's releases** [mainstream]. `GET https://www.allocine.fr/film/agenda/sem-YYYY-MM-DD/` (date = the week's Wednesday). Regex `"releaseDate":"..."` + anchors `<a class="meta-title-link" href="/film/fichefilm_gen_cfilm=ID.html">` (same order -> zip). `data_shape=release`: not time-stamped events.

## 11. Travel / getaways (separate module, see `scripts/extras.py`)

- **SNCF TGVmax** [mainstream]. €0 trains (Max Jeune 16-27 / Max Senior subscribers). Keyless Opendatasoft v2.1: `GET https://data.sncf.com/api/explore/v2.1/catalog/datasets/tgvmax/records?where=date=date'YYYY-MM-DD' AND od_happy_card='OUI' AND origine='PARIS (intramuros)'`. **The `date` field is a date type -> `date=date'...'` (NO quotes), text literals in single quotes.** `od_happy_card='OUI'` = seat available. Target Friday/Saturday. `data_shape=deal`. All the other travel sources (KAYAK, VoyagesPirates, The Flight Deal, TGV fares) are discarded (captcha, out-of-geo, or not date-filterable).

## 12. Tentpoles (coming months, see `scripts/tentpoles.py`)

Big dates set months in advance, in Paris or worth-travel. Most have a **near-fixed annual date**: a **curated list re-verified every quarter** (embedded in `tentpoles.py`) is more reliable than a scrape. Optional live refresh of art fairs:
- **Artsy (Metaphysics GraphQL)** keyless: `POST https://metaphysics-production.artsy.net/v2`, body `{"query":"{ fairs(sort: START_AT_ASC, size: 40) { name startAt endAt } }"}`. Reliable ISO dates; the **city is NOT exposed** (infer it from the name). The `artsy.net/art-fairs` HTML page is behind Cloudflare (403) -> go through the GraphQL API.
- **AI conferences**: `huggingface/ai-deadlines` (YAML per conf on GitHub raw, no key) for NeurIPS/ICML/CVPR/SIGGRAPH.
- **Luma Discover** (side-events around the big confs): `GET https://api.lu.ma/discover/get-paginated-events?pagination_limit=50` (during Cannes Lions, VivaTech, EthCC... exposes hundreds of side-events).
- For the **dates** of the tentpoles themselves: official sites (artbasel.com, frieze.com, gamescom.global, gdconf.com...), re-verified in the curated list.

## Discarded sources (and why)

| Source | Reason |
|---|---|
| **Sortiraparis** | Custom anti-bot wall + Google reCAPTCHA across the whole domain (401). IP banned after a few requests. Inaccessible without a headless browser + a paid captcha service. |
| **Billetreduc** | (1) Wrong taste: discount catalog (café-théâtre, dinner shows, kids' shows). (2) Not date-filterable: the JSON-LD `startDate` = the show's total run, not a dated session. |
| **Fnac Spectacles** | Akamai bot protection: silent drop (HTTP 000) for curl AND WebFetch. Inaccessible without a real browser. |
| **Le Bonbon** | Editorial media, not an event feed: rows = articles with a publication date, not events with date/venue. Useful only as a curation/taste signal. Real URL = `/paris/sorties/`. |
| **Paris AI Society**, **Docker Paris**, **GenAI Summit**, **Web3 & AI Paris**, **NFT Paris**, **Bright Moments**, **fxhash**, **Deep Tech Connections**, **Founders Bay** | Dormant Luma calendars (0 future event for months), dead, out-of-geo (US/SF), or past-seasonal. NFT Paris: revisit ~January. PBW: ~April. |
| **Meetup (public ICS)** | Neutralized: 0 VEVENT even on active groups, or 403 "Invalid feed signature". For a live Meetup group, scrape the HTML's `__NEXT_DATA__` (browser UA), not the ICS. |

## Seasonal sources calendar (to reactivate)

| Source | Window | Note |
|---|---|---|
| VivaTech side events | ~mid-June | `period=past` during the edition |
| Paris Blockchain Week | ~April | Industry week, many side events |
| NFT Paris (side events) | ~January/February | revisit ~December |
| AI Engineer Paris side events | ~September | fills up in August, dormant in summer |
| Paris Design Week / D'Days | ~September | art/design |
| Paris Photo | ~November | photography |
| Art Basel Paris | ~October | VIP contemporary art |
