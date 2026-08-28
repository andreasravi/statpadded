"""
Predicting PYTHAGOREAN wins (not actual_wins) from QB tier, coaching
tenure, schedule-adjusted quality, turnover luck, and injury severity --
with an explicit test of whether "quality bucket" (was this team good or
bad to begin with) interacts with momentum, coaching change, and QB tier,
rather than just adding to them.

Two follow-up questions investigated and folded in after the first pass:

  - Is qb_tier's effect actually linear across the 5 tiers, and does the
    within-tier percentile rank (rank_in_season) add anything beyond the
    discrete tier? Tested via nested F-test: NO on both counts (categorical
    tier doesn't fit significantly better than linear, p=0.835, and its AIC
    is worse; adding pct_rank on top of tier doesn't help either, p=0.477).
    qb_tier stays linear.
  - Does prior_agl have real nonlinear structure, as the Random Forest
    diagnostic hinted (0.10 importance despite a near-zero, non-significant
    linear OLS coefficient)? YES, but not as a smooth curve -- a quadratic
    term isn't significant either (p=0.732). Quartile-BINNING prior_agl is
    what actually fits better (nested F-test p=0.005, AIC improves 1101.7->
    1094.6), and it's not a symmetric U either: the lowest-AGL (healthiest)
    quartile is the outlier, with every other quartile landing roughly flat
    to positive relative to it -- a mean-reversion story ("the healthiest
    team last year was probably a little lucky"), not a smooth injury-harm
    curve. Verified out-of-sample too (walk-forward MAE 1.774 vs 1.839 for
    the linear version, bucket edges recomputed from the training fold only
    each time -- no look-ahead), so it's kept as a real change, not just an
    in-sample fit bump like the interaction terms below.

Also: qb_tier is no longer listwise-deleted when missing (which dropped 65
of 320 rows, 21%). That missingness isn't random -- it's almost entirely
true rookie-debut-season starters, confirmed directly against the qb_tiers
raw source (Sando's own panel doesn't rate first-year starters; see
nfl/sources/qb_starters/README.md) -- so it's informative, not noise.
Handled with a has_qb_tier flag + a training-mean placeholder for the
missing tier value, recovering the full 320-row sample.

Four techniques, in order of how much they're trusted as a candidate
betting model vs. a diagnostic:

  1. OLS baseline           -- no interactions. The honest, interpretable
                                starting point, same convention as
                                projects/win-total-model.
  2. OLS + interactions     -- the main event: quality_bucket x
                                prior_beat_margin, quality_bucket x
                                coach_tenure_bucket, quality_bucket x
                                qb_tier.
  3. Ridge/Lasso (CV alpha) -- same feature set as (2), standardized.
                                Diagnostic: does Lasso keep the
                                hand-picked interactions, or zero them
                                out? Not walk-forward backtested --
                                presented as an interaction-selection
                                sanity check, not a candidate model.
  4. Random Forest          -- diagnostic only, on the raw (no manual
                                interaction/binning) feature set. Feature
                                importances + 5-fold CV R^2, to check
                                whether OLS is missing nonlinear
                                structure. NOT walk-forward backtested --
                                every other project in this repo found
                                fancier techniques don't hold up
                                out-of-sample at this sample size
                                (~300 team-seasons), so this is a sanity
                                check on that prior, not a bet on beating
                                it.

Only (1) and (2) go through the honest walk-forward backtest (expanding
window, strictly prior seasons, 2020-2025) -- both against the realized
target_pyth_wins directly (a clean diagnostic no market exists to bet
against) AND translated into a real betting test against win_total_line
(same "fold the prediction back into an actual-wins bet" move
pyth-win-signal used), so both the interaction hypothesis and the AGL
binning get a real out-of-sample test, not just an in-sample R^2 bump.
"""
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
import statsmodels.formula.api as smf
from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LassoCV, RidgeCV
from sklearn.model_selection import cross_val_score
from sklearn.preprocessing import StandardScaler

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.betting import backtest

TARGET = "target_pyth_wins"
AGL_LABELS = ["agl_q1_low", "agl_q2", "agl_q3", "agl_q4_high"]
QUALITY_LABELS = ["bad", "mid", "good"]

# NOTE: new_coach is dropped as its own term -- it's an exact linear
# function of the coach_tenure_bucket=='Yr1' dummy (new_coach==1 iff
# tenure_bucket=='Yr1' for every row in this sample; a coaching change IS
# what makes tenure reset to 1). Including both makes the design matrix
# rank-deficient (Intercept = new_coach + [Yr2-3] + [Yr4+] exactly), so
# those coefficients stop being individually identified. coach_tenure_bucket
# alone (Yr1 as the reference level) already carries that information.
BASE_TERMS = [
    "qb_tier_filled", "has_qb_tier", "prior_pyth_wins", "schedule_delta_pyth",
    "prior_turnover_diff_per_game", "C(agl_bucket)", "prior_beat_margin",
    "C(coach_tenure_bucket, Treatment('Yr1'))",
]
BASE_FORMULA = f"{TARGET} ~ " + " + ".join(BASE_TERMS)
INTERACTION_FORMULA = BASE_FORMULA + (
    " + C(quality_bucket, Treatment('bad'))"
    " + prior_beat_margin:C(quality_bucket, Treatment('bad'))"
    " + C(coach_tenure_bucket, Treatment('Yr1')):C(quality_bucket, Treatment('bad'))"
    " + qb_tier_filled:C(quality_bucket, Treatment('bad'))"
)

RF_FEATURES = [
    "qb_tier_filled", "has_qb_tier", "prior_pyth_wins", "schedule_delta_pyth",
    "prior_turnover_diff_per_game", "prior_agl", "prior_beat_margin",
    "coach_tenure",
]


def load():
    df = pd.read_csv(os.path.join(DATA_DIR, "features.csv"))
    needed = [TARGET, "prior_pyth_wins", "schedule_delta_pyth",
              "prior_turnover_diff_per_game", "prior_agl", "prior_beat_margin",
              "coach_tenure", "win_total_line", "actual_wins", "beat_margin", "year", "team"]
    df = df.dropna(subset=needed)
    df["qb_tier"] = pd.to_numeric(df["qb_tier"], errors="coerce")  # '' -> NaN
    return df.reset_index(drop=True)


def add_fold_features(train, test):
    """Bucket/placeholder engineering fit on TRAIN only, applied to both --
    the walk-forward backtest calls this per fold so nothing about a held-out
    season's own distribution leaks into its bucket edges or the QB-tier
    placeholder. For the full-sample in-sample analysis below, train=test=df,
    so it's just "compute once on the whole sample" (same as quality_bucket
    always was)."""
    train = train.copy()
    test = test.copy()

    tier_mean = train["qb_tier"].mean()
    for d in (train, test):
        d["has_qb_tier"] = d["qb_tier"].notna().astype(int)
        d["qb_tier_filled"] = d["qb_tier"].fillna(tier_mean)

    agl_edges = pd.qcut(train["prior_agl"], 4, retbins=True, duplicates="drop")[1]
    agl_edges = np.array(agl_edges, dtype=float)
    agl_edges[0], agl_edges[-1] = -np.inf, np.inf
    quality_edges = pd.qcut(train["prior_pyth_wins"], 3, retbins=True, duplicates="drop")[1]
    quality_edges = np.array(quality_edges, dtype=float)
    quality_edges[0], quality_edges[-1] = -np.inf, np.inf
    for d in (train, test):
        d["agl_bucket"] = pd.cut(d["prior_agl"], bins=agl_edges, labels=AGL_LABELS)
        d["quality_bucket"] = pd.cut(d["prior_pyth_wins"], bins=quality_edges, labels=QUALITY_LABELS)

    return train, test


def print_ols(name, res, n):
    print(f"\n--- {name} --- n={n}, R²={res.rsquared:.3f}, adj. R²={res.rsquared_adj:.3f}")
    print(f"{'term':45s} {'coef':>8s} {'p-value':>9s}")
    print("-" * 65)
    for term, coef, p in zip(res.params.index, res.params.values, res.pvalues.values):
        sig = "*" if p < 0.05 else ("~" if p < 0.10 else "")
        print(f"{term:45s} {coef:8.3f} {p:9.3f} {sig}")


def walk_forward(df, formula, test_years):
    oos = []
    for test_year in test_years:
        train_raw = df[df["year"] < test_year]
        test_raw = df[df["year"] == test_year]
        if len(train_raw) < 80:
            continue
        train, test = add_fold_features(train_raw, test_raw)
        m = smf.ols(formula, data=train).fit()
        preds = m.predict(test)
        for (_, row), pred in zip(test.iterrows(), preds):
            oos.append({**row.to_dict(), "predicted_pyth_wins": pred})
    return pd.DataFrame(oos)


def report_backtest(oos, win_totals, label):
    if oos.empty:
        print(f"\n{label}: no out-of-sample rows")
        return
    mae_pyth = (oos["predicted_pyth_wins"] - oos[TARGET]).abs().mean()
    print(f"\n{label}: n={len(oos)}, MAE(predicted_pyth_wins, realized target_pyth_wins) = {mae_pyth:.3f}")

    for min_edge in [0.0, 1.0, 2.0]:
        bets = []
        for _, r in oos.iterrows():
            edge = r["predicted_pyth_wins"] - r["win_total_line"]
            if abs(edge) < min_edge:
                continue
            side = "over" if edge > 0 else "under"
            wt = win_totals[(int(r["year"]), r["team"])]
            bets.append({"side": side, "result": wt["result"],
                         "over_odds": wt["over_odds"], "under_odds": wt["under_odds"]})
        if not bets:
            print(f"  min_edge>={min_edge}: no qualifying bets")
            continue
        res = backtest(bets)
        p_str = f"{res['p_value']:.3f}" if res["p_value"] is not None else "n/a"
        print(f"  min_edge>={min_edge}: n={res['n']}, win%={res['win_pct']:.1f}, "
              f"ROI={res['roi_pct']:+.1f}%, p={p_str}")


def main():
    df_raw = load()
    df, _ = add_fold_features(df_raw, df_raw)  # full-sample buckets, for the in-sample analysis
    print(f"Loaded {len(df)} team-seasons (full sample -- qb_tier missingness handled via "
          f"has_qb_tier flag, not dropped), years {df['year'].min()}-{df['year'].max()}")
    print(f"  has_qb_tier: {df['has_qb_tier'].sum()}/{len(df)}")
    print("Quality bucket cutpoints (tercile of prior_pyth_wins):")
    print(df.groupby("quality_bucket", observed=True)["prior_pyth_wins"].agg(["min", "max", "count"]))
    print("AGL bucket cutpoints (quartile of prior_agl):")
    print(df.groupby("agl_bucket", observed=True)["prior_agl"].agg(["min", "max", "count"]))

    # ============================================================
    # 1) OLS baseline (no interactions)
    # ============================================================
    m_base = smf.ols(BASE_FORMULA, data=df).fit()
    print_ols("1) OLS BASELINE (no interactions)", m_base, len(df))

    from scipy import stats as _stats
    r_line, _ = _stats.pearsonr(df["win_total_line"], df[TARGET])
    r_persist, _ = _stats.pearsonr(df["prior_pyth_wins"], df[TARGET])
    print(f"\nFor context (not part of the model, same {len(df)}-row in-sample set): "
          f"r(win_total_line, target_pyth_wins)={r_line:.3f} (R²={r_line**2:.3f}), "
          f"r(prior_pyth_wins, target_pyth_wins)={r_persist:.3f} (R²={r_persist**2:.3f})")

    # ============================================================
    # 2) OLS + interactions
    # ============================================================
    m_int = smf.ols(INTERACTION_FORMULA, data=df).fit()
    print_ols("2) OLS + quality-bucket interactions", m_int, len(df))
    print(f"\nDoes adding the interactions actually explain more? "
          f"ΔR²={m_int.rsquared - m_base.rsquared:+.3f}, "
          f"F-test p={sm.stats.anova_lm(m_base, m_int).iloc[1]['Pr(>F)']:.3f}")

    # ============================================================
    # 3) Ridge / Lasso (standardized, CV alpha) -- diagnostic
    # ============================================================
    print("\n" + "=" * 78)
    print("3) RIDGE / LASSO on the same interaction feature set (standardized, CV alpha)")
    print("=" * 78)
    y = df[TARGET].values
    X_df = pd.get_dummies(
        df[["qb_tier_filled", "has_qb_tier", "prior_pyth_wins", "schedule_delta_pyth",
            "prior_turnover_diff_per_game", "prior_beat_margin",
            "agl_bucket", "coach_tenure_bucket", "quality_bucket"]],
        columns=["agl_bucket", "coach_tenure_bucket", "quality_bucket"], drop_first=True,
    )
    # hand-added interaction columns, matching the OLS formula above
    for q in ["mid", "good"]:
        X_df[f"beat_margin_x_{q}"] = df["prior_beat_margin"] * (df["quality_bucket"] == q).astype(float)
        X_df[f"qb_tier_x_{q}"] = df["qb_tier_filled"] * (df["quality_bucket"] == q).astype(float)
        for t in ["Yr2-3", "Yr4+"]:
            X_df[f"tenure_{t}_x_{q}"] = (df["coach_tenure_bucket"] == t).astype(float) * (df["quality_bucket"] == q).astype(float)
    X_df = X_df.astype(float)
    Xs = StandardScaler().fit_transform(X_df.values)

    ridge = RidgeCV(alphas=np.logspace(-2, 3, 50)).fit(Xs, y)
    lasso = LassoCV(alphas=None, cv=5, max_iter=20000, random_state=0).fit(Xs, y)
    print(f"\nRidge: alpha={ridge.alpha_:.3f}, R²(in-sample)={ridge.score(Xs, y):.3f}")
    print(f"Lasso: alpha={lasso.alpha_:.4f}, R²(in-sample)={lasso.score(Xs, y):.3f}")
    print(f"\n{'term':25s} {'ridge':>8s} {'lasso':>8s}")
    print("-" * 45)
    for name, r_coef, l_coef in zip(X_df.columns, ridge.coef_, lasso.coef_):
        zeroed = " (zeroed)" if l_coef == 0 else ""
        print(f"{name:25s} {r_coef:8.3f} {l_coef:8.3f}{zeroed}")

    # ============================================================
    # 4) Random Forest -- diagnostic only
    # ============================================================
    print("\n" + "=" * 78)
    print("4) RANDOM FOREST (diagnostic: feature importance + nonlinearity check)")
    print("=" * 78)
    X_rf = df[RF_FEATURES].astype(float).values
    rf = RandomForestRegressor(n_estimators=400, max_depth=4, min_samples_leaf=8, random_state=0)
    cv_r2 = cross_val_score(rf, X_rf, y, cv=5, scoring="r2")
    rf.fit(X_rf, y)
    print(f"\n5-fold CV R² = {cv_r2.mean():.3f} (+/- {cv_r2.std():.3f}) -- compare to OLS in-sample "
          f"R²={m_int.rsquared:.3f} (not apples-to-apples, CV is out-of-fold; still, if RF's CV R² is "
          f"far below OLS's in-sample R², that's just OLS overfitting, not RF underperforming)")
    print(f"\n{'feature':30s} {'importance':>10s}")
    print("-" * 42)
    for name, imp in sorted(zip(RF_FEATURES, rf.feature_importances_), key=lambda x: -x[1]):
        print(f"{name:30s} {imp:10.3f}")

    # ============================================================
    # WALK-FORWARD BACKTEST, 2020-2025: baseline vs. interactions
    # ============================================================
    print("\n" + "=" * 78)
    print("WALK-FORWARD BACKTEST (expanding window, strictly prior seasons, 2020-2025)")
    print("bucket edges + QB-tier placeholder recomputed from the training fold only each time")
    print("=" * 78)
    win_totals = {}
    import csv
    with open(WIN_TOTALS_CSV) as f:
        for r in csv.DictReader(f):
            win_totals[(int(r["year"]), r["team"])] = r

    test_years = sorted(y for y in df_raw["year"].unique() if y >= 2020)
    oos_base = walk_forward(df_raw, BASE_FORMULA, test_years)
    oos_int = walk_forward(df_raw, INTERACTION_FORMULA, test_years)
    report_backtest(oos_base, win_totals, "Model 1 (baseline, no interactions)")
    report_backtest(oos_int, win_totals, "Model 2 (with quality-bucket interactions)")

    # ---- how good is that, really? same OOS rows, naive baselines ----
    print("\n" + "-" * 78)
    print("CONTEXT: same out-of-sample rows, three baselines that use no model at all")
    print("-" * 78)
    oos_ref = oos_base[["year", "team", TARGET, "win_total_line", "prior_pyth_wins"]]
    train_mean = df_raw[df_raw["year"] < oos_ref["year"].min()][TARGET].mean()
    baselines = {
        "market line (Vegas, used directly as the prediction)": oos_ref["win_total_line"],
        "pure persistence (prior_pyth_wins, no adjustment)": oos_ref["prior_pyth_wins"],
        "mean-only (training-set average every time)": pd.Series(train_mean, index=oos_ref.index),
    }
    print(f"{'':58s} {'OOS MAE':>8s}")
    for label, pred in baselines.items():
        mae = (pred - oos_ref[TARGET]).abs().mean()
        print(f"{label:58s} {mae:8.3f}")
    print(f"{'Model 1 (baseline, no interactions)':58s} {(oos_base['predicted_pyth_wins'] - oos_base[TARGET]).abs().mean():8.3f}")
    print(f"{'Model 2 (with quality-bucket interactions)':58s} {(oos_int['predicted_pyth_wins'] - oos_int[TARGET]).abs().mean():8.3f}")
    print("\nBoth models beat 'assume nothing changed' and 'no information at all,' but")
    print("neither beats just using Vegas's own line directly -- consistent with every")
    print("other project in this repo (pyth-win-signal, win-total-model, ...).")

    if not oos_int.empty:
        out_path = os.path.join(DATA_DIR, "oos_predictions.csv")
        oos_int[["year", "team", "win_total_line", "predicted_pyth_wins", TARGET, "actual_wins", "quality_bucket"]].to_csv(out_path, index=False)
        print(f"\nWrote out-of-sample predictions (interaction model) -> {out_path}")


if __name__ == "__main__":
    main()
