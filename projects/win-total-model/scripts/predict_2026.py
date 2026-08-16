"""
Apply the fitted win-total model to the 2026 season and compare its
predictions against Kalshi's current market-implied win totals.

Inputs needed for a "current season" prediction, none of which exist in
actual_wins-completed form yet:
  - 2026 schedule (who plays whom) -- PFR's future-schedule page, a
    DIFFERENT table shape than the completed-season pages (visitor_team/
    home_team instead of winner/loser), parsed separately below.
  - 2026 opponent win-total expectations -- from nfl/sources/kalshi_win_totals
    (Covers.com/sportsbooks don't have 2026 lines archived yet; Kalshi's
    public prediction-market API does).
  - 2026 new_coach -- myfootballtoolbox.com 404s for 2026 still, and an
    initial web search returned self-contradictory results, so this list is
    user-supplied (confirmed 2026 HC hires) rather than scraped. Low-stakes
    either way: new_coach was NOT statistically significant in the fitted
    model (p=0.627), so this barely moves any prediction.
  - Everything else ("prior_*" features) is just 2025 data, which IS fully
    available.

Run: python3 predict_2026.py
"""
import csv
import os
import sys

import numpy as np
import statsmodels.api as sm
from bs4 import BeautifulSoup

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
NFL = os.path.join(REPO_ROOT, "nfl", "sources")

sys.path.insert(0, REPO_ROOT)
from nfl.common.team_codes import TEAM_NAME_TO_ABBR

FUTURE_SCHEDULE_HTML = os.path.join(NFL, "game_results", "data", "raw_future", "pfr_games_2026.html")

# Confirmed 2026 head-coach hires (user-supplied, cross-checked against an
# initial web search that had contradictions -- see module docstring).
NEW_COACHES_2026 = {"BAL", "BUF", "NYG", "PIT", "ATL", "LV", "TEN", "CLE", "ARI", "MIA"}

FEATURES = [
    "new_coach",
    "sos_this_year_line",
    "prior_year_under",
    "prior_beat_margin",
    "prior_actual_wins",
    "prior_pyth_wins",
]
TARGET = "actual_wins"


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def parse_2026_opponents():
    with open(FUTURE_SCHEDULE_HTML) as f:
        soup = BeautifulSoup(f.read(), "lxml")
    opponents = {}
    for tr in soup.find_all("tr"):
        wk = tr.find(["td", "th"], {"data-stat": "week_num"})
        if wk is None or not wk.get_text(strip=True).isdigit():
            continue

        def cell(stat):
            c = tr.find(["td", "th"], {"data-stat": stat})
            return c.get_text(strip=True) if c else ""

        vis = TEAM_NAME_TO_ABBR.get(cell("visitor_team"))
        home = TEAM_NAME_TO_ABBR.get(cell("home_team"))
        if not vis or not home:
            continue
        opponents.setdefault(vis, []).append(home)
        opponents.setdefault(home, []).append(vis)
    return opponents


def fit_full_model():
    """Refit on ALL historical data (2016-2025) -- the production model."""
    rows = load_csv(os.path.join(DATA_DIR, "features.csv"))
    for r in rows:
        for k in FEATURES + [TARGET]:
            r[k] = float(r[k])
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    y = np.array([r[TARGET] for r in rows], dtype=float)
    X_c = sm.add_constant(X)
    return sm.OLS(y, X_c).fit()


def main():
    # ---- 2026 features ----
    kalshi = {r["team"]: r for r in load_csv(os.path.join(NFL, "kalshi_win_totals", "data", "kalshi_win_totals.csv"))}
    opponents = parse_2026_opponents()

    win_totals_2025 = {r["team"]: r for r in load_csv(os.path.join(NFL, "win_totals", "data", "win_totals.csv"))
                        if r["year"] == "2025"}
    point_diff_2025 = {r["team"]: r for r in load_csv(os.path.join(NFL, "game_results", "data", "team_point_diff.csv"))
                        if r["year"] == "2025"}

    rows_2026 = []
    for team in sorted(opponents):
        opp_lines = [float(kalshi[o]["implied_line"]) for o in opponents[team] if o in kalshi and kalshi[o]["implied_line"] != ""]
        sos_2026 = sum(opp_lines) / len(opp_lines) if opp_lines else None

        wt25 = win_totals_2025.get(team)
        pd25 = point_diff_2025.get(team)
        if not (wt25 and pd25 and sos_2026 is not None and team in kalshi):
            print(f"  skipping {team}: missing data")
            continue

        prior_actual_wins = int(wt25["actual_wins"])
        prior_win_total_line = float(wt25["win_total_line"])
        prior_beat_margin = prior_actual_wins - prior_win_total_line
        prior_pyth_wins = float(pd25["pyth_wins"])

        rows_2026.append({
            "team": team,
            "new_coach": 1 if team in NEW_COACHES_2026 else 0,
            "sos_this_year_line": sos_2026,
            "prior_year_under": 1 if wt25["result"] == "Under" else (0 if wt25["result"] == "Over" else 0.5),
            "prior_beat_margin": prior_beat_margin,
            "prior_actual_wins": prior_actual_wins,
            "prior_pyth_wins": prior_pyth_wins,
            "kalshi_implied_line": float(kalshi[team]["implied_line"]),
            "kalshi_expected_wins": float(kalshi[team]["expected_wins"]),
        })

    # ---- fit + predict ----
    model = fit_full_model()
    X_2026 = np.array([[r[f] for f in FEATURES] for r in rows_2026], dtype=float)
    X_2026_c = sm.add_constant(X_2026, has_constant="add")
    preds = model.predict(X_2026_c)
    for r, pred in zip(rows_2026, preds):
        r["predicted_wins"] = round(float(pred), 2)
        r["edge_vs_kalshi_line"] = round(r["predicted_wins"] - r["kalshi_implied_line"], 2)

    rows_2026.sort(key=lambda r: r["edge_vs_kalshi_line"], reverse=True)

    out_path = os.path.join(DATA_DIR, "predictions_2026.csv")
    fieldnames = ["team", "kalshi_implied_line", "predicted_wins", "edge_vs_kalshi_line",
                  "sos_this_year_line", "prior_actual_wins", "prior_pyth_wins",
                  "prior_beat_margin", "prior_year_under", "new_coach"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows({k: r[k] for k in fieldnames} for r in rows_2026)

    print("=" * 78)
    print("2026 PREDICTIONS vs KALSHI IMPLIED LINE (ranked by edge, high to low)")
    print("=" * 78)
    print(f"{'team':6s} {'kalshi_line':>11s} {'model_pred':>10s} {'edge':>7s} {'sos':>6s}")
    print("-" * 46)
    for r in rows_2026:
        print(f"{r['team']:6s} {r['kalshi_implied_line']:11.2f} {r['predicted_wins']:10.2f} "
              f"{r['edge_vs_kalshi_line']:+7.2f} {r['sos_this_year_line']:6.2f}")

    print(f"\nWrote -> {out_path}")
    print("\nReminder: the walk-forward backtest of THIS EXACT strategy (bet the side")
    print("the model disagrees with the market on) was not statistically significant")
    print("at any edge threshold on 2020-2025 data. Treat this table as 'what a basic")
    print("6-feature model thinks', not a demonstrated betting edge.")


if __name__ == "__main__":
    main()
