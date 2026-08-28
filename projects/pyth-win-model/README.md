# Pyth Win Model: QB Tier, Coaching Tenure, Schedule, Turnover Luck, and Injuries

A from-scratch win-total model targeting **Pythagorean wins** (not
`actual_wins`) — per [`pyth-win-signal`](../pyth-win-signal/)'s own finding
that the market's line predicts real team quality with a much smaller
noise floor than it predicts the win-loss record, `pyth_wins` is the fairer
target to isolate real signal in.

Six inputs, three of them newly built this session
([`nfl/sources/turnovers`](../../nfl/sources/turnovers/),
[`nfl/sources/agl`](../../nfl/sources/agl/),
[`nfl/sources/qb_starters`](../../nfl/sources/qb_starters/)):

| Feature | Timing | What |
|---|---|---|
| `qb_tier_filled` + `has_qb_tier` | current season | starter's Sando/Athletic QB Tier (1=best, 5=worst); see "Handling missing QB tiers" below |
| `coach_tenure_bucket` | current season | Yr1 / Yr2–3 / Yr4+ with the same team |
| `prior_pyth_wins` | prior season | last year's point-differential-based win estimate |
| `schedule_delta_pyth` | current season's opponents, prior season's own SOS | reused from `schedule-swing-signal` |
| `prior_turnover_diff_per_game` | prior season | turnover margin, mean-reversion framing |
| `agl_bucket` | prior season | injury severity (Adjusted Games Lost), **quartile-binned, not linear** — see below |
| `prior_beat_margin` | prior season | last year's `actual_wins − line`, the "momentum" input |

**Timing discipline:** `qb_tier`/`coach_tenure_bucket` use the *current*
season because both are legitimately known before kickoff (roster and
coaching moves happen in the offseason; Sando's survey is itself a
preseason publication). Turnover luck and AGL are **outcomes of the season
they're measured in** — you can't know a team's in-season fumble-recovery
rate or injury total before that season happens — so they only enter
lagged, as mean-reversion bets on last year's extremes, never same-season.

## The actual question this project tests

The user's hypothesis: team quality, momentum, coaching change, and QB
tier probably don't just add up — their *effects on each other* matter. A
coaching change probably moves a bad team more than a good one; beating
the line big probably means something different for a good team
(confirmation) than a bad one (a fluke due to revert). Four techniques,
increasingly willing to find that structure, decreasingly trusted as an
actual betting model:

1. **OLS baseline** (no interactions) — the honest starting point.
2. **OLS + hand-picked interactions** — `quality_bucket` (tercile of
   `prior_pyth_wins`) × `prior_beat_margin`, × `coach_tenure_bucket`, ×
   `qb_tier_filled`. The main event.
3. **Ridge/Lasso** (standardized, CV-selected alpha) on the same
   interaction feature set — diagnostic: does Lasso's automatic selection
   agree with the hand-picked interactions, or zero them out?
4. **Random Forest** (5-fold CV, feature importances) — diagnostic only,
   checks for nonlinear structure OLS's linear terms might miss. Not
   walk-forward backtested.

Only (1) and (2) go through the honest walk-forward backtest (expanding
window, strictly prior seasons, 2020–2025) — this repo's standard
discipline for telling "explains more in-sample" from "actually helps."

## Two follow-up questions, investigated and folded in

**Is `qb_tier` actually linear, or does it need to be more granular?**
Tested `qb_tier` as a full categorical (4 free dummies) against the linear
version, and separately tested whether the QB's within-tier percentile
rank (`rank_in_season`, normalized by the number of QBs each source
covered that season, since sources vary from 21 to 62 QBs) adds anything
on top of the tier bucket. **Neither helps:** categorical tier doesn't fit
significantly better than linear (nested F-test p=0.835, and its AIC is
actually *worse* — 1106.8 vs 1101.7), and adding percentile rank on top of
tier doesn't move the needle either (p=0.477). `qb_tier` stays linear —
not a default, an empirically checked choice.

**Does `prior_agl` have real nonlinear structure?** The Random Forest
diagnostic flagged it (0.10 importance despite a near-zero, non-significant
linear OLS coefficient), so this got a real test. A quadratic term isn't
significant (p=0.732) — it's not a smooth curve. But **quartile-BINNING
`prior_agl` fits significantly better** (nested F-test p=0.005, AIC
improves 1101.7→1094.6), and the shape is a real finding, not what a
"more injuries = worse next year" story would predict: the *healthiest*
quartile is the outlier, sitting *below* every other quartile including
the most-injured one. Read as mean reversion — the healthiest team last
year was probably a little lucky and due to normalize down, while a team
that ate a bad injury year isn't further penalized the year after.
**Verified out-of-sample too** (walk-forward MAE 1.774 vs 1.839 for the
linear version, quartile edges recomputed from each training fold only —
no look-ahead), so unlike the interaction terms, this one earned its way
into the model rather than just fitting the training window.

## Handling missing QB tiers (don't drop them — they're informative)

21% of team-seasons (65/320) have no `qb_starters`-matched tier, and this
missingness isn't random. Checked directly against the raw source content
(not just the joined output) and found two distinct, both fully
structural, causes:

1. **True rookie-debut-season starters are excluded from Sando's survey
   entirely**, confirmed by reading the actual 2021 article
   (`nfl/sources/qb_tiers/data/raw/athletic_2021.json`) — every one of that
   year's five notable rookie starters (Trevor Lawrence, Justin Fields,
   Zach Wilson, Mac Jones — a Pro Bowler that year — and Davis Mills) is
   absent from the real 34-QB list, and each one's *first* covered season
   in `qb_tiers.csv` is exactly the year after their debut. This pattern
   held for every rookie-season case checked (13/13). The panel simply
   hasn't formed an opinion on a QB with zero career starts yet — there is
   nothing further to scrape here.
2. **2014/2016/2017 specifically exclude established starters still on
   their rookie contract** — already documented in `qb_tiers/README.md`:
   Over The Cap's republished table explicitly says *"I only wanted to
   look at veteran players (that means no Luck, Bradford, Newton,
   etc…)."* This drops multi-year starters like Cam Newton, Andrew Luck,
   Russell Wilson, and Andy Dalton from those specific years even though
   they were fully established. The original paywalled ESPN Insider
   pieces have no known non-paywalled mirror, per that README.

Both are real absences in the source, not a scraping failure — so instead
of dropping those 65 rows (the prior version of this model did, cutting
the usable sample from 320 to 255), missingness is now treated as
informative: `has_qb_tier` (0/1) plus `qb_tier_filled` (the training-set
mean tier when missing, so the linear term doesn't blow up on a
placeholder). This recovered the full sample, and `has_qb_tier` turned out
to be a real, significant predictor in its own right (+1.35 wins,
p<0.001) — teams starting an unrated (rookie or rookie-contract) QB
predict meaningfully worse than the tier-implied level alone would
suggest, independent of the linear tier score.

## Findings (n=320, full sample)

**A real bug caught along the way:** `new_coach` (0/1) turns out to be an
*exact* linear function of `coach_tenure_bucket=='Yr1'` — a coaching
change is definitionally what resets tenure to 1. Including both made the
design matrix rank-deficient (their sum plus the other tenure dummies
equals the intercept column exactly), which doesn't error but silently
makes those specific coefficients not individually identified — an early
run of this model reported `Yr2-3`/`Yr4+` as *highly* significant
(p<0.001) purely as an artifact of that redundancy. `new_coach` was
dropped as a separate term; `coach_tenure_bucket` alone already carries
that information cleanly.

**1) Baseline OLS (n=320, R²=0.274):** `qb_tier_filled` (−0.451, p=0.004,
correct sign), `has_qb_tier` (+1.350, p<0.001, see above),
`prior_pyth_wins` (+0.415, p<0.001), `schedule_delta_pyth` (−0.623,
p=0.032, matches `schedule-swing-signal`'s own sign). The AGL quartile
buckets sit around p=0.10–0.56 individually but earned their spot via the
nested F-test above, not by clearing 0.05 term-by-term.
`prior_turnover_diff_per_game` drops to non-significance in this larger
sample (p=0.210, was p=0.028 at n=255) — worth flagging honestly rather
than only reporting the version that looked cleaner. `prior_beat_margin`
and `coach_tenure_bucket` remain non-significant on their own, consistent
with `momentum-signals`' univariate null even inside a fuller model.

**2) OLS + quality-bucket interactions (n=320, R²=0.310):** ΔR²=+0.037,
F-test p=0.112 — closer to significant than the n=255 version (p=0.352)
but still short of it. Two coaching-tenure interactions are now marginal
(`Yr2-3 × mid`, p=0.088; `Yr4+ × mid`, p=0.056) — the same terms Lasso
independently kept.

**3) Ridge/Lasso corroborate which interactions are real vs noise.**
Lasso zeroes out the `quality_bucket_good` main effect but keeps
meaningful weight on the coaching-tenure × quality interactions
(`tenure_Yr4+_x_good`: 0.748, `tenure_Yr2-3_x_mid`: 0.375) — the same
pair the OLS F-test flagged as marginal, arrived at independently.

**4) Random Forest (5-fold CV R²=0.165, vs. OLS in-sample R²=0.310)** —
still a real gap, consistent with some OLS overfitting once interactions
are in, not RF underperforming. Feature importances: `prior_pyth_wins`
(0.441) dominates, `qb_tier_filled` (0.155) and `prior_agl` (0.101, still
fed continuous to RF, not binned) both rank ahead of `schedule_delta_pyth`
(0.099) — a reordering from the n=255 run, where `qb_tier` ranked behind
`schedule_delta_pyth`.

**5) The walk-forward backtest — the actual verdict, and it moved:**

| Model | OOS MAE (pyth_wins) | min_edge≥2.0 ROI | n |
|---|---|---|---|
| 1 — baseline | 1.845 | +25.6% (p=0.121, n=28) | 192 |
| 2 — with interactions | 1.833 | +6.4% (p=0.712, n=28) | 192 |
| *Market line* | *1.798* | *n/a* | *192* |

With the fixed sample (192 OOS rows now, up from 156) the earlier clean
"interactions hurt out-of-sample" result **softens into a near-wash** —
Model 2 now edges out Model 1 on OOS MAE (1.833 vs 1.845), reversing the
direction of the n=255 run. That reversal is itself informative: the
original result was partly an artifact of a biased sample (rookie/rookie-
contract seasons weren't missing at random, and dropping them changed
which team-seasons the interaction terms got tested against). Still,
neither model's backtest clears significance at any threshold (all
p>0.1) and **neither beats the market line directly** (1.798 MAE beats
both 1.845 and 1.833) — no demonstrated betting edge, consistent with
every other project in this repo. Given the interaction block's own F-test
still isn't significant (p=0.112) and its OOS edge over the baseline is
tiny (0.012 wins — noise-sized), **the baseline model is still the one to
default to for interpretability**, but this is now a genuinely closer
call than the first pass suggested, not a clean rejection.

## Bottom line

The core fundamentals (QB tier, prior Pythagorean wins, schedule delta,
whether the starter is even rated) all show up with correct signs and
real significance — that part holds up. Two deliberate refinements — a
validated nonlinear (quartile) treatment of injury severity, and treating
"no QB tier" as informative rather than dropping a fifth of the sample —
measurably improved the model and are now load-bearing parts of it. The
interaction hypothesis (does quality bucket change how momentum/coaching/
QB tier matter) gets more support than the first pass found, but still
doesn't clear significance or produce a real out-of-sample edge over the
plain model. And even the best version here still doesn't beat just
reading off Vegas's own line.

## Data sources

All shared, all reused except the three built this session:

- [`nfl/sources/win_totals`](../../nfl/sources/win_totals/), [`nfl/sources/game_results`](../../nfl/sources/game_results/), [`nfl/sources/coaches`](../../nfl/sources/coaches/) — existing
- [`nfl/sources/turnovers`](../../nfl/sources/turnovers/) — **new**, footballdb.com, 2014–2025
- [`nfl/sources/agl`](../../nfl/sources/agl/) — **new**, Football Outsiders/FTN, 2013–2025
- [`nfl/sources/qb_starters`](../../nfl/sources/qb_starters/) — **new**, PFR passing leaders joined to [`nfl/sources/qb_tiers`](../../nfl/sources/qb_tiers/)
- [`projects/schedule-swing-signal/data/merged.csv`](../schedule-swing-signal/data/merged.csv) — reused for `schedule_delta_pyth` (project-to-project reuse, same pattern `pyth-win-signal` used)

## Caveats

- `quality_bucket` tercile cutpoints (for the in-sample models 1–4) are
  computed once on the full sample, not recomputed per walk-forward
  training window — a small amount of look-ahead in the *bucket
  boundaries* (not the target). `agl_bucket` avoids this in the backtest
  (edges recomputed from the training fold only each time) but the
  in-sample analysis still uses full-sample edges for both, for
  simplicity — a stricter version would fold-compute both consistently.
- 20 parameters (baseline+interactions) on 320 rows is still a real
  observations-per-parameter squeeze — exactly why the walk-forward
  backtest, not the in-sample R², is what's trusted here.
- `qb_tier_filled`'s placeholder (training-mean tier) is a modeling choice,
  not a discovered fact — `has_qb_tier` is what actually carries the "was
  this QB rated at all" signal; the two terms should be read together.

## Pipeline

```bash
source venv/bin/activate
python3 projects/pyth-win-model/scripts/build_features.py   # -> data/features.csv
python3 projects/pyth-win-model/scripts/model.py             # all 4 techniques + backtest
```

`build_features.py` requires `projects/schedule-swing-signal/data/merged.csv`
to already exist (run that project's `analyze.py` first if it doesn't).
