"""
Analysis on top of data/wr_prop_grades.csv:

  1. Season-by-season O/U hit rate (yards / receptions / TDs)
  2. Hit rate bucketed by the SIZE of the line, all vs healthy (>=14 G)
  3. Year-over-year: bucket a receiver's result vs his line, then look at
     his result the NEXT year (mean reversion + how the book moves the line)

Writes one CSV per view to data/ and prints a summary.
Run: python3 projects/prop-accuracy/scripts/analyze_wr.py
"""
import csv
import os
import re
import statistics as st

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))
GRADES = os.path.join(PROJECT, "data", "wr_prop_grades.csv")
DATA = os.path.join(PROJECT, "data")


def load():
    rows = []
    with open(GRADES) as f:
        for r in csv.DictReader(f):
            for k in ("yards_line", "yards_diff", "rec_line", "rec_diff", "td_line", "td_diff"):
                r[k] = float(r[k]) if r[k] not in ("", None) else None
            r["year"] = int(r["year"])
            r["games"] = int(r["games"]) if r["games"] else None
            r["healthy"] = r["games"] is not None and r["games"] >= 14
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


# ---------------------------------------------------------------- 1. by season
def by_season(rows):
    out = []
    for y in sorted({r["year"] for r in rows}):
        s = [r for r in rows if r["year"] == y]
        rec = {"year": y, "n": len(s)}
        for stat in ("yards", "rec", "td"):
            g = [r for r in s if r[f"{stat}_diff"] is not None]
            o = sum(1 for r in g if r[f"{stat}_diff"] > 0)
            rec[f"{stat}_over"] = o
            rec[f"{stat}_graded"] = len(g)
            rec[f"{stat}_over_pct"] = pct(o, len(g))
        out.append(rec)
    _write("hit_rate_by_season.csv",
           ["year", "n", "yards_over", "yards_graded", "yards_over_pct",
            "rec_over", "rec_graded", "rec_over_pct",
            "td_over", "td_graded", "td_over_pct"], out)
    return out


# ------------------------------------------------------------- 2. by line size
TIERS = {
    "yards": ([700, 850, 1000, 1200], ["<700", "700-850", "850-1000", "1000-1200", "1200+"]),
    "rec":   ([55, 65, 75, 85], ["<=55", "56-65", "66-75", "76-85", "86+"]),
    "td":    ([4.5, 5.5, 6.5, 7.5], ["<=4.5", "5-5.5", "6-6.5", "7-7.5", "8+"]),
}


def _bucket(v, edges):
    for i, e in enumerate(edges):
        if v <= e:
            return i
    return len(edges)


def by_line_size(rows):
    for stat, (edges, labels) in TIERS.items():
        pop = [r for r in rows if r[f"{stat}_line"] is not None]
        out = []
        for i, lab in enumerate(labels):
            b = [r for r in pop if _bucket(r[f"{stat}_line"], edges) == i]
            h = [r for r in b if r["healthy"]]
            out.append({
                "tier": lab, "n": len(b),
                "over_pct_all": pct(sum(1 for r in b if r[f"{stat}_diff"] > 0), len(b)),
                "n_healthy": len(h),
                "over_pct_healthy": pct(sum(1 for r in h if r[f"{stat}_diff"] > 0), len(h)),
                "median_diff_healthy": med([r[f"{stat}_diff"] for r in h]),
                "mean_abs_miss": round(st.mean([abs(r[f"{stat}_diff"]) for r in b]), 1) if b else "",
            })
        _write(f"hit_rate_by_{stat}_line.csv",
               ["tier", "n", "over_pct_all", "n_healthy", "over_pct_healthy",
                "median_diff_healthy", "mean_abs_miss"], out)
        yield stat, out


# ------------------------------------------------------- 3. year-over-year pairs
def _norm(s):
    s = s.lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def yoy(rows):
    idx = {(_norm(r["player"]), r["year"]): r for r in rows if r["yards_diff"] is not None}
    pairs = []
    for (key, yr), a in idx.items():
        b = idx.get((key, yr + 1))
        if not b:
            continue
        pairs.append({
            "player": a["player"], "year_a": yr,
            "line_a": a["yards_line"], "diff_a": a["yards_diff"], "games_a": a["games"],
            "line_b": b["yards_line"], "diff_b": b["yards_diff"], "games_b": b["games"],
            "line_move": round(b["yards_line"] - a["yards_line"], 1),
            "result_b": b["yards_result"],
        })
    _write("year_over_year_pairs.csv",
           ["player", "year_a", "line_a", "diff_a", "games_a",
            "line_b", "diff_b", "games_b", "line_move", "result_b"], pairs)

    edges = [-300, -150, -50, 50, 150, 300, 500]
    labels = ["<=-300", "-300..-150", "-150..-50", "-50..+50", "+50..+150",
              "+150..+300", "+300..+500", "+500+"]
    buckets = []
    for i, lab in enumerate(labels):
        b = [p for p in pairs if _bucket(p["diff_a"], edges) == i]
        h = [p for p in b if p["games_b"] and p["games_b"] >= 14]
        buckets.append({
            "year_a_result": lab, "n": len(b),
            "next_over_pct": pct(sum(1 for p in b if p["result_b"] == "over"), len(b)),
            "next_median_diff": med([p["diff_b"] for p in b]),
            "book_line_move": round(st.mean([p["line_move"] for p in b]), 0) if b else "",
            "n_healthy_next": len(h),
            "next_over_pct_healthy": pct(sum(1 for p in h if p["result_b"] == "over"), len(h)),
        })
    _write("year_over_year_reversion.csv",
           ["year_a_result", "n", "next_over_pct", "next_median_diff",
            "book_line_move", "n_healthy_next", "next_over_pct_healthy"], buckets)
    return pairs, buckets


def main():
    rows = load()
    seasons = by_season(rows)
    tiers = dict(by_line_size(rows))
    pairs, buckets = yoy(rows)

    print(f"{len(rows)} graded receiver-seasons "
          f"({sorted({r['year'] for r in rows})[0]}-{sorted({r['year'] for r in rows})[-1]})\n")

    print("O/U cleared by season (receiving yards):")
    for s in seasons:
        print(f"  {s['year']}: {s['yards_over']}/{s['yards_graded']} ({s['yards_over_pct']}%)")

    print("\nReceiving-yards O/U by size of the line:")
    print(f"  {'tier':<11} {'n':>3} {'all':>5} {'healthy':>8} {'med Δ (hlt)':>12}")
    for t in tiers["yards"]:
        print(f"  {t['tier']:<11} {t['n']:>3} {str(t['over_pct_all'])+'%':>5} "
              f"{str(t['over_pct_healthy'])+'%':>8} {str(t['median_diff_healthy']):>12}")

    print("\nYear-over-year: this year's result -> next year's result:")
    print(f"  {'bucket':<12} {'n':>3} {'next over':>9} {'next med Δ':>10} {'line move':>10}")
    for b in buckets:
        print(f"  {b['year_a_result']:<12} {b['n']:>3} {str(b['next_over_pct'])+'%':>9} "
              f"{str(b['next_median_diff']):>10} {str(b['book_line_move']):>10}")

    da = [p["diff_a"] for p in pairs]
    db = [p["diff_b"] for p in pairs]
    n = len(pairs)
    ma, mb = st.mean(da), st.mean(db)
    cov = sum((x - ma) * (y - mb) for x, y in zip(da, db)) / n
    corr = cov / (st.pstdev(da) * st.pstdev(db))
    print(f"\ncorr(year-A diff, year-B diff) = {corr:+.2f}  (n={n} pairs)")
    print(f"\nwrote 6 view CSVs -> {os.path.relpath(DATA, REPO_ROOT)}/")


if __name__ == "__main__":
    main()
