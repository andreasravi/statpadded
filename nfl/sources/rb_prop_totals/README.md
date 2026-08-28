# rb_prop_totals

Preseason **season-long running-back prop over/unders** — rushing yards,
rushing TDs, and (where a book only posted a combined number) rushing +
receiving yards — from every source we've been able to re-parse. The RB
analogue of [`wr_prop_totals`](../wr_prop_totals/).

**Long format:** one row per `(year, player, stat, source)`.

- **Run:** `python3 nfl/sources/rb_prop_totals/pipeline.py`
- **Output:** `data/rb_prop_totals.csv` —
  `year, player, team, stat, line, line_low, line_high, odds_low,
  odds_high, book, proj, source, snapshot`
  - `stat` ∈ `rush_yds` | `rush_td` | `rush_rec_yds`
  - `line` is the single number to bet against — for a range source it's
    the `line_low`/`line_high` midpoint; for a single-book source all
    three are equal.
- All raw HTML is committed under `data/raw/`; there is **no live fetch**,
  the pipeline only re-parses.

## Sources

| `source` | Years | Shape | Notes |
|---|---|---|---|
| `fantasypoints` | 2023–25 | range across books (`line_low`=lowest total on the board / best for over; `line_high`=highest / best for under) + FP projection + prices | rushing yards every year; rushing **TDs 2024–25 only** (no 2023 TD grid); 2025 TD grid = **top ~17 RBs only** |
| `sportsbetting.ag` | 2022 | one offshore book, one number, no price | `book = "SportsBetting.ag"`; via gambling911.com's Aug-2022 reprint; ~30 RBs, pure rushing line for ~22 of them, rush+rec only for the pass-catching backs |

### fantasypoints

Fantasy Points' annual "NFL Rushing Yards Props" / "Rushing Touchdowns
Props" articles, paywalled now, pulled from the **Wayback Machine's
June–Aug snapshot**. Snapshot URLs are in `pipeline.py`'s `FP` dict and
the CSV's `snapshot` column. Mobile QBs (Hurts, Allen, Lamar, …) appear in
these grids and are kept — filter on your own RB list. One source typo
(`590.5.5` for Jaylen Warren 2024) is handled by taking the first clean
number. 2024's `MarShawn Lloyd` row has no team suffix.

### sportsbetting.ag

SportsBetting.ag hung ~60 RB season props (rushing yards + rushing TDs for
nearly every back, rush+rec for a few); gambling911.com reprinted the full
board in August 2022. Single book, no odds shown. **`Breece Hall` was
printed as `Bryce Hall`** (that's the Jets CB's name — the numbers, 825.5
rush yds / 5.5 TD, are the rookie RB's) and is corrected in the pipeline.
No `team` (the reprint doesn't give them).

**2022 only.** Checked for other years: gambling911 didn't reprint an
equivalent board for 2023–25 (they switched to single-game rushing-yards
write-ups), and SportsBetting.ag / BetOnline's own sites are JS apps with
no usable archived HTML. There's also no cross-reference to be had — this
source and `fantasypoints` don't share a season.

## Coverage summary

| Year | `rush_yds` | `rush_td` | `rush_rec_yds` |
|---|--:|--:|--:|
| 2022 | 22 | 22 | 8 |
| 2023 | 34 | 0 | 0 |
| 2024 | 40 | 35 | 0 |
| 2025 | 30 | 19 | 0 |

## Player names

Stored as published (`De'Von Achane`, `Kenneth Walker`, `Travis Etienne`;
`Isaiah`/`Isiah Pacheco` differs by year). Join on a normalized key
(lowercase, strip punctuation and `Jr`/`Sr`/`III`), not the raw string —
[`projects/prop-accuracy`](../../../projects/prop-accuracy/)'s `grade_rb.py`
has the matcher (with a first-initial + last-name fallback and the
`Isaiah→Isiah Pacheco` alias) and grades every line against
[`rushing_stats`](../rushing_stats/).

## Known gaps / not yet found

- **2023 rushing TDs** — no comprehensive grid from any source.
- **2022 pure rushing lines** for CMC, Ekeler, Kamara, A. Jones, D. Swift,
  Akers, Patterson, Pollard — SportsBetting.ag only posted combined yards.
- **2021 and earlier** — not attempted.
- Partial sources seen but not scraped (a handful of RBs each, with real
  book prices): Sharp Football Analysis best-bets (2022–25), BettingPros
  season-long articles, Covers "best prop per team".
