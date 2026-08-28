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
python3 projects/wr-prop-accuracy/scripts/analyze.py    # -> the 6 view CSVs
```

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

### 3. Year over year: no carryover

`corr(this year's Δ vs line, next year's Δ vs line) = +0.02` across 81
same-player pairs. How a receiver did against his number tells you nothing
about next year — the book re-prices enough to erase it (line moves −184
after a blowup miss, +215 after a monster year). Most buckets still
regress to a small *under* the next season. The one real buy-low: a
**−150 to −300 miss** (non-catastrophic down year) → **60% over the next
year, median +98**, after the book over-corrects the line down. The worst
spot is a **dead-on** result (−50 to +50) → 25% over next year: meet your
number and you get priced exactly at your level, with only downside.

## Bottom line

The market is efficient enough that beating these lines is hard and getting
harder, there's no player-level momentum to ride, and the only repeatable
angles are structural: fade 8+ TD lines, fade the 1,000–1,200 yard band,
and lean overs on healthy mid-tier (sub-1,000) receivers and on players
bouncing back from a moderate down year.
