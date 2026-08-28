# firstdown_studio_2026

First Down Studio's 2026 season "Vegas Fantasy Football Rankings" boards —
**QB + RB + WR** — captured for two things:

1. **The authoritative post-trade 2026 team for every fantasy-relevant
   skill player.** The 2026 offseason moved a *lot* of names (Jaylen
   Waddle → DEN, A.J. Brown → NE, Mike Evans → SF, DJ Moore → BUF, Kyler
   Murray → MIN, Tua → ATL, Malik Willis → MIA, …). Fantasy Alarm's prop
   grid has no team column and nflverse's prior-season team is stale, so
   the 2026 grading / picks / watch layer joins here.
2. **The projected Week-1 starter per team** — the highest-ranked QB on
   the QB board. Used to look up that QB's tier in
   [`qb_tiers`](../qb_tiers/) *by name* (qb_tiers' own team column is also
   stale for QBs who moved).

- **Run:** `python3 nfl/sources/firstdown_studio_2026/pipeline.py`
  (re-parses committed raw captures under `data/raw/`; the boards are
  client-rendered so there is no live fetch — same as
  [`rb_prop_totals`](../rb_prop_totals/))
- **Output:** `data/firstdown_2026.csv` —
  `pos, rank, player, team, rookie, proj_rush_yds, proj_rush_tds,
   proj_rec, proj_rec_yds` (projection columns filled for the RB board
   only; the RB board is also the line source for `rb_prop_totals`'s 2026
   rows).

## Notes

- `data/raw/rb_board.json` is the same capture `rb_prop_totals` reads for
  its 2026 `firstdown.studio` rows — it lives here now.
- FDS's numbers are a Vegas-prop-driven **projection**, not a posted O/U;
  its rushing-yards figure tracks FanDuel's posted season line within
  ~10–35 yds (see [`fanduel_season_props`](../fanduel_season_props/)),
  its TD figure runs high.
- Where a team has two QBs on the board (ATL: Penix > Tua; CLE: Watson >
  Sanders), the higher-ranked one is taken as the projected starter.
- Rookies (`F. Mendoza` / LV, `Jeremiyah Love` / ARI, …) may have no
  `qb_tiers` entry — those teams get no QB-tier context.
- Captured 2026-08-28. Re-capture from the boards if rosters move again.
