"""
Does the schedule-swing regression actually beat Vegas' win-total line, or
does the market already price the schedule swing in?

Everything in analyze.py fits ONE regression on the full 2015-2025 sample
and reads its coefficients -- useful for sizing the historical effect, but
not a fair test of betting performance because the model "knows" seasons it
would be betting on. This script does the honest version, mirroring
projects/win-total-model/scripts/model.py's walk-forward convention:
refit on an expanding window of strictly PRIOR seasons only, predict each
held-out season, then bet whichever side (over/under) the model disagrees
with the market on, settled at real American odds.

Three models, same walk-forward protocol, so they're comparable apples to
apples:

  1. reversion_only     next_actual_wins ~ actual_wins
                         (no schedule input at all -- the ablation/control)
  2. schedule_actual     next_actual_wins ~ actual_wins + schedule_delta_actual
                         (this project's headline model)
  3. schedule_pyth       next_actual_wins ~ pyth_wins + schedule_delta_pyth
                         (luck-adjusted version -- the "more sophisticated"
                         SOS treatment: opponent quality from Pythagorean
                         wins, own baseline from Pythagorean wins too, so a
                         team that won ugly last year isn't over-anchored)

schedule_delta_actual / schedule_delta_pyth both use `sos_this_year_line`
for the season being predicted -- opponents' own preseason Vegas win-total
lines, which exist and are public before that season starts -- so nothing
here uses information a bettor wouldn't have had.
"""
import csv
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.betting import backtest  # noqa: E402

MODELS = {
    "reversion_only": ["actual_wins"],
    "schedule_actual": ["actual_wins", "schedule_delta_actual"],
    "schedule_pyth": ["pyth_wins", "schedule_delta_pyth"],
}
TARGET = "next_actual_wins"
TEST_YEARS = list(range(2020, 2026))  # T (season being bet), same window as win-total-model


def walk_forward(df, features):
    oos = []
    for test_year in TEST_YEARS:
        train = df[df["year"] < test_year - 1]  # df['year'] is T-1; T-1 < test_year-1 => T < test_year
        test = df[df["year"] == test_year - 1]
        if len(train) < 60:
            continue
        Xtr = sm.add_constant(train[features], has_constant="add")
        m = sm.OLS(train[TARGET], Xtr).fit()
        Xte = sm.add_constant(test[features], has_constant="add")
        preds = m.predict(Xte)
        for (idx, row), pred in zip(test.iterrows(), preds):
            oos.append({
                "year": test_year, "team": row["team"],
                "predicted_wins": pred,
                "next_actual_wins": row["next_actual_wins"],
                "next_win_total_line": row["next_win_total_line"],
            })
    return pd.DataFrame(oos)


def evaluate(name, oos_df, win_totals):
    errors = (oos_df["predicted_wins"] - oos_df["next_actual_wins"]).abs()
    mae = errors.mean()
    mae_line = (oos_df["next_win_total_line"] - oos_df["next_actual_wins"]).abs().mean()

    print(f"\n{'='*78}\n{name}\n{'='*78}")
    print(f"  n={len(oos_df)} out-of-sample predictions, {TEST_YEARS[0]}-{TEST_YEARS[-1]}")
    print(f"  model MAE:  {mae:.3f}")
    print(f"  market MAE: {mae_line:.3f}  ({'model beats market' if mae < mae_line else 'market still better'})")

    rows_out = []
    for min_edge in [0.0, 1.0, 1.5, 2.0]:
        bets = []
        for _, r in oos_df.iterrows():
            edge = r["predicted_wins"] - r["next_win_total_line"]
            if abs(edge) < min_edge:
                continue
            side = "over" if edge > 0 else "under"
            wt = win_totals[(r["year"], r["team"])]
            bets.append({"side": side, "result": wt["result"], "over_odds": wt["over_odds"], "under_odds": wt["under_odds"]})
        if not bets:
            print(f"  min_edge>={min_edge}: no qualifying bets")
            continue
        res = backtest(bets)
        p_str = f"{res['p_value']:.3f}" if res["p_value"] is not None else "n/a"
        print(f"  min_edge>={min_edge:<4} n={res['n']:>3} win%={res['win_pct']:5.1f}  "
              f"ROI={res['roi_pct']:+6.1f}%  profit={res['total_profit_units']:+6.2f}u  p={p_str}")
        rows_out.append({"model": name, "min_edge": min_edge, **res})
    return rows_out


def main():
    df = pd.read_csv(os.path.join(DATA_DIR, "merged.csv"))

    win_totals = {}
    with open(WIN_TOTALS_CSV) as f:
        for r in csv.DictReader(f):
            win_totals[(int(r["year"]), r["team"])] = r

    all_summaries = []
    for name, features in MODELS.items():
        oos_df = walk_forward(df, features)
        all_summaries += evaluate(name, oos_df, win_totals)
        if name == "schedule_actual":
            oos_df.round(2).to_csv(os.path.join(DATA_DIR, "backtest_oos_predictions.csv"), index=False)

    print(f"\n{'='*78}\nSUMMARY (min_edge>=1.0)\n{'='*78}")
    print(f"{'model':20s} {'n':>4s} {'win%':>7s} {'ROI':>8s} {'profit(u)':>10s} {'p':>7s}")
    for row in all_summaries:
        if row["min_edge"] == 1.0:
            p_str = f"{row['p_value']:.3f}" if row["p_value"] is not None else "n/a"
            print(f"{row['model']:20s} {row['n']:4d} {row['win_pct']:6.1f}% {row['roi_pct']:+7.1f}% "
                  f"{row['total_profit_units']:+9.2f}u {p_str:>7s}")


if __name__ == "__main__":
    main()
