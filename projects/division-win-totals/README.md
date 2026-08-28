# division-win-totals

Which NFL divisions does the market think are unusually strong or weak going
into 2026? Sum each division's four win-total lines, and compare that sum to
the same division-sum distribution over 2015–2025 as a z-score.

- **2026 lines:** [`nfl/sources/kalshi_win_totals`](../../nfl/sources/kalshi_win_totals/)
  — live Kalshi-implied win-total line + expected wins per team.
- **History:** [`nfl/sources/win_totals`](../../nfl/sources/win_totals/) —
  Covers.com sportsbook win-total lines, 2015–2025.

## Method

```
python3 projects/division-win-totals/scripts/analyze.py
```

For each division: `sum_implied_line` = the four 2026 Kalshi lines added
up; `hist_mean` / `hist_std` = mean and population SD of that division's
summed sportsbook line across 2015–2025 (years where all four teams have a
line); `z_score` = how far 2026 sits from that history. `|z| >= 1.5` is
flagged as an outlier.

## Outputs

- `data/division_sums.csv` — one row per division: 2026 line sum, expected-win
  sum, historical mean/std, z-score.
- `data/division_data.json` — same plus each division's full 2015–2025
  history series and its 2026 team breakdown (for charting).

A league-wide sanity check prints alongside: summed expected wins should
land near 272 (17 games × 32 teams ÷ 2).
