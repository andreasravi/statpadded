"""
Parse cached HTML into clean CSVs:
  data/adp.csv         -> year, rank, name, team, pos, pos_rank, adp
  data/win_totals.csv  -> year, team, win_total_line, over_odds, under_odds, actual_wins, result

Team names are normalized to the modern-franchise 3-letter abbreviation used
by FantasyData (handles relocations: OAK/LV, SD/LAC, STL/LAR, WAS naming).
"""
import csv
import os
import re

from bs4 import BeautifulSoup

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw")
OUT_DIR = os.path.join(PROJECT_DIR, "data")

YEARS = range(2015, 2026)

# Covers.com historical team name -> canonical FantasyData abbreviation
TEAM_NAME_TO_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Oakland Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "San Diego Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "St Louis Rams": "LAR",
    "St. Louis Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Redskins": "WAS",
    "Washington Football Team": "WAS",
    "Washington Commanders": "WAS",
}


def parse_adp(year: int, rows_out: list):
    path = os.path.join(RAW_DIR, f"fd_adp_{year}.html")
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    table = soup.find("tbody")
    for tr in table.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) < 8:
            continue
        rank = tds[0].get_text(strip=True)
        name = tds[1].get_text(strip=True)
        team = tds[2].get_text(strip=True)
        bye = tds[3].get_text(strip=True)
        age = tds[4].get_text(strip=True)
        pos = tds[5].get_text(strip=True)
        pos_rank = tds[6].get_text(strip=True)
        adp = tds[7].get_text(strip=True)
        if not rank.isdigit():
            continue
        rows_out.append(
            {
                "year": year,
                "rank": int(rank),
                "name": name,
                "team": team,
                "pos": pos,
                "pos_rank": pos_rank,
                "adp": float(adp) if adp else None,
            }
        )


def parse_win_totals(year: int, rows_out: list):
    path = os.path.join(RAW_DIR, f"covers_win_{year}.html")
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    # Rows are plain <tr><td>Team</td><td>Line</td><td>OverOdds</td><td>UnderOdds</td>
    #   <td>Week settled</td><td>Actual Wins</td><td>Result</td></tr>
    for tr in soup.find_all("tr"):
        tds = tr.find_all("td")
        if len(tds) != 7:
            continue
        team_name = tds[0].get_text(strip=True)
        abbr = TEAM_NAME_TO_ABBR.get(team_name)
        if not abbr:
            continue
        win_total = tds[1].get_text(strip=True)
        over_odds = tds[2].get_text(strip=True)
        under_odds = tds[3].get_text(strip=True)
        actual_wins = tds[5].get_text(strip=True)
        result = tds[6].get_text(strip=True)
        try:
            win_total_f = float(win_total)
            actual_wins_i = int(actual_wins)
        except ValueError:
            continue
        rows_out.append(
            {
                "year": year,
                "team": abbr,
                "win_total_line": win_total_f,
                "over_odds": over_odds,
                "under_odds": under_odds,
                "actual_wins": actual_wins_i,
                "result": result,
            }
        )


def main():
    adp_rows = []
    win_rows = []
    for year in YEARS:
        parse_adp(year, adp_rows)
        parse_win_totals(year, win_rows)

    adp_path = os.path.join(OUT_DIR, "adp.csv")
    with open(adp_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "rank", "name", "team", "pos", "pos_rank", "adp"])
        w.writeheader()
        w.writerows(adp_rows)

    win_path = os.path.join(OUT_DIR, "win_totals.csv")
    with open(win_path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "year",
                "team",
                "win_total_line",
                "over_odds",
                "under_odds",
                "actual_wins",
                "result",
            ],
        )
        w.writeheader()
        w.writerows(win_rows)

    print(f"Wrote {len(adp_rows)} ADP rows -> {adp_path}")
    print(f"Wrote {len(win_rows)} win-total rows -> {win_path}")

    # sanity check: expect ~32 teams x 11 years = 352 for win totals
    expected = len(list(YEARS)) * 32
    print(f"(expected ~{expected} win-total rows)")


if __name__ == "__main__":
    main()
