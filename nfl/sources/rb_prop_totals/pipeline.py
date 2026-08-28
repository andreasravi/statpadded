"""
Preseason season-long running-back prop over/unders — rushing yards,
rushing TDs, and (where a book only hung a combined number) rushing +
receiving yards — from every source we've been able to re-parse.

Long format: one row per (year, player, stat, source).

Sources (all committed as raw HTML under data/raw/, no live fetch):

  fantasypoints — Fantasy Points' annual "NFL Rushing Yards Props" /
    "Rushing Touchdowns Props" grids, Wayback June–Aug snapshot. Gives a
    *range across books* (`line_low` = lowest total on the board, best for
    an over bettor; `line_high` = highest, best for an under bettor) plus
    Fantasy Points' own projection. Yards 2023–25; TDs 2024–25 only.

  sportsbetting.ag — SportsBetting.ag's ~60-prop RB board, as reproduced
    by gambling911.com in Aug 2022. Single book, single number, no price.
    The only comprehensive 2022 season-long RB list found. Note: its
    "Bryce Hall" is the Jets' rookie RB **Breece Hall** (book/site typo,
    corrected here).

Run:    python3 nfl/sources/rb_prop_totals/pipeline.py
Output: data/rb_prop_totals.csv --
        year, player, team, stat, line, line_low, line_high,
        odds_low, odds_high, book, proj, source, snapshot
        stat ∈ {rush_yds, rush_td, rush_rec_yds}
"""
import csv
import html as _html
import os
import re

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "rb_prop_totals.csv")

FIELDNAMES = [
    "year", "player", "team", "stat", "line", "line_low", "line_high",
    "odds_low", "odds_high", "book", "proj", "source", "snapshot",
]

_NUM = re.compile(r"-?\d+(?:\.\d+)?")
_ODDS = re.compile(r"([+-]\d{2,4})")
_TEAM_FIX = {"LA": "LAR"}


def _mid(a, b):
    try:
        return f"{(float(a) + float(b)) / 2:g}"
    except (TypeError, ValueError):
        return ""


# --------------------------------------------------------------------------
# Fantasy Points
# --------------------------------------------------------------------------
FP = {  # (stat, year) -> (raw filename, wayback snapshot url)
    ("rush_yds", 2023): ("ry2023.html", "https://web.archive.org/web/20230614022112id_/https://www.fantasypoints.com/nfl/articles/2023/nfl-rushing-yardage-props"),
    ("rush_yds", 2024): ("ry2024.html", "https://web.archive.org/web/20240628170709id_/https://www.fantasypoints.com/nfl/articles/2024/nfl-rushing-yard-props"),
    ("rush_td", 2024): ("td2024.html", "https://web.archive.org/web/20240627020904id_/https://www.fantasypoints.com/nfl/articles/2024/nfl-rushing-touchdown-props"),
    ("rush_yds", 2025): ("ry2025.html", "https://web.archive.org/web/20250610031125id_/https://www.fantasypoints.com/nfl/articles/2025/nfl-rushing-yards-props"),
    ("rush_td", 2025): ("td2025.html", "https://web.archive.org/web/20250804194343id_/https://www.fantasypoints.com/nfl/articles/2025/nfl-rushing-touchdowns-props"),
}


def _cells(row_html):
    return [
        _html.unescape(re.sub(r"<[^>]+>", " ", c)).replace("’", "'").strip()
        for c in re.findall(r"<t[dh][^>]*>(.*?)</t[dh]>", row_html, re.S)
    ]


def _fp_grid(page_html):
    for t in re.findall(r"<table.*?</table>", page_html, re.S):
        rows = [_cells(r) for r in re.findall(r"<tr[^>]*>(.*?)</tr>", t, re.S)]
        rows = [r for r in rows if any(r)]
        if len(rows) >= 5 and len(rows[0]) >= 4:
            return rows
    return None


def _split_name_team(cell):
    m = re.match(r"^(.*?)\s*\(([A-Za-z0-9.]+)\)\s*$", cell)
    if not m:
        return cell.strip(), ""
    code = m.group(2).strip().upper()
    return m.group(1).strip(), _TEAM_FIX.get(code, code)


def _parse_cell(cell):
    """'1375.5 (-110, MGM)' -> ('1375.5', '-110'); '1225.5 (DraftKings)' -> ('1225.5', '')."""
    if not cell:
        return "", ""
    nums = _NUM.findall(cell.split("(")[0])
    odds = _ODDS.search(cell)
    return (nums[0] if nums else ""), (odds.group(1) if odds else "")


def parse_fantasypoints():
    rows = []
    for (stat, year), (fname, snap) in FP.items():
        path = os.path.join(RAW_DIR, fname)
        with open(path, encoding="utf-8", errors="replace") as f:
            grid = _fp_grid(f.read())
        if not grid:
            print(f"  (no FP grid: {stat} {year})")
            continue
        for r in grid[1:]:
            if len(r) < 4 or not re.search(r"[A-Za-z]", r[0]) or _NUM.fullmatch(r[0].strip()):
                continue
            name, team = _split_name_team(r[0])
            proj = _NUM.findall(r[1])
            high_line, high_odds = _parse_cell(r[2])  # highest total (under)
            low_line, low_odds = _parse_cell(r[3])    # lowest total (over)
            if not (low_line or high_line):
                continue
            rows.append({
                "year": year, "player": name, "team": team, "stat": stat,
                "line": _mid(low_line, high_line), "line_low": low_line, "line_high": high_line,
                "odds_low": low_odds, "odds_high": high_odds, "book": "",
                "proj": proj[0] if proj else "", "source": "fantasypoints", "snapshot": snap,
            })
    return rows


# --------------------------------------------------------------------------
# SportsBetting.ag 2022 (via gambling911.com)
# --------------------------------------------------------------------------
SB_SNAP = "https://www.gambling911.com/running-back-prop-bets-for-the-2022-season.html"
SB_STAT = {
    "Rushing Yards": "rush_yds",
    "Rushing TDs": "rush_td",
    "Rushing & Receiving Yards": "rush_rec_yds",
}
SB_NAME_FIX = {"Bryce Hall": "Breece Hall"}  # site typo: Jets rookie RB


def parse_sportsbetting_ag():
    path = os.path.join(RAW_DIR, "sportsbetting_ag_2022.html")
    with open(path, encoding="utf-8", errors="replace") as f:
        h = f.read()
    h = re.sub(r"<(script|style)[^>]*>.*?</\1>", " ", h, flags=re.S)
    text = _html.unescape(re.sub(r"<[^>]+>", "\n", h)).replace("’", "'")
    lines = [re.sub(r"\s+", " ", x).strip() for x in text.splitlines()]
    lines = [x for x in lines if x]

    out = []
    cur = stat = None
    for x in lines:
        m = re.match(r"^([A-Z][A-Za-z.'\- ]+?) - Total (.+)$", x)
        if m:
            cur = SB_NAME_FIX.get(m.group(1).strip(), m.group(1).strip())
            stat = SB_STAT.get(m.group(2).strip())
            continue
        m = re.match(r"^Over/Under\s+([\d.]+)", x)
        if m and cur and stat:
            out.append({
                "year": 2022, "player": cur, "team": "", "stat": stat,
                "line": m.group(1), "line_low": m.group(1), "line_high": m.group(1),
                "odds_low": "", "odds_high": "", "book": "SportsBetting.ag",
                "proj": "", "source": "sportsbetting.ag", "snapshot": SB_SNAP,
            })
            stat = None
    return out


def main():
    rows = parse_fantasypoints() + parse_sportsbetting_ag()
    rows.sort(key=lambda r: (r["year"], r["stat"], -float(r["line"] or 0)))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    for year in sorted({r["year"] for r in rows}):
        yr = [r for r in rows if r["year"] == year]
        by = {}
        for r in yr:
            by[r["stat"]] = by.get(r["stat"], 0) + 1
        src = ",".join(sorted({r["source"] for r in yr}))
        print(f"{year}: " + "  ".join(f"{k}={v}" for k, v in sorted(by.items())) + f"   [{src}]")
    print(f"\nwrote {len(rows)} rows -> {os.path.relpath(OUT_PATH, REPO_ROOT)}")


if __name__ == "__main__":
    main()
