"""
NFL regular-season win-total odds, per team per season.
Source: Covers.com Sports Odds History
  https://www.covers.com/sportsoddshistory/nfl-win/?y={year}&sa=nfl&t=win

Output: data/win_totals.csv
  year, team, win_total_line, over_odds, under_odds, actual_wins, result

Run directly to fetch (cached) + parse:
  python3 nfl/sources/win_totals/pipeline.py [start_year] [end_year]
"""
import csv
import os
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from nfl.common.http import get_cached_or_fetch
from nfl.common.team_codes import TEAM_NAME_TO_ABBR

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "win_totals.csv")

DEFAULT_START, DEFAULT_END = 2015, 2025


def fetch_year(year: int) -> str:
    url = f"https://www.covers.com/sportsoddshistory/nfl-win/?y={year}&sa=nfl&t=win"
    return get_cached_or_fetch(RAW_DIR, "covers_win", year, url)


def parse_year(year: int, rows_out: list):
    path = fetch_year(year)
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 7:
            continue
        team_name = tds[0].get_text(strip=True)
        abbr = TEAM_NAME_TO_ABBR.get(team_name)
        if not abbr:
            continue
        try:
            win_total = float(tds[1].get_text(strip=True))
            actual_wins = int(tds[5].get_text(strip=True))
        except ValueError:
            continue
        rows_out.append(
            {
                "year": year,
                "team": abbr,
                "win_total_line": win_total,
                "over_odds": tds[2].get_text(strip=True),
                "under_odds": tds[3].get_text(strip=True),
                "actual_wins": actual_wins,
                "result": tds[6].get_text(strip=True),
            }
        )


def build(start_year=DEFAULT_START, end_year=DEFAULT_END):
    rows = []
    for year in range(start_year, end_year + 1):
        parse_year(year, rows)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fieldnames = ["year", "team", "win_total_line", "over_odds", "under_odds", "actual_wins", "result"]
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
