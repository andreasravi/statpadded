"""
Does an RB's team context -- preseason Vegas win total, and the preseason
QB tier -- explain any of the miss in the rushing-yards prop lines? Both
inputs are set in the summer, so year-X result vs year-X context is not
lookahead. RB counterpart of context_wr.py; rush-only yardage rows.

Inputs (all preseason / external):
  data/rb_prop_grades.csv                              graded results
  nfl/sources/win_totals/data/win_totals.csv           preseason win total
  nfl/sources/qb_starters/data/qb_starter_tiers.csv    primary starter tier

Writes data/rb_context_by_win_total.csv, data/rb_context_by_qb_tier.csv,
data/rb_context_summary.json and prints a summary + OLS.
Run: python3 projects/prop-accuracy/scripts/context_rb.py
"""
import csv
import json
import os
import statistics as st

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")

GRADES = os.path.join(DATA, "rb_prop_grades.csv")
WIN_TOTALS = os.path.join(REPO_ROOT, "nfl/sources/win_totals/data/win_totals.csv")
QB_TIERS = os.path.join(REPO_ROOT, "nfl/sources/qb_starters/data/qb_starter_tiers.csv")


def load():
    wt = {(int(r["year"]), r["team"]): float(r["win_total_line"])
          for r in csv.DictReader(open(WIN_TOTALS))}
    qb = {(int(r["year"]), r["team"]): int(r["tier"])
          for r in csv.DictReader(open(QB_TIERS)) if r["tier"]}
    rows = []
    for r in csv.DictReader(open(GRADES)):
        if r["yards_kind"] != "rush" or not r["yards_diff"]:
            continue
        key = (int(r["year"]), r.get("team_start") or r["team"])
        r["year"] = key[0]
        r["yards_line"] = float(r["yards_line"])
        r["yards_diff"] = float(r["yards_diff"])
        r["games"] = int(r["games"]) if r["games"] != "" else None
        r["healthy"] = r["games"] is not None and r["games"] >= 14
        r["win_total"] = wt.get(key)
        r["qb_tier"] = qb.get(key)
        rows.append(r)
    return rows


def pct(o, n):
    return round(100 * o / n) if n else ""


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else ""


def _bucket(rows, keyfn, labels):
    out = []
    for lab in labels:
        b = [r for r in rows if keyfn(r) == lab]
        h = [r for r in b if r["healthy"]]
        out.append({
            "bucket": lab, "n": len(b),
            "avg_line": round(st.mean([r["yards_line"] for r in b]), 0) if b else "",
            "over_pct_all": pct(sum(1 for r in b if r["yards_diff"] > 0), len(b)),
            "mean_diff_all": round(st.mean([r["yards_diff"] for r in b]), 0) if b else "",
            "n_healthy": len(h),
            "over_pct_healthy": pct(sum(1 for r in h if r["yards_diff"] > 0), len(h)),
            "median_diff_healthy": med([r["yards_diff"] for r in h]),
        })
    return out


def _wt_label(r):
    w = r["win_total"]
    if w is None:
        return None
    if w < 7:
        return "<7 (bad)"
    if w < 8.5:
        return "7-8"
    if w < 9.5:
        return "8.5-9"
    if w < 10.5:
        return "9.5-10"
    return "10.5+ (contender)"


def _ols(rows, cols):
    """tiny multivariate OLS, no numpy: returns {col: coef}, r2."""
    ys = [r["yards_diff"] for r in rows]
    X = [[1.0] + [float(r[c]) for c in cols] for r in rows]
    n, k = len(X), len(cols) + 1
    XtX = [[sum(X[i][a] * X[i][b] for i in range(n)) for b in range(k)] for a in range(k)]
    Xty = [sum(X[i][a] * ys[i] for i in range(n)) for a in range(k)]
    # Gauss-Jordan
    M = [row[:] + [Xty[i]] for i, row in enumerate(XtX)]
    for i in range(k):
        p = M[i][i] or 1e-9
        M[i] = [v / p for v in M[i]]
        for j in range(k):
            if j != i:
                f = M[j][i]
                M[j] = [a - f * b for a, b in zip(M[j], M[i])]
    beta = [M[i][k] for i in range(k)]
    yhat = [sum(beta[a] * X[i][a] for a in range(k)) for i in range(n)]
    ybar = st.mean(ys)
    ss_res = sum((ys[i] - yhat[i]) ** 2 for i in range(n))
    ss_tot = sum((y - ybar) ** 2 for y in ys)
    return dict(zip(["intercept"] + cols, beta)), 1 - ss_res / ss_tot


def main():
    rows = load()
    wt_rows = [r for r in rows if r["win_total"] is not None]
    qb_rows = [r for r in rows if r["qb_tier"] is not None]

    wt_view = _bucket(wt_rows, _wt_label,
                      ["<7 (bad)", "7-8", "8.5-9", "9.5-10", "10.5+ (contender)"])
    qb_view = _bucket(qb_rows, lambda r: r["qb_tier"], [1, 2, 3, 4, 5])

    fn = ["bucket", "n", "avg_line", "over_pct_all", "mean_diff_all",
          "n_healthy", "over_pct_healthy", "median_diff_healthy"]
    for name, view in (("rb_context_by_win_total.csv", wt_view),
                       ("rb_context_by_qb_tier.csv", qb_view)):
        with open(os.path.join(DATA, name), "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=fn)
            w.writeheader()
            w.writerows(view)

    ols_rows = [r for r in rows if r["win_total"] is not None and r["qb_tier"] is not None]
    coef, r2 = _ols(ols_rows, ["yards_line", "win_total", "qb_tier"])

    summary = {
        "n_graded_rush": len(rows),
        "n_with_win_total": len(wt_rows),
        "n_with_qb_tier": len(qb_rows),
        "ols_n": len(ols_rows), "ols_r2": round(r2, 3),
        "ols_coef": {k: round(v, 1) for k, v in coef.items()},
    }
    with open(os.path.join(DATA, "rb_context_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)

    print("Rushing-yards Δ vs line, by preseason team win total (rush-only):")
    print(f"  {'bucket':<20} {'n':>3} {'over%':>6} {'meanΔ':>7} {'hlt over%':>10} {'hlt medΔ':>9}")
    for v in wt_view:
        print(f"  {v['bucket']:<20} {v['n']:>3} {str(v['over_pct_all'])+'%':>6} "
              f"{str(v['mean_diff_all']):>7} {str(v['over_pct_healthy'])+'%':>10} "
              f"{str(v['median_diff_healthy']):>9}")
    print("\nby preseason QB tier (1 elite ... 5 replacement):")
    for v in qb_view:
        print(f"  tier {v['bucket']}   n={v['n']:>3}  over {str(v['over_pct_all'])+'%':>5}  "
              f"meanΔ {str(v['mean_diff_all']):>6}  (healthy over {v['over_pct_healthy']}%)")
    print(f"\nOLS  yards_diff ~ yards_line + win_total + qb_tier   "
          f"(n={len(ols_rows)}, R²={r2:.3f})")
    for k, v in coef.items():
        print(f"   {k:<12} {v:+.1f}")
    print(f"\nwrote 3 context files -> {os.path.relpath(DATA, REPO_ROOT)}/ (rb_context_*)")


if __name__ == "__main__":
    main()
