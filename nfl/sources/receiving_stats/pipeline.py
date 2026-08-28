"""
NFL receiving season stats, regular season, one row per player per season --
actual production to grade preseason expectations against (Vegas prop
lines, ADP, projections). Source: nflverse-data `stats_player_reg_{year}`
release (already season-aggregated; no play-by-play rollup). No Cloudflare
wall -- auto-fetches. See README.md.

Run:    python3 nfl/sources/receiving_stats/pipeline.py [year ...]
Output: data/receiving_stats.csv -- one row per player-season, >=1 target:
        year, player_id, player, team, position, games, targets,
        receptions, receiving_yards, receiving_tds, receiving_air_yards,
        target_share
"""
import csv
import os
import sys

import pandas as pd

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "receiving_stats.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.team_codes import normalize_nflverse_abbr

DEFAULT_YEARS = [2021, 2022, 2023, 2024, 2025]

RELEASE_URL = (
    "https://github.com/nflverse/nflverse-data/releases/download/"
    "stats_player/stats_player_reg_{year}.csv.gz"
)

KEEP = [
    "player_id", "player_display_name", "position", "recent_team", "games",
    "targets", "receptions", "receiving_yards", "receiving_tds",
    "receiving_air_yards", "target_share",
]

FIELDNAMES = [
    "year", "player_id", "player", "team", "position", "games", "targets",
    "receptions", "receiving_yards", "receiving_tds", "receiving_air_yards",
    "target_share",
]


def _cache_year(year):
    path = os.path.join(RAW_DIR, f"receiving_stats_{year}.csv")
    if os.path.exists(path):
        return path
    print(f"Fetching {year} season player stats ...")
    df = pd.read_csv(RELEASE_URL.format(year=year), low_memory=False)
    df = df[[c for c in KEEP if c in df.columns]].copy()
    df = df[df["targets"].fillna(0) > 0]
    os.makedirs(RAW_DIR, exist_ok=True)
    df.to_csv(path, index=False)
    return path


def build(years=None):
    years = years or DEFAULT_YEARS
    rows = []
    for year in years:
        df = pd.read_csv(_cache_year(year))
        for _, r in df.iterrows():
            rows.append({
                "year": year,
                "player_id": r.get("player_id", ""),
                "player": r["player_display_name"],
                "team": normalize_nflverse_abbr(str(r.get("recent_team", ""))),
                "position": r.get("position", ""),
                "games": int(r["games"]) if pd.notna(r["games"]) else "",
                "targets": int(r["targets"]) if pd.notna(r["targets"]) else "",
                "receptions": int(r["receptions"]) if pd.notna(r["receptions"]) else "",
                "receiving_yards": int(r["receiving_yards"]) if pd.notna(r["receiving_yards"]) else "",
                "receiving_tds": int(r["receiving_tds"]) if pd.notna(r["receiving_tds"]) else "",
                "receiving_air_yards": int(r["receiving_air_yards"]) if pd.notna(r.get("receiving_air_yards")) else "",
                "target_share": round(float(r["target_share"]), 4) if pd.notna(r.get("target_share")) else "",
            })
    rows.sort(key=lambda x: (x["year"], -(x["receiving_yards"] or 0)))
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"wrote {len(rows)} player-seasons -> {os.path.relpath(OUT_PATH, REPO_ROOT)}")


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]]
    build(args or None)
