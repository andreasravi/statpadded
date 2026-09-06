"""
The "every observation in one place" table, computed exactly and
consistently -- every situation with its over rate, sample size n, and a
z-statistic testing the over rate against a coin flip (50%).

  z = (p_hat - 0.5) / sqrt(0.25 / n)      |z| > 1.96  ~  significant at 5%

This is the actionable test: is this line beatable, or is 50/50 fair?
(Not a test against the base rate -- that would ask "does the situation
matter", which is a different question.)

Writes data/cheatsheet.csv and prints the WR + RB tables.
Run: python3 projects/prop-accuracy/scripts/cheatsheet.py
"""
import csv
import math
import os
import re

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")

QBW = os.path.join(ROOT, "nfl/sources/qb_starters/data/qb_starter_tiers.csv")
WT = os.path.join(ROOT, "nfl/sources/win_totals/data/win_totals.csv")
RECV = os.path.join(ROOT, "nfl/sources/receiving_stats/data/receiving_stats.csv")
RUSH = os.path.join(ROOT, "nfl/sources/rushing_stats/data/rushing_stats.csv")
UD = os.path.join(ROOT, "nfl/sources/underdog_adp/data/underdog_adp.csv")


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


QB_TIER = {(int(r["year"]), r["team"]): int(r["tier"])
           for r in csv.DictReader(open(QBW)) if r["tier"]}
WIN_TOT = {(int(r["year"]), r["team"]): float(r["win_total_line"])
           for r in csv.DictReader(open(WT))}
PRECV = {(norm(r["player"]), int(r["year"])): {"y": int(r["receiving_yards"] or 0), "g": int(r["games"] or 0)}
         for r in csv.DictReader(open(RECV))}
PRUSH = {(norm(r["player"]), int(r["year"])): {"y": int(r["rushing_yards"] or 0), "g": int(r["games"] or 0)}
         for r in csv.DictReader(open(RUSH))}
_rb_adp = {}
for r in csv.DictReader(open(UD)):
    if r["pos"] == "RB" and r["adp"]:
        _rb_adp.setdefault(int(r["year"]), []).append((norm(r["player"]), float(r["adp"])))
RB_RANK = {y: {n: i for i, (n, _) in enumerate(sorted(v, key=lambda t: t[1]), 1)}
           for y, v in _rb_adp.items()}


def load(fn, prior, rush_only=False):
    rows = []
    for r in csv.DictReader(open(os.path.join(DATA, fn))):
        if rush_only and r.get("yards_kind") != "rush":
            continue
        y = int(r["year"]); tm = r["team_start"] or r["team"]
        g = int(r["games"] or 0)
        p = prior.get((norm(r["player"]), y - 1))
        d = {
            "year": y, "g": g, "healthy": g >= 14,
            "qb_tier": QB_TIER.get((y, tm)), "win_total": WIN_TOT.get((y, tm)),
            "prior_g": p["g"] if p else None, "prior_y": p["y"] if p else None,
            "rank": RB_RANK.get(y, {}).get(norm(r["player"])),
        }
        for m in ("yards", "rec", "td"):
            res = r.get(f"{m}_result")
            d[m] = 1 if res == "over" else (0 if res == "under" else None)
            d[f"{m}_line"] = float(r[f"{m}_line"]) if r.get(f"{m}_line") else None
        rows.append(d)
    return rows


def stat(sub, metric):
    v = [r[metric] for r in sub if r[metric] is not None]
    n = len(v)
    if n == 0:
        return None
    p = sum(v) / n
    z = (p - 0.5) / math.sqrt(0.25 / n) if n else 0.0
    return {"n": n, "over_pct": round(100 * p), "z": round(z, 1)}


def sig(z):
    az = abs(z)
    return "***" if az >= 2.58 else "**" if az >= 1.96 else "*" if az >= 1.64 else ""


SITU = {
    "WR": [
        ("Availability (yards)", None),
        ("finished < 14 games", lambda r: r["g"] < 14, "yards"),
        ("finished >= 14 games", lambda r: r["healthy"], "yards"),
        ("Yards line size (all)", None),
        ("700-850 line", lambda r: r["yards_line"] and 700 < r["yards_line"] <= 850, "yards"),
        ("850-1000 line", lambda r: r["yards_line"] and 850 < r["yards_line"] <= 1000, "yards"),
        ("1000-1200 line (dead zone)", lambda r: r["yards_line"] and 1000 < r["yards_line"] <= 1200, "yards"),
        ("1200+ line", lambda r: r["yards_line"] and r["yards_line"] > 1200, "yards"),
        ("Yards line size (healthy only)", None),
        ("700-850, healthy", lambda r: r["healthy"] and r["yards_line"] and 700 < r["yards_line"] <= 850, "yards"),
        ("850-1000, healthy", lambda r: r["healthy"] and r["yards_line"] and 850 < r["yards_line"] <= 1000, "yards"),
        ("1000-1200, healthy", lambda r: r["healthy"] and r["yards_line"] and 1000 < r["yards_line"] <= 1200, "yards"),
        ("1200+, healthy", lambda r: r["healthy"] and r["yards_line"] and r["yards_line"] > 1200, "yards"),
        ("Reception line (all)", None),
        ("<= 55 rec line", lambda r: r["rec_line"] and r["rec_line"] <= 55, "rec"),
        ("56-65 rec line", lambda r: r["rec_line"] and 55 < r["rec_line"] <= 65, "rec"),
        ("66-75 rec line", lambda r: r["rec_line"] and 65 < r["rec_line"] <= 75, "rec"),
        ("76-85 rec line", lambda r: r["rec_line"] and 75 < r["rec_line"] <= 85, "rec"),
        ("86+ rec line", lambda r: r["rec_line"] and r["rec_line"] > 85, "rec"),
        ("TD line (all)", None),
        ("<= 7.5 TD line", lambda r: r["td_line"] and r["td_line"] <= 7.5, "td"),
        ("8+ TD line", lambda r: r["td_line"] and r["td_line"] >= 8, "td"),
        ("QB & team (yards)", None),
        ("weak/unproven QB (tier 4-5)", lambda r: r["qb_tier"] and r["qb_tier"] >= 4, "yards"),
        ("weak QB, healthy", lambda r: r["healthy"] and r["qb_tier"] and r["qb_tier"] >= 4, "yards"),
        ("elite/good QB (tier 1-2)", lambda r: r["qb_tier"] and r["qb_tier"] <= 2, "yards"),
        ("team win total 7-8", lambda r: r["win_total"] and 7 <= r["win_total"] <= 8, "yards"),
        ("tank team (< 7 wins)", lambda r: r["win_total"] and r["win_total"] < 7, "yards"),
        ("Prior year (yards)", None),
        ("line set >= 150 over last yr", lambda r: r["prior_y"] is not None and r["yards_line"] - r["prior_y"] >= 150, "yards"),
        ("line cut >= 150 below last yr", lambda r: r["prior_y"] is not None and r["yards_line"] - r["prior_y"] <= -150, "yards"),
        ("line cut >= 150, healthy", lambda r: r["healthy"] and r["prior_y"] is not None and r["yards_line"] - r["prior_y"] <= -150, "yards"),
        ("off an injury year (< 14 g)", lambda r: r["prior_g"] is not None and r["prior_g"] < 14, "yards"),
        ("Vs last year's result (yards)", None),
        ("beat by 300+ last yr", lambda r: r["prior_y"] is not None and r["prior_g"] and r["prior_g"] >= 14 and False, "yards"),  # placeholder
    ],
}

# year-over-year needs same-player pairs -> compute separately
def yoy_rows(rows):
    idx = {}
    for r in rows:
        pass
    return []


def run(pos, rows):
    print(f"\n{'='*74}\n{pos}   (z tests the over rate vs 50%; * p<.10  ** p<.05  *** p<.01)\n{'='*74}")
    print(f"  {'situation':<34} {'over%':>6} {'n':>4} {'z':>6}")
    out = []
    for item in SITU[pos]:
        if item[1] is None:
            print(f"  -- {item[0]} --")
            continue
        label, fn, metric = item
        s = stat([r for r in rows if _safe(fn, r)], metric)
        if not s:
            continue
        print(f"  {label:<34} {str(s['over_pct'])+'%':>6} {s['n']:>4} {s['z']:>+6.1f} {sig(s['z'])}")
        out.append({"pos": pos, "situation": label, "metric": metric, **s, "sig": sig(s["z"])})
    return out


def _safe(fn, r):
    try:
        return bool(fn(r))
    except (TypeError, KeyError):
        return False


# ---- year-over-year: needs the pairs from analyze output ----
def yoy_block(pos, pairs_csv):
    rows = list(csv.DictReader(open(os.path.join(DATA, pairs_csv))))
    for r in rows:
        r["diff_a"] = float(r["diff_a"]); r["diff_b"] = float(r["diff_b"])
        r["over_b"] = 1 if r["result_b"] == "over" else 0
    bands = [("beat 300+ last yr", lambda x: x >= 300),
             ("missed 150-300 last yr", lambda x: -300 <= x <= -150),
             ("hit dead-on (+-50) last yr", lambda x: -50 <= x <= 50)]
    out = []
    print(f"\n  -- {pos} vs last year's result (same-player pairs) --")
    for lab, fn in bands:
        sub = [r for r in rows if fn(r["diff_a"])]
        if not sub:
            continue
        n = len(sub); p = sum(r["over_b"] for r in sub) / n
        z = (p - 0.5) / math.sqrt(0.25 / n)
        print(f"  {lab:<34} {str(round(100*p))+'%':>6} {n:>4} {z:>+6.1f} {sig(z)}")
        out.append({"pos": pos, "situation": lab, "metric": "yards_yoy",
                    "n": n, "over_pct": round(100 * p), "z": round(z, 1), "sig": sig(z)})
    return out


# RB situations
SITU["RB"] = [
    ("Availability (rush yards)", None),
    ("finished < 14 games", lambda r: r["g"] < 14, "yards"),
    ("finished >= 14 games", lambda r: r["healthy"], "yards"),
    ("Rush-yards line size (all)", None),
    ("< 600 line", lambda r: r["yards_line"] and r["yards_line"] <= 600, "yards"),
    ("600-800 line", lambda r: r["yards_line"] and 600 < r["yards_line"] <= 800, "yards"),
    ("800-1000 line", lambda r: r["yards_line"] and 800 < r["yards_line"] <= 1000, "yards"),
    ("1000-1200 line (dead zone)", lambda r: r["yards_line"] and 1000 < r["yards_line"] <= 1200, "yards"),
    ("1200+ line", lambda r: r["yards_line"] and r["yards_line"] > 1200, "yards"),
    ("Rush-yards line size (healthy only)", None),
    ("< 1000, healthy", lambda r: r["healthy"] and r["yards_line"] and r["yards_line"] <= 1000, "yards"),
    ("1000-1200, healthy", lambda r: r["healthy"] and r["yards_line"] and 1000 < r["yards_line"] <= 1200, "yards"),
    ("Rush-TD line (all)", None),
    ("5-8.5 TD line", lambda r: r["td_line"] and 4.5 < r["td_line"] <= 8.5, "td"),
    ("9-10.5 TD line", lambda r: r["td_line"] and 8.5 < r["td_line"] <= 10.5, "td"),
    ("Draft cost -- Underdog ADP (all)", None),
    ("RB1-18 by ADP", lambda r: r["rank"] and r["rank"] <= 18, "yards"),
    ("RB19-30 by ADP", lambda r: r["rank"] and 18 < r["rank"] <= 30, "yards"),
    ("RB19-30, healthy", lambda r: r["healthy"] and r["rank"] and 18 < r["rank"] <= 30, "yards"),
    ("RB31+ by ADP (committee)", lambda r: r["rank"] and r["rank"] >= 31, "yards"),
    ("Prior year (yards)", None),
    ("line set >= 150 over last yr", lambda r: r["prior_y"] is not None and r["yards_line"] - r["prior_y"] >= 150, "yards"),
    ("line cut >= 150 below last yr", lambda r: r["prior_y"] is not None and r["yards_line"] - r["prior_y"] <= -150, "yards"),
    ("off an injury year (< 14 g)", lambda r: r["prior_g"] is not None and r["prior_g"] < 14, "yards"),
    ("off an injury year, healthy", lambda r: r["healthy"] and r["prior_g"] is not None and r["prior_g"] < 14, "yards"),
]

# strip the bad WR placeholder row
SITU["WR"] = [x for x in SITU["WR"] if not (isinstance(x, tuple) and len(x) == 3 and x[0].startswith("beat by 300"))]


def main():
    wr = load("wr_prop_grades.csv", PRECV)
    rb = load("rb_prop_grades.csv", PRUSH, rush_only=True)
    out = []
    out += run("WR", wr)
    out += yoy_block("WR", "year_over_year_pairs.csv")
    out += run("RB", rb)
    out += yoy_block("RB", "rb_year_over_year_pairs.csv")
    with open(os.path.join(DATA, "cheatsheet.csv"), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["pos", "situation", "metric", "over_pct", "n", "z", "sig"])
        w.writeheader(); w.writerows(out)
    print(f"\nwrote {len(out)} rows -> data/cheatsheet.csv")


if __name__ == "__main__":
    main()
