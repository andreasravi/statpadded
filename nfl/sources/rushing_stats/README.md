# rushing_stats

NFL rushing season stats, regular season, one row per player per season —
actual production to grade preseason RB expectations against (Vegas prop
lines, ADP, projections). Sibling of [`receiving_stats`](../receiving_stats/);
same source, rushing columns instead of receiving.

- **Source:** `nflverse-data` season-level player stats release —
  `stats_player_reg_{year}.csv.gz` (already aggregated to season totals by
  nflverse) plus `stats_player_week_{year}` for the first-game team. No
  Cloudflare wall — auto-fetches.
- **Run:** `python3 nfl/sources/rushing_stats/pipeline.py [year ...]`
  (default 2021–2025)
- **Output:** `data/rushing_stats.csv` — one row per player-season for
  every player with ≥ 1 carry:
  `year, player_id, player, team, team_start, traded, position, games,
   carries, rushing_yards, rushing_tds, rushing_first_downs,
   receptions, receiving_yards, receiving_tds, rush_rec_yards, rush_rec_tds`

## Notes

- `player_id` is nflverse's stable `gsis_id` — prefer it over name when
  joining across seasons.
- `team` is `recent_team` (last team that season); `team_start` is the
  team from the player's first regular-season game (what a preseason line
  or ADP was priced around); `traded` = `yes` when they differ. Both
  normalized via `nfl/common/team_codes.normalize_nflverse_abbr` (nflverse
  uses `LA` for the Rams; this repo uses `LAR`).
- Carries **receiving** columns too, and precomputes `rush_rec_yards` /
  `rush_rec_tds`, so a combined rush+rec prop line (some 2022 pass-catching
  backs in `rb_prop_totals`) can be graded on the same footing.
- `games` is games *played* — divide by it for per-game rates, and check
  it before treating a season total as a full sample. In the RB prop
  analysis (`projects/prop-accuracy`) `games < 14` is the single biggest
  predictor of a rushing-yards under.
- Regular season only; playoffs excluded, matching how preseason lines and
  ADP are framed.
- A back who missed the whole season has **no row here** (needs ≥ 1
  carry); the grader treats a known zero-snap season as a real 0, not a
  gap.
- Includes anyone with a carry (QBs, WRs on jet sweeps, …), not just RBs —
  filter on `position`.
