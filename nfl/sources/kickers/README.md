# kickers

NFL kicker season stats, 2022-2025, plus EXACT fantasy points computed under
a custom kicker scoring system (PAT made/missed, FG missed by distance
bucket, FG made yards) -- see [`pipeline.py`](pipeline.py) for the exact
formula and [`../../../projects/kicker-punter-model/`](../../../projects/kicker-punter-model/)
for the projection model that consumes this.

- **Source:** `nflverse-data` play-by-play (every FG/PAT attempt league-wide,
  with its real distance and result) --
  `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.csv.gz`

## Fetching (auto -- no Cloudflare wall, unlike PFR-sourced `game_results`)

Just run `pipeline.py`. On a year with no cache, it downloads that season's
full play-by-play once (via `nfl/common/pbp.py`), keeps only the FG/PAT rows
and columns it needs, and caches that lean extract at
`data/raw/pbp_kicking_{year}.csv`. Re-running is instant after that -- no
manual browser step required.

## Outputs

- **`data/kicking_stats.csv`** -- one row per player-team-season: FGA/FGM,
  FG%, PAT made/missed, exact FG-made-yards (summed from each make's real
  kick distance), FG misses by distance bucket, and the resulting
  `fantasy_points` / `fantasy_points_per_game` under this league's scoring.
  Regular season only (playoff plays are filtered out).

## Run

```bash
source venv/bin/activate
python3 nfl/sources/kickers/pipeline.py [year ...]
```
