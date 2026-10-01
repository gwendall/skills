---
name: city-events
description: Help someone live a richer life by finding them the best events tuned to their taste for art + tech + culture + gaming + food, from the well-known to the niche/cool/VIP. Three horizons, no API key needed - (1) THIS week's events in Paris via Luma, Resident Advisor, Shotgun, Dice, galleries (slash-paris, Palais de Tokyo), IRL gaming (AFJV, Game Dev IDF, Unreal, start.gg), Eventbrite, film clubs and the official agenda (Que Faire à Paris); (2) the upcoming months' TENTPOLES (Art Basel, Frieze, Gamescom, GDC, VivaTech, Paris Games Week...) in Paris or worth-travel; (3) EXTRAS (new restaurants from Le Fooding, weekly cinema releases from AlloCiné, weekend getaways via TGVmax €0). Dedupes, scores by taste, returns a shortlist with a "why you" line, and can place 'option' holds in the calendar (ICS). Starts with Paris (other cities are extensible). Triggers on "the best events this week", "what to do in Paris", "find me cool outings/parties", "tech/art/culture/gaming/food events", "what to do this weekend", "gallery openings/exhibitions", "upcoming fairs/confs/festivals", "Art Basel/Frieze/Gamescom", "new restaurants", "weekend getaway", "what's on this week", "find cool events".
compatibility: Requires python3 (stdlib only, no dependencies) + network access. No API key (except start.gg, optional via the free $STARTGG_TOKEN). Works in Claude Code and any agent with Bash. Sources verified for Paris; the engine is reusable for other cities.
homepage: local
metadata: {"version":"1.0.0","updated":"2026-06-24","author":"gwendall","openclaw":{"requires":{"bins":["python3"]},"emoji":"calendar"}}
---

# city-events - the best events of the week, tuned to your taste

Given **a city** (Paris by default) and **a week** (the current week by default), produce a **ranked shortlist** of events worth attending for someone who loves **art + tech + culture**, deliberately mixing the **well-known** (institutions, big parties) with the **niche / cool / VIP** (confidential openings, AI demo nights, underground parties, invite-only dinners).

The problem: the good stuff is scattered across dozens of incompatible platforms (Luma for tech/startup, Resident Advisor for clubs, galleries for art, the city's open data for official culture...), each with its own access. This skill aggregates them **without any API key**, dedupes, scores by taste, and delivers a list ready to decide on.

> The full catalog of sources (URLs, exact endpoints, tiers, gotchas) is in **`references/sources-paris.md`**. Read it to understand, fix, or extend a source. This file describes the method.

## Three horizons, three scripts

The taste (art/tech/culture/gaming/food, well-known + niche/VIP) is the same everywhere; only the horizon changes:

| Horizon | Script | What |
|---|---|---|
| **This week** (local) | `scripts/fetch_events.py` | The main engine: dated Paris events, scored, deduped. This is the core. |
| **The coming months** (multi-city) | `scripts/tentpoles.py` | The big dates: art fairs, biennials, design shows, gaming/esport cons, major AI/tech confs, festivals. Flag 📍 Paris vs ✈️ worth-travel. Curated, re-verifiable list + live Artsy refresh. **Side-events drill-down**: `--side-events "art basel paris"` re-runs the weekly engine over the tentpole's window (parties/openings are only published at T-2/4 weeks, so sparse far from the date, rich as it approaches: VivaTech at T-1 week = 254 side-events). |
| **Non-event feeds** | `scripts/extras.py` | New restaurants (Le Fooding), this week's cinema releases (AlloCiné), TGVmax €0 weekend getaways. These are "deals/outings", not time-stamped events. |

For a "make my week/month richer" brief, run all three and merge them in the output: the week (fetch_events), what is coming up soon and worth preparing for (nearby tentpoles), and the current extras.

## Architecture (mechanical script + judging agent)

Like `wallet-analysis`: the **script does the mechanical work**, the **agent does the judgment**.

- **`scripts/fetch_events.py`** pulls every source for the week's window, **normalizes** to a common schema, **dedupes** (the same event seen on several sources), **pre-scores** with a transparent numeric rubric, and outputs a sorted **JSON**.
- **The agent** (you) takes that JSON and does what a script cannot: **final curation**, **diversity** (do not deliver 15 techno parties and zero art), **"why you"** per event, and the writing. The numeric score is a **prior**, not a verdict.

## TL;DR - the fast path

```bash
# Current week, city Paris, JSON output
python3 scripts/fetch_events.py --city paris --json /tmp/events.json

# See the summary (active sources, volume) -> stderr
# The JSON contains: window, counts, source_stats, events[] (sorted by descending score)
```

Then: read `/tmp/events.json`, apply the **curation + diversity** (below), and write the **shortlist** in the output format. An empty source (a monthly calendar with no event this week) is **normal** and skipped silently.

Useful options:
```bash
--start 2026-06-29 --end 2026-07-05   # explicit window (otherwise current Monday..Sunday)
--today 2026-06-24                    # simulate "today" (computes the week around it)
--only ra,shotgun,dice                # only some sources (by id, see catalog)
--skip eventbrite,qfap                # exclude some sources
--limit 60                            # keep the top N after scoring
```

## The method, step by step

### Step 0 - frame the window
The week = **Monday 00:00 -> Sunday 23:59 (Europe/Paris)**. The script computes it on its own (or via `--start/--end/--today`). For "this weekend", pass `--start <friday> --end <sunday>`.

### Step 1 - pull (the script)
The script queries, in conceptual parallel, every source in the `SOURCES_PARIS` registry (see the bottom of `fetch_events.py`), each with its verified access method (Luma API, Resident Advisor GraphQL, open data, JSON-LD, `__NEXT_DATA__` scrape). **Robustness**: any source that errors (4xx/5xx, captcha, empty JSON) is skipped without crashing and logged to stderr. The goal is best-effort, not perfect exhaustiveness.

### Step 2 - normalization
Each event becomes:
```json
{"title","start","end","venue","address","lat_lon","url","cover_url",
 "price","source","source_tier","tags","access","host","artists",
 "sources","axes","score","score_breakdown"}
```
`start`/`end` in ISO 8601. `source_tier` ∈ {vip, cool, niche, mainstream}. `axes` ∈ a subset of {tech, art, culture}, **inferred from the title** and the real tags (not the catch-all tag from the source).

### Step 3 - deduplication
The same event can surface on 2-3 sources (an AI party on `luma_paris` AND a dedicated calendar; a concert on `ra` AND `shotgun`). Primary key = `(start day) + normalized title slug`. On merge: keep the richest version (cover, venue, line-up), **the highest tier**, the union of the tags, and list all the `sources`. (An event's `sources` field tells you how many platforms it appears on: strong overlap = a visibility signal.)

### Step 4 - pre-scoring (the numeric prior)
Score = weighted sum (details in each event's `score_breakdown`):

- **A. Taste affinity** (max ~7): +2 per interest axis touched among {tech/ai/web3, art/design/creative, culture/music, **gaming/esport**, **food**}, +1 bonus for an explicit **art × tech** crossover. An event that crosses 2 axes climbs fast. The axes are inferred from the title (not the source's catch-all tag), so a generic "networking afterwork" stays low.
- **B. Well-known <-> niche/VIP balance** (max +4): `vip` +4, `cool` +3, `niche` +2, `mainstream` +1.
- **C. Quality signals** (max +4): +2 named line-up/speakers (artists present), +1 iconic venue (Station F, Palais de Tokyo, Silencio, Rex...), +1 identifiable host/curator.
- **D. Rarity / limited access** (max +3): +2 for invite/waitlist, +1 for sold-out (proven desirability).
- **E. Freshness** (max +2): +1 starts this week, +1 within the next 3 days.
- **F. Buzz / popularity** (max +5): real attendance signals, the "there's a crowd" factor. Sold out or waitlist +3; near capacity +2; then by number of registrants (`popularity`): >=200 +3, >=80 +2, >=30 +1. Captured from Luma (`guest_count`, `is_sold_out`, `is_near_capacity`, `waitlist_active`) and Resident Advisor (`attending`).
- **Penalties**: -3 for a generic single-axis mainstream item (family workshop, standard guided tour) **and with zero registrants**, -1 for a "ghost" event (no venue and no URL).

The sum = the **score /~20** shown per event. An event is "worth it" when the score is high because it crosses your taste AND there is a crowd (sold out, waitlist, many registrants). To cut the noise: `--min-score N` on the engine side, or the **Gems** toggle on the page side (default: score >= 8, sold out/near capacity, or >50 registrants).

The script sorts by descending score. **This score is only a starting point.**

### Step 5 - curation + judgment (you, the agent)
This is where you add what the numbers miss:
- **Read the titles and line-ups.** An event scored 9 can be a disguised HR afterwork; one scored 7 can be THE opening of the week. Re-evaluate.
- **Cross-check with the news** if relevant (fashion week, biennial, a major exhibition release) via `references/sources-paris.md` (seasonal calendar).
- **Spot the crossovers** art×tech (generative art, NFT, AI×design, a party in an art venue): that is the heart of the taste.

### Step 6 - diversity (anti-monoculture)
Before cutting the top, **balance the shortlist** (Resident Advisor has volume and otherwise crushes everything):
- Target split over ~12-15 events: ~40% tech/ai/web3, ~30% art/galleries/niche-music, ~20% strong mainstream culture, ~10% VIP/rare.
- **Cap ~3 events per source/host** so a single dense calendar does not monopolize.
- Always include **at least 1 VIP/rare** and **at least 1 mainstream must-see** (the "well-known AND underground" mix is explicitly requested).

## Output format

A one-line intro, then one block per event, ranked:

```
Week of {monday} to {sunday} - {N} events kept out of {M} collected ({K} active sources).

### {rank}. {Title}   {tier-emoji}
**{day} {date} · {time}** - {Venue}, {arrondissement}
{Free | from 15€ | Waitlist | Sold out} · {main tags}
**Why you:** {1 sentence - the art×tech crossover, the line-up, the rarity, the venue}
🔗 {url}
```

Tier emojis: `🔒` VIP · `🎯` cool · `🧪` niche · `🏛` mainstream. At the bottom, remind the reader of the seasonal sources to reactivate if the week falls near a window (see catalog: VivaTech ~June, PBW ~April, NFT Paris ~January, AI Engineer ~September).

Keep the links clickable. Do not invent events: everything comes from the JSON. If a category is empty this week (e.g. no opening), say so rather than fill the gap.

## Delivery: holds on your calendar

Rather than reading a list, you can have the **best picks placed as "options" in your calendar**. Two paths:

### A. ICS export (no auth, works right away)
```bash
python3 scripts/fetch_events.py --city paris --ics /tmp/options.ics --ics-limit 8
```
Generates an `.ics` with the top N as **`TENTATIVE` + `TRANSPARENT`** events: they show up as suggestions **without blocking** your slots, prefixed `[OPTION] {tier-emoji} {title}`, with venue, link and "why" in the description. You import it into Google/Apple/Outlook Calendar, or serve it at a URL and **subscribe** to it (it then refreshes on its own if regenerated every week via `/schedule`). The `[OPTION]` entries can be bulk-deleted at once.

### B. Google Calendar live (upgrade, requires auth)
If the Google Calendar MCP is authenticated: (1) read the week's free/busy, (2) avoid or flag picks that **clash** with a slot already taken, (3) create the `[OPTION]` holds (tentative/transparent) only in free slots. Always cap it (top ~5/week + 1 "digest" event at the very top linking to the full list), never dump 15 holds.

Common rule: a hold is an **option**, not a commitment. You confirm by switching the event to "busy" / by RSVPing. Keep the holds visually distinct (prefix + color if available).

### C. Standalone HTML page (to browse the latest data)
```bash
python3 scripts/fetch_events.py --city paris --json /tmp/ev.json
python3 scripts/tentpoles.py --json /tmp/tp.json
python3 scripts/extras.py --json /tmp/ex.json
python3 scripts/render_html.py --events /tmp/ev.json --tentpoles /tmp/tp.json --extras /tmp/ex.json --out /tmp/digest.html
```
`render_html.py` produces **a single `.html` file** (inline CSS, no dependency, no JS framework) with the 3 horizons (This week / Upcoming / Extras). Open it locally, or serve it statically (GitHub Pages, Vercel, Cloudflare Pages, or any static host). To keep it fresh, regenerate it every week via cron or `/schedule` (the job runs the 4 commands then publishes the HTML). A micro-app (Next.js) is only useful if you want live interactive filtering / multi-city: it would then read the same JSON.

## Extending to another city

The **engine** (fetchers, normalization, dedup, scoring) is generic; only the **sources** are specific to Paris. For a new city:

1. Identify its IDs: Luma discover place_id (`discplace-*` in the HTML of `luma.com/<city>`), Resident Advisor area (`areas.eq`), Dice city id (`api.dice.fm/cities`), Shotgun slug, any local open data, local art institutions.
2. Add a `SOURCES_<CITY>` list in `fetch_events.py` (copy `SOURCES_PARIS`, swap the IDs) and register it in `REGISTRY`.
3. Write `references/sources-<city>.md` on the same model.
4. The global sources (Resident Advisor, Shotgun, Dice, Eventbrite, Luma) only change ID/area; the local sources (official agenda, galleries) have to be found per city.

Running a discovery workflow (as for Paris) is the fastest way to build a new city's registry: fan out by angle (Luma, nightlife, art, official), then verify each source's programmatic access.

## Limits / honesty

- **No key, so best-effort.** Resident Advisor (unofficial GraphQL), Shotgun (social-crawler UA), Dice (rotating `buildId`) are undocumented accesses that can break: the script skips and logs, it does not lie. If a key source goes down, say so in the output.
- **Uneven coverage.** Very strong on tech/AI (Luma), nightlife (RA/Shotgun/Dice) and official culture (Que Faire). Thinner on confidential gallery openings (slash-paris + Palais de Tokyo cover part of it) and nil on the truly private/word-of-mouth (unlisted VIP dinners).
- **The score is a prior, not an oracle.** It does not "understand" an event; it counts signals. The final ranking is your judgment.
- **Dead/seasonal sources.** Many Luma calendars are monthly or seasonal: a week with no event on a source is not a bug. The seasonal calendar is in the catalog.
- **No aggressive scraping.** One request per source (two for Shotgun/Dice). Do not parallelize to the point of getting banned; respect the sites.
