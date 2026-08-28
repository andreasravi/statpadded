"""
A simple "how good is this team's offense going to be in 2026" proxy, used
to set the baseline opportunity level for every kicker/punter projection.

Method: recency-weighted average of the team's actual points-for over the
last 3 completed seasons (2023-2025, weights 0.5/0.3/0.2 -- most recent
season counts most), then scaled up or down by how this year's market win
total compares to the team's recent actual win total. E.g. a team that
averaged 7 wins the last 3 years but is priced for 10 wins in 2026 gets its
recent scoring average scaled up ~1.3x; a team priced for fewer wins than
its recent average gets scaled down. The scale factor is clipped to
[0.7, 1.4] so one extreme Vegas number can't blow up the estimate.

A second column, team_point_diff_proxy_2026, does the analogous thing for
point differential (used by the punter model, where opportunity tracks a
team's point differential rather than raw points-for -- see README). Since
point differential can be negative, it's not safe to scale it multiplicatively
the way points-for is (multiplying an already-negative number by >1 pushes
it the wrong way) -- instead it's shifted additively: the league-wide
historical relationship between average point differential and wins (fit
once, by linear regression) says how many points/game one extra expected win
is worth, and that's added to the recency-weighted point differential.

Inputs:
  nfl/sources/game_results/data/team_point_diff.csv   points_for/point_diff by team-year
  nfl/sources/win_totals/data/win_totals.csv           actual_wins by team-year
  nfl/sources/kalshi_win_totals/data/kalshi_win_totals.csv   2026 market expected_wins

Output:
  data/team_offense_proxy.csv
"""
import csv
import os
import sys

from scipy import stats

HERE = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_CSV = os.path.join(HERE, "data", "team_offense_proxy.csv")

POINT_DIFF_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "game_results", "data", "team_point_diff.csv")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")
KALSHI_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "kalshi_win_totals", "data", "kalshi_win_totals.csv")

RECENCY_YEARS = [2025, 2024, 2023]
RECENCY_WEIGHTS = {2025: 0.5, 2024: 0.3, 2023: 0.2}
SCALE_MIN, SCALE_MAX = 0.7, 1.4


def load_points_for():
    pf = {}  # (year, team) -> points_for
    pd_pg = {}  # (year, team) -> avg_point_diff (per game)
    with open(POINT_DIFF_CSV) as f:
        for r in csv.DictReader(f):
            key = (int(r["year"]), r["team"])
            pf[key] = float(r["points_for"])
            pd_pg[key] = float(r["avg_point_diff"])
    return pf, pd_pg


def wins_per_point_of_diff():
    """League-wide historical slope: how many extra wins one extra point/game
    of average point differential is worth. Used to shift (additively, not
    scale) a team's recency point-diff proxy toward its 2026 market win total."""
    rows = []
    with open(POINT_DIFF_CSV) as f:
        rows = list(csv.DictReader(f))
    wins = load_actual_wins()
    xs, ys = [], []
    for r in rows:
        key = (int(r["year"]), r["team"])
        if key in wins:
            xs.append(float(r["avg_point_diff"]))
            ys.append(wins[key])
    slope, intercept, r, p, se = stats.linregress(xs, ys)
    return slope  # wins per point/game of differential


def load_actual_wins():
    wins = {}
    with open(WIN_TOTALS_CSV) as f:
        for r in csv.DictReader(f):
            wins[(int(r["year"]), r["team"])] = float(r["actual_wins"])
    return wins


def load_kalshi_expected_wins():
    exp = {}
    with open(KALSHI_CSV) as f:
        for r in csv.DictReader(f):
            exp[r["team"]] = float(r["expected_wins"])
    return exp


def build():
    pf, pd_pg = load_points_for()
    wins = load_actual_wins()
    kalshi = load_kalshi_expected_wins()
    win_slope = wins_per_point_of_diff()  # wins per point/game of differential

    teams = sorted(kalshi.keys())
    rows = []
    for team in teams:
        pf_vals = [(y, pf.get((y, team))) for y in RECENCY_YEARS]
        pd_vals = [(y, pd_pg.get((y, team))) for y in RECENCY_YEARS]
        wins_vals = [(y, wins.get((y, team))) for y in RECENCY_YEARS]
        if any(v is None for _, v in pf_vals):
            continue

        recency_pf = sum(RECENCY_WEIGHTS[y] * v for y, v in pf_vals)
        recency_pd = sum(RECENCY_WEIGHTS[y] * v for y, v in pd_vals)
        recency_wins = sum(RECENCY_WEIGHTS[y] * v for y, v in wins_vals)
        exp_wins_2026 = kalshi[team]
        win_delta = exp_wins_2026 - recency_wins

        scale = exp_wins_2026 / recency_wins if recency_wins else 1.0
        scale = max(SCALE_MIN, min(SCALE_MAX, scale))
        proxy_2026 = round(recency_pf * scale, 1)

        pd_shift = win_delta / win_slope if win_slope else 0.0
        pd_proxy_2026 = round(recency_pd + pd_shift, 2)

        rows.append({
            "team": team,
            "recency_avg_points_for": round(recency_pf, 1),
            "recency_avg_point_diff_pg": round(recency_pd, 2),
            "recency_avg_wins": round(recency_wins, 2),
            "kalshi_expected_wins_2026": exp_wins_2026,
            "scale_factor": round(scale, 3),
            "team_offense_proxy_2026": proxy_2026,
            "team_point_diff_proxy_2026": pd_proxy_2026,
        })

    rows.sort(key=lambda r: -r["team_offense_proxy_2026"])
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["team", "recency_avg_points_for", "recency_avg_point_diff_pg", "recency_avg_wins",
                  "kalshi_expected_wins_2026", "scale_factor", "team_offense_proxy_2026",
                  "team_point_diff_proxy_2026"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} teams -> {OUT_CSV}")
    return rows


if __name__ == "__main__":
    build()
