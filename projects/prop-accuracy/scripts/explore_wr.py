"""
Deeper exploratory pass on the WR prop grades -- the distribution work, not
just the hit-rate tables in analyze_wr.py. Four questions:

  A. Shape of (actual - line): how fat is the under tail, how often within
     a coin-flip of the number, biggest blowups either way.
  B. Conditional on the line size: how often under, and -- when a receiver
     DOES beat -- by how much (vs how much he falls short when he misses).
  C. The line vs the player's PREVIOUS season: does the book just chase
     last year's box score, and does a bullish vs bearish re-rate predict
     the result? (prior-year actual from receiving_stats, which has 2021.)
  D. The biggest single misses, with health / trade / QB context.

Inputs (all already in the repo):
  data/wr_prop_grades.csv                              graded lines
  nfl/sources/receiving_stats/data/receiving_stats.csv prior-season actuals

Writes data/wr_miss_distribution.csv, data/wr_beat_magnitude_by_line.csv,
data/wr_line_vs_prior_year.csv, data/wr_explore_summary.json (embedded in
settle-sheet.html) and prints the full summary.
Run: python3 projects/prop-accuracy/scripts/explore_wr.py
"""
import csv
import json
import os
import re
import statistics as st

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")
GRADES = os.path.join(DATA, "wr_prop_grades.csv")
RECV = os.path.join(REPO_ROOT, "nfl/sources/receiving_stats/data/receiving_stats.csv")

METRICS = ("yards", "rec", "td")


def _norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_grades():
    rows = []
    for r in csv.DictReader(open(GRADES)):
        for k in ("yards_line", "yards_actual", "yards_diff", "rec_line", "rec_actual",
                  "rec_diff", "td_line", "td_actual", "td_diff"):
            r[k] = float(r[k]) if r[k] not in ("", None) else None
        r["year"] = int(r["year"])
        r["games"] = int(r["games"]) if r["games"] else None
        r["healthy"] = r["games"] is not None and r["games"] >= 14
        rows.append(r)
    return rows


def load_prior():
    """(norm_name, year) -> receiving row, every WR-season 2021+."""
    idx = {}
    for r in csv.DictReader(open(RECV)):
        for k in ("games", "targets", "receptions", "receiving_yards", "receiving_tds"):
            r[k] = int(r[k]) if r[k] not in ("", None) else 0
        idx[(_norm(r["player"]), int(r["year"]))] = r
    return idx


def pct(a, b):
    return round(100 * a / b) if b else None


def q(xs, p):
    xs = sorted(xs)
    if not xs:
        return None
    i = (len(xs) - 1) * p
    lo, hi = int(i), min(int(i) + 1, len(xs) - 1)
    return round(xs[lo] + (xs[hi] - xs[lo]) * (i - lo), 1)


def skew(xs):
    if len(xs) < 3:
        return None
    m, s = st.mean(xs), st.pstdev(xs)
    return round(sum(((x - m) / s) ** 3 for x in xs) / len(xs), 2) if s else None


# ------------------------------------------------ A. shape of the miss
# per metric: (blowup threshold, "coin-flip" band) in that stat's own units
SCALE = {"yards": (200, 50), "rec": (5, 3), "td": (1.5, 1)}


def _dist(name, diffs, near):
    diffs = [d for d in diffs if d is not None]
    n = len(diffs)
    row = {
        "group": name, "n": n,
        "mean": round(st.mean(diffs), 1), "median": round(st.median(diffs), 1),
        "stdev": round(st.pstdev(diffs), 1), "skew": skew(diffs),
        "p10": q(diffs, .10), "p25": q(diffs, .25), "p75": q(diffs, .75), "p90": q(diffs, .90),
        "min": round(min(diffs), 1), "max": round(max(diffs), 1),
        "pct_under": pct(sum(1 for d in diffs if d < 0), n),
        "pct_near_the_number": pct(sum(1 for d in diffs if abs(d) <= near), n),
    }
    return row


def shape(rows):
    print("=" * 74)
    print("A. SHAPE OF (actual - line)")
    print("=" * 74)
    out = []
    headline = {}
    for m in METRICS:
        wide, near = SCALE[m]
        alld = [r[f"{m}_diff"] for r in rows]
        hlt = [r[f"{m}_diff"] for r in rows if r["healthy"]]
        inj = [r[f"{m}_diff"] for r in rows if r["games"] is not None and not r["healthy"]]
        a = [d for d in alld if d is not None]
        if not a:
            continue
        for label, ds in (("all", alld), ("healthy >=14g", hlt), ("injured <14g", inj)):
            d = _dist(f"{m} / {label}", ds, near)
            if d["n"]:
                out.append(d)
        dd = _dist(m, alld, near)
        blow_u = pct(sum(1 for x in a if x <= -wide), len(a))
        blow_o = pct(sum(1 for x in a if x >= wide), len(a))
        headline[m] = {"n": len(a), "near": near, "wide": wide,
                       "pct_under": dd["pct_under"], "pct_near": dd["pct_near_the_number"],
                       "blowup_under_pct": blow_u, "blowup_over_pct": blow_o,
                       "mean": dd["mean"], "median": dd["median"], "skew": dd["skew"]}
        print(f"\n{m.upper()}  (n={len(a)})   under {dd['pct_under']}%"
              f"   within +-{near:g} of the number {dd['pct_near_the_number']}%"
              f"   blowup under(<= -{wide:g}) {blow_u}%   blowup over(>= +{wide:g}) {blow_o}%")
        print(f"   mean {dd['mean']:+g}   median {dd['median']:+g}   sd {dd['stdev']:g}   skew {dd['skew']}")
        print(f"   p10/p25/median/p75/p90 = {dd['p10']:+g} / {dd['p25']:+g} / "
              f"{dd['median']:+g} / {dd['p75']:+g} / {dd['p90']:+g}")
        # text histogram
        step = wide / 2
        edges = [(-4 + i) * step for i in range(9)]
        counts = [0] * (len(edges) + 1)
        for x in a:
            placed = False
            for i, e in enumerate(edges):
                if x < e:
                    counts[i] += 1
                    placed = True
                    break
            if not placed:
                counts[-1] += 1
        labels = ([f"< {edges[0]:+g}"]
                  + [f"{edges[i]:+g}..{edges[i+1]:+g}" for i in range(len(edges) - 1)]
                  + [f">= {edges[-1]:+g}"])
        for lab, c in zip(labels, counts):
            print(f"      {lab:>16} | {'#' * c} {c}")
    with open(os.path.join(DATA, "wr_miss_distribution.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    return headline


# --------------------------- B. how often under + beat magnitude by line
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


def beat_magnitude(rows):
    print("\n" + "=" * 74)
    print("B. HOW OFTEN UNDER, AND BY HOW MUCH THEY CLEAR WHEN THEY DO  (by line size)")
    print("=" * 74)
    out = []
    for m, (edges, labels) in TIERS.items():
        pop = [r for r in rows if r[f"{m}_line"] is not None and r[f"{m}_diff"] is not None]
        if not pop:
            continue
        print(f"\n{m.upper()}")
        print(f"  {'tier':<11} {'n':>3} {'under%':>7} {'hlt under%':>11} "
              f"{'beat by (med|over)':>19} {'miss by (med|under)':>20} {'ratio':>6}")
        for i, lab in enumerate(labels):
            b = [r for r in pop if _bucket(r[f"{m}_line"], edges) == i]
            if not b:
                continue
            h = [r for r in b if r["healthy"]]
            overs = [r[f"{m}_diff"] for r in b if r[f"{m}_diff"] > 0]
            unders = [r[f"{m}_diff"] for r in b if r[f"{m}_diff"] < 0]
            mo = round(st.median(overs), 1) if overs else None
            mu = round(st.median(unders), 1) if unders else None
            ratio = round(abs(mo / mu), 2) if mo and mu else None
            rec = {
                "metric": m, "tier": lab, "n": len(b),
                "under_pct": pct(len(unders), len(b)),
                "healthy_n": len(h),
                "healthy_under_pct": pct(sum(1 for r in h if r[f"{m}_diff"] < 0), len(h)),
                "median_beat_when_over": mo, "n_over": len(overs),
                "median_miss_when_under": mu, "n_under": len(unders),
                "beat_miss_ratio": ratio,
            }
            out.append(rec)
            print(f"  {lab:<11} {len(b):>3} {str(rec['under_pct'])+'%':>7} "
                  f"{str(rec['healthy_under_pct'])+'%':>11} "
                  f"{str(mo)+' (n='+str(len(overs))+')':>19} "
                  f"{str(mu)+' (n='+str(len(unders))+')':>20} {str(ratio):>6}")
    with open(os.path.join(DATA, "wr_beat_magnitude_by_line.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(out[0].keys()))
        w.writeheader()
        w.writerows(out)
    return out


# ------------------------------- C. the line vs last year's box score
def line_vs_prior(rows, prior):
    print("\n" + "=" * 74)
    print("C. THE LINE vs THE PLAYER'S PREVIOUS SEASON  (yards)")
    print("=" * 74)
    pairs = []
    for r in rows:
        if r["yards_line"] is None:
            continue
        p = prior.get((_norm(r["player"]), r["year"] - 1))
        if not p:
            continue
        pa = p["receiving_yards"]
        pairs.append({
            "year": r["year"], "player": r["player"],
            "prior_yards": pa, "prior_games": p["games"],
            "line": r["yards_line"], "line_minus_prior": round(r["yards_line"] - pa, 1),
            "actual": r["yards_actual"], "diff": r["yards_diff"],
            "result": r["yards_result"], "games": r["games"],
            "prior_injury": p["games"] < 14,
        })
    n = len(pairs)
    la = [pp["line"] for pp in pairs]
    pr = [pp["prior_yards"] for pp in pairs]
    di = [pp["diff"] for pp in pairs]
    mL, mP = st.mean(la), st.mean(pr)
    cov = sum((x - mL) * (y - mP) for x, y in zip(la, pr)) / n
    corr_lp = cov / (st.pstdev(la) * st.pstdev(pr))
    mD = st.mean(di)
    covD = sum((y - mP) * (x - mD) for y, x in zip(pr, di)) / n
    corr_pd = covD / (st.pstdev(pr) * st.pstdev(di))
    print(f"\n  n={n} receiver-seasons with a prior-year receiving line in the data")
    print(f"  corr(line, prior-year yards)      = {corr_lp:+.2f}   "
          f"(the book leans hard on last year's total)")
    print(f"  corr(prior-year yards, this Δ)    = {corr_pd:+.2f}   "
          f"(last year's raw total barely predicts the miss)")
    print(f"  mean line - prior actual          = {st.mean([pp['line_minus_prior'] for pp in pairs]):+.0f}")

    print("\n  Re-rate direction -- did the book set the line above or below last year?")
    print(f"  {'bucket':<26} {'n':>3} {'over%':>6} {'medΔ':>7} {'healthy over%':>14}")
    band = [("set >= 150 above last yr", lambda x: x >= 150),
            ("within +-150 of last yr", lambda x: -150 <= x < 150),
            ("cut >= 150 below last yr", lambda x: x < -150)]
    cview = []
    for lab, fn in band:
        b = [pp for pp in pairs if fn(pp["line_minus_prior"])]
        if not b:
            continue
        h = [pp for pp in b if pp["games"] and pp["games"] >= 14]
        rec = {"bucket": lab, "n": len(b),
               "over_pct": pct(sum(1 for pp in b if pp["result"] == "over"), len(b)),
               "median_diff": round(st.median([pp["diff"] for pp in b]), 1),
               "healthy_n": len(h),
               "healthy_over_pct": pct(sum(1 for pp in h if pp["result"] == "over"), len(h))}
        cview.append(rec)
        print(f"  {lab:<26} {len(b):>3} {str(rec['over_pct'])+'%':>6} "
              f"{rec['median_diff']:>+7g} {str(rec['healthy_over_pct'])+'%':>14}")

    print("\n  Coming off a prior-year injury (<14 g last season):")
    inj_view = []
    for lab, sub in (("prior injury (<14 g)", [p for p in pairs if p["prior_injury"]]),
                     ("prior full season", [p for p in pairs if not p["prior_injury"]])):
        o = sum(1 for pp in sub if pp["result"] == "over")
        h = [pp for pp in sub if pp["games"] and pp["games"] >= 14]
        oh = sum(1 for pp in h if pp["result"] == "over")
        rec = {"bucket": lab, "n": len(sub), "over_pct": pct(o, len(sub)),
               "healthy_n": len(h), "healthy_over_pct": pct(oh, len(h)),
               "median_diff": round(st.median([pp["diff"] for pp in sub]), 1)}
        inj_view.append(rec)
        print(f"    {lab:<22} n={len(sub):>3}  over {rec['over_pct']}%   "
              f"healthy over {rec['healthy_over_pct']}% (n={len(h)})   "
              f"median Δ {rec['median_diff']:+g}")

    with open(os.path.join(DATA, "wr_line_vs_prior_year.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(pairs[0].keys()))
        w.writeheader()
        w.writerows(sorted(pairs, key=lambda x: (x["year"], -x["line"])))
    return {"n": n, "corr_line_prior": round(corr_lp, 2), "corr_prior_diff": round(corr_pd, 2),
            "mean_line_minus_prior": round(st.mean([pp["line_minus_prior"] for pp in pairs])),
            "rerate": cview, "prior_injury": inj_view}


# ------------------------------------------- D. biggest single misses
def biggest(rows, prior, k=12):
    print("\n" + "=" * 74)
    print(f"D. THE {k} BIGGEST YARDS MISSES EACH WAY")
    print("=" * 74)
    g = [r for r in rows if r["yards_diff"] is not None]
    for lab, key in (("UNDER (line - actual, worst first)", lambda r: r["yards_diff"]),
                     ("OVER (actual - line, best first)", lambda r: -r["yards_diff"])):
        print(f"\n  {lab}")
        for r in sorted(g, key=key)[:k]:
            p = prior.get((_norm(r["player"]), r["year"] - 1))
            pnote = (f"prior {p['receiving_yards']}y/{p['games']}g" if p else "no prior yr")
            tr = " TRADED" if r["traded"] == "yes" else ""
            print(f"    {r['year']}  {r['player']:<22} line {r['yards_line']:>7g}  "
                  f"actual {r['yards_actual']:>5g}  Δ {r['yards_diff']:>+7g}  "
                  f"{r['games']:>2}g{tr:<8}  {pnote}")


def main():
    rows = load_grades()
    prior = load_prior()
    yrs = sorted({r["year"] for r in rows})
    print(f"{len(rows)} graded receiver-seasons, {yrs[0]}-{yrs[-1]}\n")
    headline = shape(rows)
    beat = beat_magnitude(rows)
    prior_view = line_vs_prior(rows, prior)
    biggest(rows, prior)

    summary = {
        "n_graded": len(rows), "years": [yrs[0], yrs[-1]],
        "miss_shape": headline,
        "beat_magnitude_by_line": beat,
        "line_vs_prior_year": prior_view,
    }
    with open(os.path.join(DATA, "wr_explore_summary.json"), "w") as f:
        json.dump(summary, f, indent=1)
    print(f"\nwrote wr_miss_distribution.csv, wr_beat_magnitude_by_line.csv, "
          f"wr_line_vs_prior_year.csv, wr_explore_summary.json -> "
          f"{os.path.relpath(DATA, REPO_ROOT)}/")


if __name__ == "__main__":
    main()
