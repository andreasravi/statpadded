"""
Every prior project in this repo tried to predict ACTUAL_WINS. But
actual_wins = pyth_wins + luck, where pyth_wins is the point-differential
-based (Pythagorean) win estimate -- "how good the team really was" -- and
luck is how much a team over/underperformed its own point differential in
close games, which is close to unpredictable noise.

That means every model built so far (including this repo's own
win-total-model) was partly fighting an irreducible noise floor. This
project re-targets PYTH_WINS instead of actual_wins for the SAME season,
using:

  1. How much better does the market's own current-season win_total_line
     predict real quality (pyth_wins) than it predicts the noisy actual
     win-loss record? (It should, structurally -- confirms how much of the
     "unexplained" variance elsewhere in this repo was just luck, not a
     missed signal.)
  2. Do the fundamentals already built for win-total-model (coaching,
     schedule, prior performance, prior luck, ADP) add anything to the
     market line when the target is quality instead of record?
  3. RESIDUAL SCAN: after fitting pyth_wins ~ win_total_line, do any
     fundamentals correlate with what's LEFT OVER -- i.e. does the market
     line miss something about a team's true quality that a public
     fundamental could have told it?
  4. If anything survives #3, does folding it into an ACTUAL_WINS
     prediction (the bettable target) produce a walk-forward edge that
     model.py's line-free fundamentals model didn't find?

Note: pyth_wins for the season being "predicted" is itself only knowable
AFTER that season is played -- like actual_wins, it is an outcome, not a
preseason input. This is not a forecasting model; it's a diagnostic that
uses a less noisy target to find out whether unexplained variance
elsewhere in this repo is missing signal or just unpredictable luck.
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
NFL = os.path.join(REPO_ROOT, "nfl", "sources")
WIN_TOTAL_MODEL_FEATURES_CSV = os.path.join(
    REPO_ROOT, "projects", "win-total-model", "data", "features.csv"
)

sys.path.insert(0, REPO_ROOT)
from nfl.common.betting import backtest

# same fundamentals set as projects/win-total-model, for apples-to-apples comparison
CORE_FEATURES = [
    "new_coach",
    "sos_this_year_line",
    "prior_year_under",
    "prior_beat_margin",
    "prior_actual_wins",
    "prior_pyth_wins",
]

# broader scan for the residual test -- every fundamental already sitting in
# features.csv, not just the six used in the core model
ALL_FUNDAMENTALS = CORE_FEATURES + [
    "prior_avg_point_diff",
    "prior_luck",
    "sos_prior_year_wins",
    "adp_top100_count",
    "adp_linear_weight",
]


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def build_merged():
    """features.csv already has win_total_line, actual_wins, and every
    fundamental for each (year, team). Add that SAME season's own
    pyth_wins (not the prior-year one already in features.csv) as the new
    target, plus in-season luck for reference."""
    features = load_csv(WIN_TOTAL_MODEL_FEATURES_CSV)
    point_diff = load_csv(os.path.join(NFL, "game_results", "data", "team_point_diff.csv"))
    pd_by_key = {(int(r["year"]), r["team"]): r for r in point_diff}

    rows = []
    for r in features:
        key = (int(r["year"]), r["team"])
        pd_row = pd_by_key.get(key)
        if not pd_row:
            continue
        row = dict(r)
        row["target_pyth_wins"] = float(pd_row["pyth_wins"])
        row["target_avg_point_diff"] = float(pd_row["avg_point_diff"])
        row["target_luck"] = float(r["actual_wins"]) - float(pd_row["pyth_wins"])
        rows.append(row)

    rows.sort(key=lambda r: (int(r["year"]), r["team"]))
    out_path = os.path.join(DATA_DIR, "merged.csv")
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} team-season rows -> {out_path}")
    return rows


def to_float(rows, cols):
    for r in rows:
        for c in cols:
            if r[c] != "":
                r[c] = float(r[c])
    return rows


def design_matrix(rows, features, target):
    X = np.array([[r[f] for f in features] for r in rows], dtype=float)
    y = np.array([r[target] for r in rows], dtype=float)
    return X, y


def print_ols(model, features, label):
    print(f"\n{label}: n={int(model.nobs)}, R²={model.rsquared:.3f}, adj. R²={model.rsquared_adj:.3f}")
    print(f"{'term':22s} {'coef':>8s} {'std err':>9s} {'p-value':>9s}")
    print("-" * 52)
    print(f"{'const':22s} {model.params[0]:8.3f} {model.bse[0]:9.3f} {model.pvalues[0]:9.3f}")
    for i, name in enumerate(features, start=1):
        sig = "*" if model.pvalues[i] < 0.05 else ""
        print(f"{name:22s} {model.params[i]:8.3f} {model.bse[i]:9.3f} {model.pvalues[i]:9.3f} {sig}")


def main():
    rows = build_merged()
    numeric_cols = ["win_total_line", "actual_wins", "target_pyth_wins", "target_avg_point_diff",
                     "target_luck"] + ALL_FUNDAMENTALS
    rows = to_float(rows, numeric_cols)

    # ============================================================
    # 1) BASELINE DECOMPOSITION: does the line predict quality better
    #    than it predicts the noisy actual record?
    # ============================================================
    print("=" * 78)
    print("1) DOES win_total_line PREDICT REAL QUALITY BETTER THAN THE ACTUAL RECORD?")
    print("=" * 78)
    line = [r["win_total_line"] for r in rows]
    actual = [r["actual_wins"] for r in rows]
    pyth = [r["target_pyth_wins"] for r in rows]
    luck = [r["target_luck"] for r in rows]

    r_actual, p_actual = stats.pearsonr(line, actual)
    r_pyth, p_pyth = stats.pearsonr(line, pyth)
    r_luck, p_luck = stats.pearsonr(line, luck)
    print(f"\nr(line, actual_wins)  = {r_actual:+.3f} (R²={r_actual**2:.3f}), p={p_actual:.4f}")
    print(f"r(line, pyth_wins)    = {r_pyth:+.3f} (R²={r_pyth**2:.3f}), p={p_pyth:.4f}")
    print(f"r(line, target_luck)  = {r_luck:+.3f} (R²={r_luck**2:.3f}), p={p_luck:.4f}")
    print(f"\nstd dev: actual_wins={np.std(actual):.2f}, pyth_wins={np.std(pyth):.2f}, "
          f"luck={np.std(luck):.2f} wins")
    print("(luck's std dev is the size of the noise floor every actual_wins model in this")
    print(" repo has been fighting -- and if r(line, luck) is ~0, the market isn't leaving")
    print(" quality signal on the table for luck reasons, it structurally can't predict luck.)")

    # ============================================================
    # 2) OLS: pyth_wins ~ win_total_line  (baseline quality model)
    # ============================================================
    print("\n" + "=" * 78)
    print("2) OLS: target_pyth_wins ~ win_total_line")
    print("=" * 78)
    X, y = design_matrix(rows, ["win_total_line"], "target_pyth_wins")
    X_c = sm.add_constant(X)
    model_line = sm.OLS(y, X_c).fit()
    print_ols(model_line, ["win_total_line"], "line-only model")
    resid_line_only = y - model_line.predict(X_c)

    # ============================================================
    # 3) OLS: pyth_wins ~ win_total_line + CORE_FEATURES
    # ============================================================
    print("\n" + "=" * 78)
    print("3) OLS: target_pyth_wins ~ win_total_line + " + " + ".join(CORE_FEATURES))
    print("=" * 78)
    full_features = ["win_total_line"] + CORE_FEATURES
    Xf, yf = design_matrix(rows, full_features, "target_pyth_wins")
    Xf_c = sm.add_constant(Xf)
    model_full = sm.OLS(yf, Xf_c).fit()
    print_ols(model_full, full_features, "line + fundamentals model")
    print(f"\nR² gain over line-only: {model_full.rsquared - model_line.rsquared:+.3f}")

    # ============================================================
    # 4) RESIDUAL SCAN: what's left over after the line explains quality?
    # ============================================================
    print("\n" + "=" * 78)
    print("4) RESIDUAL SCAN: (pyth_wins - line-only prediction) vs every fundamental")
    print("=" * 78)
    print("\nIf the market's line already captures everything a public fundamental knows")
    print("about a team's true quality, these should all be indistinguishable from zero.")
    print(f"\n{'feature':22s} {'r':>8s} {'p-value':>9s}")
    print("-" * 42)
    results = []
    for feat in ALL_FUNDAMENTALS:
        vals = [r[feat] for r in rows]
        r_val, p_val = stats.pearsonr(vals, resid_line_only)
        results.append((feat, r_val, p_val))
    results.sort(key=lambda t: -abs(t[1]))
    for feat, r_val, p_val in results:
        sig = "*" if p_val < 0.05 else ""
        print(f"{feat:22s} {r_val:+8.3f} {p_val:9.4f} {sig}")
    n_tested = len(ALL_FUNDAMENTALS)
    n_sig = sum(1 for _, _, p in results if p < 0.05)
    print(f"\n{n_sig}/{n_tested} features cross p<0.05 uncorrected -- with {n_tested} features")
    print(f"tested on one residual, ~{n_tested * 0.05:.1f} 'significant' hits are expected by")
    print("chance alone even if nothing is real (multiple-comparisons caveat, same as every")
    print("other residual/bucket scan in this repo).")

    # ============================================================
    # 5) DOES THE TOP RESIDUAL SIGNAL TRANSLATE INTO A BETTABLE EDGE?
    #    Fold it into an ACTUAL_WINS walk-forward model and backtest it.
    # ============================================================
    top_feat, top_r, top_p = results[0]
    print("\n" + "=" * 78)
    print(f"5) DOES '{top_feat}' (strongest residual hit) HELP PREDICT ACTUAL_WINS OOS?")
    print("=" * 78)
    print(f"\nStrongest residual-quality signal: {top_feat} (r={top_r:+.3f}, p={top_p:.4f}).")
    print("Testing whether adding it to a line-based ACTUAL_WINS model beats the market")
    print("line alone, walk-forward, out-of-sample, 2020-2025 -- the real bettable question.")

    bt_features = ["win_total_line", top_feat]
    test_years = sorted(set(int(r["year"]) for r in rows if int(r["year"]) >= 2020))
    oos_rows = []
    for test_year in test_years:
        train = [r for r in rows if int(r["year"]) < test_year]
        test = [r for r in rows if int(r["year"]) == test_year]
        if len(train) < 60:
            continue
        Xtr, ytr = design_matrix(train, bt_features, "actual_wins")
        Xtr_c = sm.add_constant(Xtr, has_constant="add")
        m = sm.OLS(ytr, Xtr_c).fit()
        Xte, yte = design_matrix(test, bt_features, "actual_wins")
        Xte_c = sm.add_constant(Xte, has_constant="add")
        preds = m.predict(Xte_c)
        for r, pred in zip(test, preds):
            oos_rows.append({**r, "predicted_wins": pred})

    errors = [abs(r["predicted_wins"] - r["actual_wins"]) for r in oos_rows]
    mae = sum(errors) / len(errors)
    mae_line = sum(abs(r["win_total_line"] - r["actual_wins"]) for r in oos_rows) / len(oos_rows)
    print(f"\nModel MAE (line + {top_feat}):  {mae:.3f}")
    print(f"Market MAE (line alone):          {mae_line:.3f}")

    win_totals = {}
    for r in load_csv(os.path.join(NFL, "win_totals", "data", "win_totals.csv")):
        win_totals[(int(r["year"]), r["team"])] = r

    print("\nBETTING STRATEGY: bet OVER if predicted_wins > line, UNDER if <")
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
            print(f"  min_edge >= {min_edge}: no qualifying bets")
            continue
        res = backtest(bets)
        p_str = f"{res['p_value']:.3f}" if res["p_value"] is not None else "n/a"
        print(f"  min_edge >= {min_edge}: n={res['n']}, win%={res['win_pct']:.1f}, "
              f"ROI={res['roi_pct']:+.1f}%, p={p_str}")

    oos_path = os.path.join(DATA_DIR, "oos_predictions.csv")
    with open(oos_path, "w", newline="") as f:
        fieldnames = ["year", "team", "win_total_line", "predicted_wins", "actual_wins", "target_pyth_wins"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in oos_rows:
            w.writerow({
                "year": int(r["year"]), "team": r["team"],
                "win_total_line": r["win_total_line"],
                "predicted_wins": round(r["predicted_wins"], 2),
                "actual_wins": r["actual_wins"],
                "target_pyth_wins": r["target_pyth_wins"],
            })
    print(f"\nWrote out-of-sample predictions -> {oos_path}")


if __name__ == "__main__":
    main()
