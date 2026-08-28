# wr_prop_totals

Fantasy Alarm's annual "wide receiver values using NFL player prop totals"
article, one per season — a study grid of each fantasy-relevant WR's
preseason Vegas prop lines (receiving yards / receptions / TDs) next to a
projected-PPR estimate and that player's current ADP.

- **What it is:** early/mid-August prop lines for that season, pulled off
  one sportsbook, published alongside ADP so the author can flag receivers
  whose Vegas number implies more (or less) than their draft cost.
- **Source:** fantasyalarm.com. Plain server-rendered HTML with the grid as
  a single `<table>` — no browser rendering, no Cloudflare wall, so this
  auto-fetches like `win_totals` / `adp` / `coaches`.
  - 2022: [`...-prop-totals-2022/131547`](https://www.fantasyalarm.com/articles/nfl/wide-receivers/identifying-fantasy-football-wide-receiver-values-using-nfl-player-prop-totals-2022/131547)
  - 2023: [`using-2023-nfl-player-props-...-wide-receiver/150731`](https://www.fantasyalarm.com/articles/nfl/wide-receivers/using-2023-nfl-player-props-to-find-fantasy-football-draft-values-at-wide-receiver/150731)
  - 2024: [`how-to-use-vegas-nfl-odds-player-props-.../162149`](https://www.fantasyalarm.com/articles/nfl/fantasy-football-advice/how-to-use-vegas-nfl-odds-player-props-to-find-fantasy-football-values/162149)
  - 2025: [`...-prop-totals/178604`](https://www.fantasyalarm.com/articles/nfl/wide-receivers/identifying-fantasy-football-wide-receiver-values-using-nfl-player-prop-totals/178604)
  - 2026: [`...-prop-totals-2026/193991`](https://www.fantasyalarm.com/articles/nfl/wide-receivers/identifying-fantasy-football-wide-receiver-values-using-nfl-player-prop-totals-2026/193991)
- **Run:** `python3 nfl/sources/wr_prop_totals/pipeline.py [year ...]`
- **Output:** `data/wr_prop_totals.csv` —
  `year, player, yards_line, rec_line, td_line, proj_ppr, adp, props_rank, adp_rank, sportsbook`

## Fetching (auto)

Run `pipeline.py`. A year with no cached `data/raw/wr_prop_totals_{year}.html`
is fetched once via `nfl/common/http.get_cached_or_fetch`, then parsed.
Re-running only re-parses.

## Schema drift across years — read before using

| Year | Yards | Rec | TDs | Proj PPR | ADP | Ranks | Sportsbook named |
|---|---|---|---|---|---|---|---|
| 2022 | yes | no  | no  | no  | yes | no  | FanDuel |
| 2023 | yes | yes | yes | yes | yes | yes | DraftKings |
| 2024 | yes | yes | yes | yes | yes | yes | (unstated) |
| 2025 | yes | yes | yes | yes | yes | yes | (unstated) |
| 2026 | yes | yes | yes | yes | yes | yes | (unstated) |

Missing columns come through blank in the CSV, never backfilled.

- **2022 is receiving-yards only** — no reception, TD, PPR, or rank columns.
- **2022's page embeds a second, stale table** — a leftover ~2021 list
  (DeAndre Hopkins, Antonio Brown, Chase Claypool, whole-number lines like
  `1350`). The pipeline picks whichever table has the most `X.5` yards
  values, which is always the real current-season grid; 2022's real grid
  is the second table.
- **The player-name column header is inconsistent** — `Player`,
  `Players`, and (2023) `DraftKings Over Unders` all label the same column.
- **`props_rank`** is the article's own ranking of receivers by projected
  prop value — labeled `POINTS RANK` in 2023–25, `Props Rank` in 2026.
  `adp_rank` is their rank by ADP. The article's `DIF` column
  (`props_rank − adp_rank`) is not stored — it's trivially recomputable.
- **`sportsbook`** is only filled when the article names the book in the
  column header (2022 FanDuel, 2023 DraftKings); later years don't say, so
  it's blank.

## Player names

Stored as published, with two fixes: curly apostrophes (`’`) normalized to
straight (`'`), and the 2026 grid's `Amon-Ra St. Bown` typo corrected to
`Amon-Ra St. Brown`. Names are **not** otherwise normalized — join on a
normalized key (strip punctuation / `Jr`/`Sr`/`III`), not the raw string.
[`projects/wr-prop-accuracy`](../../../projects/wr-prop-accuracy/) has the
matcher it uses against [`receiving_stats`](../receiving_stats/).

## `proj_ppr`

The article's own projected full-PPR points, not a Vegas-derived number.
Carried through as published for reference; the prop lines are the point of
this source.
