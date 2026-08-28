"""
Fantasy Alarm's annual "wide receiver values using NFL player prop totals"
article, one per season -- a study grid of each fantasy-relevant WR's
preseason Vegas prop lines (receiving yards / receptions / TDs) plus a
projected-PPR estimate and that player's current ADP.

Plain server-rendered HTML (grid is one <table>), no Cloudflare wall, so
this auto-fetches like win_totals/adp. Column set drifts year to year
(2022 is receiving-yards only; 2022's page also embeds a stale ~2021
table this picks around) -- see README.md for the full schema-drift table.

Run:    python3 nfl/sources/wr_prop_totals/pipeline.py [year ...]
Output: data/wr_prop_totals.csv
        year, player, yards_line, rec_line, td_line, proj_ppr, adp,
        props_rank, adp_rank, sportsbook
"""
import csv
import html as _html
import os
import re
import sys

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "wr_prop_totals.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.http import get_cached_or_fetch

FIELDNAMES = [
    "year", "player", "yards_line", "rec_line", "td_line",
    "proj_ppr", "adp", "props_rank", "adp_rank", "sportsbook",
]

YEAR_URLS = {
    2022: "https://www.fantasyalarm.com/articles/nfl/wide-receivers/identifying-fantasy-football-wide-receiver-values-using-nfl-player-prop-totals-2022/131547",
    2023: "https://www.fantasyalarm.com/articles/nfl/wide-receivers/using-2023-nfl-player-props-to-find-fantasy-football-draft-values-at-wide-receiver/150731",
    2024: "https://www.fantasyalarm.com/articles/nfl/fantasy-football-advice/how-to-use-vegas-nfl-odds-player-props-to-find-fantasy-football-values/162149",
    2025: "https://www.fantasyalarm.com/articles/nfl/wide-receivers/identifying-fantasy-football-wide-receiver-values-using-nfl-player-prop-totals/178604",
    2026: "https://www.fantasyalarm.com/articles/nfl/wide-receivers/identifying-fantasy-football-wide-receiver-values-using-nfl-player-prop-totals-2026/193991",
}

SPORTSBOOK = {2022: "FanDuel", 2023: "DraftKings"}  # named in-header; later years unstated

NAME_FIXES = {"Amon-Ra St. Bown": "Amon-Ra St. Brown"}


def _cells(row_html):
    return [
        _html.unescape(re.sub(r"<[^>]+>", "", c)).replace("’", "'").strip()
        for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)
    ]


def _tables(page_html):
    for t in re.findall(r"<table.*?</table>", page_html, re.S):
        rows = [_cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)]
        rows = [r for r in rows if r]
        if len(rows) >= 3:
            yield rows


def _pick_grid(page_html):
    """The real grid is the table with the most half-point yards values."""
    best, best_score = None, -1
    for rows in _tables(page_html):
        score = sum(
            1 for r in rows[1:]
            if len(r) >= 2 and re.fullmatch(r"\d{3,4}\.5", r[1].strip())
        )
        # fall back to any 3-4 digit number for 2022's odd whole-number quoting
        if score == 0:
            score = sum(
                1 for r in rows[1:]
                if len(r) >= 2 and re.fullmatch(r"\d{3,4}(\.\d+)?", r[1].strip())
            ) - 100  # keep it strictly below a real .5 table
        if score > best_score:
            best, best_score = rows, score
    return best


def _num(s):
    s = (s or "").strip().replace(",", "")
    if not s or not re.fullmatch(r"-?\d+(\.\d+)?", s):
        return ""
    return s


def _col_index(header, *needles):
    for i, h in enumerate(header):
        hl = h.lower()
        if all(n in hl for n in needles):
            return i
    return None


def parse_year(year):
    path = os.path.join(RAW_DIR, f"wr_prop_totals_{year}.html")
    if not os.path.exists(path):
        path = get_cached_or_fetch(RAW_DIR, "wr_prop_totals", year, YEAR_URLS[year])
    with open(path, encoding="utf-8") as f:
        rows = _pick_grid(f.read())
    if not rows:
        print(f"  (no grid found for {year})")
        return []

    header = rows[0]
    ix = {
        "yards": _col_index(header, "yard"),
        "rec": _col_index(header, "rec"),
        "td": _col_index(header, "td"),
        "ppr": _col_index(header, "ppr"),
        "adp": next((i for i, h in enumerate(header) if h.strip().lower() == "adp"), None),
        "props_rank": _col_index(header, "points", "rank") or _col_index(header, "props", "rank"),
        "adp_rank": _col_index(header, "adp", "rank"),
    }

    out = []
    for r in rows[1:]:
        if len(r) < 2 or not r[0]:
            continue
        name = NAME_FIXES.get(r[0], r[0])
        rec = {k: "" for k in FIELDNAMES}
        rec.update(year=year, player=name, sportsbook=SPORTSBOOK.get(year, ""))
        rec["yards_line"] = _num(r[ix["yards"]]) if ix["yards"] is not None and ix["yards"] < len(r) else ""
        for key, col in (("rec_line", "rec"), ("td_line", "td"), ("proj_ppr", "ppr"),
                         ("adp", "adp"), ("props_rank", "props_rank"), ("adp_rank", "adp_rank")):
            i = ix[col]
            rec[key] = _num(r[i]) if i is not None and i < len(r) else ""
        if rec["yards_line"] == "":
            continue
        out.append(rec)
    return out


def main(years=None):
    years = years or sorted(YEAR_URLS)
    all_rows = []
    for y in years:
        rows = parse_year(y)
        print(f"{y}: {len(rows)} receivers")
        all_rows.extend(rows)
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(all_rows)
    print(f"\nwrote {len(all_rows)} rows -> {os.path.relpath(OUT_PATH, REPO_ROOT)}")


if __name__ == "__main__":
    args = [int(a) for a in sys.argv[1:]]
    main(args or None)
