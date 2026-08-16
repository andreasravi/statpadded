"""
NFL fantasy-football ADP (average draft position), 2QB/superflex format,
top 100 players per season (free-tier cap).
Source: FantasyData
  https://fantasydata.com/nfl/2qb-adp?season={year}&team=

Output: data/adp.csv
  year, rank, name, team, pos, pos_rank, adp

Run directly to fetch (cached) + parse:
  python3 nfl/sources/adp/pipeline.py [start_year] [end_year]
"""
import csv
import os
import sys

from bs4 import BeautifulSoup

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from nfl.common.http import get_cached_or_fetch

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "adp.csv")

DEFAULT_START, DEFAULT_END = 2015, 2025


def fetch_year(year: int) -> str:
    url = f"https://fantasydata.com/nfl/2qb-adp?season={year}&team="
    return get_cached_or_fetch(RAW_DIR, "fd_adp", year, url)


def parse_year(year: int, rows_out: list):
    path = fetch_year(year)
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    table = soup.find("tbody")
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue
        rank = tds[0].get_text(strip=True)
        if not rank.isdigit():
            continue
        adp = tds[7].get_text(strip=True)
        rows_out.append(
            {
                "year": year,
                "rank": int(rank),
                "name": tds[1].get_text(strip=True),
                "team": tds[2].get_text(strip=True),
                "pos": tds[5].get_text(strip=True),
                "pos_rank": tds[6].get_text(strip=True),
                "adp": float(adp) if adp else None,
            }
        )


def build(start_year=DEFAULT_START, end_year=DEFAULT_END):
    rows = []
    for year in range(start_year, end_year + 1):
        parse_year(year, rows)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fieldnames = ["year", "rank", "name", "team", "pos", "pos_rank", "adp"]
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
