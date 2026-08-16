# ADP vs Win Totals

Does a team stacked with recognizable fantasy-football names actually win more —
and is that something the Vegas win-total market has already priced in?

## Data sources

- **FantasyData** 2QB/superflex ADP, top 100 players (free-tier cap), per season
  → `https://fantasydata.com/nfl/2qb-adp?season={year}&team=`
- **Covers.com** Sports Odds History, NFL regular-season win totals per season
  (market line, over/under odds, actual wins, result)
  → `https://www.covers.com/sportsoddshistory/nfl-win/?y={year}&sa=nfl&t=win`

Seasons covered: **2015–2025** (11 completed seasons × 32 teams = 352 team-seasons).

## Pipeline

Run from the repo root with the shared `venv` active:

```bash
source venv/bin/activate
python3 projects/adp-win-correlation/scripts/fetch_data.py   # cache raw HTML -> data/raw/
python3 projects/adp-win-correlation/scripts/parse_data.py   # -> data/adp.csv, data/win_totals.csv
python3 projects/adp-win-correlation/scripts/analyze.py      # -> data/merged.csv + printed stats
```

`fetch_data.py` skips any year already cached in `data/raw/`, so re-running the
pipeline after a code change doesn't re-hit either site.

## Files

```
scripts/
  fetch_data.py   fetch + cache raw HTML per season (idempotent)
  parse_data.py   HTML -> data/adp.csv, data/win_totals.csv
  analyze.py      merges both, computes correlations, writes data/merged.csv
data/
  raw/            cached HTML, one file per (source, year)
  adp.csv         year, rank, name, team, pos, pos_rank, adp
  win_totals.csv  year, team, win_total_line, over_odds, under_odds, actual_wins, result
  merged.csv      one row per team-season with all ADP metrics + win outcomes
```

## Team identity normalization

FantasyData always labels a franchise by its *current* city/name; Covers.com uses
the name as it was *that season*. `parse_data.py` maps both to one abbreviation:
Oakland/Las Vegas Raiders → `LV`, San Diego/LA Chargers → `LAC`, St. Louis/LA Rams
→ `LAR`, Washington Redskins/Football Team/Commanders → `WAS`.

## Metrics tested

- `top25_count` / `top50_count` / `top100_count` — plain head count of a team's
  players inside that ADP cutoff
- `linear_weight` — rank-weighted score, `sum(101 - rank)` for each top-100 player
  (gentle taper; rewards roster depth of "pretty good" names)
- `reciprocal_weight` — `sum(100 / rank)` (steep; rewards having one true
  superstar over several good-not-great names)
- `best_rank` — the ADP rank of the team's single highest-drafted player

Each is checked against `actual_wins`, `win_total_line` (the market's preseason
number), and `beat_margin` (`actual_wins - win_total_line`).

## Findings (see `analyze.py` output / the published artifact for full numbers)

- Rank-weighted metrics correlate with actual wins **better** than a plain head
  count (`linear_weight` r≈+0.38 vs `top100_count` r≈+0.32) — so *how good* the
  players are matters a bit more than *how many* clear the top-100 bar.
- But every metric — count, weighted, or best-player-rank — correlates with the
  **market win-total line** even more strongly than with real wins. Vegas is
  already pricing roster star-power in, and pricing it in harder than it
  actually pays off.
- None of the metrics predict `beat_margin` (beating the line) at a level
  distinguishable from zero. Rank-weighting doesn't uncover a hidden edge — it
  just makes the "priced-in" signal a little cleaner to see.
