"""
Actual end-of-season fantasy finish per player — how a player actually
ranked once the season played out, to compare against preseason
expectations (e.g. `nfl/sources/underdog_adp`'s August ADP).

There's no dedicated "final standings" page. Instead, each season's finish
gets published as a column on *next* year's Underdog rankings article (a
"how'd last year's picks turn out" reference column), so this source reads
that column back out of next year's page rather than needing its own site.
Same trick used inline by `nfl/sources/underdog_adp` for `finish_prev_year`
— this source just makes it a first-class, standalone dataset instead of a
side column, and adds the one further year `underdog_adp` doesn't reach
back to.

Source: underdognetwork.com (same `__NEXT_DATA__`-embedded-table trick as
`underdog_adp` — see that source's README).
  2023 season's finish <- 2024's August-update article's "2023 Finish" col
  2024 season's finish <- 2025's August-update article's "Finish2024" col
  2025 season's finish <- 2026's post-draft article's "Season 2025"/
                           "Per Game 2025" cols (the first year Underdog
                           split total-points finish from per-game finish)

Output: data/fantasy_finish.csv
  year, player, team, pos, season_finish, per_game_finish

Run directly to fetch (cached) + parse:
  python3 nfl/sources/fantasy_finish/pipeline.py
"""
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from nfl.common.http import get_cached_or_fetch
from nfl.common.team_codes import normalize_underdog_team

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "fantasy_finish.csv")

# season -> (source article URL, season-finish column, per-game-finish column or None)
SEASON_SOURCES = {
    2023: (
        "https://underdognetwork.com/football/fantasy-rankings/2024-fantasy-football-rankings-august-update",
        "2023 Finish", None,
    ),
    2024: (
        "https://underdognetwork.com/football/fantasy-rankings/2025-fantasy-football-rankings-with-preseason-and-training-camp-news",
        "Finish2024", None,
    ),
    2025: (
        "https://underdognetwork.com/football/fantasy-rankings/2026-fantasy-football-rankings",
        "Season 2025", "Per Game 2025",
    ),
}

FIELDNAMES = ["year", "player", "team", "pos", "season_finish", "per_game_finish"]

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


def fetch_season(year: int) -> str:
    url = SEASON_SOURCES[year][0]
    return get_cached_or_fetch(RAW_DIR, "fantasy_finish", year, url)


def _main_table(tables: list) -> dict:
    candidates = [t for t in tables if "capped" not in t["title"].lower()]
    candidates.sort(key=lambda t: len(t["tableData"]), reverse=True)
    return candidates[0]


def _num(v):
    if v is None or v == "":
        return None
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def parse_season(year: int, rows_out: list):
    _, season_col, per_game_col = SEASON_SOURCES[year]
    path = fetch_season(year)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    m = NEXT_DATA_RE.search(html)
    if not m:
        raise RuntimeError(f"{year}: __NEXT_DATA__ not found in {path}")
    data = json.loads(m.group(1))
    post = data["props"]["pageProps"]["post"]
    blocks = post["articleBody"]["links"]["entries"]["block"]
    tables = [b for b in blocks if b.get("__typename") == "Table"]
    table = _main_table(tables)

    for r in table["tableData"]:
        finish = _num(r.get(season_col))
        if finish is None:
            continue  # didn't play / no ranked finish that season
        rows_out.append(
            {
                "year": year,
                "player": (r.get("Player") or "").strip(),
                "team": normalize_underdog_team(r.get("Team")),
                "pos": (r.get("Pos") or "").strip(),
                "season_finish": finish,
                "per_game_finish": _num(r.get(per_game_col)) if per_game_col else None,
            }
        )


def build(years=(2023, 2024, 2025)):
    rows = []
    for year in years:
        parse_season(year, rows)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    build()
