# Coaching Changes vs Win Totals

Does hiring a new head coach predict a team's win total or year-over-year
improvement — and do new-coach teams beat or miss the Vegas win-total line
with any consistency?

## Data sources

Both are shared, reusable pipelines under [`nfl/sources/`](../../nfl/sources/)
rather than duplicated in this project:

- [`nfl/sources/coaches`](../../nfl/sources/coaches/) — head coach per team
  per season, MyFootballToolbox.com, 2014–2025 (2014 pulled as a lookback
  year so `new_coach` can be computed for the 2015 season)
- [`nfl/sources/win_totals`](../../nfl/sources/win_totals/) — Vegas win-total
  line + actual wins per team per season, Covers.com, 2015–2025

## Pipeline

```bash
source venv/bin/activate
python3 nfl/sources/coaches/pipeline.py        # -> nfl/sources/coaches/data/coaches.csv
python3 nfl/sources/win_totals/pipeline.py     # -> nfl/sources/win_totals/data/win_totals.csv
python3 projects/coaching-win-impact/scripts/analyze.py   # -> data/merged.csv + printed stats
```

## Method

- `new_coach` = 1 if a team's season-opening head coach differs from the
  prior season's; mid-season interim coaches are dropped (kept: the coach
  who started the season, since that's who a preseason win-total line is
  actually priced against).
- `tenure` = consecutive years (within the pulled window) under the same
  coach — a lower bound for coaches already in place before 2014.
- Three separate questions, each answered on `data/merged.csv`:
  1. `new_coach` vs `wins_change` (actual wins this year − last year)
  2. `new_coach` vs `line_change` (how far Vegas moves the win total YoY)
  3. `new_coach` vs `beat_margin` (actual wins − this year's own line) —
     the "is this exploitable" question

## Findings (n = 341 team-seasons with a valid prior year, 2015–2025)

| Question | Result |
|---|---|
| New coach → YoY win change | **+1.60 wins** (new) vs **−0.39** (incumbent). r = +0.23, p < 0.0001 — real and significant. |
| New coach → line movement YoY | Line *drops* 0.65 for new-coach teams (they were bad, hence the firing) but only rises 0.23 for incumbents — the market may under-price the bounce-back. |
| New coach → beats own line | +0.10 avg margin (new) vs −0.18 (incumbent). r = +0.04, **p = 0.43 — not significant.** |

Reading these together: new coaches show up on teams coming off bad seasons
(prior wins ≈ 5.5) that were always likely to regress toward the mean —
untangling "new coach bump" from ordinary mean reversion isn't possible with
win totals alone. The predictive win-change effect is real, but it doesn't
translate into a statistically reliable edge against the market's own line
for that team — any lean toward "back the new coach" is inside the noise at
this sample size.

Coaching **tenure** shows average wins climbing steadily from year 1 (7.15)
to year 6+ (9.59) — mostly a survivorship signal (bad coaches get fired
before reaching year 5+). The beat-margin-by-tenure breakdown is noisier and
should be read cautiously at the tails (n=26 at tenure 5).
