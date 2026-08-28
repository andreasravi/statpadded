"""
NFL punter season stats, 2022-2025, plus EXACT fantasy points under this
league's custom punter scoring:

  Punts inside the 20              +1  (per punt)
  Punt average 44.0+                +3  (per GAME, that game's average punt distance)
  Punt average 42.0-43.9            +2  (per GAME)
  Punt average 40.0-41.9            +1  (per GAME)
  (a game with an average under 40.0 yards scores 0 from this bucket)

Only PT20 is a per-punt stat; the "Punt Average" tiers score once per GAME
based on that game's average distance, not once per individual punt.

Source: nflverse-data play-by-play (every punt, with its exact gross
distance and an inside-the-20 flag) -- see nfl/common/pbp.py. This replaces
an earlier version of this pipeline that *estimated* the per-punt bucket
score (and, before that, mistakenly scored the average tiers per punt
instead of per game). Play-by-play gives the real distance of every single
punt, so each game's average is computed exactly, no estimation.

Auto-fetches (no Cloudflare wall on the nflverse-data release, unlike PFR):
running this script with no cached data/raw/pbp_punting_{year}.csv pulls the
season's full play-by-play once, keeps only punt rows and columns, and
caches that lean extract. Re-running is instant after that.

Outputs:
  data/punting_stats.csv   one row per player-team-season
"""
import csv
import os
import sys

import pandas as pd

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_CSV = os.path.join(HERE, "data", "punting_stats.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.pbp import fetch_pbp_columns
from nfl.common.team_codes import normalize_nflverse_abbr

DEFAULT_YEARS = [2022, 2023, 2024, 2025]

PBP_COLUMNS = [
    "game_id", "week", "season_type", "posteam", "punter_player_id", "punter_player_name",
    "punt_attempt", "kick_distance", "punt_inside_twenty", "punt_blocked",
]

PT20_PTS = 1
PTA44_PTS = 3
PTA42_PTS = 2
PTA40_PTS = 1


def _cache_year(year: int) -> str:
    path = os.path.join(RAW_DIR, f"pbp_punting_{year}.csv")
    if os.path.exists(path):
        return path
    print(f"Fetching {year} play-by-play (punting columns) ...")
    df = fetch_pbp_columns(year, PBP_COLUMNS)
    df = df[(df["punt_attempt"] == 1) & df["punter_player_name"].notna() & (df["season_type"] == "REG")].copy()
    df["posteam"] = df["posteam"].apply(normalize_nflverse_abbr)
    os.makedirs(RAW_DIR, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def _game_avg_bucket_points(avg: float) -> float:
    if pd.isna(avg):
        return 0.0  # every punt in the game was blocked: no valid average
    if avg >= 44:
        return PTA44_PTS
    if avg >= 42:
        return PTA42_PTS
    if avg >= 40:
        return PTA40_PTS
    return 0.0


def build(years=DEFAULT_YEARS) -> list:
    frames = []
    for year in years:
        path = _cache_year(year)
        df = pd.read_csv(path)
        df["year"] = year
        frames.append(df)
    plays = pd.concat(frames, ignore_index=True)

    player_cols = ["year", "posteam", "punter_player_id", "punter_player_name"]

    # per-game average -> that game's bucket points (blocked punts excluded
    # from the average, matching how "punt average" is normally reported)
    non_blocked = plays[plays["punt_blocked"] != 1]
    game_avg = (
        non_blocked.groupby(player_cols + ["game_id"])["kick_distance"]
        .mean()
        .reset_index(name="game_avg")
    )
    game_avg["game_bucket_points"] = game_avg["game_avg"].apply(_game_avg_bucket_points)
    season_bucket_points = game_avg.groupby(player_cols)["game_bucket_points"].sum().rename("bucket_points")

    rows = []
    for key, g in plays.groupby(player_cols):
        year, team, pid, name = key
        games = g["game_id"].nunique()
        punts = len(g)
        nb = g[g["punt_blocked"] != 1]
        punt_avg = round(nb["kick_distance"].mean(), 1) if len(nb) else 0.0
        in20 = int(g["punt_inside_twenty"].fillna(0).sum())

        bucket_points = round(float(season_bucket_points.get(key, 0.0)), 2)
        pt20_points = in20 * PT20_PTS
        fantasy_points = round(bucket_points + pt20_points, 2)
        avg_bucket_points_per_game = round(bucket_points / games, 3) if games else 0.0  # pure leg skill, volume-independent

        rows.append({
            "year": year,
            "player": name,
            "team": team,
            "games": games,
            "punts": punts,
            "punt_avg": punt_avg,
            "punt_in_20": in20,
            "avg_bucket_points_per_game": avg_bucket_points_per_game,
            "bucket_points": bucket_points,
            "pt20_points": pt20_points,
            "fantasy_points": fantasy_points,
            "fantasy_points_per_game": round(fantasy_points / games, 2) if games else 0.0,
        })

    rows.sort(key=lambda r: (r["year"], -r["fantasy_points"]))
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["year", "player", "team", "games", "punts", "punt_avg", "punt_in_20",
                  "avg_bucket_points_per_game", "bucket_points", "pt20_points",
                  "fantasy_points", "fantasy_points_per_game"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} punter-seasons -> {OUT_CSV}")
    return rows


if __name__ == "__main__":
    years = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else DEFAULT_YEARS
    build(years)
