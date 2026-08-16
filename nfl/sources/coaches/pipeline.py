"""
NFL head coach by team, per season.
Source: MyFootballToolbox.com
  https://myfootballtoolbox.com/nfl/coaches/years/{year}/

Output: data/coaches.csv
  year, team, head_coach, new_coach
    new_coach = 1 if this team's head coach differs from the prior season's
    (i.e. this is the coach's first year with the team), else 0. The first
    season in range has new_coach left blank ("") since there's no prior
    year in the pulled data to compare against.

Run directly to fetch (cached) + parse:
  python3 nfl/sources/coaches/pipeline.py [start_year] [end_year]

Note: pass one year earlier than you need new_coach flags for, e.g. to get
reliable new_coach flags for 2015-2025 pull 2014-2025.
"""
import csv
import os
import re
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from nfl.common.http import get_cached_or_fetch

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "coaches.csv")

DEFAULT_START, DEFAULT_END = 2014, 2025

# MyFootballToolbox shows each team's logo as it was THAT season (unlike
# fantasydata, which always shows the current-franchise logo) -- so a
# relocated team's abbreviation changes mid-history and would otherwise
# break the year-over-year new_coach comparison right at the relocation
# boundary. Normalize to the same canonical codes used everywhere else.
ABBR_ALIAS = {
    "OAK": "LV",
    "SD": "LAC",
    "STL": "LAR",
}


def fetch_year(year: int) -> str:
    url = f"https://myfootballtoolbox.com/nfl/coaches/years/{year}/"
    return get_cached_or_fetch(RAW_DIR, "coaches", year, url)


def parse_year(year: int, rows_out: list):
    path = fetch_year(year)
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    table = soup.find("table")
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 2:
            continue
        team_cell, coach_cell = tds
        img = team_cell.find("img")
        if not img or not img.get("src"):
            continue
        m = re.search(r"team_logos_48x48/([A-Z]+)\.png", img["src"])
        if not m:
            continue
        abbr = m.group(1)
        abbr = ABBR_ALIAS.get(abbr, abbr)
        coach = coach_cell.get_text(strip=True)
        if not coach:
            continue
        rows_out.append({"year": year, "team": abbr, "head_coach": coach})


def build(start_year=DEFAULT_START, end_year=DEFAULT_END):
    all_rows = []
    for year in range(start_year, end_year + 1):
        parse_year(year, all_rows)

    # A team can list >1 coach in a year (mid-season firing -> interim coach
    # gets their own row on the site). Keep only the first row per (year,
    # team) -- the coach who started the season -- since that's what a
    # preseason win-total line is actually priced against.
    seen = set()
    raw_rows = []
    for r in all_rows:
        key = (r["year"], r["team"])
        if key in seen:
            continue
        seen.add(key)
        raw_rows.append(r)

    # figure new_coach by comparing to the prior fetched year for that team
    by_key = {(r["year"], r["team"]): r["head_coach"] for r in raw_rows}
    rows = []
    for r in raw_rows:
        prior = by_key.get((r["year"] - 1, r["team"]))
        if prior is None:
            new_coach = ""  # no prior year pulled to compare against
        else:
            new_coach = 1 if prior != r["head_coach"] else 0
        rows.append({**r, "new_coach": new_coach})

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fieldnames = ["year", "team", "head_coach", "new_coach"]
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    args = sys.argv[1:]
    start = int(args[0]) if len(args) > 0 else DEFAULT_START
    end = int(args[1]) if len(args) > 1 else DEFAULT_END
    build(start, end)
