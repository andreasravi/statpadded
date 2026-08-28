# fantasy_finish

Actual end-of-season fantasy finish per player, 2023–2025 — how a player
*actually* ranked once the season played out, for comparing against
preseason expectations (e.g. [`nfl/sources/underdog_adp`](../underdog_adp/)'s
August ADP).

- **What it is:** a season-end rank per player — `season_finish` (rank by
  total fantasy points, so missed games hurt it) and, 2025 only,
  `per_game_finish` (rank by points-per-game while active — a way to tell
  "missed a lot of games" apart from "was just bad while playing").
- **Source:** underdognetwork.com. There's no dedicated "final standings"
  page — each season's finish instead gets published as a reference column
  on *next* year's rankings article (a "how'd last year's picks turn out"
  column), so this pipeline reads that column back out of next year's
  page rather than needing its own site. Same `__NEXT_DATA__`-embedded-
  table trick as `underdog_adp` (see that source's README) — no browser
  rendering needed.
  - 2023 season's finish ← 2024's August-update article's `"2023 Finish"` column
  - 2024 season's finish ← 2025's August-update article's `"Finish2024"` column
  - 2025 season's finish ← [2026's post-draft article](https://underdognetwork.com/football/fantasy-rankings/2026-fantasy-football-rankings)'s `"Season 2025"`/`"Per Game 2025"` columns (the first year Underdog split the two)
- **Run:** `python3 pipeline.py`
- **Output:** `data/fantasy_finish.csv` —
  `year, player, team, pos, season_finish, per_game_finish`

## Notes

- A player with no ranked finish that season at all (didn't play enough to
  be ranked) is simply absent from the output for that year, rather than
  written as a null row — most often because they missed most/all of the
  season to injury, but not always (could also be a late-season signing,
  retirement, etc.).
- `per_game_finish` is blank for 2023 and 2024 — those years' source
  articles only published one finish column (total points), not a
  per-game split.
- Team/name normalization matches `underdog_adp`
  (`normalize_underdog_team()` in `nfl/common/team_codes.py`).
