# wr-prop-accuracy

How accurate are the preseason wide-receiver prop lines Fantasy Alarm
publishes every August? Grade every receiver's receiving-yards / receptions
/ TD line against what actually landed in the regular-season box score, and
look for structure in the misses — does the *size* of the line predict
whether it clears, and does one year's result carry into the next?

- **Prop lines:** [`nfl/sources/wr_prop_totals`](../../nfl/sources/wr_prop_totals/)
  — Fantasy Alarm's annual WR prop-value grid, 2022–2026 (2022 is
  receiving-yards only).
- **Actuals:** [`nfl/sources/receiving_stats`](../../nfl/sources/receiving_stats/)
  — nflverse regular-season receiving totals + games played.
- **Visual write-up:** [`settle-sheet.html`](settle-sheet.html) — a
  self-contained page (sortable per-season tables, a miss histogram, the
  hit-rate-by-tier breakdown, a 2026 watch list). Also published as a
  Claude artifact: https://claude.ai/code/artifact/9511311e-ed4b-4feb-a98d-2188db080ff6

## Method

```
python3 projects/wr-prop-accuracy/scripts/grade.py     # -> data/wr_prop_grades.csv
python3 projects/wr-prop-accuracy/scripts/analyze.py    # -> hit-rate / year-over-year view CSVs
python3 projects/wr-prop-accuracy/scripts/context.py    # -> QB-tier / win-total view CSVs + context_summary.json
```

`context.py` additionally joins each graded prop to two **preseason** team
inputs -- the QB's tier ([`nfl/sources/qb_starters`](../../nfl/sources/qb_starters/))
and the team's Vegas win-total line
([`nfl/sources/win_totals`](../../nfl/sources/win_totals/)) -- neither of
which is a within-season outcome, so year-X prop result vs year-X preseason
context is not lookahead.

`coverage.py` checks the grid against an independent WR ADP ranking
(`underdog_adp` for 2023-25, FantasyData `adp` for 2022) and writes
`data/adp_coverage_gaps.csv` -- see the coverage note below.

`grade.py` matches each published prop row to a nflverse player-season on a
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
handful of top-25-by-ADP WRs each year (`coverage.py`):

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
