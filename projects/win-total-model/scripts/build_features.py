"""
Merge every shared nfl/sources/ dataset into one team-season feature table
for modeling actual_wins and beat_margin (actual_wins - win_total_line).

All "prior_*" features use YEAR-1 data only -- nothing computed from the
season being predicted leaks into its own row. sos_this_year_line and
new_coach/adp are legitimately knowable before the season starts (preseason
market lines, roster, coaching staff), so they use the CURRENT year.

Output: data/features.csv, one row per team-season, 2016-2025 (2015 excluded
since there's no 2014 game-results/point-diff data to build prior-year
features from).
"""
import csv
import os
import sys
from collections import defaultdict

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
NFL = os.path.join(REPO_ROOT, "nfl", "sources")

sys.path.insert(0, REPO_ROOT)


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def main():
    win_totals = load_csv(os.path.join(NFL, "win_totals", "data", "win_totals.csv"))
    point_diff = load_csv(os.path.join(NFL, "game_results", "data", "team_point_diff.csv"))
    sos = load_csv(os.path.join(NFL, "game_results", "data", "strength_of_schedule.csv"))
    coaches = load_csv(os.path.join(NFL, "coaches", "data", "coaches.csv"))
    adp = load_csv(os.path.join(NFL, "adp", "data", "adp.csv"))

    wt_by_key = {(int(r["year"]), r["team"]): r for r in win_totals}
    pd_by_key = {(int(r["year"]), r["team"]): r for r in point_diff}
    sos_by_key = {(int(r["year"]), r["team"]): r for r in sos}
    coach_by_key = {(int(r["year"]), r["team"]): r for r in coaches}

    # ADP star-power per (year, team): count of top-100 picks + rank-weighted score
    adp_counts = defaultdict(lambda: {"top100_count": 0, "linear_weight": 0})
    for r in adp:
        rank = int(r["rank"])
        if rank > 100:
            continue
        key = (int(r["year"]), r["team"])
        adp_counts[key]["top100_count"] += 1
        adp_counts[key]["linear_weight"] += 101 - rank

    rows = []
    for (year, team), wt in wt_by_key.items():
        prior_wt = wt_by_key.get((year - 1, team))
        prior_pd = pd_by_key.get((year - 1, team))
        this_sos = sos_by_key.get((year, team))
        this_coach = coach_by_key.get((year, team))
        this_adp = adp_counts.get((year, team), {"top100_count": 0, "linear_weight": 0})

        if not (prior_wt and prior_pd and this_sos):
            continue  # need a full prior season of games + a market line for this year

        prior_actual_wins = int(prior_wt["actual_wins"])
        prior_win_total_line = float(prior_wt["win_total_line"])
        prior_beat_margin = prior_actual_wins - prior_win_total_line
        prior_result = prior_wt["result"]  # 'Over' / 'Under' / 'Push'
        prior_pyth_wins = float(prior_pd["pyth_wins"])
        prior_luck = prior_actual_wins - prior_pyth_wins  # + = overperformed point diff (due for regression)

        row = {
            "year": year,
            "team": team,
            "win_total_line": float(wt["win_total_line"]),
            "actual_wins": int(wt["actual_wins"]),
            "beat_margin": int(wt["actual_wins"]) - float(wt["win_total_line"]),
            "new_coach": int(this_coach["new_coach"]) if this_coach and this_coach["new_coach"] != "" else "",
            "sos_this_year_line": float(this_sos["sos_this_year_line"]) if this_sos["sos_this_year_line"] != "" else "",
            "prior_year_under": 1 if prior_result == "Under" else (0 if prior_result == "Over" else 0.5),
            "prior_beat_margin": round(prior_beat_margin, 3),
            "prior_actual_wins": prior_actual_wins,
            "prior_avg_point_diff": float(prior_pd["avg_point_diff"]),
            "prior_pyth_wins": prior_pyth_wins,
            "prior_luck": round(prior_luck, 3),
            "sos_prior_year_wins": float(this_sos["sos_prior_year_wins"]) if this_sos["sos_prior_year_wins"] != "" else "",
            "adp_top100_count": this_adp["top100_count"],
            "adp_linear_weight": this_adp["linear_weight"],
        }
        rows.append(row)

    rows.sort(key=lambda r: (r["year"], r["team"]))

    out_path = os.path.join(DATA_DIR, "features.csv")
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} team-season rows -> {out_path}")
    print(f"Years covered: {rows[0]['year']}-{rows[-1]['year']}")


if __name__ == "__main__":
    main()
