"""
NFL kicker season stats, 2022-2025, plus EXACT fantasy points under this
league's custom kicker scoring:

  Each PAT made               +1
  Each PAT missed              -2
  FG missed (0-39 yds)         -1.5
  FG missed (40-49 yds)        -1
  FG missed (50-59 yds)        -0.5
  FG made yards                 0.1 / yard  (a 50-yard make scores 5.0)
  (60+ yard misses, vanishingly rare, are folded into the 50-59 bucket)

Source: nflverse-data play-by-play (every FG/PAT attempt, with its exact
kick distance and result) -- see nfl/common/pbp.py. This replaces an
earlier version of this pipeline that estimated FG-made yardage from PFR's
season-level distance-BUCKET counts (0-19/20-29/30-39/40-49/50+) using fixed
bucket midpoints; play-by-play gives the real distance on every kick, so
there's no estimation left in this version -- every point total here is
exact under the scoring rules above, not approximated.

Auto-fetches (no Cloudflare wall on the nflverse-data release, unlike PFR):
running this script with no cached data/raw/pbp_kicking_{year}.csv pulls the
season's full play-by-play once, keeps only FG/PAT rows and columns, and
caches that lean extract. Re-running is instant after that.

Also tracks 50+ yard FG attempts/makes (fga_50plus, fgm_50plus) per
player-season, on top of what the scoring formula itself needs -- these
aren't scored specially, but a kicker's long-range attempt VOLUME (not
long-range MAKE RATE, which is mostly single-season noise) turned out to be
a real, moderately persistent signal that meaningfully improves the
projection model in projects/kicker-punter-model/ -- see that project's
README for the backtest that found this.

Outputs:
  data/kicking_stats.csv   one row per player-team-season
"""
import csv
import os
import sys

import pandas as pd

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_CSV = os.path.join(HERE, "data", "kicking_stats.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.pbp import fetch_pbp_columns
from nfl.common.team_codes import normalize_nflverse_abbr

DEFAULT_YEARS = [2022, 2023, 2024, 2025]

PBP_COLUMNS = [
    "game_id", "week", "season_type", "posteam", "kicker_player_id", "kicker_player_name",
    "field_goal_attempt", "field_goal_result", "kick_distance",
    "extra_point_attempt", "extra_point_result",
]

PAT_MADE_PTS = 1
PAT_MISSED_PTS = -2
FG_MISS_0_39_PTS = -1.5
FG_MISS_40_49_PTS = -1
FG_MISS_50_59_PTS = -0.5
FG_YARD_PTS = 0.1


def _cache_year(year: int) -> str:
    path = os.path.join(RAW_DIR, f"pbp_kicking_{year}.csv")
    if os.path.exists(path):
        return path
    print(f"Fetching {year} play-by-play (kicking columns) ...")
    df = fetch_pbp_columns(year, PBP_COLUMNS)
    is_kick_play = (df["field_goal_attempt"] == 1) | (df["extra_point_attempt"] == 1)
    df = df[is_kick_play & df["kicker_player_name"].notna() & (df["season_type"] == "REG")].copy()
    df["posteam"] = df["posteam"].apply(normalize_nflverse_abbr)
    os.makedirs(RAW_DIR, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def _fg_bucket(distance: float) -> str:
    if distance < 40:
        return "0_39"
    if distance < 50:
        return "40_49"
    return "50_59"  # PFR/this scoring has no explicit 60+ tier; folded in here


def build(years=DEFAULT_YEARS) -> list:
    frames = []
    for year in years:
        path = _cache_year(year)
        df = pd.read_csv(path)
        df["year"] = year
        frames.append(df)
    plays = pd.concat(frames, ignore_index=True)

    rows = []
    group_cols = ["year", "posteam", "kicker_player_id", "kicker_player_name"]
    for (year, team, kid, name), g in plays.groupby(group_cols):
        games = g["game_id"].nunique()

        fg = g[g["field_goal_attempt"] == 1]
        fgm = fg[fg["field_goal_result"] == "made"]
        fg_missed_or_blocked = fg[fg["field_goal_result"] != "made"]

        fga, fgm_n = len(fg), len(fgm)
        fg_made_yards = fgm["kick_distance"].sum()
        fg_pct = round(100 * fgm_n / fga, 1) if fga else 0.0

        miss_counts = {"0_39": 0, "40_49": 0, "50_59": 0}
        for _, r in fg_missed_or_blocked.iterrows():
            dist = r["kick_distance"]
            bucket = _fg_bucket(dist) if pd.notna(dist) else "0_39"  # blocked kicks have no distance; treat as short-range miss
            miss_counts[bucket] += 1

        # 50+ yard attempts: not part of the scoring formula, but a coach's
        # willingness to send a kicker out from 50+ is a real, moderately
        # persistent signal (unlike long-range MAKE rate, which is mostly
        # single-season noise) -- see projects/kicker-punter-model/README.md.
        long_fg = fg[fg["kick_distance"] >= 50]
        fga_50plus = len(long_fg)
        fgm_50plus = int((long_fg["field_goal_result"] == "made").sum())

        xp = g[g["extra_point_attempt"] == 1]
        xpa = len(xp)
        pat_made = int((xp["extra_point_result"] == "good").sum())
        pat_missed = xpa - pat_made

        fantasy_points = (
            pat_made * PAT_MADE_PTS
            + pat_missed * PAT_MISSED_PTS
            + fg_made_yards * FG_YARD_PTS
            + miss_counts["0_39"] * FG_MISS_0_39_PTS
            + miss_counts["40_49"] * FG_MISS_40_49_PTS
            + miss_counts["50_59"] * FG_MISS_50_59_PTS
        )

        rows.append({
            "year": year,
            "player": name,
            "team": team,
            "games": games,
            "fga": fga,
            "fgm": fgm_n,
            "fg_pct": fg_pct,
            "xpa": xpa,
            "xpm": pat_made,
            "pat_made": pat_made,
            "pat_missed": pat_missed,
            "fg_made_yards": int(fg_made_yards),
            "fg_missed_0_39": miss_counts["0_39"],
            "fg_missed_40_49": miss_counts["40_49"],
            "fg_missed_50_59": miss_counts["50_59"],
            "fga_50plus": fga_50plus,
            "fgm_50plus": fgm_50plus,
            "fantasy_points": round(fantasy_points, 2),
            "fantasy_points_per_game": round(fantasy_points / games, 2) if games else 0.0,
        })

    rows.sort(key=lambda r: (r["year"], -r["fantasy_points"]))
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["year", "player", "team", "games", "fga", "fgm", "fg_pct", "xpa", "xpm",
                  "pat_made", "pat_missed", "fg_made_yards", "fg_missed_0_39",
                  "fg_missed_40_49", "fg_missed_50_59", "fga_50plus", "fgm_50plus",
                  "fantasy_points", "fantasy_points_per_game"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} kicker-seasons -> {OUT_CSV}")
    return rows


if __name__ == "__main__":
    years = [int(a) for a in sys.argv[1:]] if len(sys.argv) > 1 else DEFAULT_YEARS
    build(years)
