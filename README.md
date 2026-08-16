# statpadded

A collection of small sports-data / stats projects.

- **`nfl/`** — shared, reusable NFL data pipelines (fetch + cache + parse).
  Any project that needs win totals, ADP, coaching data, etc. reads from here
  instead of re-scraping its own copy.
- **`projects/<name>/`** — one folder per analysis. Each has its own README,
  merge/analysis scripts, and output data, and pulls its inputs from `nfl/`
  (or a future `<sport>/` sibling) rather than duplicating fetch logic.

## Layout

```
nfl/                          shared NFL data sources
  common/                      team-name normalization, fetch/cache helper
  sources/<name>/
    pipeline.py                 fetch (cached) + parse -> data/*.csv
    data/raw/                   cached raw HTML, never re-fetched once cached
    data/*.csv                  the clean dataset

projects/<name>/               one analysis per folder
  README.md                     what it does, findings
  scripts/analyze.py            reads from nfl/sources/*, writes data/merged.csv
  data/merged.csv

venv/                          shared Python virtualenv (gitignored)
```

## Projects

- [`projects/adp-win-correlation`](projects/adp-win-correlation/) — does a
  team's count of recognizable fantasy-football (ADP) players predict its
  win total, or is that already priced into the Vegas win-total line?
- [`projects/coaching-win-impact`](projects/coaching-win-impact/) — do new
  head coaches predict year-over-year win improvement, and do new-coach
  teams beat or miss their Vegas win total with any consistency?
- [`projects/win-total-signals`](projects/win-total-signals/) — do big
  year-over-year jumps in a team's win-total line, or multi-year over/under
  streaks, predict anything about the following season?
- [`projects/win-total-model`](projects/win-total-model/) — a 6-feature
  model (coaching, schedule, streak, point differential) predicting win
  totals, backtested as a betting strategy and applied to 2026

## NFL data sources

See [`nfl/README.md`](nfl/README.md) for the full list and how to run each
pipeline (win totals, ADP, coaches — Covers.com / FantasyData /
MyFootballToolbox.com).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas beautifulsoup4 scipy matplotlib lxml
```
