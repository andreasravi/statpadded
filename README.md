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
- [`projects/pyth-win-signal`](projects/pyth-win-signal/) — re-targets
  Pythagorean (point-differential-based) wins instead of actual wins to
  separate luck from signal: does the market line predict true team quality
  better than the noisy record, and is anything left in the residuals?
- [`projects/momentum-signals`](projects/momentum-signals/) — borrows three
  finance momentum/reversal constructions (time-series, fundamental,
  cross-sectional winners-minus-losers) and tests each as a real,
  odds-priced betting signal on win-total `beat_margin`.
- [`projects/schedule-swing-signal`](projects/schedule-swing-signal/) — how
  much does a team's win total actually move the season after its strength
  of schedule swings hard, once you control for ordinary mean reversion —
  sized against the 2026 Patriots (easiest 2025 schedule in the NFL, into
  the single largest projected schedule swing in the 2015–2025 sample).
- [`projects/kicker-punter-model`](projects/kicker-punter-model/) — a basic
  kicker/punter fantasy projection model for 2026: kicker scoring is
  regressed on team offense to get an opportunity-adjusted ability residual
  per kicker; punters are explored openly first (it turns out punt *volume*
  tracks a *bad* offense while per-punt skill is team-independent) before
  the same residual approach is applied.
- [`projects/pyth-win-model`](projects/pyth-win-model/) — predicts
  Pythagorean wins from QB tier, coaching tenure, schedule delta,
  turnover-luck and injury-severity mean reversion, plus an explicit test
  of whether team quality interacts with momentum/coaching/QB tier rather
  than just adding to them (OLS, OLS+interactions, Ridge/Lasso, Random
  Forest) — the interactions get weak in-sample support but hurt the
  out-of-sample backtest, so the plain model wins.
- [`projects/preseason-adp-moves`](projects/preseason-adp-moves/) — two
  angles on preseason fantasy-ADP moves and injuries. Part 1: do the
  biggest preseason ADP moves cluster around injury/suspension/trade news?
  (a same-page `Diff` column looked like the right tool but turned out to
  be noise — a known ACL/MCL tear barely moves it — so this instead diffs
  two independent ADP reads, format-corrected; mostly a null result, with
  one clean exception; team-level ADP volatility doesn't predict a team's
  actual injury toll either). Part 2, working backward from actual
  end-of-season fantasy finish: which players busted hardest relative to
  their August draft slot, and how many of those were genuinely hurt in
  the preseason rather than during the season? (about half of the
  biggest candidates, verified against news coverage — Christian
  McCaffrey's 2024 is the clean, large example).
- [`projects/prop-accuracy`](projects/prop-accuracy/) — grades preseason
  player prop lines against actual regular-season production, WR and RB,
  same method in one directory.
  - **WR** (receiving yards / receptions / TDs, Fantasy Alarm 2022–26):
    lines run slightly rich and getting richer (yards O/U cleared 46% →
    35% by season); no year-over-year carryover (r ≈ 0); the repeatable
    structure is by line size — fade 8+ TD lines and the 1,000–1,200 yard
    "dead zone", lean overs on healthy sub-1,000-yard receivers. The
    strongest single signal: overs on WRs whose line got shaded down for a
    weak/unproven QB. Self-contained visual write-up + 2026 watch list.
  - **RB** (rushing yards / TDs, Fantasy Points 2023–25 + SportsBetting.ag
    2022; 134 graded RB-seasons): the rushing-yards *under* is almost
    entirely an injury bet — a back who plays ≥14 games clears the over
    **64%**, one who doesn't clears it **3%** (1 of 38). The 1,000–1,200
    dead zone reappears. Unlike WR, team context (QB tier, win total)
    explains almost nothing (OLS R² ≈ 0.01) once you account for health.

## NFL data sources

See [`nfl/README.md`](nfl/README.md) for the full list and how to run each
pipeline (win totals, ADP, coaches — Covers.com / FantasyData /
MyFootballToolbox.com).

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install pandas beautifulsoup4 scipy matplotlib lxml scikit-learn statsmodels
```
