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
| [`qb_tiers`](sources/qb_tiers/) | Mike Sando's annual QB Tiers survey (execs/coaches sort every starting QB into 5 tiers) | ESPN Insider / The Athletic (+ third-party mirrors) | 2014–2026, long-format by QB |
| [`qb_starters`](sources/qb_starters/) | Primary starting QB per team per season, joined to that QB's `qb_tiers` tier | Pro-Football-Reference | 2014–2025 |
| [`turnovers`](sources/turnovers/) | Team turnover differential (INT/fumble takeaway & giveaway split) + a fumble-recovery-rate "luck" lens | footballdb.com | 2014–2025 |
| [`agl`](sources/agl/) | Adjusted Games Lost — injury-severity metric (Football Outsiders → FTN) | footballoutsiders.com (archived) / ftnfantasy.com | 2013–2025 |
| [`kickers`](sources/kickers/) | Kicker season stats (exact FG/PAT results and distances) + fantasy points under a custom kicker scoring system | `nflverse-data` play-by-play | 2022–2025 |
| [`punters`](sources/punters/) | Punter season stats (exact per-punt distance, inside-20) + fantasy points under a custom punter scoring system | `nflverse-data` play-by-play | 2022–2025 |
| [`underdog_adp`](sources/underdog_adp/) | Preseason (early/mid-August) fantasy ADP per player, plus each year's own `Diff`/`Notes` columns where present | Underdog Network | 2023–2025 |
| [`fantasy_finish`](sources/fantasy_finish/) | Actual end-of-season fantasy finish per player (total + per-game where published) | Underdog Network | 2023–2025 |
| [`wr_prop_totals`](sources/wr_prop_totals/) | Preseason WR prop lines (receiving yards / receptions / TDs) + projected PPR + ADP, from Fantasy Alarm's annual prop-value grid | Fantasy Alarm | 2022–2026 (2022 yards-only) |
| [`receiving_stats`](sources/receiving_stats/) | Regular-season receiving totals per player-season (targets, rec, yards, TDs, air yards, target share) + games played | `nflverse-data` season stats | 2021–2025 |

Run any auto-fetching source directly:

```bash
source venv/bin/activate
python3 nfl/sources/win_totals/pipeline.py [start_year] [end_year]
python3 nfl/sources/adp/pipeline.py [start_year] [end_year]
python3 nfl/sources/coaches/pipeline.py [start_year] [end_year]
python3 nfl/sources/kickers/pipeline.py [year ...]
python3 nfl/sources/punters/pipeline.py [year ...]
python3 nfl/sources/underdog_adp/pipeline.py
python3 nfl/sources/fantasy_finish/pipeline.py
python3 nfl/sources/wr_prop_totals/pipeline.py [year ...]
python3 nfl/sources/receiving_stats/pipeline.py [year ...]
```

Each is idempotent — it skips any year already cached in its `data/raw/`.
`game_results` is the exception: PFR is Cloudflare-protected, so its raw
HTML has to be fetched with a browser tool rather than auto-fetched (see
its README) — but re-running `python3 nfl/sources/game_results/pipeline.py`
is still safe/idempotent for the parsing step once cached. `kickers`,
`punters`, and `receiving_stats` source from `nflverse-data` instead of PFR
specifically to avoid that wall, so they auto-fetch like
`win_totals`/`adp`/`coaches` (`kickers`/`punters` roll up play-by-play via
`common/pbp.py`; `receiving_stats` reads the already-aggregated season
release directly).

## `common/`

- `team_codes.py` — every source's historical/relocated team names normalized
  to one canonical 3-letter abbreviation (e.g. Oakland/Las Vegas Raiders →
  `LV`), so datasets from different sources join cleanly on `(year, team)`.
  Also has `normalize_pfr_abbr()` / `normalize_nflverse_abbr()` for each
  site's own short codes (e.g. PFR's `KAN`/`GNB`, nflverse's `LA` for the
  Rams), which differ from the canonical abbreviation for a few teams.
- `http.py` — shared fetch-and-cache helper used by most sources'
  `pipeline.py` (HTML sources).
- `pbp.py` — shared play-by-play fetch helper (`kickers`/`punters`) that
  pulls a season's `nflverse-data` CSV with only the requested columns.
