# prop-accuracy

How accurate are the preseason NFL player prop lines that fantasy/betting
outlets publish every August? Grade every line against what actually
landed in the regular-season box score, and look for structure in the
misses — does the *size* of the line predict whether it clears, does team
context explain any of it, and does one year's result carry into the next?

Two positions, same method, same directory:

| | Wide receivers | Running backs |
|---|---|---|
| Prop lines | [`wr_prop_totals`](../../nfl/sources/wr_prop_totals/) — Fantasy Alarm grid, 2022–26 | [`rb_prop_totals`](../../nfl/sources/rb_prop_totals/) — Fantasy Points 2023–25 + SportsBetting.ag 2022 |
| Actuals | [`receiving_stats`](../../nfl/sources/receiving_stats/) (nflverse) | [`rushing_stats`](../../nfl/sources/rushing_stats/) (nflverse) |
| Stats graded | receiving yards / receptions / TDs | rushing yards (or rush+rec) / rushing TDs |
| Scripts | `*_wr.py` | `*_rb.py` |

- **WR visual write-up:** [`settle-sheet.html`](settle-sheet.html), also a
  Claude artifact: https://claude.ai/code/artifact/9511311e-ed4b-4feb-a98d-2188db080ff6

## Method

```
# wide receivers
python3 projects/prop-accuracy/scripts/grade_wr.py      # -> data/wr_prop_grades.csv
python3 projects/prop-accuracy/scripts/analyze_wr.py    # -> hit_rate_* / year_over_year_* CSVs
python3 projects/prop-accuracy/scripts/explore_wr.py    # -> wr_miss_distribution / wr_beat_magnitude_by_line / wr_line_vs_prior_year CSVs
python3 projects/prop-accuracy/scripts/context_wr.py    # -> context_* CSVs + context_summary.json
python3 projects/prop-accuracy/scripts/coverage_wr.py   # -> adp_coverage_gaps.csv

# running backs
python3 projects/prop-accuracy/scripts/grade_rb.py      # -> data/rb_prop_grades.csv
python3 projects/prop-accuracy/scripts/analyze_rb.py    # -> data/rb_hit_rate_* / rb_year_over_year_* CSVs
python3 projects/prop-accuracy/scripts/explore_rb.py    # -> rb_miss_distribution / rb_beat_magnitude_by_line / rb_line_vs_prior_year / rb_hit_rate_by_draft_cost CSVs
python3 projects/prop-accuracy/scripts/context_rb.py    # -> data/rb_context_* CSVs + rb_context_summary.json
python3 projects/prop-accuracy/scripts/coverage_rb.py   # -> data/rb_adp_coverage_gaps.csv
```

WR view CSVs are unprefixed (historical); RB ones are `rb_`-prefixed.

---

# Wide receivers

How accurate are the preseason WR prop lines Fantasy Alarm publishes every
August?

`context_wr.py` additionally joins each graded prop to two **preseason** team
inputs -- the QB's tier ([`nfl/sources/qb_starters`](../../nfl/sources/qb_starters/))
and the team's Vegas win-total line
([`nfl/sources/win_totals`](../../nfl/sources/win_totals/)) -- neither of
which is a within-season outcome, so year-X prop result vs year-X preseason
context is not lookahead.

`explore_wr.py` is the deeper exploratory pass — the distribution of the
miss, the beat/short-fall magnitude inside each line tier, and the line vs
the player's *previous* season (prior-year actuals come from
`receiving_stats`, which goes back to 2021). Writes
`wr_miss_distribution.csv`, `wr_beat_magnitude_by_line.csv`,
`wr_line_vs_prior_year.csv`.

`coverage_wr.py` checks the grid against an independent WR ADP ranking
(`underdog_adp` for 2023-25, FantasyData `adp` for 2022) and writes
`data/adp_coverage_gaps.csv` -- see the coverage note below.

`grade_wr.py` matches each published prop row to a nflverse player-season on a
normalized name key (strip punctuation / Jr-Sr-III, then first-initial +
last-name fallback; ties broken by targets, which handles mid-season
trades). 158 of 158 gradable rows (2022–25) match; the 2026 grid is carried
but not graded (season not played).

`games < 14` marks a season that wasn't a full sample. It matters a lot
here — most of the worst misses are availability, not per-game form — so
every rate below is reported both raw and "healthy only" (≥ 14 games).

## What the data says

### 1. The lines run slightly rich, and it's gotten worse

Receiving-yards O/U cleared: **69/158 (44%)** across 2022–25 — and the trend
is down: **46% → 54% → 40% → 35%** by season. Receptions 44%, TDs 40%.
Among receivers who played ≥ 14 games it's a near-coin-flip (56% over on
yards); the sub-14-game seasons are almost automatic unders and drag the
raw number down.

### 2. Does the size of the line predict the miss?

| Stat | Signal | The soft spot | The trap |
|---|---|---|---|
| **Yards** | weak (r ≈ −0.06) | healthy WR, **sub-1,000 line → 61% over, median +98** | the **1,000–1,200 "dead zone"** — 48% even when healthy, median −8 |
| **Receptions** | none (r ≈ 0) | **both** ends: 86+ line (75% healthy) *and* 56–65 possession guys (88%) | the **76–85** target-hog-WR2 band — 40% healthy, median −9.5 |
| **TDs** | real & negative (r ≈ −0.2) | everything under 7.5 is ~a coin flip | **8+ TD lines: 28% over, 36% even healthy** — the most reliable fade |

The 1,000+ yard tier goes **41% over (55% healthy)**; the drag is that ~26%
of that tier misses 14+ games and *none* of those beat the over. It's not a
standing edge though — the tier ran +100 yds vs the line in '22, −118 in
'25.

**When they beat, how much do they beat by?** (`explore_wr.py`, section B —
median over-shoot vs median short-fall inside each yards tier)

| Line | under % (healthy) | beat by, median (when over) | miss by, median (when under) |
|---|---|---|---|
| 700–850 | **33%** | +294 | −224 |
| 850–1000 | 36% | +196 | **−294** |
| 1000–1200 | 52% | +231 | −161 |
| 1200+ | 33% | +287 | −197 |

The **850–1000** band is the worst risk/reward on the board: a healthy WR
there is under only ~36% of the time, but the misses (−294 median) are
nearly twice the size of the beats (+196). The **700–850** band is the
inverse and the best pure over — low under rate *and* the beats out-size
the misses. Receptions: a **≤55 line is a 93% under (91% healthy)** — the
single most automatic fade in the data; the **56–65** possession band is a
30% under (12% healthy). TDs: an **8+ line is a 72% under (64% healthy),
median −3.5** — nothing else is close.

### 3. The shape of the miss: the line is almost never "about right"

Across 158 receiver-seasons the receiving-yards result lands **within ±50
of the line only 14% of the time** (median miss −37, SD 318). It's a
near-symmetric distribution in the middle (skew ≈ 0) with two fat tails:
**30% blow the under by 200+ yards, 25% blow the over by 200+**. A season-
long receiving prop is a coin flip on a number that will usually be wrong
by a couple hundred yards — the edge, if there is one, is in *which* tail.
Every one of the 12 worst under misses is an injury season (≤ 10 games);
every one of the 12 biggest overs is a 16–17-game season. Receptions
(within ±3 just 8% of the time) and TDs (within ±1, 32%) are the same
shape.

### 4. The line is last year's box score, lightly discounted

`corr(line, the player's prior-season receiving yards) = +0.78` — the book
anchors the number hard to last year, then shades it down a mean **71
yards** for regression/age/injury risk. But the prior-season *total* itself
tells you nothing about the result (`corr(prior yards, this year's Δ) =
+0.03`). What matters is the **direction of the re-rate** (`explore_wr.py`,
section C):

| Line vs last year's actual | n | over % | over % (healthy) |
|---|---|---|---|
| set **≥ 150 above** (bullish / breakout buy-in) | 19 | **37%** | 46% |
| within ±150 | 78 | 42% | 58% |
| cut **≥ 150 below** (bearish / written off) | 49 | **51%** | **69%** |

When the book prices in a leap, it's been wrong more often than not; the
receivers it gave up on have been the better overs. Same story for health:
a WR **coming off a prior-year injury** (< 14 g) goes **36% over (47%
healthy), median −90** — the post-injury line still isn't discounted
enough for the re-injury / slow-ramp risk.

### 5. Team context: the QB tier is the real lever, and the market overreacts to it

Joining each yards line to the **preseason** QB tier of the team the
receiver *started* the season with (n=137):

| QB tier | n | over % (all) | mean Δ vs line |
|---|---|---|---|
| 1 (elite) | 27 | 41% | −30 |
| 2 | 45 | 38% | −57 |
| 3 | 40 | 40% | −13 |
| **4–5 (weak)** | 25 | **64%** | **+64** |

`diff ~ yards_line + qb_tier + win_total` OLS: **qb_tier ≈ +88 yds per step
down the tiers, p ≈ 0.014**; `yards_line` itself is insignificant once tier
and win total are in. The book shades a WR's line down hard for a weak-QB
label, and the label is noisy enough (Purdy/Baker/Darnold were all
tier-4-ish and fine) that the shade has been too aggressive. Elite-QB WRs,
especially on contenders (mean −43, n=62), have been the thinnest overs.
**Caveats:** 25 weak-QB seasons is small; ~21 team-seasons have no tiered
starter in the source and are excluded; a few "primary starters" are the
actual not the projected QB. The join uses `team_start` (first-game team,
from `receiving_stats`), not `recent_team`, so the ~3 mid-season trades in
the sample (Adams / Cooper / Johnson '24) get their preseason team's
context.

Team **win total** is U-shaped for yards — the **7–8 win** band is the trap
(29% over, mean −84); tank teams (volume) and contenders both fare better
(OLS win_total ≈ +47 yds/win, p ≈ 0.03, but that's a linear read of a
non-linear shape — trust the bucket view).
For **receptions**, context barely matters (R² ≈ 0.03) except that
**contender WRs clear 68%** — high-volume passing offenses throw a lot of
catchable balls even when the yardage doesn't follow.

### 6. Year over year: no carryover

`corr(this year's Δ vs line, next year's Δ vs line) = +0.02` across 81
same-player pairs. How a receiver did against his number tells you nothing
about next year — the book re-prices enough to erase it (line moves −184
after a blowup miss, +215 after a monster year). Most buckets still
regress to a small *under* the next season. The one real buy-low: a
**−150 to −300 miss** (non-catastrophic down year) → **60% over the next
year, median +98**, after the book over-corrects the line down. The worst
spot is a **dead-on** result (−50 to +50) → 25% over next year: meet your
number and you get priced exactly at your level, with only downside.

### Coverage: who the grid skips

The grid is an editor's pick, not a mechanical top-N, and it misses a
handful of top-25-by-ADP WRs each year (`coverage_wr.py`):

| Year | Missing from grid (WR rank by ADP) |
|---|---|
| 2022 | Michael Thomas (20), Chris Godwin (22) |
| 2023 | Jerry Jeudy (20), Terry McLaurin (23), DeAndre Hopkins (24) |
| 2024 | **Brandon Aiyuk (16)**, Malik Nabers (20), Tank Dell (25) |
| 2025 | Terry McLaurin (20) |

The omissions cluster on injury-cloud veterans (Thomas, Godwin, Aiyuk,
McLaurin '25), late-signing / new-team vets (Hopkins '23), and a rookie
the author skipped (Nabers '24). Several are exactly the profiles most
likely to bust, so the raw hit rates here are probably a touch *optimistic*
versus a true top-25-by-ADP census. McLaurin is a persistent blind spot
(missing 2 of 3 years he'd have qualified). Aiyuk '24 is the biggest gap —
a genuine top-16 WR by ADP, held out in camp, then a Week-7 ACL tear.

## Bottom line

The market is efficient enough that beating these lines is hard and getting
harder, there's no player-level momentum to ride, and the repeatable angles
are structural:

- **Fade:** 8+ TD lines (72% under), ≤55 reception lines (93% under), the
  850–1,000 yard band (misses ~2× the beats), a line set ≥150 above last
  year, and a WR coming off an injury year.
- **Lean over:** healthy sub-1,000-yard receivers (esp. the 700–850 band),
  a line the book *cut* ≥150 below last year, players bouncing back from a
  moderate (−150 to −300) down year, and — the strongest single signal,
  though small-sample — receivers whose line got shaded down for a weak or
  unproven QB.
- Elite-QB WR1s on contenders are where the overs run thinnest.

The through-line across the new cuts: the book prices the season off last
year's box score and the preseason narrative (breakout buzz, QB downgrade,
"coming back from injury"), and it leans on those priors a little too hard
in every direction.

---

# Running backs

Season-long **rushing-yards** and **rushing-TD** O/U lines graded against
nflverse regular-season rushing totals. Lines: Fantasy Points' annual
grids (2023–25, range across ~6 books) and SportsBetting.ag's 2022 board
via gambling911 (one offshore book). 134 graded RB-seasons, 2022–25 —
126 with a true rushing-yards line, 8 (2022 pass-catching backs) with a
rush+rec line only, 76 with a rushing-TD line (none for 2023 — no grid
exists that year).

`grade_rb.py` also joins Underdog ADP (2023–25) and flags `top30`.
`yards_actual` is rushing yards for a `rush` line, rush+rec yards for a
`rush+rec` line, so it always matches what the book priced. A back who
missed the whole season (2025 Joe Mixon) is graded as a 0 — a real max
under, not a gap.

`explore_rb.py` is the deeper exploratory pass (RB counterpart of
`explore_wr.py`): the distribution of the miss, the beat/short-fall
magnitude inside each line tier, the line vs the back's *previous* season
(prior rushing totals from `rushing_stats`, back to 2021), and — using the
ADP the grades carry — the hit rate by draft slot.

## What the data says

### 1. RB rushing-yards unders are almost entirely an injury bet

Rushing-yards O/U cleared **57/126 (45%)** overall — but split by health
the number falls apart:

| | n | over % |
|---|---|---|
| Played ≥ 14 games | 88 | **64%** |
| Played < 14 games | 38 | **3%** (1 of 38) |

Every one of the six worst under misses is a season-ending injury (Chubb
'23 2 g, CMC '24 4 g, Mixon '25 0 g, Dobbins '23 1 g, Brooks '24 3 g,
Conner '25 3 g). If the back stays healthy the over is a 64% proposition —
a stronger lean than the healthy-WR yards number (56%). The whole edge in
the *under* is forecasting availability; the book's yardage number for a
back who plays a full season has been consistently a touch low.

By season (rush-only): **36% → 35% → 55% → 50%** over — 2022–23 were
brutal for overs, 2024–25 clearly better, same directional wobble as the
WR series but no persistent trend.

### 2. Size of the line

| Tier | n | over % (all) | over % healthy | median Δ healthy |
|---|---|---|---|---|
| < 600 | 17 | 41% | 58% | +62 |
| 600–800 | 34 | 47% | 65% | +70 |
| 800–1000 | 51 | 49% | 71% | +181 |
| 1000–1200 | 18 | **33%** | **43%** | −27 |
| 1200+ | 6 | 50% | 75% | +235 |

The **1000–1200 "dead zone" reappears** — the same band that traps WR
receiving-yards lines. A workhorse priced at 1000–1200 rushing yards has
cleared only 43% even healthy (median −27); below 1000, a healthy back is
a 65–71% over. Rushing **TDs**: the 5–6.5 band is the fade (27% over, 38%
healthy); 9–10.5 has over-hit (69%) on a small n=16.

**When they beat, how much by?** (`explore_rb.py`, section B — median
over-shoot vs median short-fall inside each rushing-yards tier)

| Line | under % (healthy) | beat by, median | miss by, median | ratio |
|---|---|---|---|---|
| < 600 | 42% | +104 | −277 | 0.37 |
| 600–800 | 35% | +227 | −340 | 0.67 |
| 800–1000 | 29% | +252 | −350 | 0.72 |
| 1000–1200 | 57% | +339 | −131 | **2.59** |

Below 1000 the shape is **bimodal and asymmetric** — a healthy back is a
65–70% over, but when a back in these tiers misses (almost always injury)
he misses ~1.4× as big as the overs pay. The **1000–1200** band flips it:
you're *more* likely under (57% healthy) but the downside is capped
(−131) while the overs are huge (+339) — a workhorse who's already
established doesn't crater unless he's hurt, and if he's hurt he was
priced too high anyway.

### 3. The shape of the miss: even less "about right" than for WR

Across 126 rush-only lines the result lands **within ±50 of the number
just 8%** of the time (WR: 14%), median −41, SD 387 (wider than WR's 318).
Skew ≈ 0, but **36% blow the under by 200+ yards** and 29% blow the over
by 200+. Every one of the 12 worst under misses is a ≤ 8-game injury
season; every one of the 12 biggest overs is a 14–17-game workhorse year
(Barkley's 2,005, Henry's 1,921). The rushing-yards prop is a coin flip on
a number that will usually be wrong by 250+ yards, and the tail you land
in is almost entirely about health.

### 4. The line vs last year — and here RB is the *opposite* of WR

`corr(line, prior-season rushing yards) = +0.76` — same hard anchor to
last year, shaded down a mean 79 yards. But the re-rate direction points
the other way from receivers (`explore_rb.py`, section C):

| Line vs last year's rushing yards | n | over % | over % (healthy) |
|---|---|---|---|
| set **≥ 150 above** (bullish) | 14 | **57%** | **100%** |
| within ±150 | 59 | 49% | 62% |
| cut **≥ 150 below** (bearish) | 41 | 41% | 59% |

For a back, when the book prices in a step up it has still been *too low*
(14 seasons, all 8 of the healthy ones cleared). And the biggest reversal is
**prior-year injury**: a back coming off a < 14-game season went **64%
over (85% healthy, median +108)** — the exact inverse of the receiver
number (36% over). RB injuries are mostly acute and the workload comes
back intact, so the post-injury discount has been far too steep. Back
the bounce-back back; fade the bounce-back receiver.

### 5. Draft cost: the mid-round back is the sweet spot, and RB31+ is a trap

Using the Underdog ADP the grades carry (2023–25 rows, `explore_rb.py`
section E):

| Draft slot | n | avg line | over % | over % (healthy) |
|---|---|---|---|---|
| RB1–8 | 24 | 1,029 | 54% | 62% |
| RB9–18 | 28 | 902 | 54% | 71% |
| RB19–30 | 25 | 771 | 52% | **80%** |
| **RB31+** | 11 | 662 | **9%** | **14%** |

Among *draftable* backs the healthy over rate climbs as the price drops —
the RB19–30 range (mid-round, real role, modest line) has been the best
healthy over on the board. But the cliff at RB31+ is total: a back going
that late who still has a posted line is a committee/handcuff type, and
those have cleared 1 in 11. The line's own size stops mattering; the
draft slot is the tell.

### 6. Team context matters much less than for WR

Joining each rush-only line to the RB's `team_start` preseason context
(n=104 with both inputs):

- **Win total:** no clean monotone signal on raw over % (36–52% across
  buckets); contenders (10.5+) are marginally best. Healthy backs clear
  50–71% in every win-total bucket — health swamps game script.
- **QB tier:** tier-1 (elite QB) RBs clear **58% (73% healthy)** — the
  *opposite* of the WR finding, where elite-QB WRs were the thinnest
  overs. Plausible mechanism: elite QB → more scoring drives → more
  goal-line and positive-script carries. But n is small and the effect is
  weak.
- `yards_diff ~ yards_line + win_total + qb_tier` OLS: **R² ≈ 0.01** —
  essentially no explanatory power, versus R² and a significant qb_tier
  term on the WR side. For RBs, context is mostly noise; health is the
  variable.

### 7. Year over year: the book over-corrects

`corr(year-A Δ vs line, year-B Δ vs line) = −0.21` (n=58 pairs) — mildly
*negative*: a back who smashed his number tends to miss it the next year
and vice versa, because the line chases the last result (moves +124 after
a big over, −120 after a moderate under). Bounce-back after a
non-catastrophic down year is strong (−150 to −50 miss → 86% over next
season, small n) — the same buy-low the WR data shows, a bit sharper here.

### Coverage: top-30-ADP RBs with no line (`coverage_rb.py`)

| Year | Missing (RB rank by Underdog ADP) |
|---|---|
| 2023 | Mattison (18), Javonte Williams (27), Kamara (29), James Cook (30) |
| 2024 | Brian Robinson Jr. (30) |
| 2025 | TreVeyon Henderson (15), RJ Harvey (20), Pacheco (23), Montgomery (25), Kaleb Johnson (26), Jordan Mason (28), Tyrone Tracy (29), Jaylen Warren (30) |

Clusters on rookies (Henderson, Harvey, Johnson), committee backs, and
2025 low-volume vets. 2022 can't be coverage-checked — no RB ADP source
in the repo before 2023.

## Bottom line (RB)

The one repeatable edge is **health-conditioned**: a healthy RB beats his
rushing-yards number ~64% of the time, and every meaningful under is an
injury.

- **Lean over:** healthy sub-1,000-yard backs (esp. the RB19–30 mid-round
  range — 80% healthy), backs coming off an injury year (85% healthy —
  the market over-discounts them), backs getting a bullish re-rate, and
  bouncebacks from a moderate down year.
- **Fade:** the 1,000–1,200 dead zone, any back going RB31+ who still has
  a posted line (1-for-11), and — for TDs — the 5–8.5 band.
- Unlike WR, team context (QB, win total) tells you almost nothing once
  you've accounted for whether the back plays, and the year-over-year
  signal is mildly *negative* (the line chases the last result).

The sharpest RB-vs-WR contrast: a receiver coming back from injury or
getting a breakout re-rate is a *fade*; the same back is a *buy*. RB
injuries don't linger in the box score the way soft-tissue / usage
questions do for receivers.

## Known gaps

- **2023 rushing TDs** — no comprehensive grid from any source.
- **2022** — one offshore book only; spot-checks vs SI Sportsbook /
  BetMGM / DraftKings put SportsBetting.ag within ~25–50 yds for most
  backs but ~100 low on the very top tier (Jonathan Taylor 1350.5 vs
  1450.5 elsewhere). No team/ADP for 2022 rows.
- **2026** — no comprehensive board pulled yet. The full grids
  (FantasyPoints, FantasyTeamAdvice, BettingPros) are paywalled or
  JS-gated; free articles (Sharp Football, FantasyPros/BettingPros) only
  cite a handful of lines each. So there is no RB equivalent of the WR
  "2026 — what stands out" section until a source is added to
  `rb_prop_totals`.
