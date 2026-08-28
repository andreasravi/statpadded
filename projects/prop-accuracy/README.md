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
python3 projects/prop-accuracy/scripts/context_wr.py    # -> context_* CSVs + context_summary.json
python3 projects/prop-accuracy/scripts/coverage_wr.py   # -> adp_coverage_gaps.csv

# running backs
python3 projects/prop-accuracy/scripts/grade_rb.py      # -> data/rb_prop_grades.csv
python3 projects/prop-accuracy/scripts/analyze_rb.py    # -> data/rb_hit_rate_* / rb_year_over_year_* CSVs
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

### 3. Team context: the QB tier is the real lever, and the market overreacts to it

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

### 4. Year over year: no carryover

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
are structural: fade 8+ TD lines and the 1,000–1,200 yard band; lean overs
on healthy sub-1,000-yard receivers, on players bouncing back from a
moderate down year, and — the strongest single signal, though small-sample
— on receivers whose line got shaded down for a weak or unproven QB.
Elite-QB WR1s on contenders are where the overs run thinnest.

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

### 3. Team context matters much less than for WR

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

### 4. Year over year: the book over-corrects

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
injury. Fade the 1000–1200 dead zone, lean over on healthy sub-1000-yard
backs and on bouncebacks from a moderate down year. Unlike WR, team
context (QB, win total) tells you almost nothing once you've accounted for
whether the back plays.

## Known gaps

- **2023 rushing TDs** — no comprehensive grid from any source.
- **2022** — one offshore book only; spot-checks vs SI Sportsbook /
  BetMGM / DraftKings put SportsBetting.ag within ~25–50 yds for most
  backs but ~100 low on the very top tier (Jonathan Taylor 1350.5 vs
  1450.5 elsewhere). No team/ADP for 2022 rows.
- **2026** — lines are live now (BettingPros / Covers / DK); not yet pulled.
