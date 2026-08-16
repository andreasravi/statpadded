"""
Two signal-hunting questions on the shared nfl/sources/win_totals dataset
(2015-2025, no new scraping needed):

  1. LINE-JUMP ACCURACY: when Vegas moves a team's win-total line sharply
     year-over-year (implying they expect big improvement or big decline),
     is that new number more or less reliable than a stable line? Does a
     big jump tend to overshoot (mean-reversion / market overreaction) or
     undershoot (market underreacting, trend continues)?

  2. STREAK PERSISTENCE: if a team beat the over (or under) last year, or
     for multiple years running, does that predict beating the same side
     again next year (momentum/hot hand) or the opposite (mean reversion,
     "fade the streak")?

  3. ODDS-WEIGHTED BACKTEST: win-rate and beat-margin treat every bet as
     worth the same, but a -180 favorite and a +150 dog pay off completely
     differently. This section actually settles each strategy's bets at
     the real over_odds/under_odds price (flat 1-unit stakes) to see what
     it would have made or lost, not just how often it "hit."
"""
import csv
import os
import sys
from collections import defaultdict

from scipy import stats

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.betting import backtest


def load_win_totals():
    with open(WIN_TOTALS_CSV) as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        r["year"] = int(r["year"])
        r["win_total_line"] = float(r["win_total_line"])
        r["actual_wins"] = int(r["actual_wins"])
        r["beat_margin"] = r["actual_wins"] - r["win_total_line"]
    return rows


def line_change_bucket(c):
    if c <= -2.5:
        return "big_drop (<=-2.5)"
    if c <= -0.5:
        return "mod_drop (-2.5..-0.5)"
    if c < 0.5:
        return "stable (-0.5..+0.5)"
    if c < 2.5:
        return "mod_rise (+0.5..+2.5)"
    return "big_rise (>=+2.5)"


BUCKET_ORDER = [
    "big_drop (<=-2.5)",
    "mod_drop (-2.5..-0.5)",
    "stable (-0.5..+0.5)",
    "mod_rise (+0.5..+2.5)",
    "big_rise (>=+2.5)",
]


def main():
    rows = load_win_totals()
    by_key = {(r["year"], r["team"]): r for r in rows}

    # baseline result mix, for context on every % below
    n_all = len(rows)
    base_over = sum(1 for r in rows if r["result"] == "Over") / n_all * 100
    base_under = sum(1 for r in rows if r["result"] == "Under") / n_all * 100
    base_push = sum(1 for r in rows if r["result"] == "Push") / n_all * 100
    print("=" * 78)
    print(f"BASELINE (n={n_all}): Over {base_over:.1f}% / Under {base_under:.1f}% / Push {base_push:.1f}%")
    print("(the market is not perfectly 50/50 in this sample -- use this as the")
    print(" reference point for every over%/under% below, not 50%)")
    print("=" * 78)

    # ---------------------------------------------------------------
    # 1) LINE-JUMP ACCURACY
    # ---------------------------------------------------------------
    pairs = []
    for (y, t), r in by_key.items():
        prior = by_key.get((y - 1, t))
        if prior is None:
            continue
        line_change = r["win_total_line"] - prior["win_total_line"]
        pairs.append({**r, "line_change": line_change, "bucket": line_change_bucket(line_change)})

    merged_path = os.path.join(DATA_DIR, "line_change_merged.csv")
    with open(merged_path, "w", newline="") as f:
        fieldnames = ["year", "team", "line_change", "bucket", "win_total_line",
                      "actual_wins", "beat_margin", "result"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows({k: p[k] for k in fieldnames} for p in pairs)

    print(f"\nWrote {len(pairs)} line-change rows -> {merged_path}\n")

    print("=" * 78)
    print("1) DOES A BIG YoY LINE JUMP PREDICT HITTING OR MISSING THE NEW LINE?")
    print("=" * 78)
    x = [p["line_change"] for p in pairs]
    y = [p["beat_margin"] for p in pairs]
    r_val, p_val = stats.pearsonr(x, y)
    print(f"\nPearson r(line_change, beat_margin) = {r_val:+.3f} (p={p_val:.4f})")
    print("  negative r => big rises tend to OVERSHOOT (team misses under the new,")
    print("    higher number) and big drops tend to UNDERSHOOT (team beats the new,")
    print("    lower number) -- i.e. the market overreacts and mean-reverts")
    print("  positive r => the opposite: bigger moves predict MORE room to keep")
    print("    beating/missing in the same direction -- market underreacts\n")

    print(f"{'bucket':24s} {'n':>4s} {'avg_line_chg':>13s} {'avg_beat_margin':>16s} "
          f"{'MAE':>6s} {'over%':>7s} {'under%':>8s}")
    print("-" * 90)
    buckets = defaultdict(list)
    for p in pairs:
        buckets[p["bucket"]].append(p)
    for b in BUCKET_ORDER:
        grp = buckets.get(b, [])
        if not grp:
            continue
        n = len(grp)
        avg_chg = sum(g["line_change"] for g in grp) / n
        avg_margin = sum(g["beat_margin"] for g in grp) / n
        mae = sum(abs(g["beat_margin"]) for g in grp) / n
        over_pct = sum(1 for g in grp if g["result"] == "Over") / n * 100
        under_pct = sum(1 for g in grp if g["result"] == "Under") / n * 100
        print(f"{b:24s} {n:4d} {avg_chg:13.2f} {avg_margin:+16.2f} {mae:6.2f} "
              f"{over_pct:7.1f} {under_pct:8.1f}")

    # ---------------------------------------------------------------
    # 2) STREAK PERSISTENCE (autocorrelation)
    # ---------------------------------------------------------------
    print("\n" + "=" * 78)
    print("2) DOES BEATING (OR MISSING) THE LINE PREDICT DOING IT AGAIN?")
    print("=" * 78)

    # lag-1 autocorrelation of beat_margin (continuous)
    lag_pairs = [(by_key[(y - 1, t)]["beat_margin"], r["beat_margin"])
                 for (y, t), r in by_key.items() if (y - 1, t) in by_key]
    r_val, p_val = stats.pearsonr([a for a, b in lag_pairs], [b for a, b in lag_pairs])
    print(f"\nLag-1 autocorrelation, r(beat_margin[y-1], beat_margin[y]) = "
          f"{r_val:+.3f} (p={p_val:.4f}), n={len(lag_pairs)}")
    print("  negative r => mean reversion (last year's overs tend to come back")
    print("    down, last year's unders tend to bounce up)")
    print("  positive r => momentum (last year's overs keep overing)\n")

    # 1-year-prior result -> this year's result
    print("One year prior result -> this year's outcome:")
    print(f"{'prior result':14s} {'n':>4s} {'this_over%':>11s} {'this_under%':>12s} "
          f"{'avg_beat_margin':>16s}")
    print("-" * 62)
    for prior_result in ["Over", "Under"]:
        grp = [r for (y, t), r in by_key.items()
               if (y - 1, t) in by_key and by_key[(y - 1, t)]["result"] == prior_result]
        n = len(grp)
        over_pct = sum(1 for g in grp if g["result"] == "Over") / n * 100
        under_pct = sum(1 for g in grp if g["result"] == "Under") / n * 100
        avg_margin = sum(g["beat_margin"] for g in grp) / n
        print(f"{prior_result:14s} {n:4d} {over_pct:11.1f} {under_pct:12.1f} {avg_margin:+16.2f}")

    # 2-year streaks
    print("\nTwo years running the SAME way -> the following (3rd) year:")
    print(f"{'2yr streak':14s} {'n':>4s} {'this_over%':>11s} {'this_under%':>12s} "
          f"{'avg_beat_margin':>16s} {'p (vs 0)':>10s}")
    print("-" * 74)
    for streak_result in ["Over", "Under"]:
        grp = []
        for (y, t), r in by_key.items():
            p1 = by_key.get((y - 1, t))
            p2 = by_key.get((y - 2, t))
            if p1 and p2 and p1["result"] == p2["result"] == streak_result:
                grp.append(r)
        n = len(grp)
        if n == 0:
            continue
        over_pct = sum(1 for g in grp if g["result"] == "Over") / n * 100
        under_pct = sum(1 for g in grp if g["result"] == "Under") / n * 100
        margins = [g["beat_margin"] for g in grp]
        avg_margin = sum(margins) / n
        _, p_ttest = stats.ttest_1samp(margins, 0)
        print(f"{streak_result + ',' + streak_result:14s} {n:4d} {over_pct:11.1f} "
              f"{under_pct:12.1f} {avg_margin:+16.2f} {p_ttest:10.3f}")

    # 3-year streaks
    print("\nThree years running the SAME way -> the following (4th) year:")
    print(f"{'3yr streak':14s} {'n':>4s} {'this_over%':>11s} {'this_under%':>12s} "
          f"{'avg_beat_margin':>16s} {'p (vs 0)':>10s}")
    print("-" * 74)
    streak3_groups = {}
    for streak_result in ["Over", "Under"]:
        grp = []
        for (y, t), r in by_key.items():
            p1 = by_key.get((y - 1, t))
            p2 = by_key.get((y - 2, t))
            p3 = by_key.get((y - 3, t))
            if p1 and p2 and p3 and p1["result"] == p2["result"] == p3["result"] == streak_result:
                grp.append(r)
        streak3_groups[streak_result] = grp
        n = len(grp)
        if n == 0:
            continue
        over_pct = sum(1 for g in grp if g["result"] == "Over") / n * 100
        under_pct = sum(1 for g in grp if g["result"] == "Under") / n * 100
        margins = [g["beat_margin"] for g in grp]
        avg_margin = sum(margins) / n
        _, p_ttest = stats.ttest_1samp(margins, 0)
        print(f"{streak_result*3:14s} {n:4d} {over_pct:11.1f} {under_pct:12.1f} "
              f"{avg_margin:+16.2f} {p_ttest:10.3f}")
    print("\n  p (vs 0) is a one-sample t-test of that streak group's beat_margin against")
    print("  zero -- NOT corrected for the multiple comparisons run in this script, so")
    print("  treat anything above ~0.05 as suggestive at best, not confirmed.")

    # ---------------------------------------------------------------
    # 3) ODDS-WEIGHTED BACKTEST -- flat 1-unit stakes, real prices
    # ---------------------------------------------------------------
    print("\n" + "=" * 78)
    print("3) ODDS-WEIGHTED BACKTEST (flat 1-unit stakes, real over/under prices)")
    print("=" * 78)

    strategies = [
        ("Bet the OVER, every time", rows, "over"),
        ("Bet the UNDER, every time", rows, "under"),
        ("Big line drop (<=-2.5) -> bet OVER", buckets.get("big_drop (<=-2.5)", []), "over"),
        ("Big line rise (>=+2.5) -> bet UNDER", buckets.get("big_rise (>=+2.5)", []), "under"),
        ("3yr OVER streak -> fade, bet UNDER", streak3_groups.get("Over", []), "under"),
        ("3yr UNDER streak -> fade, bet OVER", streak3_groups.get("Under", []), "over"),
    ]

    print(f"{'strategy':38s} {'n':>4s} {'win%':>6s} {'profit(u)':>10s} {'roi%':>7s} "
          f"{'profit/bet':>11s} {'p (vs 0)':>9s}")
    print("-" * 92)
    backtest_results = {}
    for label, group, side in strategies:
        if not group:
            continue
        bets = [{"side": side, "result": g["result"], "over_odds": g["over_odds"],
                 "under_odds": g["under_odds"]} for g in group]
        res = backtest(bets)
        backtest_results[label] = res
        p_str = f"{res['p_value']:.3f}" if res["p_value"] is not None else "n/a"
        print(f"{label:38s} {res['n']:4d} {res['win_pct']:6.1f} "
              f"{res['total_profit_units']:+10.2f} {res['roi_pct']:+7.1f} "
              f"{res['profit_per_bet']:+11.3f} {p_str:>9s}")

    print("\n  profit(u) / profit_per_bet are in stake units (bet 1 unit per game,")
    print("  win/lose/push settles at the real recorded over_odds or under_odds).")
    print("  roi% = total_profit / total_staked. p (vs 0) is a one-sample t-test of")
    print("  per-bet profit against zero -- not corrected for testing 6 strategies")
    print("  here, so treat p > ~0.05 as unproven, not disproven.")

    bt_path = os.path.join(DATA_DIR, "backtest_results.csv")
    with open(bt_path, "w", newline="") as f:
        fieldnames = ["strategy", "n", "win_pct", "total_profit_units", "roi_pct",
                      "profit_per_bet", "p_value"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for label, res in backtest_results.items():
            w.writerow({
                "strategy": label,
                "n": res["n"],
                "win_pct": round(res["win_pct"], 2),
                "total_profit_units": round(res["total_profit_units"], 3),
                "roi_pct": round(res["roi_pct"], 2),
                "profit_per_bet": round(res["profit_per_bet"], 4),
                "p_value": round(res["p_value"], 4) if res["p_value"] is not None else "",
            })
    print(f"\nWrote backtest summary -> {bt_path}")


if __name__ == "__main__":
    main()
