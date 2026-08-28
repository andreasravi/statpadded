"""
NFL team turnover differential, per season.
Source: The Football Database (footballdb.com)
  https://www.footballdb.com/statistics/turnovers.html?lg=NFL&yr={year}&type=reg

footballdb.com sits behind the same Cloudflare JS challenge as
Pro-Football-Reference (see nfl/sources/game_results/README.md) -- plain
HTTP requests get a 403, and even same-origin `fetch()` calls issued from
inside an already-loaded page get re-challenged (rapid successive requests
look bot-like to Cloudflare even with a valid session). So there's no
auto-fetch step here: each year was pulled by navigating a real browser to
the URL above and reading `table.statistics` out of the live DOM, then
cached as data/raw/turnovers_{year}.json (already-parsed rows, not raw
HTML -- the table markup is mostly layout divs with no extra information
in them once the sortable-header links are stripped).

Output: data/turnovers.csv
  year, team, games, take_int, take_fum, take_tot, give_int, give_fum,
  give_tot, turnover_diff, turnover_diff_per_game, fumble_recovery_rate

  turnover_diff = takeaways total - giveaways total (matches the site's own
    "Diff" column, kept as an int -- there is one data-quality wrinkle in
    2022 where two teams (CIN, BUF) played only 16 games due to
    postponed/cancelled games, so turnover_diff_per_game exists to make
    cross-team comparisons fair within a season).

  fumble_recovery_rate = take_fum / (take_fum + give_fum) -- the "luck"
    lens on turnover margin: fumble recoveries are close to a 50/50 coin
    flip regardless of team skill (the ball is live, recovery is mostly
    about which team's bodies happen to be closest when it bounces), while
    interception rate has a real, sticky skill/scheme component. A team
    recovering, say, 65% of all fumbles in its games one season is a
    strong regression-to-the-mean candidate the next -- much more so than
    a team with a similarly inflated interception rate. Blank if a team
    had zero total fumbles that season (never happens in this data, but
    guarded anyway).

Rebuild (parsing only, no network):
  python3 nfl/sources/turnovers/pipeline.py
"""
import csv
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from nfl.common.team_codes import TEAM_NAME_TO_ABBR

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "turnovers.csv")

DEFAULT_START, DEFAULT_END = 2014, 2025


def parse_year(year: int) -> list:
    path = os.path.join(RAW_DIR, f"turnovers_{year}.json")
    if not os.path.exists(path):
        print(f"  (missing {path}, skipping {year})")
        return []
    with open(path, encoding="utf-8") as f:
        rows = json.load(f)

    out = []
    for r in rows:
        team = TEAM_NAME_TO_ABBR.get(r["team"])
        if team is None:
            raise ValueError(f"{year}: unmapped team name {r['team']!r}")
        take_fum, give_fum = r["take_fum"], r["give_fum"]
        fum_total = take_fum + give_fum
        out.append({
            "year": year,
            "team": team,
            "games": r["gms"],
            "take_int": r["take_int"],
            "take_fum": take_fum,
            "take_tot": r["take_tot"],
            "give_int": r["give_int"],
            "give_fum": give_fum,
            "give_tot": r["give_tot"],
            "turnover_diff": r["take_tot"] - r["give_tot"],
            "turnover_diff_per_game": round((r["take_tot"] - r["give_tot"]) / r["gms"], 4),
            "fumble_recovery_rate": round(take_fum / fum_total, 4) if fum_total else "",
        })
    return out


def build(start_year=DEFAULT_START, end_year=DEFAULT_END):
    all_rows = []
    for year in range(start_year, end_year + 1):
        year_rows = parse_year(year)
        all_rows.extend(year_rows)
        print(f"{year}: {len(year_rows)} teams")

    # sanity check: every season should have exactly 32 teams once populated
    by_year = {}
    for r in all_rows:
        by_year.setdefault(r["year"], set()).add(r["team"])
    for year, teams in sorted(by_year.items()):
        if len(teams) != 32:
            print(f"  WARNING: {year} has {len(teams)} teams, expected 32")

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    fieldnames = ["year", "team", "games", "take_int", "take_fum", "take_tot",
                  "give_int", "give_fum", "give_tot", "turnover_diff",
                  "turnover_diff_per_game", "fumble_recovery_rate"]
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
