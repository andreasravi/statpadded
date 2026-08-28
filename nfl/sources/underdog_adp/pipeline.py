"""
Underdog Network preseason fantasy-football ADP rankings (August update),
player-level — includes each player's ADP movement ("Diff") and, for 2025
only, a short news tag ("Notes": injury/suspension/trade/rookie/etc.).

Source: underdognetwork.com "Fantasy Rankings ... August Update" articles.
These are Next.js pages that embed their rankings table as structured JSON
in a `__NEXT_DATA__` script tag server-side, so no browser rendering is
needed — a plain fetch of the page HTML already contains the full table.

Each year's article has evolved its own table schema (see README), so this
pipeline normalizes all three to one common shape:
  year, rank, player, team, pos, pos_rank, adp, diff, finish_prev_year, notes

`diff`, `pos_rank`, and `notes` are blank where that year's table doesn't
have the column (2023 has no `diff`/`notes`; 2024 has no `pos_rank`/`notes`).

Output: data/underdog_adp.csv

Run directly to fetch (cached) + parse:
  python3 nfl/sources/underdog_adp/pipeline.py
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
OUT_PATH = os.path.join(HERE, "data", "underdog_adp.csv")

YEAR_URLS = {
    2023: "https://underdognetwork.com/football/fantasy-rankings/2023-fantasy-football-rankings-and-adp-august-update",
    2024: "https://underdognetwork.com/football/fantasy-rankings/2024-fantasy-football-rankings-august-update",
    2025: "https://underdognetwork.com/football/fantasy-rankings/2025-fantasy-football-rankings-with-preseason-and-training-camp-news",
}

FIELDNAMES = [
    "year", "rank", "player", "team", "pos", "pos_rank",
    "adp", "diff", "finish_prev_year", "notes",
]

NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', re.S
)


def fetch_year(year: int) -> str:
    return get_cached_or_fetch(RAW_DIR, "underdog_adp", year, YEAR_URLS[year])


def _main_table(tables: list) -> dict:
    """Pick the article's main rankings table. Some years embed a second,
    unrelated table (e.g. 2023's Underdog "Capped" best-ball tournament
    rankings) alongside the real ADP table — skip anything titled 'Capped'
    and take the largest of what's left."""
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


def parse_year(year: int, rows_out: list):
    path = fetch_year(year)
    with open(path, encoding="utf-8") as f:
        html = f.read()

    m = NEXT_DATA_RE.search(html)
    if not m:
        raise RuntimeError(f"{year}: __NEXT_DATA__ not found in {path}")
    data = json.loads(m.group(1))
    post = data["props"]["pageProps"]["post"]
    blocks = post["articleBody"]["links"]["entries"]["block"]
    tables = [b for b in blocks if b.get("__typename") == "Table"]
    if not tables:
        raise RuntimeError(f"{year}: no Table entries found")
    table = _main_table(tables)

    # 2024/2025 key the prior-season finish column by that season's year;
    # 2023's table only carries "2022 Finish".
    finish_keys = (f"{year - 1} Finish", f"Finish{year - 1}")

    for r in table["tableData"]:
        finish = None
        for k in finish_keys:
            if k in r:
                finish = _num(r[k])
                break

        rows_out.append(
            {
                "year": year,
                "rank": int(r["Rank"]) if r.get("Rank") not in (None, "") else None,
                "player": (r.get("Player") or "").strip(),
                "team": normalize_underdog_team(r.get("Team")),
                "pos": (r.get("Pos") or "").strip(),
                "pos_rank": r.get("PosRank") or r.get("Pos Rank") or None,
                "adp": _num(r.get("ADP")),
                "diff": _num(r.get("Diff")),
                "finish_prev_year": finish,
                "notes": (r.get("Notes") or "").strip() or None,
            }
        )


def build(years=(2023, 2024, 2025)):
    rows = []
    for year in years:
        parse_year(year, rows)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} rows -> {OUT_PATH}")
    return OUT_PATH


if __name__ == "__main__":
    build()
