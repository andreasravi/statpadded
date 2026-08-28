# Pythagorean Win Signal: Does the Line Predict Quality, Not Just Record?

Every other project in this repo tried to predict **`actual_wins`**. But
`actual_wins = pyth_wins + luck`, where `pyth_wins` is the point-differential
-based (Pythagorean) win estimate — "how good the team really was" — and
`luck` is how much a team over/underperformed its own point differential in
close games, which is close to unpredictable game-to-game noise.

This project re-targets **that same season's own `pyth_wins`** instead of
`actual_wins`, using the market's current-season win-total line as the
primary predictor plus the fundamentals already built for
[`win-total-model`](../win-total-model/) (coaching, schedule, prior
performance/luck, ADP). Two questions:

1. Does the line predict real quality better than it predicts the noisy
   win-loss record?
2. After the line, is there any fundamental left over in the residuals that
   the market isn't already pricing into its quality estimate?

**Important caveat:** `pyth_wins` for the season being "predicted" is only
knowable *after* that season is played — exactly like `actual_wins`, it's an
outcome, not a preseason input. This is **not a forecasting model**; it's a
diagnostic that uses a less noisy target to figure out whether the
unexplained variance everywhere else in this repo is missing signal or just
unpredictable luck.

## Data sources

All shared, all reused — nothing scraped for this project:

- [`nfl/sources/win_totals`](../../nfl/sources/win_totals/) — market line, actual wins
- [`nfl/sources/game_results`](../../nfl/sources/game_results/) — `pyth_wins`, point differential
- [`projects/win-total-model/data/features.csv`](../win-total-model/data/features.csv) — the fundamentals set (coaching, schedule, prior performance, ADP) built for that project, reused directly rather than rebuilt

## Pipeline

```bash
source venv/bin/activate
python3 projects/pyth-win-signal/scripts/analyze.py
```

Requires `projects/win-total-model/data/features.csv` to already exist (run
that project's `build_features.py` first if it doesn't). Writes
`data/merged.csv` and `data/oos_predictions.csv`, prints all stats.

## Findings (n=320, 2016–2025)

**1) The line predicts quality about as well, relatively, as it predicts the
record — but with a much smaller absolute error.**

| | r(line, ·) | R² | target std dev |
|---|---|---|---|
| `actual_wins` | +0.531 | 0.282 | 3.16 wins |
| `target_pyth_wins` | +0.530 | 0.281 | 2.44 wins |
| `target_luck` | +0.264 | 0.070 | 1.46 wins |

The R² is nearly identical (0.281 vs 0.282) — surprising, since `pyth_wins`
has less noise to explain. The reason: `line` is *also* mildly correlated
with `target_luck` (r=+0.26, not the ~0 you'd expect from pure randomness —
plausibly because favored/better teams close out close games slightly more
often, so some of "luck" is itself quality-adjacent rather than pure noise).
Net effect: because `pyth_wins` itself has a smaller noise floor (std 2.44 vs
3.16 wins), the model's *absolute* residual error on quality is meaningfully
tighter — implied RMSE ≈2.07 wins on `pyth_wins` vs ≈2.68 wins on
`actual_wins`. Put simply: the market's line is a noticeably better predictor
of "how good is this team really" than it looks like from its performance
against the actual standings, because a big chunk of the standings' spread
is luck nobody can predict.

**2) Adding fundamentals barely moves quality R² (+0.011), and none of them
are individually significant** once `win_total_line` is in the model —
`new_coach`, `sos_this_year_line`, `prior_year_under`, `prior_beat_margin`,
`prior_actual_wins`, `prior_pyth_wins` all sit at p>0.13.

**3) Residual scan — no signal at all, cleaner null than anywhere else in
this repo.** Correlating each of 11 available fundamentals (the 6 above plus
`prior_avg_point_diff`, `prior_luck`, `sos_prior_year_wins`, ADP top-100
count, ADP linear weight) against `(pyth_wins − line-only prediction)`:
**0 of 11 cross p<0.05** (best: `prior_beat_margin` r=−0.078, p=0.16). Every
other project in this repo tested fundamentals against the noisy
`actual_wins`/`beat_margin`, where a real signal could in principle be
masked by luck-driven noise. Here, even with luck mostly stripped out of the
target, nothing shows up — the market's line isn't leaving a public
fundamental on the table when it comes to assessing a team's real quality.

**4) Folding the (non-significant) top residual hit back into an
`actual_wins` walk-forward backtest — still no edge.** `line +
prior_beat_margin`, refit expanding-window, tested 2020–2025 (192 bets):
MAE 2.260 vs the market's own 2.247, and betting every disagreement went
**−10.4% ROI (p=0.127)** — not significant, and worse than doing nothing.

## Bottom line

Re-targeting Pythagorean wins instead of actual wins confirms *why* nothing
in this repo has found an edge: a large share of what looked like
"unexplained variance" in the actual-wins models is just the ~1.5-win
standard deviation of in-season luck, which is structurally unpredictable —
not a sign the market or the fundamentals are missing something. Tested
against the cleaner, luck-stripped target, the market's preseason line
already captures essentially all of what these public fundamentals know
about a team's true quality (0/11 residual hits), and the one weak
candidate that did surface doesn't survive contact with a real, odds-priced
backtest.
