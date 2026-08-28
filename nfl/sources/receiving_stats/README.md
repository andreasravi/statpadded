# receiving_stats

NFL receiving season stats, regular season, one row per player per season —
actual production to grade preseason expectations against (Vegas prop
lines, ADP, projections).

- **Source:** `nflverse-data` season-level player stats release —
  `https://github.com/nflverse/nflverse-data/releases/download/stats_player/stats_player_reg_{year}.csv.gz`.
  Already aggregated to season totals by nflverse (no play-by-play rollup
  needed, unlike `kickers`/`punters`). No Cloudflare wall — auto-fetches.
- **Run:** `python3 nfl/sources/receiving_stats/pipeline.py [year ...]`
  (default 2021–2025)
- **Output:** `data/receiving_stats.csv` — one row per player-season for
  every player with ≥ 1 target:
  `year, player_id, player, team, team_start, traded, position, games,
   targets, receptions, receiving_yards, receiving_tds,
   receiving_air_yards, target_share`

## Fetching (auto)

Run `pipeline.py`. A year with no cache downloads that season's
`stats_player_reg` file (season totals) and `stats_player_week` file (for
the first-game team) once, keeps what it needs, and caches lean extracts at
`data/raw/receiving_stats_{year}.csv` and `data/raw/receiving_start_team_{year}.csv`.
Re-running is instant.

## Notes

- `player_id` is nflverse's stable `gsis_id` — prefer it over name when
  joining across seasons.
- `team` is `recent_team` (the player's last team that season, so a
  mid-season trade shows only the destination); `team_start` is the team
  from the player's first regular-season game (what a preseason line/ADP was
  priced around); `traded` = `yes` when they differ. Both normalized to this
  repo's canonical abbreviation via
  `nfl/common/team_codes.normalize_nflverse_abbr` (nflverse uses `LA` for
  the Rams; this repo uses `LAR`).
- `games` is games *played* — the number to divide by for per-game rates,
  and the one to check before treating a season total as a full sample.
- Season totals are **regular season only**; playoff production is
  excluded, matching how preseason lines and ADP are framed.
- Includes WR/TE/RB (anyone targeted), not just wide receivers — filter on
  `position` if you only want one.
