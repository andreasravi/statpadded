"""
Borrows three standard finance momentum/reversal constructions and applies
them to NFL win-total beat_margin (actual_wins - win_total_line), using only
the existing shared win_totals + game_results datasets (no new scraping):

  1. TIME-SERIES MOMENTUM/REVERSAL -- the classic "does an asset's own past
     return predict its own future return" test, at multiple lags (1, 2, 3
     years) and multiple trailing-window lengths (avg of trailing 2 or 3
     years, not just the immediate prior year). Equities show short-term
     reversal (~1 month), intermediate-term momentum (~3-12 months), and
     long-term reversal (~3-5 years) -- multiple lags are checked here for
     the same reason: to see whether a sign flip shows up at any horizon.

  2. FUNDAMENTAL ("earnings") MOMENTUM -- instead of the market-relative
     beat_margin, use the trend in the team's own underlying quality
     (pyth_wins, year-over-year) to predict this year's beat_margin. The
     finance analog is earnings momentum: does an accelerating fundamental
     trend predict returns beyond what the price (here: the market's line)
     already reflects?

  3. CROSS-SECTIONAL RELATIVE MOMENTUM -- the actual winners-minus-losers
     portfolio construction from Jegadeesh & Titman (1993): each season,
     rank all 32 teams against EACH OTHER (not against their own history)
     by trailing beat_margin, form a "winners" tercile and a "losers"
     tercile, and test whether betting WITH the trend (over on winners,
     under on losers) or AGAINST it (fade) produces a real, odds-priced
     edge.

Every test here is legitimately knowable before the season starts (all
inputs are trailing/lagged), so unlike the pyth-win-signal project, these
ARE candidate preseason betting signals, not just diagnostics -- which is
why each one is followed through to an actual backtest against real odds.
"""
import csv
import os
import sys

import numpy as np
from scipy import stats

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
NFL = os.path.join(REPO_ROOT, "nfl", "sources")

sys.path.insert(0, REPO_ROOT)
from nfl.common.betting import backtest


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def build_series():
    wt = load_csv(os.path.join(NFL, "win_totals", "data", "win_totals.csv"))
    pd_rows = load_csv(os.path.join(NFL, "game_results", "data", "team_point_diff.csv"))

    by_ty = {}
    for r in wt:
        y, t = int(r["year"]), r["team"]
        by_ty[(y, t)] = {
            "win_total_line": float(r["win_total_line"]),
            "actual_wins": int(r["actual_wins"]),
            "beat_margin": int(r["actual_wins"]) - float(r["win_total_line"]),
            "over_odds": r["over_odds"], "under_odds": r["under_odds"], "result": r["result"],
        }
    pyth_by_ty = {(int(r["year"]), r["team"]): float(r["pyth_wins"]) for r in pd_rows}
    return by_ty, pyth_by_ty


def section(title):
    print("\n" + "=" * 78)
    print(title)
    print("=" * 78)


def main():
    by_ty, pyth_by_ty = build_series()
    years = sorted(set(y for (y, _) in by_ty.keys()))
    print(f"years: {years[0]}-{years[-1]}, {len(set(t for _, t in by_ty))} teams")

    # ================================================================
    # 1) TIME-SERIES MOMENTUM/REVERSAL -- multi-lag autocorrelation
    # ================================================================
    section("1) TIME-SERIES: multi-lag autocorrelation of a team's own beat_margin")
    print(f"\n{'lag (years)':12s} {'n':>5s} {'r':>8s} {'p-value':>9s}")
    print("-" * 38)
    for lag in [1, 2, 3]:
        xs, ys = [], []
        for (y, t), row in by_ty.items():
            prev = by_ty.get((y - lag, t))
            if prev:
                xs.append(prev["beat_margin"])
                ys.append(row["beat_margin"])
        r, p = stats.pearsonr(xs, ys)
        sig = "*" if p < 0.05 else ""
        print(f"{lag:<12d} {len(xs):5d} {r:+8.3f} {p:9.3f} {sig}")

    print(f"\n{'trailing window':18s} {'n':>5s} {'r':>8s} {'p-value':>9s}")
    print("-" * 44)
    for k in [2, 3]:
        xs, ys = [], []
        for (y, t), row in by_ty.items():
            trail = [by_ty[(y - i, t)]["beat_margin"] for i in range(1, k + 1) if (y - i, t) in by_ty]
            if len(trail) == k:
                xs.append(np.mean(trail))
                ys.append(row["beat_margin"])
        r, p = stats.pearsonr(xs, ys)
        sig = "*" if p < 0.05 else ""
        print(f"trailing {k}yr avg{'':6s} {len(xs):5d} {r:+8.3f} {p:9.3f} {sig}")

    # ================================================================
    # 2) FUNDAMENTAL MOMENTUM -- trend in real quality (pyth_wins)
    # ================================================================
    section("2) FUNDAMENTAL MOMENTUM: pyth_wins trend (y-1 minus y-2) vs THIS year's beat_margin")
    xs, ys = [], []
    for (y, t), row in by_ty.items():
        p1, p2 = pyth_by_ty.get((y - 1, t)), pyth_by_ty.get((y - 2, t))
        if p1 is not None and p2 is not None:
            xs.append(p1 - p2)
            ys.append(row["beat_margin"])
    r, p = stats.pearsonr(xs, ys)
    print(f"\nn={len(xs)}, r={r:+.3f}, p={p:.3f}")
    print("(does a team's accelerating/decelerating underlying quality trend predict")
    print(" beating this year's line beyond what the line already reflects?)")

    # ================================================================
    # 3) CROSS-SECTIONAL RELATIVE MOMENTUM -- winners-minus-losers
    # ================================================================
    all_group_rows = []
    for k in [1, 2]:
        section(f"3) CROSS-SECTIONAL MOMENTUM: rank teams within each season by trailing {k}yr avg beat_margin")
        rows = []
        for y in years:
            candidates = []
            for t in sorted(set(tm for (yy, tm) in by_ty.keys() if yy == y)):
                trail = [by_ty[(y - i, t)]["beat_margin"] for i in range(1, k + 1) if (y - i, t) in by_ty]
                if len(trail) == k and (y, t) in by_ty:
                    candidates.append((t, np.mean(trail)))
            if len(candidates) < 20:
                continue
            # sort by trail_avg, team name as tiebreaker -- deterministic across runs
            candidates.sort(key=lambda x: (x[1], x[0]))
            third = len(candidates) // 3
            for t, trail_avg in candidates[:third]:
                rows.append({"year": y, "team": t, "window": k, "group": "loser",
                             "trail_avg": trail_avg, **by_ty[(y, t)]})
            for t, trail_avg in candidates[-third:]:
                rows.append({"year": y, "team": t, "window": k, "group": "winner",
                             "trail_avg": trail_avg, **by_ty[(y, t)]})
        all_group_rows.extend(rows)

        for g in ["winner", "loser"]:
            grp = [r for r in rows if r["group"] == g]
            bm = [r["beat_margin"] for r in grp]
            t_, p_ = stats.ttest_1samp(bm, 0)
            print(f"\n{g}s (n={len(grp)}): trailing avg beat_margin={np.mean([r['trail_avg'] for r in grp]):+.2f} "
                  f"-> THIS season's beat_margin mean={np.mean(bm):+.3f} (t={t_:.2f}, p={p_:.3f} vs 0)")

        winners_bm = [r["beat_margin"] for r in rows if r["group"] == "winner"]
        losers_bm = [r["beat_margin"] for r in rows if r["group"] == "loser"]
        t2, p2 = stats.ttest_ind(winners_bm, losers_bm)
        print(f"\nwinners vs losers beat_margin gap: t={t2:.2f}, p={p2:.3f}")

        for strategy, side_fn in [
            ("MOMENTUM (bet WITH the trend: over on winners, under on losers)",
             lambda g: "over" if g == "winner" else "under"),
            ("REVERSAL (fade the trend: under on winners, over on losers)",
             lambda g: "under" if g == "winner" else "over"),
        ]:
            bets = [{"side": side_fn(r["group"]), "result": r["result"],
                     "over_odds": r["over_odds"], "under_odds": r["under_odds"]} for r in rows]
            res = backtest(bets)
            p_str = f"{res['p_value']:.3f}" if res["p_value"] is not None else "n/a"
            print(f"\n  {strategy}")
            print(f"  n={res['n']}, win%={res['win_pct']:.1f}, ROI={res['roi_pct']:+.1f}%, p={p_str}")

    out_path = os.path.join(DATA_DIR, "cross_sectional_groups.csv")
    fieldnames = ["year", "team", "window", "group", "trail_avg", "win_total_line",
                  "actual_wins", "beat_margin", "result"]
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in all_group_rows:
            w.writerow({k_: r[k_] for k_ in fieldnames})
    print(f"\nWrote {len(all_group_rows)} winner/loser group rows -> {out_path}")


if __name__ == "__main__":
    main()
