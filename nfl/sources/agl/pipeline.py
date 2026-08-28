"""
NFL team Adjusted Games Lost (AGL), per season, 2013-2025.

AGL is Football Outsiders' (now FTN's) injury-severity metric: not a simple
games-missed count, but a weighted measure that (1) counts injuries to
starters and important situational reserves more than bench players, and
(2) counts players who play through an injury-report designation at a
reduced weight rather than either fully in or fully out. Originated by Bill
Barnwell at Football Outsiders in the early 2000s; still produced today by
Aaron Schatz at FTN (footballoutsiders.com shut down in 2023 and its
archive is only reachable via the Wayback Machine now -- see below).

Source articles (one per season, several restate the prior season's total
alongside that year's own numbers as the methodology evolved slightly over
time -- see "vintage" notes in each data/raw/agl_{year}.json):
  2013-2020: Football Outsiders, footballoutsiders.com/stat-analysis/...
             (site is gone; pulled via web.archive.org snapshots)
  2021-2025: FTN Fantasy, ftnfantasy.com/nfl/...
Full list of source URLs and per-year vintage notes: see README.md and the
"source_article"/"source_note" fields in each data/raw/agl_{year}.json.

Output: data/agl.csv
  year, team, agl, agl_rank, off_agl, def_agl

  off_agl/def_agl are blank where the source article for that season didn't
  publish (or wasn't captured with) an offense/defense split -- 2014,
  2023, 2024, and 2025 have it; 2013 and 2015-2022 are total-only.

Rebuild (parsing only, no network):
  python3 nfl/sources/agl/pipeline.py
"""
import csv
import json
import os
import sys

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "agl.csv")

DEFAULT_START, DEFAULT_END = 2013, 2025

# These sources give team abbreviations directly rather than full names, but
# use a few outlet-specific / pre-relocation codes. Normalize to the same
# canonical codes used everywhere else in nfl/sources (see
# nfl/common/team_codes.py) -- JAC/LARM/STL/SD/OAK are all the same
# franchise as JAX/LAR/LAR/LAC/LV under a different-era label.
ABBR_ALIAS = {
    "JAC": "JAX",
    "LARM": "LAR",
    "STL": "LAR",
    "SD": "LAC",
    "OAK": "LV",
}


def parse_year(year: int) -> list:
    path = os.path.join(RAW_DIR, f"agl_{year}.json")
    if not os.path.exists(path):
        print(f"  (missing {path}, skipping {year})")
        return []
    with open(path, encoding="utf-8") as f:
        data = json.load(f)

    out = []
    for r in data["teams"]:
        team = ABBR_ALIAS.get(r["team"], r["team"])
        out.append({
            "year": year,
            "team": team,
            "agl": r["agl"],
            "agl_rank": r["rank"],
            "off_agl": r.get("off_agl", ""),
            "def_agl": r.get("def_agl", ""),
        })
    return out


def build(start_year=DEFAULT_START, end_year=DEFAULT_END):
    all_rows = []
    for year in range(start_year, end_year + 1):
        year_rows = parse_year(year)
        all_rows.extend(year_rows)
        print(f"{year}: {len(year_rows)} teams")

    by_year = {}
    for r in all_rows:
        by_year.setdefault(r["year"], set()).add(r["team"])
    for year, teams in sorted(by_year.items()):
        if len(teams) != 32:
            print(f"  WARNING: {year} has {len(teams)} teams, expected 32")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fieldnames = ["year", "team", "agl", "agl_rank", "off_agl", "def_agl"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(all_rows)
    print(f"Wrote {len(all_rows)} rows -> {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    args = sys.argv[1:]
    start = int(args[0]) if len(args) > 0 else DEFAULT_START
    end = int(args[1]) if len(args) > 1 else DEFAULT_END
    build(start, end)
