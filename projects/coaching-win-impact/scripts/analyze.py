"""
Do NFL coaching changes predict anything about win totals?

Joins the shared nfl/sources/coaches and nfl/sources/win_totals datasets and
checks three separate questions:

  1. Does a new head coach predict year-over-year win improvement
     (actual_wins this year vs actual_wins last year)?
  2. Does Vegas move the win-total line differently for a new-coach team
     vs an incumbent-coach team?
  3. Do new-coach teams beat or miss their OWN season's win-total line with
     any more consistency than incumbent-coach teams (i.e. is a coaching
     change an exploitable market inefficiency, or already priced in)?

Also looks at coaching tenure (years 1/2/3/4+ under the same coach) since
"new coach" is really just tenure-year-1.
"""
import csv
import os
import sys
from collections import defaultdict

from scipy import stats

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")

sys.path.insert(0, REPO_ROOT)
COACHES_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "coaches", "data", "coaches.csv")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    coaches = load_csv(COACHES_CSV)
    win_totals = load_csv(WIN_TOTALS_CSV)

    coach_by_key = {(int(r["year"]), r["team"]): r for r in coaches}
    wt_by_key = {(int(r["year"]), r["team"]): r for r in win_totals}

    # tenure: consecutive years (within our pulled window) under the same
    # coach, counting the first pulled year as tenure 1. This underestimates
    # tenure for a coach who was already in place before the earliest
    # pulled coaches year (2014).
    tenure_by_key = {}
    years_sorted = sorted({int(r["year"]) for r in coaches})
    for team in {r["team"] for r in coaches}:
        run = 0
        prev_coach = None
        for y in years_sorted:
            row = coach_by_key.get((y, team))
            if row is None:
                run = 0
                prev_coach = None
                continue
            if row["head_coach"] == prev_coach:
                run += 1
            else:
                run = 1
            tenure_by_key[(y, team)] = run
            prev_coach = row["head_coach"]

    merged = []
    for (year, team), wt in wt_by_key.items():
        coach_row = coach_by_key.get((year, team))
        if coach_row is None or coach_row["new_coach"] == "":
            continue  # no reliable new_coach flag (edge of pulled window)
        prior_wt = wt_by_key.get((year - 1, team))
        rec = {
            "year": year,
            "team": team,
            "head_coach": coach_row["head_coach"],
            "new_coach": int(coach_row["new_coach"]),
            "tenure": tenure_by_key.get((year, team)),
            "win_total_line": float(wt["win_total_line"]),
            "actual_wins": int(wt["actual_wins"]),
            "result": wt["result"],
            "beat_margin": int(wt["actual_wins"]) - float(wt["win_total_line"]),
            "prior_actual_wins": int(prior_wt["actual_wins"]) if prior_wt else None,
            "prior_win_total_line": float(prior_wt["win_total_line"]) if prior_wt else None,
        }
        rec["wins_change"] = rec["actual_wins"] - rec["prior_actual_wins"] if prior_wt else ""
        rec["line_change"] = (
            rec["win_total_line"] - rec["prior_win_total_line"] if prior_wt else ""
        )
        merged.append(rec)

    out_path = os.path.join(DATA_DIR, "merged.csv")
    fieldnames = [
        "year", "team", "head_coach", "new_coach", "tenure",
        "win_total_line", "actual_wins", "result", "beat_margin",
        "prior_actual_wins", "prior_win_total_line", "wins_change", "line_change",
    ]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(merged)
    print(f"Wrote merged dataset ({len(merged)} rows) -> {out_path}\n")

    with_prior = [r for r in merged if r["wins_change"] != ""]

    # ---- 1: new coach vs year-over-year win change ----
    print("=" * 78)
    print("1) NEW COACH vs YEAR-OVER-YEAR WIN CHANGE")
    print("=" * 78)
    new = [r for r in with_prior if r["new_coach"] == 1]
    inc = [r for r in with_prior if r["new_coach"] == 0]
    for label, group in [("New coach (year 1)", new), ("Incumbent coach", inc)]:
        n = len(group)
        avg_change = sum(r["wins_change"] for r in group) / n
        avg_wins = sum(r["actual_wins"] for r in group) / n
        avg_prior = sum(r["prior_actual_wins"] for r in group) / n
        print(f"  {label:22s} n={n:3d}  prior_wins={avg_prior:5.2f} -> wins={avg_wins:5.2f}  "
              f"avg YoY change={avg_change:+5.2f}")

    x = [r["new_coach"] for r in with_prior]
    y = [r["wins_change"] for r in with_prior]
    r_val, p_val = stats.pointbiserialr(x, y)
    print(f"\n  point-biserial r(new_coach, wins_change) = {r_val:+.3f} (p={p_val:.4f})")

    # ---- 2: new coach vs how Vegas moves the line ----
    print("\n" + "=" * 78)
    print("2) NEW COACH vs HOW VEGAS MOVES THE WIN-TOTAL LINE YoY")
    print("=" * 78)
    for label, group in [("New coach (year 1)", new), ("Incumbent coach", inc)]:
        n = len(group)
        avg_line_change = sum(r["line_change"] for r in group) / n
        print(f"  {label:22s} n={n:3d}  avg line change YoY={avg_line_change:+5.2f}")

    # ---- 3: new coach vs beating the CURRENT season's line ----
    print("\n" + "=" * 78)
    print("3) NEW COACH vs BEATING THIS SEASON'S OWN WIN-TOTAL LINE")
    print("=" * 78)
    all_new = [r for r in merged if r["new_coach"] == 1]
    all_inc = [r for r in merged if r["new_coach"] == 0]
    for label, group in [("New coach (year 1)", all_new), ("Incumbent coach", all_inc)]:
        n = len(group)
        avg_margin = sum(r["beat_margin"] for r in group) / n
        overs = sum(1 for r in group if r["result"] == "Over") / n * 100
        unders = sum(1 for r in group if r["result"] == "Under") / n * 100
        print(f"  {label:22s} n={n:3d}  avg beat_margin={avg_margin:+5.2f}  "
              f"over%={overs:5.1f}  under%={unders:5.1f}")

    x = [r["new_coach"] for r in merged]
    y = [r["beat_margin"] for r in merged]
    r_val, p_val = stats.pointbiserialr(x, y)
    print(f"\n  point-biserial r(new_coach, beat_margin) = {r_val:+.3f} (p={p_val:.4f})")

    # ---- bonus: by tenure year ----
    print("\n" + "-" * 78)
    print("By coaching tenure (years with same coach, capped display at 6+)")
    print("(tenure is a lower bound for coaches already in place before 2014)")
    print("-" * 78)
    buckets = defaultdict(list)
    for r in merged:
        t = r["tenure"] if r["tenure"] and r["tenure"] < 6 else "6+"
        buckets[t].append(r)
    order = [1, 2, 3, 4, 5, "6+"]
    for t in order:
        rows = buckets.get(t, [])
        if not rows:
            continue
        n = len(rows)
        avg_wins = sum(r["actual_wins"] for r in rows) / n
        avg_margin = sum(r["beat_margin"] for r in rows) / n
        overs = sum(1 for r in rows if r["result"] == "Over") / n * 100
        print(f"  tenure={str(t):3s}  n={n:3d}  avg_wins={avg_wins:5.2f}  "
              f"avg_beat_margin={avg_margin:+5.2f}  over%={overs:5.1f}")


if __name__ == "__main__":
    main()
