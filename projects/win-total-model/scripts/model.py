"""
A basic win-total model: predict actual_wins from team fundamentals known
BEFORE the season (no market win_total_line as an input), using:

  new_coach            coaching change flag (0/1)
  sos_this_year_line   upcoming strength of schedule (Vegas-based: avg of
                        opponents' own win-total lines this season)
  prior_year_under     streak history binary (1 = missed the under last
                        year, 0 = beat the over, 0.5 = push)
  prior_beat_margin    last year's line outperformance (actual - line)
  prior_actual_wins    last year's real win total
  prior_pyth_wins      point-differential-based (Pythagorean) win estimate
                        from last year -- "how good were they really"

Two things this script does:
  1. IN-SAMPLE FIT (statsmodels OLS on all 2016-2025 data) -- coefficients,
     significance, R², and a comparison to "just use last year's actual
     wins" and "just use the market line" as naive baselines.
  2. WALK-FORWARD BACKTEST -- refit on an expanding window of strictly
     PRIOR seasons only (no look-ahead) and predict each held-out season
     2020-2025, then bet whichever side (over/under) the model disagrees
     with the market on, settled at real odds via nfl/common/betting.py.
"""
import csv
import os
import sys

import numpy as np
import statsmodels.api as sm
from scipy import stats

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.betting import backtest

FEATURES = [
    "new_coach",
    "sos_this_year_line",
    "prior_year_under",
    "prior_beat_margin",
    "prior_actual_wins",
    "prior_pyth_wins",
]
TARGET = "actual_wins"


def load_features():
    with open(os.path.join(DATA_DIR, "features.csv")) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["year"] = int(r["year"])
        for k in FEATURES + [TARGET, "win_total_line", "beat_margin", "prior_actual_wins"]:
            if r[k] != "":
                r[k] = float(r[k])
    return rows


def design_matrix(rows):
    X = np.array([[r[f] for f in FEATURES] for r in rows], dtype=float)
    y = np.array([r[TARGET] for r in rows], dtype=float)
    return X, y


def main():
    rows = load_features()

    # ============================================================
    # 1) IN-SAMPLE FIT (all 320 rows, 2016-2025)
    # ============================================================
    print("=" * 78)
    print("IN-SAMPLE OLS FIT: actual_wins ~ " + " + ".join(FEATURES))
    print("=" * 78)
    X, y = design_matrix(rows)
    X_const = sm.add_constant(X)
    model = sm.OLS(y, X_const).fit()

    print(f"\nn = {len(rows)}, R² = {model.rsquared:.3f}, adj. R² = {model.rsquared_adj:.3f}\n")
    print(f"{'term':22s} {'coef':>8s} {'std err':>9s} {'p-value':>9s}")
    print("-" * 52)
    print(f"{'const':22s} {model.params[0]:8.3f} {model.bse[0]:9.3f} {model.pvalues[0]:9.3f}")
    for i, name in enumerate(FEATURES, start=1):
        sig = "*" if model.pvalues[i] < 0.05 else ""
        print(f"{name:22s} {model.params[i]:8.3f} {model.bse[i]:9.3f} {model.pvalues[i]:9.3f} {sig}")

    # naive baselines for context
    r_line, _ = stats.pearsonr([r["win_total_line"] for r in rows], y)
    r_prior, _ = stats.pearsonr([r["prior_actual_wins"] for r in rows], y)
    print(f"\nFor context (not part of the model): r(win_total_line, actual_wins) = {r_line:.3f} "
          f"(R²={r_line**2:.3f})")
    print(f"                                       r(prior_actual_wins, actual_wins) = {r_prior:.3f} "
          f"(R²={r_prior**2:.3f})")
    print("Our multi-feature model uses NO current-year market line as an input --")
    print("this is what you can predict from team fundamentals alone, to compare")
    print("against what the market already captures.")

    # ============================================================
    # 2) WALK-FORWARD OUT-OF-SAMPLE BACKTEST, 2020-2025
    # ============================================================
    print("\n" + "=" * 78)
    print("WALK-FORWARD BACKTEST (expanding window, strictly prior seasons only)")
    print("=" * 78)

    test_years = sorted(set(r["year"] for r in rows if r["year"] >= 2020))
    oos_rows = []
    for test_year in test_years:
        train = [r for r in rows if r["year"] < test_year]
        test = [r for r in rows if r["year"] == test_year]
        if len(train) < 60:  # need a reasonable amount of training data
            continue
        Xtr, ytr = design_matrix(train)
        Xtr_c = sm.add_constant(Xtr, has_constant="add")
        m = sm.OLS(ytr, Xtr_c).fit()

        Xte, yte = design_matrix(test)
        Xte_c = sm.add_constant(Xte, has_constant="add")
        preds = m.predict(Xte_c)

        for r, pred in zip(test, preds):
            oos_rows.append({**r, "predicted_wins": pred})

    print(f"\nGenerated {len(oos_rows)} out-of-sample predictions "
          f"({test_years[0] if oos_rows else '-'}-2025)\n")

    errors = [abs(r["predicted_wins"] - r["actual_wins"]) for r in oos_rows]
    mae = sum(errors) / len(errors)
    mae_line = sum(abs(r["win_total_line"] - r["actual_wins"]) for r in oos_rows) / len(oos_rows)
    print(f"Model MAE (|predicted_wins - actual_wins|):        {mae:.3f}")
    print(f"Market MAE (|win_total_line - actual_wins|):       {mae_line:.3f}")
    print("(lower is better; if model MAE > market MAE, the market alone is still")
    print(" the better predictor of actual wins -- not unusual, and not fatal to a")
    print(" betting strategy, which only needs to find the market's OWN blind spots.)")

    # ---- betting strategy: bet whichever side the model disagrees with the market on ----
    print("\n" + "-" * 78)
    print("BETTING STRATEGY: bet OVER if predicted_wins > line, UNDER if <")
    print("-" * 78)

    win_totals = {}
    with open(WIN_TOTALS_CSV) as f:
        for r in csv.DictReader(f):
            win_totals[(int(r["year"]), r["team"])] = r

    for min_edge in [0.0, 1.0, 2.0]:
        bets = []
        for r in oos_rows:
            edge = r["predicted_wins"] - r["win_total_line"]
            if abs(edge) < min_edge:
                continue
            side = "over" if edge > 0 else "under"
            wt = win_totals[(int(r["year"]), r["team"])]
            bets.append({"side": side, "result": wt["result"],
                         "over_odds": wt["over_odds"], "under_odds": wt["under_odds"]})
        if not bets:
            print(f"\nmin_edge >= {min_edge}: no qualifying bets")
            continue
        res = backtest(bets)
        p_str = f"{res['p_value']:.3f}" if res["p_value"] is not None else "n/a"
        print(f"\nmin_edge >= {min_edge} wins: n={res['n']}, win%={res['win_pct']:.1f}, "
              f"ROI={res['roi_pct']:+.1f}%, profit={res['total_profit_units']:+.2f}u, "
              f"p={p_str}")

    # save OOS predictions for reference / for the artifact
    oos_path = os.path.join(DATA_DIR, "oos_predictions.csv")
    with open(oos_path, "w", newline="") as f:
        fieldnames = ["year", "team", "win_total_line", "predicted_wins", "actual_wins",
                      "beat_margin"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in oos_rows:
            w.writerow({
                "year": int(r["year"]), "team": r["team"],
                "win_total_line": r["win_total_line"],
                "predicted_wins": round(r["predicted_wins"], 2),
                "actual_wins": r["actual_wins"], "beat_margin": r["beat_margin"],
            })
    print(f"\nWrote out-of-sample predictions -> {oos_path}")


if __name__ == "__main__":
    main()
