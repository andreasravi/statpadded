# nfl/

Shared, reusable NFL data pipelines. Each subfolder under `sources/` fetches
one dataset, caches the raw HTML so it's never re-pulled once cached, and
parses it into one clean CSV. Projects under `../projects/` read these CSVs
directly (by relative path) instead of re-fetching anything themselves —
add a new project that needs win totals or ADP or coaches, and it just reads
the existing `data/*.csv` here.

If a project needs a dataset that doesn't exist yet, add it here as
`nfl/sources/<name>/pipeline.py` following the existing sources as a
template, not inside the project folder — that's what keeps this reusable
instead of re-scraped per project.

## Sources

| Source | What | Site | Years |
|---|---|---|---|
| [`win_totals`](sources/win_totals/) | Vegas preseason win-total line, odds, actual wins, over/under result | Covers.com | 2015–2025 |
| [`adp`](sources/adp/) | Fantasy football average draft position (2QB/superflex, top 100) | FantasyData | 2015–2025 |
| [`coaches`](sources/coaches/) | Head coach per team per season + new-hire flag | MyFootballToolbox.com | 2014–2025 |
| [`game_results`](sources/game_results/) | Every game's final score + derived point differential, Pythagorean wins, strength of schedule | Pro-Football-Reference | 2015–2025 |
| [`kalshi_win_totals`](sources/kalshi_win_totals/) | Live current-season win-total odds (implied line + expected wins), reconstructed from Kalshi's per-team win-threshold contract ladder | Kalshi (public API) | current season only, live snapshot |

Run any auto-fetching source directly:

```bash
source venv/bin/activate
python3 nfl/sources/win_totals/pipeline.py [start_year] [end_year]
python3 nfl/sources/adp/pipeline.py [start_year] [end_year]
python3 nfl/sources/coaches/pipeline.py [start_year] [end_year]
```

Each is idempotent — it skips any year already cached in its `data/raw/`.
`game_results` is the exception: PFR is Cloudflare-protected, so its raw
HTML has to be fetched with a browser tool rather than auto-fetched (see
its README) — but re-running `python3 nfl/sources/game_results/pipeline.py`
is still safe/idempotent for the parsing step once cached.

## `common/`

- `team_codes.py` — every source's historical/relocated team names normalized
  to one canonical 3-letter abbreviation (e.g. Oakland/Las Vegas Raiders →
  `LV`), so datasets from different sources join cleanly on `(year, team)`.
- `http.py` — shared fetch-and-cache helper used by every source's
  `pipeline.py`.
