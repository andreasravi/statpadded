"""
Join preseason WR prop lines (nfl/sources/wr_prop_totals) to actual
regular-season receiving production (nfl/sources/receiving_stats) and grade
each line over/under.

Output: projects/wr-prop-accuracy/data/wr_prop_grades.csv
  year, player, matched_name, team, games,
  yards_line, yards_actual, yards_diff, yards_result,
  rec_line, rec_actual, rec_diff, rec_result,
  td_line, td_actual, td_diff, td_result

Blank line/diff/result cells where that year's article didn't publish the
line (2022 is receiving-yards only). `games` < 14 flags a season that
wasn't a full sample -- most big misses in this data are availability, not
per-game form, so filter on it before drawing talent conclusions.

Run: python3 projects/wr-prop-accuracy/scripts/grade.py
"""
import csv
import os
import re
import sys

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))

PROPS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "wr_prop_totals", "data", "wr_prop_totals.csv")
STATS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "receiving_stats", "data", "receiving_stats.csv")
OUT_PATH = os.path.join(PROJECT, "data", "wr_prop_grades.csv")

FIELDNAMES = [
    "year", "player", "matched_name", "team", "team_start", "traded", "games",
    "yards_line", "yards_actual", "yards_diff", "yards_result",
    "rec_line", "rec_actual", "rec_diff", "rec_result",
    "td_line", "td_actual", "td_diff", "td_result",
]


def norm(s):
    s = (s or "").lower().strip()
    s = s.replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_stats():
    by_year = {}
    with open(STATS_CSV) as f:
        for r in csv.DictReader(f):
            by_year.setdefault(int(r["year"]), []).append(r)
    return by_year


def match(name, pool):
    """pool = list of receiving_stats rows for one season."""
    key = norm(name)
    exact = [r for r in pool if norm(r["player"]) == key]
    if exact:  # most targets wins ties (traded player etc.)
        return max(exact, key=lambda r: int(r["targets"] or 0))
    first, last = key.split()[0], key.split()[-1]
    pat = re.compile(rf"{re.escape(first[0])}\w* {re.escape(last)}$")
    cand = [r for r in pool if pat.fullmatch(norm(r["player"]))]
    if cand:
        return max(cand, key=lambda r: int(r["targets"] or 0))
    return None


def grade(line, actual):
    if line == "" or actual is None:
        return "", "", ""
    line_f = float(line)
    diff = round(actual - line_f, 1)
    return line, diff, ("over" if actual > line_f else "under")


def main():
    stats = load_stats()
    out, misses = [], []
    with open(PROPS_CSV) as f:
        props = list(csv.DictReader(f))

    pending = sorted({int(p["year"]) for p in props if int(p["year"]) not in stats})
    for p in props:
        year = int(p["year"])
        if year not in stats:  # season not played yet -> nothing to grade against
            continue
        m = match(p["player"], stats.get(year, []))
        if m is None:
            misses.append((year, p["player"]))
            continue
        ay = int(m["receiving_yards"] or 0)
        ar = int(m["receptions"] or 0)
        at = int(m["receiving_tds"] or 0)
        row = dict.fromkeys(FIELDNAMES, "")
        row.update(
            year=year, player=p["player"], matched_name=m["player"],
            team=m["team"], team_start=m.get("team_start", m["team"]),
            traded=m.get("traded", ""), games=m["games"],
            yards_actual=ay, rec_actual=ar, td_actual=at,
        )
        row["yards_line"], row["yards_diff"], row["yards_result"] = grade(p["yards_line"], ay)
        row["rec_line"], row["rec_diff"], row["rec_result"] = grade(p["rec_line"], ar)
        row["td_line"], row["td_diff"], row["td_result"] = grade(p["td_line"], at)
        out.append(row)

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(out)

    graded = [r for r in out if r["yards_result"]]
    over = sum(1 for r in graded if r["yards_result"] == "over")
    print(f"graded {len(out)} receiver-seasons ({len(misses)} unmatched)")
    print(f"receiving-yards O/U: {over}/{len(graded)} over ({100*over/len(graded):.0f}%)")
    if pending:
        print(f"pending (season not played): {', '.join(map(str, pending))} "
              f"-- prop lines are in nfl/sources/wr_prop_totals")
    if misses:
        print("UNMATCHED:", misses)
    print(f"wrote {os.path.relpath(OUT_PATH, REPO_ROOT)}")


if __name__ == "__main__":
    main()
