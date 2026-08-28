"""
First Down Studio's 2026 season "Vegas Fantasy Football Rankings" boards,
QB + RB + WR -- the authoritative post-trade 2026 team assignment for every
fantasy-relevant skill player, plus FDS's Vegas-prop-driven yardage/TD
projection.

Why this exists: FantasyAlarm's prop grid and nflverse's prior-season team
are both stale for players who changed teams in the (wild) 2026 offseason
-- Jaylen Waddle to DEN, A.J. Brown to NE, Kyler Murray to MIN, Tua to
ATL, etc. The 2026 grading / picks / watch layer joins here for team and
for the projected Week-1 starter per team.

Boards are client-rendered; the raw table captures are committed under
data/raw/ and this pipeline only re-parses (no live fetch), same as
rb_prop_totals.

Run:    python3 nfl/sources/firstdown_studio_2026/pipeline.py
Output: data/firstdown_2026.csv --
        pos, rank, player, team, rookie,
        proj_rush_yds, proj_rush_tds, proj_rec, proj_rec_yds
        (projection columns are populated for the RB board only)
"""
import csv
import json
import os

HERE = os.path.dirname(__file__)
RAW = os.path.join(HERE, "data", "raw")
OUT = os.path.join(HERE, "data", "firstdown_2026.csv")
FIELDNAMES = ["pos", "rank", "player", "team", "rookie",
              "proj_rush_yds", "proj_rush_tds", "proj_rec", "proj_rec_yds"]

_TEAM_FIX = {"LA": "LAR"}


def _load(name):
    return json.load(open(os.path.join(RAW, name), encoding="utf-8"))["rows"]


def main():
    rows = []
    for board, pos in (("qb_board.json", "QB"), ("rb_board.json", "RB"), ("wr_board.json", "WR")):
        for r in _load(board):
            rows.append({
                "pos": pos, "rank": r["rank"], "player": r["player"],
                "team": _TEAM_FIX.get(r["team"], r["team"]),
                "rookie": "Y" if r.get("rookie") else "",
                "proj_rush_yds": r.get("rush_yds", ""),
                "proj_rush_tds": r.get("rush_tds", ""),
                "proj_rec": r.get("rec", ""),
                "proj_rec_yds": r.get("rec_yds", ""),
            })
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)

    from collections import Counter
    by = Counter(r["pos"] for r in rows)
    # projected Week-1 starter per team = highest-ranked QB on the QB board
    starters = {}
    for r in sorted((x for x in rows if x["pos"] == "QB"), key=lambda x: x["rank"]):
        starters.setdefault(r["team"], r["player"])
    print("  " + "  ".join(f"{k}={v}" for k, v in sorted(by.items())))
    print(f"  {len(starters)} teams with a projected starter")
    print(f"wrote {len(rows)} rows -> {os.path.relpath(OUT, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))}")


if __name__ == "__main__":
    main()
