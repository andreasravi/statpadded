# kicker-punter-model

A basic kicker and punter fantasy projection model for the 2026 season,
under this league's custom scoring:

```
Kicking                                    Punting
PAT made              +1                   Punts inside the 20         +1 (per punt)
PAT missed            -2                   Punt avg 44.0+               +3 (per GAME)
FG missed 0-39yd       -1.5                Punt avg 42.0-43.9           +2 (per GAME)
FG missed 40-49yd      -1                  Punt avg 40.0-41.9           +1 (per GAME)
FG missed 50-59yd      -0.5
FG made yards           0.1/yd
```

Kicking scores per *kick* (every FG/PAT attempt on its own). Punting is
mixed: PT20 scores per *punt*, but the "Punt average" tiers score once per
*game*, based on that game's average punt distance — not per individual
punt. That distinction matters a lot: scoring the average tiers per punt
instead of per game (an earlier version of this model's mistake) inflates
punter totals well past kicker totals, which doesn't happen once it's
scored per game as the league intends — see the corrected numbers below.

## TL;DR results

- [`data/projections_2026.csv`](data/projections_2026.csv) — every team's
  projected 2026 kicker and punter, season point totals (17 games) and
  per-game, plus the flags described below.
- Top projected kicker: **Brandon Aubrey (DAL)**, ~202 pts — elite leg (long
  FGs are worth a lot under this yardage-based scoring) on a good offense.
- Top projected punter: **Matt Haack (ARI)**, ~76 pts — but see below before
  reading anything into the ranking: the model's own top punter picks do
  *worse* than randomly guessing at identifying who'll actually finish
  top-3/top-5, so treat the punter list as an interchangeable group, not an
  ordered ranking. Either way, punters top out far lower than kickers under
  this scoring once the average-distance bonus is correctly capped at once
  per game rather than paid on every punt.

## Approach

**Kickers**: how many scoring opportunities a kicker gets is mostly about
how good their offense is (more scoring drives → more FGA/PAT); how well
they convert those opportunities into points is the kicker's own skill.
So: regress each kicker-season's fantasy points/game on that team's
points-for/game that season, and treat the *residual* — actual minus what a
league-average kicker would have scored behind that same offense — as a
portable "ability" number that travels with the kicker if they change teams.
A 2026 projection = (league fit applied to the team's projected 2026
scoring) + (that kicker's recency-weighted career residual, decay 0.6/year
so last season counts most). A rookie/no-history kicker just gets the
league-average expectation (residual = 0) with a flag noting it's a guess.

**Punters**: explored openly rather than assumed, per the brief — see
Findings below. Since the average-distance bonus is capped once per game,
punt *volume* (games punted, mostly) matters far less to total points than
it would if it were per-punt, and PT20 (genuinely per-punt) becomes a
bigger share of the total. Team quality still leans the same direction —
bad offenses force more games with heavy punting reps and more inside-20
looks — but the relationship is much weaker than a naive per-punt scoring
read would suggest (see Findings). Two different team-offense-based models
(point differential, then team punt volume specifically) were tried and
both were beaten by simply dropping team offense altogether: the shipped
model is each punter's own recency-weighted `avg_bucket_points_per_game`
history (skill) plus a flat, non-team-specific PT20 expectation — see
"Is there any real signal for punters, anywhere?" below for the full
investigation, including why this still isn't good enough to reliably
call a top-3/top-5 punter.

**Team offense proxy for 2026**: recency-weighted (0.5/0.3/0.2 for
2025/2024/2023) average of a team's actual points-for and point
differential over the last 3 seasons, adjusted toward this year's Kalshi
market win total (a team priced well above/below its recent win total gets
scaled toward that expectation, clipped to keep one outlier line from
dominating). See [`data/team_offense_proxy.csv`](data/team_offense_proxy.csv).

**Current 2026 rosters**: each team's presumed kicker/punter, defaulting to
the 2025 primary starter (by the team they *finished* the season with, not
just whoever they had the most attempts for — a real bug this project hit
and fixed, see Caveats) and overridden for confirmed 2026 free-agency moves
(Jason Sanders MIA→NYG, Jordan Stout BAL→NYG, Kai Kroeger NO→HOU, plus a
longer punter chain and a straight MIA↔ATL swap — see
[`scripts/build_current_rosters.py`](scripts/build_current_rosters.py) for
sourcing and every override). Two flags travel with every row:
- `new_player` — this exact person has no usable prior history (rookie/UDFA,
  or the job is simply "OPEN" with no confirmed name), OR they changed teams
  (their history is still used — skill is portable — but it's worth knowing).
- `unstable_team` — the team ran 2+ kickers/punters with real volume
  (≥5 FGA or ≥5 punts) in 2025, i.e. an in-season competition/injury
  carousel, so next year's incumbent is less certain than a clean depth
  chart. **7 of 32 teams** had a kicker carousel like this in 2025 (ATL,
  CHI, IND, LAR, NO, NYG, WAS) vs. only **2 of 32** for punters (ARI, BUF,
  both backup appearances during a starter's injury) — the kicker job
  itself turns over far more than the punter job does, independent of who's
  playing it.

## Findings (the punter exploration)

Pooled 2022-2025 punter-seasons (≥4 games played), correlated against that
season's team points-for/game, points-against/game, and point
differential/game:

| punter outcome | vs points-for/gm | vs points-against/gm | vs point-diff/gm |
|---|---|---|---|
| fantasy pts/game | **r = -0.27** | r = +0.01 | r = -0.20 |
| punts/game (raw volume) | **r = -0.68** | r = -0.01 | r = -0.47 |
| avg-bucket pts/game (pure skill) | r = -0.08 | r = +0.14 | r = -0.13 |

Once the average-distance bonus is correctly capped at once per game, punt
*volume* is still strongly tied to a bad offense (r = -0.68, unchanged from
a naive per-punt reading — bad teams simply play more punting snaps), but
that volume link barely survives into total fantasy points anymore
(r = -0.27, roughly half the per-punt-scoring version) because PT20 is the
only truly volume-scaled category left. *Skill* — the average-bucket points
a punter earns per game, stripped of volume — still has essentially no
relationship to team quality (all three |r| < 0.14). The conclusion is the
same as before, just less dramatic in the total-points column: a punter's
leg ability is team-independent, but under this scoring their team's
opportunity environment matters less to their final total than it would
under naive per-punt bucket scoring.

Year-over-year autocorrelation of fantasy points/game (does this season
predict next season?):

| | r | n |
|---|---|---|
| same **punter**, year *t* → *t+1* | +0.27 | 85 |
| same **team's punter slot**, year *t* → *t+1* (any player) | +0.15 | 96 |

Both are weaker than the naive per-punt-scoring version, and now the
**player**-level number is clearly higher than the team-level one — the
opposite ordering from before. That flips the practical takeaway: once
volume matters less to the score, the *person* punting predicts next
season's total better than the *depth-chart slot* does. This still supports
using a portable per-player ability residual (rather than, say, a pure
team-slot average) when a punter changes teams.

## How predictive is this, actually? (walk-forward backtest)

[`scripts/backtest.py`](scripts/backtest.py) refits the whole model — league
regression, ability residuals, team proxy — using only seasons strictly
before a target year (2023, 2024, 2025 each tested this way, no lookahead),
then checks the prediction against what actually happened. Two honest
findings, averaged across the three target years:

| | kicker | punter |
|---|---|---|
| **Total points** (model r²) | 0.72 | 0.84 |
| **Total points** (naive "league-average rate × actual games" r²) | 0.76 | 0.85 |
| **Per-game rate** (model r², no playing-time info) | 0.02 | 0.11 |
| **VORP rank** (Spearman ρ vs. actual VORP, replacement rank 12) | 0.73 | 0.64 |
| **Top-10 VORP overlap** (of 10, per year) | 4–6 | 2–6 |

(Punter numbers reflect the skill-history model described below, not the
original team-offense-regression version this project started with.)

Two things jump out, and neither is flattering in the way a "how predictive
is this" headline number usually wants to be:

1. **The strong total-points number is mostly playing time, not skill.**
   Both the model's and the naive baselines' season totals in this backtest
   use each player's *actual* games played that year (known in hindsight,
   since this evaluates a finished season) — and a dead-simple "everyone
   scores the league-average rate" baseline does *at least as well* as the
   model, in every single year tested. Once games played is stripped out
   entirely (the per-game RATE row — no playing-time information for either
   side), the model's real skill-prediction power collapses to r² ≈ 0.02
   for kickers — barely distinguishable from noise, and about on par with
   just carrying over last year's rate. Punters do a bit better (r² ≈ 0.11,
   after the skill-history model below) but still explain less than an
   eighth of the variance. This matches a
   well-known fact in kicker analytics: FG/PAT accuracy has notoriously low
   year-to-year persistence at the individual level — most of what
   separates a good kicker-season from a bad one is health, opportunity,
   and variance, not a stable underlying "skill" this model (or a much
   fancier one) can reliably isolate a year in advance.
2. **VORP rank correlation is moderate, and it's inheriting problem #1.**
   Spearman ρ ≈ 0.6–0.7 sounds like a real, useful signal for draft value —
   and it is, directionally — but since it's built on the same
   total-points numbers, most of that correlation is really "the model
   correctly assumes last year's starters mostly stay starters," not a
   skill read. Top-10 VORP overlap of 4–6 out of 10 says the same thing
   less charitably: about half the actual top-10 value list is missed each
   year.

Practical takeaway: use this model to separate *starters from backups/
open jobs* (where it's doing real work — team offense and playing-time
priors) and *don't* over-trust it to rank two established starting kickers
against each other by a few points — that fine-grained distinction is very
close to unpredictable a year out with this feature set, and probably with
most simple feature sets.

### Does it actually call the *best* guys? (elite-tier hit rates)

The question that matters more than an R² is narrower: if you draft the
model's predicted top-N, how often is that pick actually good? Same
walk-forward setup, ranked by the preseason-only signal
(`predicted_fp_per_game` — no actual-games-played leakage), pooled across
the 3 backtest years:

| kicker — model picked... | n picks | finished above avg | actual top-10 | actual top-5 | actual top-3 |
|---|---|---|---|---|---|
| predicted rank 1-3 | 9 | 67% | 67% | 67% | 44% |
| predicted rank 4-5 | 6 | 100%* | 50% | 33% | 17% |
| predicted rank 6-10 | 15 | 33% | 20% | 0% | 0% |

| punter — model picked... | n picks | finished above avg | actual top-10 | actual top-5 | actual top-3 |
|---|---|---|---|---|---|
| predicted rank 1-3 | 9 | 44% | 22% | 11% | 0% |
| predicted rank 4-5 | 6 | 83%* | 33% | 33% | 0% |
| predicted rank 6-10 | 15 | 60% | 33% | 7% | 7% |

**random baseline** (picking blind from the same ~35-38 player pool each
year): 50% above avg, 28% top-10, 14% top-5, 8% top-3.

*(n=6 per band — 3 years × 2 slots — so read individual cells as directional,
not precise probabilities; 83% here is 5/6.)*

**Kickers**: there's a real, usable gradient. The model's rank 1-3 picks
hit above-average two-thirds of the time and finish actual top-3 more often
than random chance would predict (44% vs. an 8% random-baseline rate) —
that's genuine signal at the very top. It decays fast below that: rank
6-10 picks are *worse than random* on every single metric here. **Trust
picks 1-5, be much more skeptical of picks 6-10 — random picking would
have done better.**

**Punters**: no clean gradient at all, and — this is the sobering part —
the model's own rank 1-3 picks (its most confident punters) underperform
the random baseline on every metric (44% vs 50% above-avg, 22% vs 28%
top-10, 11% vs 14% top-5, 0% vs 8% top-3). Rank 6-10 modestly beats random
on some columns, which given n=15 and the pattern being the *opposite* of
what a real signal should look like (worse picks outperforming better
ones) reads as noise, not signal. The punter model below (built around
each punter's own skill history rather than team offense) is a genuine,
leak-free improvement in aggregate correlation and VORP-rank terms — see
the numbers above — but it does **not** fix this specific problem, and the
top tier's "above average" hit rate is if anything slightly worse than the
model version this project started with. The honest read stands: the
model can nudge you toward punters likely to be fine in aggregate, but has
essentially no ability to pick out the single best punter in the league —
**treat the punter ranking as a loose grouping, not an ordered list.**

### Is there *any* real signal for punters, anywhere? (a deeper dig)

Before accepting "the punter ranking doesn't work," it's worth checking
whether that's a property of the *data* or just this particular *model*.
Digging into the pieces this league's punter scoring is actually built
from:

| metric | same-year corr. w/ fantasy pts/gm | year-over-year persistence (same player) |
|---|---|---|
| gross punt average (yards/punt) | r = 0.61 | **r = 0.45** |
| PT20 rate (punts inside 20 ÷ punts) | r = 0.61 | r = 0.06 (n.s., p = 0.60) |
| the average-distance bucket score itself | — | r = 0.30 (single prior yr) → 0.39 (2+ prior yrs averaged) |

Leg strength (raw punt average) is a real, moderately sticky individual
skill — r ≈ 0.45 year to year is genuine signal, and it gets a little
better (≈0.39) when averaged over multiple prior seasons instead of just
the last one, the way noise-reduction is supposed to work. But **PT20 rate
has essentially zero persistence** — whether a punter pins the opponent
inside the 20 this year tells you almost nothing about next year, at
either the player or team level. Since PT20 is worth a real chunk of the
scoring and the average-distance bonus is capped at 3 pts/game regardless
of how much better than "44+" a punt actually was, half of this scoring
system is built from a genuinely unpredictable input and the other half's
predictive value gets compressed by the per-game cap.

Rebuilding the ability model to isolate the two — predict the
average-distance bucket score from the player's own multi-year history
(no team adjustment, since team quality barely correlates with skill
anyway) and predict PT20 separately from team offense (the one place it
does show a real, if modest, r ≈ -0.33 relationship) — is more
mechanistically honest, but **doesn't meaningfully change the outcome**:
pooled rate r² comes out ≈ 0.07, and elite-tier hit rates stay in the same
weak range (a rank-1-3 pick hit actual top-3 11% of the time under the
decomposed version, similar to the blended version's 0%). The ceiling
isn't a modeling choice, it's that a punter's individual-punt distance has
a real ~9-yard standard deviation within a season (confirmed against the
old estimation approach earlier in this README) and this league's scoring
caps out how much of a skill edge can show up in the score, while paying
out real points for a category (PT20) that has no detectable persistence
at all with the features available here.

**Bottom line for punters**: there's real signal in leg strength, but not
enough to reliably call a top-3/top-5 finisher under this specific scoring
system a year in advance — this isn't a "went back to the drawing board and
found a bug" situation, it's a genuine ceiling. If forced to lean on
*something* beyond "they're all roughly interchangeable," multi-year
average-bucket-score (leg strength with the noise averaged down) is the
closest thing to a real differentiator this data offers — see
`avg_bucket_points_per_game` in [`punting_stats.csv`](../../nfl/sources/punters/data/punting_stats.csv)
for punters with 2+ qualifying seasons — but treat it as a weak lean, not a
confident ranking.

**Follow-up: this recommendation was actually shipped, and re-tested.**
Team offense's own weak connection to punter skill raised an obvious next
question: what about team *punt volume* specifically, rather than points-
for or point-differential? Volume is the mechanistically direct link to
PT20 opportunity, and unlike PT20 rate it has real team-level year-over-year
persistence (r=0.36 — bad-offense teams tend to stay bad-offense teams). A
proper leak-free ablation tested three versions: team-volume-only,
player-skill-only, and both combined. Player skill alone won clearly
(pooled rate r²=0.106 vs 0.048 combined vs 0.005 team-volume-only) — team
punt volume is real and persistent as its own number, but translates too
noisily into any one punter's score to help, and actively hurts when
blended in. So the model shipped here dropped team offense entirely: each
punter's own recency-weighted `avg_bucket_points_per_game` history plus a
flat (non-team-specific) PT20 expectation. It's a genuine, leak-checked
improvement over the original team-offense-regression version in aggregate
correlation and VORP-rank terms (see the table two sections up) — but as
the elite-tier hit-rate table above shows, it does **not** solve the
top-3/top-5 problem; if anything the top tier's "above average" rate
dropped. Two different, reasonably thorough attempts at improving this
converged on the same ceiling from different directions — about as
convincing a "this isn't a solvable modeling problem with this data" signal
as this kind of investigation can produce.

```bash
python3 projects/kicker-punter-model/scripts/backtest.py
```

### A kicker upgrade that looked real, then didn't survive a rerun

The reverse question is worth asking for kickers too: is there a feature
that predicts the elite tier *better* than team offense + own history?
Long-range accuracy was a natural candidate — under this league's
yardage-scored FG formula, a 50+ yard make is worth real extra points. Two
things needed checking first: does long-range performance actually persist
year to year (unlike PT20 for punters), and does adding it as a feature
improve the walk-forward backtest?

| kicker metric | year-over-year persistence (same player) |
|---|---|
| long-range (50+) MAKE % | r = -0.02 (n.s.) — pure single-season noise |
| overall FG% | r = -0.02 (n.s.) — also pure noise |
| long-range (50+) ATTEMPT volume | **r = +0.29** (p < 0.01) — a coach's trust in a kicker's leg is a real, somewhat sticky signal, unlike whether any given long kick happens to go in |

That's a genuinely different pattern from FG accuracy (which, matching
well-known kicker analytics, essentially doesn't persist at all) — so
attempt volume looked like a promising second predictor. A first pass
built exactly that: team offense + the kicker's own recency-weighted
long-range-attempt rate, feeding a proper walk-forward backtest. It looked
like a clear win — out-of-sample r² roughly doubled (0.023 → 0.046) and the
top-3 tier's above-average rate jumped to 78%.

**It didn't hold up.** That first version had a real information leak: it
computed each kicker's long-range-history feature once, using their *full*
prior-season average relative to the target year, and then used that same
number for *every one* of that kicker's training rows — so an early
training season could "see" a later training season's data for the same
player. Rebuilding it with a proper expanding window (each row uses only
seasons strictly before it) made most of the improvement disappear, and on
the roughly 2 years of data available to test it (the feature needs 2+
prior seasons per kicker, which drops one of the three backtest years to
too-small-to-fit), it actually made the top-3 tier noticeably *worse*, not
better, while modestly helping the back tier. The honest read: with only
four seasons of history on hand, there isn't enough data to tell whether
long-range-attempt volume is a real additional signal or not — it's
plausible it would help with more years behind it, but it isn't proven
here, so the production model stays the simpler one. `fga_50plus` /
`fgm_50plus` are still tracked in
[`kicking_stats.csv`](../../nfl/sources/kickers/data/kicking_stats.csv)
(cheap to keep, informative on their own), and `backtest.py`'s
`fit_and_predict(..., long_range_col=...)` still supports testing this
properly if more seasons become available later.

## Caveats / approximations (basic model, not a precise one)

Scoring itself is now **exact**, not estimated: an earlier version of this
model used PFR's season-level stats (FGA/FGM by distance *bucket*, season
punt *average*) and approximated each kicker's FG yardage and each punter's
per-punt bucket points from those aggregates. It's since been rebuilt on
`nflverse-data` **play-by-play** — every single FG/PAT/punt, with its real
distance and result — so `nfl/sources/{kickers,punters}/pipeline.py` now
compute the league's exact scoring rules against exact per-play data, not a
distribution assumption. (One nice side effect: it also confirmed the old
estimate was a decent approximation — final point totals moved only a few
percent once switched to exact data, and the punter skill-vs-volume finding
below held up almost unchanged.) It's also a better data source
mechanically: nflverse-data isn't Cloudflare-protected, so both pipelines
now auto-fetch with no browser step, unlike `game_results`.

What's still an approximation in the *projection* (not the historical
scoring):
- **50-59 yard FG misses and 60+ yard misses are folded together** (this
  league's scoring has no explicit 60+ tier, and such misses are rare enough
  this barely matters).
- **Games played assumes a full 17-game season** for every projection — no
  injury-risk discount.
- **Play-by-play is regular season only** (postseason games are filtered
  out via `season_type`) so per-game rates aren't diluted by deep playoff
  runs.
- **"OPEN" jobs and rookies get the league-average expectation** (ability
  residual = 0), which is the most defensible number for an unknown but is
  obviously a wider-uncertainty guess than a proven veteran's projection.
- Only 4 seasons of history (2022-2025) went into the ability estimates —
  enough for a first cut, thin for anyone with 1 season of data (see
  `seasons` column in the ability CSVs before trusting a residual).
- **2026 roster assignments were manually verified per-team, not derived
  automatically** — `build_current_rosters.py`'s default logic picks each
  team's highest-2025-attempts kicker/punter, which silently breaks for
  anyone who changed teams mid-2025: it'll assign them to whichever team
  they had more attempts with, not whichever team they finished the season
  (and are actually on going into 2026) with. Caught this concretely with
  Blake Grupe (more FGA with NO early in 2025, but finished the season with
  IND, per week-by-week data in the raw play-by-play cache) — the default
  would've kept him on NO for 2026, which was wrong on two counts (he's on
  IND, and NO has since moved on to a different kicker entirely). Every
  `KICKER_OVERRIDES` / `PUNTER_OVERRIDES` entry with a note citing multiple
  sources has been individually checked this way; an earlier draft of this
  list had gotten one signing's destination wrong from a single unreliable
  search summary (see the note in `build_current_rosters.py`) before being
  re-verified. Team assignments still have a real shelf life — this was
  accurate as of when it was researched, not a live feed.

## Files

```
data/
  team_offense_proxy.csv       recency-weighted + market-adjusted 2026 team scoring/point-diff proxy
  current_rosters_2026.csv     2026 kicker/punter per team, new_player + unstable_team flags
  kicker_ability.csv           every kicker's recency-weighted career ability residual
  punter_ability.csv           same, for punters
  projections_2026.csv         final combined 2026 projections (the deliverable)

scripts/
  build_team_offense.py        team offense/point-diff proxy for 2026
  build_current_rosters.py     2026 roster mapping + flags (sourced from 2026 FA news, see file)
  analyze_ability.py           league fits + ability residuals + the punter exploration above
  project_2026.py              combines everything -> projections_2026.csv
  backtest.py                  walk-forward predictive-power check (total points, rate, VORP) -- see above
```

## Run

```bash
source venv/bin/activate
python3 nfl/sources/kickers/pipeline.py      # auto-fetches nflverse play-by-play -> kicking_stats.csv
python3 nfl/sources/punters/pipeline.py      # auto-fetches nflverse play-by-play -> punting_stats.csv
python3 projects/kicker-punter-model/scripts/build_team_offense.py
python3 projects/kicker-punter-model/scripts/build_current_rosters.py
python3 projects/kicker-punter-model/scripts/project_2026.py   # also reruns analyze_ability.py's fits
```

`nfl/sources/{kickers,punters}/pipeline.py` fetch straight from
`nflverse-data`'s public GitHub release the first time each season is
needed, caching a lean per-play extract in their own `data/raw/` — no
browser tool required (unlike `game_results`, which sources from
Cloudflare-protected PFR). To add a new season once it's over, just widen
`DEFAULT_YEARS` in each pipeline (or pass years as CLI args) and re-run.
