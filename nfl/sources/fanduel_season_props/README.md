# fanduel_season_props

**Live** FanDuel season-long player prop over/unders with the actual
posted odds on each side — rushing yards, rushing TDs, receiving yards,
passing yards, passing TDs. The thing the historical `*_prop_totals`
sources can only approximate after the fact: what the market has up *right
now*, and how it's juiced.

- **Source:** FanDuel's sportsbook web API
  (`sbapi.nj.sportsbook.fanduel.com/api/content-managed-page?...&customPageId=nfl`),
  the same JSON the site's React app renders from. Uses FanDuel's public
  web key (`_ak`); answers from any IP. Every
  `<Player> Regular Season <Stat> 2026-27` market is a two-runner
  Over/Under — the line is in the runner name, the price in
  `winRunnerOdds`.
- **Run:** `python3 nfl/sources/fanduel_season_props/pipeline.py`
- **Output:** `data/fanduel_season_props.csv` —
  `fetched_at, player, position, stat, line, over_odds, under_odds,
   over_implied, under_implied, no_vig_over, market_id`
  - `stat` ∈ `rush_yds` | `rush_td` | `rec_yds` | `pass_yds` | `pass_td`
  - `*_implied` = the American odds as a raw probability; `no_vig_over` =
    the over probability after removing the hold (`po / (po + pu)`).
- Raw response cached at `data/raw_snapshot.json`.

## Live, not archival

Like [`kalshi_win_totals`](../kalshi_win_totals/) this is a **snapshot** —
no year parameter, always whatever season FanDuel currently has up,
stamped with the pull time. Each run overwrites the output; copy it first
if you want to keep a dated read.

## Notes

- **Season-long yardage O/Us sit at −114 / −114** (an even two-way market,
  ~8.8% hold split evenly). FanDuel posts them balanced and only moves
  them on real action, so the *line* is the signal, not the price. The
  **TD** markets do carry a real lean — e.g. Travis Etienne 5.5 rush TD at
  O +130 / U −182, a hard under.
- Coverage is the top of each position only (~26 RB rushing-yards, ~43 WR
  receiving-yards, ~23 QB). For the deeper bench, cross-reference
  [`rb_prop_totals`](../rb_prop_totals/)'s `firstdown.studio` rows — which
  land within ~10–35 yds of these posted numbers (median |Δ| ≈ 8).
- Milestone / alt-line markets ("1,250+ / 1,500+ rushing yards") are **not
  on this feed** — they live in a separate FanDuel special that the
  `customPageId=nfl` page doesn't carry, and DraftKings' API is
  Akamai-blocked from a datacenter IP. Not currently pulled.
- Names are FanDuel's spellings (`Kenneth Walker III`, `Marvin Harrison
  Jr.`); join on a normalized key.
