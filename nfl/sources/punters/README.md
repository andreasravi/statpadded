# punters

NFL punter season stats, 2022-2025, plus EXACT fantasy points computed under
a custom punter scoring system (punts inside the 20, and per-punt points by
distance bucket) -- see [`pipeline.py`](pipeline.py) for the exact formula
and [`../../../projects/kicker-punter-model/`](../../../projects/kicker-punter-model/)
for the projection model that consumes this.

- **Source:** `nflverse-data` play-by-play (every punt league-wide, with its
  real gross distance and an inside-the-20 flag) --
  `https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.csv.gz`

## Fetching (auto -- no Cloudflare wall, unlike PFR-sourced `game_results`)

Same as `kickers/` -- just run `pipeline.py`. It auto-downloads and caches a
lean per-punt extract at `data/raw/pbp_punting_{year}.csv` the first time
each year is needed; no browser tool required.

## Outputs

- **`data/punting_stats.csv`** -- one row per player-team-season: punts,
  gross average, punts inside the 20, and the resulting `fantasy_points` /
  `fantasy_points_per_game` under this league's scoring. The per-punt
  distance-bucket score is computed exactly -- each individual punt's real
  yardage decides its own bucket, not an estimated distribution. Regular
  season only (playoff plays are filtered out).

## Run

```bash
source venv/bin/activate
python3 nfl/sources/punters/pipeline.py [year ...]
```
