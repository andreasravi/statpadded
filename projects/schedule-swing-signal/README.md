# schedule-swing-signal

Motivating question: the 2026 narrative is "Patriots regress hard — 14 wins
last year, way tougher schedule this year." Is that a real, sized effect,
or a story people tell about a small number?

This measures, historically, what a team's win total (and Pythagorean win
total — point-differential-based, luck-stripped) does the season after its
strength of schedule (SOS) swings, and sizes that against the much bigger
force already at work: ordinary mean reversion.

## Three SOS measures (all on a wins scale, so directly comparable)

1. **`sos_actual_wins`** — retrospective. Average *actual* wins of a
   team's opponents in that same season. "How hard did this schedule
   really turn out to be." Not precomputed anywhere else in this repo —
   built here from `game_results` (opponent list) joined to `win_totals`
   (opponent actual wins).
2. **`sos_pyth_wins`** — same idea, luck-adjusted: opponents' Pythagorean
   wins instead of their actual record, so a schedule doesn't look hard
   just because three opponents won a bunch of one-score games.
3. **`sos_next_yr_line`** — prospective. Average Vegas preseason
   win-total line of a team's opponents in the *following* season — the
   market's own forecast of the upcoming schedule. Already exists as
   `sos_this_year_line` in `nfl/sources/game_results/data/strength_of_schedule.csv`;
   shifted back a year here to attach it to the prior season's row.

```
schedule_delta_actual = sos_next_yr_line − sos_actual_wins
schedule_delta_pyth   = sos_next_yr_line − sos_pyth_wins
```
Positive = the schedule is projected to get harder than it actually was.

Outcomes: `win_change = actual_wins(Y+1) − actual_wins(Y)`,
`pyth_win_change = pyth_wins(Y+1) − pyth_wins(Y)`.

**Sample:** all 32 teams, seasons 2015–2024 paired with the following
season (2016–2025) — 320 team-season pairs, every one where both years'
data exist.

## Findings

**The schedule-swing effect is real but small next to mean reversion.**

| Model | coef on schedule_delta | p | R² |
|---|---|---|---|
| `win_change ~ schedule_delta_actual` (alone) | −2.05 | <0.001 | 0.11 |
| `win_change ~ schedule_delta_actual + actual_wins` | **−0.66** | 0.038 | 0.32 |
| `pyth_win_change ~ schedule_delta_pyth` (alone) | −2.02 | <0.001 | 0.13 |
| `pyth_win_change ~ schedule_delta_pyth + pyth_wins` | **−0.86** | 0.003 | 0.31 |

The univariate coefficient (~−2 wins per +1 win of average-opponent-quality
increase) is badly inflated by confounding: teams that win a lot tend to
have had an easy schedule (weak-schedule feedback loop) and are already
overdue to regress for reasons that have nothing to do with schedule. Once
you control for the team's own win total that season (`actual_wins`, the
mean-reversion term — coefficient **−0.58**, the dominant force, `p<0.001`),
the schedule's own marginal effect drops to **about 0.6–0.9 wins lost per
+1 win of average-opponent-quality increase**. Real, statistically
distinguishable from zero, but roughly a third to a half the size of the
naive univariate number, and small next to reversion itself.

**Quartile view (unconditional, includes the reversion confound):**

| schedule_delta_actual quartile | avg win_change |
|---|---|
| Q1 — schedule got easier | +1.33 |
| Q2 | +0.75 |
| Q3 | −0.34 |
| Q4 — schedule got much harder | −1.54 |

A clean, monotonic ~2.9-win spread from best to worst quartile — but most
of that gap is reversion riding along with schedule direction, not schedule
causing it on its own (see the controlled regression above for the
isolated piece).

**Outlier scan — won ≥10 games on a bottom-quartile-easiest schedule, then
the schedule swung into the top quartile (hardest)** (n=36, 2015–2024, both
sides matched at the 25% cut — see note below): average `win_change` =
**−2.44**, vs. **−1.89** for *all* ≥10-win teams regardless of what
happened to their schedule. So this specific pattern — "had it easy,
cashed in, then got a much harder slate" — costs about **0.5–0.6 wins
beyond ordinary regression on average**, but the tail is long: CHI 2018
(12→8), WAS 2024 (12→5), DAL 2023 (12→7), CAR 2015 (15→6), JAX 2017 (10→5),
NYJ 2015 (10→5) all cratered by 4+ wins — though every one of those also
has a real non-schedule story (coaching change, QB injury/departure,
roster teardown), so treat the tail as "this combination correlates with
collapse," not "schedule alone did it." The reverse bucket (≥10 wins,
schedule got *easier*) shows almost no relief (−2.10, n=10, barely
different from the −1.89 baseline) — a small, noisy sample, but it's a
reminder the effect isn't symmetric or dependable in either direction at
the individual-team level.

*Threshold note:* an earlier pass cut "easy" at the bottom tercile but
"got harder" at the top quartile, with no principled reason for the two
different splits — a plain mismatch, not a deliberate choice. The result
is stable regardless (bucket average lands −2.3 to −2.4 across
quartile/quartile, tercile/tercile, 40/40, and median/median cuts, all
against the same −1.89 baseline), but the number now reported uses matched
quartiles on both sides.

## Case study: Patriots 2025 → 2026

- **2025 schedule was the single easiest in the NFL** by both measures:
  `sos_actual_wins` = 6.71 (league avg 8.50), `sos_pyth_wins` = 6.79
  (league avg 8.48) — rank 1 of 32 either way. NE went 14–3 against that,
  outscoring their point differential's implied 12.46 Pythagorean wins by
  +1.54 (modest positive luck, not the main story).
- **2026 opponents** (AFC East ×2, full AFC West, full NFC North, plus
  PIT/JAX/SEA — [patriots.com](https://www.patriots.com/news/new-england-patriots-finalize-2026-opponents),
  [NESN](https://nesn.com/new-england-patriots/news/patriots-schedule-2026-games-dates-list-season/33b51d5ff01cee9fb1da8e4d))
  average **8.48 expected wins** per the live Kalshi market
  (`nfl/sources/kalshi_win_totals`) — there's no Vegas preseason line for
  2026 yet, so this is the closest current-market equivalent.
- **`schedule_delta_actual` = +1.78, `schedule_delta_pyth` = +1.69** — both
  land at the **100th percentile of the 320-team-season sample**: the
  single largest projected schedule swing of anyone, any year, 2015–2025
  (edges out GB's 2020→2021 jump, the previous record-holder at +1.83).
  The narrative is not wrong about the direction or the size of the swing
  — it's the most extreme case in eleven years of data.
- **Model-implied 2026 win total: ~9.6 wins** (`win_change` = −4.4 from
  the controlled regression). Split that: about **−3.2 wins is ordinary
  mean reversion** from being a 14-win team (would apply on a flat
  schedule too), and about **−1.2 wins is the incremental hit from this
  specific schedule swing being the most extreme on record**. The
  Pythagorean-wins version of the same model lands even lower, ~9.0.
- **Kalshi's own live 2026 NE line is already ~9.8 expected wins** — i.e.
  the market has already priced in almost exactly this size of decline.
  The schedule-difficulty narrative is directionally correct and the
  magnitude checks out against history, but it doesn't look like an edge
  *against the current market price* — the market isn't sleeping on it.

## Level regression: pyth_wins(T) on the pure hindsight schedule swing

The regressions above predict the *change* in wins, and lean on
`sos_next_yr_line` (a Vegas preseason line) for the not-yet-played side of
the schedule delta — necessary for the 2026 case study, but it mixes a
market forecast (noisy) with a realized outcome (exact) on the two sides of
the same subtraction.

This version instead regresses the *level* of `pyth_wins(T)` on two fully
realized (hindsight) inputs — usable for any pair of seasons that have
both already happened:

```
pyth_wins(T) = β0 + β1 · opp_pyth_delta + β2 · pyth_wins(T−1)
opp_pyth_delta = sos_pyth_wins(T) − sos_pyth_wins(T−1)   [both realized]
```

n=320 (seasons 2016–2025, same universe as above, one year later start
since T−1 needs its own value):

| term | coef | p | 
|---|---|---|
| intercept | +3.88 | <0.001 |
| `opp_pyth_delta` | **−1.88** | <0.001 |
| `pyth_wins(T−1)` | +0.54 | <0.001 |
| R² | 0.324 | n=320 |

Stripping out the market-proxy noise roughly **doubles** the apparent
schedule coefficient versus the change-regression in the section above
(−1.88 vs. −0.86) — using a Vegas/market line as a stand-in for one side of
a schedule-strength delta was quietly attenuating the estimated effect.
This is the more trustworthy read of the *true* historical relationship
between a schedule swing and next season's Pythagorean win total, precisely
because both sides of the swing are known outcomes, not forecasts.

**Applying it to the Patriots** (T=2026, T−1=2025) requires substituting
Kalshi's live opponent-average expected wins (8.48) for the still-unrealized
`sos_pyth_wins(2026)` — the same proxy problem as the case study above, so
treat this as extrapolation, not hindsight measurement:

| input | value |
|---|---|
| `pyth_wins(2025)` | 12.46 |
| `sos_pyth_wins(2025)` | 6.79 |
| `sos_pyth_wins(2026)` proxy (Kalshi opponent avg) | 8.48 |
| `opp_pyth_delta` | **+1.69** |
| → percentile vs. 320 realized historical deltas | **100th** — exceeds the max ever observed (1.51) |
| **model-implied `pyth_wins(2026)`** | **7.45** (90% prediction interval 4.1–10.8) |
| — of which pure mean-reversion off 2025 (delta held flat) | 10.62 |
| — incremental hit from this specific schedule swing | **−3.17 wins** |

This model is notably more bearish than the change-based one (7.45 vs. ~9.0
projected Pythagorean wins) because the coefficient itself is roughly twice
as large once the market-noise contamination is removed. But it should be
read with real caution: NE's implied 2026 delta (+1.69) sits *beyond* the
largest hindsight swing ever observed in the training data (1.51) — this
prediction is extrapolating past the edge of the sample, exactly where a
linear model is least trustworthy, and the 90% prediction interval (4.1 to
10.8 wins) is wide enough to cover almost anything from a lost season to a
perfectly ordinary one.

## Betting backtest: does it beat Vegas?

Every regression above fits on the full 2015–2025 sample and reads its
coefficients — useful for sizing the historical effect, but not a fair
betting test, since the model "knows" seasons it would be wagering on.
`scripts/backtest.py` runs the honest version: an expanding-window
walk-forward backtest (refit on strictly prior seasons only, same
convention as [`projects/win-total-model`](../win-total-model/)), testing
2020–2025, betting whichever side (over/under) each model disagrees with
that season's real Vegas win-total line on, settled at real American odds
via `nfl/common/betting.py`.

Three models, all using only information a bettor actually has before the
season (`sos_this_year_line` — opponents' own preseason lines — not any
realized/hindsight opponent outcome):

| Model | Predicts `next_actual_wins` from |
|---|---|
| `reversion_only` | prior actual wins (no schedule input — the control) |
| `schedule_actual` | prior actual wins + `schedule_delta_actual` |
| `schedule_pyth` | prior *Pythagorean* wins + `schedule_delta_pyth` (luck-adjusted — the "more sophisticated" SOS treatment) |

**Results, n=192 out-of-sample team-seasons (2020–2025):**

| Model | Model MAE | Market MAE | min_edge≥1.0: n / win% / ROI / p | min_edge≥2.0: n / win% / ROI / p |
|---|---|---|---|---|
| `reversion_only` | 2.489 | 2.247 | 81 / 53.1% / −0.5% / p=0.96 | 25 / 56.0% / +3.1% / p=0.86 |
| `schedule_actual` | 2.472 | 2.247 | 83 / 53.0% / −1.0% / p=0.92 | 21 / 61.9% / +16.8% / p=0.39 |
| `schedule_pyth` | 2.482 | 2.247 | 77 / 50.6% / −0.0% / p=1.00 | 16 / 62.5% / +21.7% / p=0.34 |

**Verdict: no.** All three models' out-of-sample MAE (2.47–2.49 wins) is
*worse* than just using the market's own preseason line directly (2.25) —
Vegas's line is a better predictor of actual wins than any of these
regressions on their own. At the standard min_edge≥1.0 threshold none of
the three shows a real edge (win% ~50–53%, ROI roughly flat, p-values all
≥0.9 — indistinguishable from a coin flip). The eye-catching numbers at
min_edge≥2.0 (+17–22% ROI) come from only 16–21 bets each — noisy, not
significant (p≈0.35–0.39), and exactly the kind of result that stops
looking good the moment you check whether it survives on more data. The
"more sophisticated" luck-adjusted (`schedule_pyth`) version doesn't
reliably beat the plain-wins version either — comparable or marginally
better at the thin high-edge cut, worse at the standard one.

This lines up with the Patriots case study's own honest caveat: Kalshi's
live 2026 NE line already sits close to what the schedule-swing math would
imply. The schedule-swing story is real as a *description* of what
happened to teams historically (see the regressions above), but there's no
evidence here that it's an exploitable, standalone edge against a market
that's presumably already doing something similar — pricing next season's
schedule into the number before you ever see it.

Run it: `python3 projects/schedule-swing-signal/scripts/backtest.py`.
Out-of-sample predictions for the `schedule_actual` model are saved to
`data/backtest_oos_predictions.csv`.

## Caveats

- n=320 team-seasons is a reasonably sized sample for the league-wide
  regressions, but the Patriots case study is n=1 — the historical
  coefficients are averages across very different rosters, coaches, and
  eras; treat the ~9–9.6 projection as a magnitude sanity check, not a
  forecast.
- `sos_next_yr_line` (used for the 2015–2025 pairs) and the Kalshi
  `expected_wins` snapshot (used for the 2026 case study) aren't quite the
  same instrument — one is a settled preseason sportsbook line, the other
  a live prediction-market snapshot taken today. Close enough to compare,
  not identical.
- The 2026 opponent list is hand-entered from public schedule-release
  reporting (see links above), not pulled from `game_results.csv`, since
  PFR doesn't have a 2026 schedule page to scrape yet.
- Outlier-bucket teams almost always have a second story (new coach, QB
  change, injuries) running alongside the schedule swing — this analysis
  can't cleanly separate "schedule did it" from "everything else that
  happens to correlate with a big schedule swing."

## Run

```bash
source venv/bin/activate
python3 projects/schedule-swing-signal/scripts/analyze.py
```

Outputs `data/merged.csv` — one row per team-season (2015–2024) with both
schedule-difficulty measures, the following season's schedule-difficulty
measure, and both win-change outcomes.
