"""
Merge ADP data with win totals and test for a relationship between a team's
fantasy-relevant roster and its win total, three ways:

  1. Raw count of top-N ADP players on the roster (N = 25/50/100)
  2. Rank-weighted score: every rostered player in the top 100 contributes,
     weighted so a #1-overall ADP guy counts far more than a #95 flex piece
       - linear decay:  weight = 101 - rank        (gentle taper)
       - reciprocal:    weight = 100 / rank         (steep, front-loaded)
  3. Best-player-on-team: the ADP rank of each team's single highest pick
     (lower = better), since one true superstar may matter more than depth

Each is checked against actual wins, the market win-total line, and the
beat-the-line margin (actual wins - line) to see whether it's just "good
players -> good teams" (priced in) or an exploitable signal (not priced in).
"""
import csv
import os
from collections import defaultdict

from scipy import stats

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
ADP_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "adp", "data", "adp.csv")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")


def load_adp():
    with open(ADP_CSV) as f:
        return list(csv.DictReader(f))


def load_win_totals():
    with open(WIN_TOTALS_CSV) as f:
        return list(csv.DictReader(f))


def build_team_metrics(adp_rows):
    """One row per (year, team) with count, weighted-score, and best-rank metrics."""
    by_team = defaultdict(list)
    for row in adp_rows:
        key = (int(row["year"]), row["team"])
        by_team[key].append(int(row["rank"]))

    metrics = {}
    for key, ranks in by_team.items():
        ranks.sort()
        metrics[key] = {
            "top25_count": sum(1 for r in ranks if r <= 25),
            "top50_count": sum(1 for r in ranks if r <= 50),
            "top100_count": sum(1 for r in ranks if r <= 100),
            "linear_weight": sum(101 - r for r in ranks if r <= 100),
            "reciprocal_weight": round(sum(100 / r for r in ranks if r <= 100), 2),
            "best_rank": min(ranks) if ranks else 101,  # 101 = no top-100 player
        }
    return metrics


def main():
    adp = load_adp()
    wins = load_win_totals()
    team_metrics = build_team_metrics(adp)

    metric_keys = [
        "top25_count",
        "top50_count",
        "top100_count",
        "linear_weight",
        "reciprocal_weight",
        "best_rank",
    ]

    merged = []
    for w in wins:
        key = (int(w["year"]), w["team"])
        rec = {
            "year": int(w["year"]),
            "team": w["team"],
            "win_total_line": float(w["win_total_line"]),
            "actual_wins": int(w["actual_wins"]),
            "result": w["result"],
        }
        rec["beat_margin"] = rec["actual_wins"] - rec["win_total_line"]
        m = team_metrics.get(key, {k: 0 for k in metric_keys})
        if key not in team_metrics:
            m["best_rank"] = 101
        rec.update(m)
        merged.append(rec)

    out_path = os.path.join(DATA_DIR, "merged.csv")
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(merged[0].keys()))
        w.writeheader()
        w.writerows(merged)
    print(f"Wrote merged dataset ({len(merged)} rows) -> {out_path}\n")

    # ---- correlations: each metric vs wins, vs line, vs beat-margin ----
    print("=" * 78)
    print("METRIC  vs  actual wins / market line / beat-the-line margin")
    print("(best_rank is inverted in sign since LOWER rank = better roster)")
    print("=" * 78)
    y_wins = [r["actual_wins"] for r in merged]
    y_line = [r["win_total_line"] for r in merged]
    y_margin = [r["beat_margin"] for r in merged]

    header = f"{'metric':20s} {'r vs wins':>12s} {'r vs line':>12s} {'r vs beat-margin':>18s}"
    print(header)
    print("-" * len(header))
    for mk in metric_keys:
        x = [r[mk] for r in merged]
        if mk == "best_rank":
            x = [-v for v in x]  # flip so "higher = better" like the others
        r_wins, _ = stats.pearsonr(x, y_wins)
        r_line, _ = stats.pearsonr(x, y_line)
        r_margin, p_margin = stats.pearsonr(x, y_margin)
        flag = "  <- p<0.05" if p_margin < 0.05 else ""
        print(f"{mk:20s} {r_wins:12.3f} {r_line:12.3f} {r_margin:18.3f}{flag}")

    # ---- does weighting beat plain counting? compare top100_count vs reciprocal_weight ----
    print("\n" + "=" * 78)
    print("Does rank-weighting add anything over a plain top-100 head count?")
    print("=" * 78)
    for mk in ["top100_count", "linear_weight", "reciprocal_weight"]:
        x = [r[mk] for r in merged]
        r_wins, p_wins = stats.pearsonr(x, y_wins)
        r_margin, p_margin = stats.pearsonr(x, y_margin)
        print(f"  {mk:20s} r(wins)={r_wins:+.3f} (p={p_wins:.4f})   "
              f"r(beat_margin)={r_margin:+.3f} (p={p_margin:.4f})")

    # ---- best_rank: does having THE #1 or #2 overall guy matter beyond depth? ----
    print("\n" + "-" * 78)
    print("Team's single best ADP rank -> avg wins / avg beat margin")
    print("-" * 78)
    buckets = defaultdict(list)
    for r in merged:
        br = r["best_rank"]
        if br <= 5:
            b = "1-5 (elite)"
        elif br <= 15:
            b = "6-15"
        elif br <= 30:
            b = "16-30"
        elif br <= 100:
            b = "31-100"
        else:
            b = "no top-100 player"
        buckets[b].append(r)
    order = ["1-5 (elite)", "6-15", "16-30", "31-100", "no top-100 player"]
    for b in order:
        rows = buckets.get(b, [])
        if not rows:
            continue
        n = len(rows)
        avg_wins = sum(r["actual_wins"] for r in rows) / n
        avg_margin = sum(r["beat_margin"] for r in rows) / n
        overs = sum(1 for r in rows if r["result"] == "Over") / n * 100
        print(f"  {b:20s} n={n:3d}  avg_wins={avg_wins:5.2f}  "
              f"avg_beat_margin={avg_margin:+5.2f}  over%={overs:5.1f}")


if __name__ == "__main__":
    main()
