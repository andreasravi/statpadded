# ADP vs Win Totals

Does a team stacked with recognizable fantasy-football names actually win more —
and is that something the Vegas win-total market has already priced in?

## Data sources

Both are shared, reusable pipelines under [`nfl/sources/`](../../nfl/sources/)
rather than duplicated in this project:

- [`nfl/sources/adp`](../../nfl/sources/adp/) — FantasyData 2QB/superflex ADP,
  top 100 players (free-tier cap), 2015–2025
- [`nfl/sources/win_totals`](../../nfl/sources/win_totals/) — Covers.com
  Sports Odds History, NFL win totals, 2015–2025

Seasons covered: **2015–2025** (11 completed seasons × 32 teams = 352 team-seasons).

## Pipeline

Run from the repo root with the shared `venv` active:

```bash
source venv/bin/activate
python3 nfl/sources/adp/pipeline.py           # -> nfl/sources/adp/data/adp.csv
python3 nfl/sources/win_totals/pipeline.py    # -> nfl/sources/win_totals/data/win_totals.csv
python3 projects/adp-win-correlation/scripts/analyze.py   # -> data/merged.csv + printed stats
```

Both source pipelines skip any year already cached in their `data/raw/`.

## Files

```
scripts/
  analyze.py      merges the two shared datasets, computes correlations,
                   writes data/merged.csv
data/
  merged.csv       one row per team-season with all ADP metrics + win outcomes
```

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
