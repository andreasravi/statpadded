"""
Does a WR's team context -- their QB's preseason tier and the team's
preseason Vegas win total -- explain any of the miss in the receiving
prop lines? Both inputs are set in the summer, before a down is played, so
joining year-X prop results to year-X preseason context is not lookahead.

Inputs (all preseason / external):
  projects/wr-prop-accuracy/data/wr_prop_grades.csv   graded prop results
  nfl/sources/win_totals/data/win_totals.csv          preseason win-total line
  nfl/sources/qb_starters/data/qb_starter_tiers.csv   primary starter + Sando tier

Caveat: qb_starter_tiers picks the QB with the most starts that season, so
a team whose projected starter got hurt Week 1 may show the backup. The
tier value itself is always the preseason number. ~90% of team-seasons the
projected and actual QB1 are the same.

Writes data/context_by_qb_tier.csv, data/context_by_win_total.csv,
data/context_grid.csv and prints a summary + an OLS.
Run: python3 projects/wr-prop-accuracy/scripts/context.py
"""
import csv
import os
import statistics as st

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")

GRADES = os.path.join(DATA, "wr_prop_grades.csv")
WIN_TOTALS = os.path.join(REPO_ROOT, "nfl/sources/win_totals/data/win_totals.csv")
QB_TIERS = os.path.join(REPO_ROOT, "nfl/sources/qb_starters/data/qb_starter_tiers.csv")


def load():
    wt = {}
    for r in csv.DictReader(open(WIN_TOTALS)):
        wt[(int(r["year"]), r["team"])] = float(r["win_total_line"])
    qb = {}
    for r in csv.DictReader(open(QB_TIERS)):
        if r["tier"]:
            qb[(int(r["year"]), r["team"])] = (int(r["tier"]), r["qb_name"])

    rows = []
    for r in csv.DictReader(open(GRADES)):
        y = int(r["year"])
        # the prop line was set preseason, so use the team the receiver
        # STARTED the season with, not recent_team (matters for the ~3
        # graded seasons with a mid-season trade -- Adams/Cooper/Johnson '24)
        team = r.get("team_start") or r["team"]
        key = (y, team)
        if key not in wt:
            continue
        for k in ("yards_diff", "rec_diff", "yards_line", "rec_line"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        r["year"] = y
        r["games"] = int(r["games"]) if r["games"] else None
        r["healthy"] = r["games"] is not None and r["games"] >= 14
        r["win_total"] = wt[key]
        r["qb_tier"], r["qb_name"] = qb.get(key, (None, ""))
        rows.append(r)
    return rows


def _write(name, fieldnames, rows):
    with open(os.path.join(DATA, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)


def pct(o, n):
    return round(100 * o / n) if n else ""


def med(xs):
    xs = [x for x in xs if x is not None]
    return round(st.median(xs), 1) if xs else ""


def _bucketed(rows, stat, keyfn, labels):
    out = []
    for lab in labels:
        b = [r for r in rows if r[f"{stat}_diff"] is not None and keyfn(r) == lab]
        h = [r for r in b if r["healthy"]]
        out.append({
            "bucket": lab, "n": len(b),
            "avg_line": round(st.mean([r[f"{stat}_line"] for r in b]), 0) if b else "",
            "over_pct_all": pct(sum(1 for r in b if r[f"{stat}_diff"] > 0), len(b)),
            "mean_diff_all": round(st.mean([r[f"{stat}_diff"] for r in b]), 0) if b else "",
            "n_healthy": len(h),
            "over_pct_healthy": pct(sum(1 for r in h if r[f"{stat}_diff"] > 0), len(h)),
            "median_diff_healthy": med([r[f"{stat}_diff"] for r in h]),
        })
    return out


def _wt_label(r):
    w = r["win_total"]
    if w < 7:
        return "<7 (bad)"
    if w < 8.5:
        return "7-8 (below .500)"
    if w < 9.5:
        return "8.5-9 (around .500)"
    if w < 10.5:
        return "9.5-10 (good)"
    return "10.5+ (contender)"


WT_LABELS = ["<7 (bad)", "7-8 (below .500)", "8.5-9 (around .500)", "9.5-10 (good)", "10.5+ (contender)"]
TIER_LABELS = ["1 (elite)", "2", "3", "4-5 (weak)", "untiered"]


def _tier_label(r):
    t = r["qb_tier"]
    if t is None:
        return "untiered"
    if t >= 4:
        return "4-5 (weak)"
    return TIER_LABELS[t - 1]


def main():
    rows = load()
    n = len(rows)
    tiered = sum(1 for r in rows if r["qb_tier"] is not None)
    print(f"{n} WR-seasons with a team win-total line (2022-2025); "
          f"{tiered} also have a primary-QB tier "
          f"({n - tiered} on teams the qb_starter_tiers source doesn't cover that year)\n")

    for stat in ("yards", "rec"):
        by_tier = _bucketed(rows, stat, _tier_label, TIER_LABELS)
        by_wt = _bucketed(rows, stat, _wt_label, WT_LABELS)
        _write(f"context_{stat}_by_qb_tier.csv",
               ["bucket", "n", "avg_line", "over_pct_all", "mean_diff_all",
                "n_healthy", "over_pct_healthy", "median_diff_healthy"], by_tier)
        _write(f"context_{stat}_by_win_total.csv",
               ["bucket", "n", "avg_line", "over_pct_all", "mean_diff_all",
                "n_healthy", "over_pct_healthy", "median_diff_healthy"], by_wt)

        name = "Receiving yards" if stat == "yards" else "Receptions"
        print(f"=== {name} O/U by QB tier (preseason) ===")
        print(f"  {'tier':<10} {'n':>3} {'avg line':>9} {'over% all':>10} {'mean Δ':>8} {'over% hlt':>10} {'med Δ hlt':>10}")
        for b in by_tier:
            print(f"  {b['bucket']:<10} {b['n']:>3} {b['avg_line']:>9} "
                  f"{str(b['over_pct_all'])+'%':>10} {str(b['mean_diff_all']):>8} "
                  f"{str(b['over_pct_healthy'])+'%':>10} {str(b['median_diff_healthy']):>10}")
        print(f"\n=== {name} O/U by team preseason win total ===")
        print(f"  {'win total':<20} {'n':>3} {'avg line':>9} {'over% all':>10} {'mean Δ':>8} {'over% hlt':>10} {'med Δ hlt':>10}")
        for b in by_wt:
            print(f"  {b['bucket']:<20} {b['n']:>3} {b['avg_line']:>9} "
                  f"{str(b['over_pct_all'])+'%':>10} {str(b['mean_diff_all']):>8} "
                  f"{str(b['over_pct_healthy'])+'%':>10} {str(b['median_diff_healthy']):>10}")
        print()

    # 2x2: QB caliber x team caliber, yards (tiered rows only)
    tr = [r for r in rows if r["qb_tier"] is not None and r["yards_diff"] is not None]
    print("=== Receiving-yards mean Δ vs line: QB caliber x team caliber (tiered QBs) ===")
    print(f"  {'':<16} {'bad team (<8.5)':>20} {'good team (>=9.5)':>20}")
    for qlab, qtest in (("elite QB (t1-2)", lambda r: r["qb_tier"] <= 2),
                        ("mid QB (t3)", lambda r: r["qb_tier"] == 3),
                        ("weak QB (t4-5)", lambda r: r["qb_tier"] >= 4)):
        cells = []
        for ttest in (lambda r: r["win_total"] < 8.5, lambda r: r["win_total"] >= 9.5):
            b = [r for r in tr if qtest(r) and ttest(r)]
            o = sum(1 for r in b if r["yards_diff"] > 0)
            cells.append(f"{round(st.mean([r['yards_diff'] for r in b])):+d} (n={len(b)}, {pct(o,len(b))}%)" if b else "-")
        print(f"  {qlab:<16} {cells[0]:>20} {cells[1]:>20}")

    # OLS: does QB tier / win total add anything beyond the line size itself?
    try:
        import numpy as np
        import statsmodels.api as sm
        for stat in ("yards", "rec"):
            d = [r for r in rows if r[f"{stat}_diff"] is not None and r["qb_tier"] is not None]
            X = np.array([[r[f"{stat}_line"], r["qb_tier"], r["win_total"]] for r in d], float)
            X = sm.add_constant(X)
            y = np.array([r[f"{stat}_diff"] for r in d], float)
            res = sm.OLS(y, X).fit()
            nm = "yards" if stat == "yards" else "rec"
            print(f"\n=== OLS: {nm}_diff ~ {nm}_line + qb_tier + win_total  (n={len(d)}) ===")
            for label, coef, p in zip(["const", f"{nm}_line", "qb_tier", "win_total"],
                                      res.params, res.pvalues):
                print(f"  {label:<12} coef {coef:+9.3f}   p {p:.3f}")
            print(f"  R^2 {res.rsquared:.3f}")
    except ImportError:
        print("\n(statsmodels not available -- skipping OLS)")

    # ---- 2026 overlay: each grid WR's team win total + preseason QB tier ----
    import json
    kal = {r["team"]: float(r["implied_line"])
           for r in csv.DictReader(open(os.path.join(
               REPO_ROOT, "nfl/sources/kalshi_win_totals/data/kalshi_win_totals.csv")))}
    NICK = {"49ers": "SF", "Bears": "CHI", "Bengals": "CIN", "Bills": "BUF",
            "Broncos": "DEN", "Browns": "CLE", "Buccaneers": "TB", "Cardinals": "ARI",
            "Chargers": "LAC", "Chiefs": "KC", "Colts": "IND", "Commanders": "WAS",
            "Cowboys": "DAL", "Dolphins": "MIA", "Eagles": "PHI", "Falcons": "ATL",
            "Giants": "NYG", "Jaguars": "JAX", "Jets": "NYJ", "Lions": "DET",
            "Packers": "GB", "Panthers": "CAR", "Patriots": "NE", "Raiders": "LV",
            "Rams": "LAR", "Ravens": "BAL", "Saints": "NO", "Seahawks": "SEA",
            "Steelers": "PIT", "Texans": "HOU", "Titans": "TEN", "Vikings": "MIN"}
    # projected Week-1 starter tier per team (2026), from The Athletic's 2026 survey;
    # where the source lists a starter + backup, keep the projected starter.
    STARTER_2026 = {
        "ATL": "Michael Penix Jr.", "CLE": "Deshaun Watson", "MIN": "J.J. McCarthy",
    }
    qb26 = {}
    qb_tiers_csv = os.path.join(REPO_ROOT, "nfl/sources/qb_tiers/data/qb_tiers.csv")
    for r in csv.DictReader(open(qb_tiers_csv)):
        if r["season"] != "2026":
            continue
        ab = NICK.get(r["team"])
        if not ab:
            continue
        if ab in STARTER_2026 and r["qb_name"] != STARTER_2026[ab]:
            continue
        qb26.setdefault(ab, (r["tier"], r["qb_name"]))

    grid26 = []
    for r in csv.DictReader(open(os.path.join(
            REPO_ROOT, "nfl/sources/wr_prop_totals/data/wr_prop_totals.csv"))):
        if r["year"] != "2026":
            continue
        grid26.append({"player": r["player"], "yards_line": r["yards_line"],
                       "rec_line": r["rec_line"], "td_line": r["td_line"]})

    summary = {
        "n_qb_tier": tiered, "n_win_total": n,
        "yards_by_qb_tier": _bucketed(rows, "yards", _tier_label, TIER_LABELS),
        "yards_by_win_total": _bucketed(rows, "yards", _wt_label, WT_LABELS),
        "rec_by_qb_tier": _bucketed(rows, "rec", _tier_label, TIER_LABELS),
        "rec_by_win_total": _bucketed(rows, "rec", _wt_label, WT_LABELS),
        "qb26": qb26, "wt26": {k: round(v, 1) for k, v in kal.items()},
    }
    with open(os.path.join(DATA, "context_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)

    print(f"\nwrote context view CSVs + context_summary.json -> {os.path.relpath(DATA, REPO_ROOT)}/")


if __name__ == "__main__":
    main()
