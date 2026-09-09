"""
Which observations are a *trend across ordered buckets* (a real relationship
you can reason about), vs a single bucket that only looks good because we
cut the data until one cell went significant?

For each candidate relationship, print the over rate in every bucket in
order, and a rank-correlation between bucket position and over rate:
  |r| > 0.8  -> the effect moves consistently across the whole range
  |r| < 0.8  -> flat / zig-zag; any one significant cell is probably noise

No "healthy" conditioning -- everything here is knowable before Week 1.
Run: python3 projects/prop-accuracy/scripts/trends.py
"""
import csv
import math
import os
import re
import statistics as st

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DATA = os.path.join(os.path.dirname(HERE), "data")
QBW = os.path.join(ROOT, "nfl/sources/qb_starters/data/qb_starter_tiers.csv")
RECV = os.path.join(ROOT, "nfl/sources/receiving_stats/data/receiving_stats.csv")
RUSH = os.path.join(ROOT, "nfl/sources/rushing_stats/data/rushing_stats.csv")


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


QBT = {(int(r["year"]), r["team"]): int(r["tier"])
       for r in csv.DictReader(open(QBW)) if r["tier"]}
PRECV = {(norm(r["player"]), int(r["year"])): int(r["receiving_yards"] or 0)
         for r in csv.DictReader(open(RECV))}
PRUSH = {(norm(r["player"]), int(r["year"])): int(r["rushing_yards"] or 0)
         for r in csv.DictReader(open(RUSH))}


def zscore(o, n):
    return (o / n - 0.5) / math.sqrt(0.25 / n) if n else 0.0


def load(fn, prior, rush=False):
    out = []
    for r in csv.DictReader(open(fn)):
        if rush and r.get("yards_kind") != "rush":
            continue
        y, tm = int(r["year"]), (r["team_start"] or r["team"])
        out.append({
            "yl": float(r["yards_line"]) if r["yards_line"] else None,
            "tl": float(r["td_line"]) if r.get("td_line") else None,
            "yo": 1 if r["yards_result"] == "over" else 0 if r["yards_result"] == "under" else None,
            "to": 1 if r["td_result"] == "over" else 0 if r["td_result"] == "under" else None,
            "qt": QBT.get((y, tm)),
            "py": prior.get((norm(r["player"]), y - 1)),
        })
    return out


def trend(title, src, key, buckets, mech):
    print(f"\n{title}")
    ys = []
    for lab, f in buckets:
        s = [r for r in src if r[key] is not None and f(r)]
        n = len(s)
        if n == 0:
            continue
        o = sum(r[key] for r in s)
        p = o / n
        ys.append(p)
        print(f"  {lab:<20} {o:>3}/{n:<3} {round(100 * p):>3}%  z {zscore(o, n):>+4.1f}  {'#' * round(p * 28)}")
    if len(ys) >= 3:
        mx, my = st.mean(range(len(ys))), st.mean(ys)
        num = sum((i - mx) * (v - my) for i, v in enumerate(ys))
        den = math.sqrt(sum((i - mx) ** 2 for i in range(len(ys))) * sum((v - my) ** 2 for v in ys))
        r = num / den if den else 0
        tag = "CLEAN TREND" if abs(r) > 0.8 else "noisy / flat"
        print(f"  -> across buckets r = {r:+.2f}   [{tag}]")
        print(f"     {mech}")


def main():
    wr = load(os.path.join(DATA, "wr_prop_grades.csv"), PRECV)
    rb = load(os.path.join(DATA, "rb_prop_grades.csv"), PRUSH, rush=True)

    trend("WR receiving yards  x  QB tier  (1 elite -> 5 replacement)", wr, "yo",
          [("tier 1", lambda r: r["qt"] == 1), ("tier 2", lambda r: r["qt"] == 2),
           ("tier 3", lambda r: r["qt"] == 3), ("tier 4", lambda r: r["qt"] == 4),
           ("tier 5", lambda r: r["qt"] == 5)],
          "the book shades a WR's yardage down for a weak-QB label and over-does it")

    trend("RB rushing yards  vs the player's LINE LAST YEAR", rb, "yo",
          [("cut 250+ below", lambda r: r["py"] is not None and r["yl"] - r["py"] <= -250),
           ("cut 100-250", lambda r: r["py"] is not None and -250 < r["yl"] - r["py"] <= -100),
           ("within +-100", lambda r: r["py"] is not None and -100 < r["yl"] - r["py"] < 100),
           ("raised 100+", lambda r: r["py"] is not None and r["yl"] - r["py"] >= 100)],
          "an RB line only gets raised for a real role change; the number lags the new reality")

    trend("WR receiving yards  vs the player's LINE LAST YEAR", wr, "yo",
          [("cut 250+ below", lambda r: r["py"] is not None and r["yl"] - r["py"] <= -250),
           ("cut 100-250", lambda r: r["py"] is not None and -250 < r["yl"] - r["py"] <= -100),
           ("within +-100", lambda r: r["py"] is not None and -100 < r["yl"] - r["py"] < 100),
           ("raised 100-250", lambda r: r["py"] is not None and 100 <= r["yl"] - r["py"] < 250),
           ("raised 250+", lambda r: r["py"] is not None and r["yl"] - r["py"] >= 250)],
          "the celebrated WR re-rate signal -- check if it actually trends")

    trend("WR TD line size  ->  over rate", wr, "to",
          [("<= 4.5", lambda r: r["tl"] <= 4.5), ("5 - 5.5", lambda r: 4.5 < r["tl"] <= 5.5),
           ("6 - 6.5", lambda r: 5.5 < r["tl"] <= 6.5), ("7 - 7.5", lambda r: 6.5 < r["tl"] <= 7.5),
           ("8 - 8.5", lambda r: 7.5 < r["tl"] <= 8.5), ("9+", lambda r: r["tl"] >= 9)],
          "is the '8+ TD fade' a gradient, or one small cliff at 9+?")

    trend("WR TD  x  QB tier", wr, "to",
          [("tier 1", lambda r: r["qt"] == 1), ("tier 2", lambda r: r["qt"] == 2),
           ("tier 3", lambda r: r["qt"] == 3), ("tier 4-5", lambda r: r["qt"] and r["qt"] >= 4)],
          "does QB quality move WR TD outcomes the way it moves yards?")


if __name__ == "__main__":
    main()
