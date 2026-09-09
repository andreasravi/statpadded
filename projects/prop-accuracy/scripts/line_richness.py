"""
"Vegas has corrected the systematic over/under bias -- the lines are lower
now." Is that true?

Two year-by-year reads:
  1. graded over rate -- if the book fixed a rich-line bias, this drifts
     toward 50%.
  2. line vs the player's PRIOR-season total -- if the book got more
     conservative, this discount grows (more negative).

Plus where the 2026 lines land on both. No "healthy" filter.
Run: python3 projects/prop-accuracy/scripts/line_richness.py
"""
import csv
import os
import re
import statistics as st

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DATA = os.path.join(os.path.dirname(HERE), "data")
RECV = os.path.join(ROOT, "nfl/sources/receiving_stats/data/receiving_stats.csv")
RUSH = os.path.join(ROOT, "nfl/sources/rushing_stats/data/rushing_stats.csv")
WR_P = os.path.join(ROOT, "nfl/sources/wr_prop_totals/data/wr_prop_totals.csv")
RB_P = os.path.join(ROOT, "nfl/sources/rb_prop_totals/data/rb_prop_totals.csv")
FD = os.path.join(ROOT, "nfl/sources/fanduel_season_props/data/fanduel_season_props.csv")


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


PR = {
    "wr": {(norm(r["player"]), int(r["year"])): int(r["receiving_yards"] or 0)
           for r in csv.DictReader(open(RECV))},
    "rb": {(norm(r["player"]), int(r["year"])): int(r["rushing_yards"] or 0)
           for r in csv.DictReader(open(RUSH))},
}


def section(pos, grades, rush=False):
    prior = PR[pos]
    print(f"\n=== {pos.upper()} {'rushing' if pos == 'rb' else 'receiving'} yards ===")
    print(f"  {'year':<6}{'n':>4}{'over %':>8}{'med(actual - line)':>20}{'med(line - prev-yr total)':>27}")
    for yr in ("2022", "2023", "2024", "2025"):
        rows = []
        for r in csv.DictReader(open(grades)):
            if r["year"] != yr or not r["yards_result"]:
                continue
            if rush and r.get("yards_kind") != "rush":
                continue
            line, act = float(r["yards_line"]), float(r["yards_actual"])
            p = prior.get((norm(r["player"]), int(yr) - 1))
            rows.append((line, act, p))
        n = len(rows)
        o = sum(1 for l, a, _ in rows if a > l)
        miss = st.median([a - l for l, a, _ in rows])
        disc = st.median([l - p for l, a, p in rows if p and p > 0])
        print(f"  {yr:<6}{n:>4}{round(100 * o / n):>7}%{miss:>+20.0f}{disc:>+27.0f}")


def d26(name, rows, prior):
    lp = [x for x in rows if x is not None]
    print(f"  {name:<24} line - 2025 total:  median {st.median(lp):+.0f}   mean {st.mean(lp):+.0f}   (n={len(lp)})")


def main():
    section("wr", os.path.join(DATA, "wr_prop_grades.csv"))
    section("rb", os.path.join(DATA, "rb_prop_grades.csv"), rush=True)

    print("\n=== where the 2026 lines land (line minus 2025 actual) ===")
    pw = PR["wr"]
    d26("WR  Fantasy Alarm grid", [float(r["yards_line"]) - pw[(norm(r["player"]), 2025)]
        for r in csv.DictReader(open(WR_P))
        if r["year"] == "2026" and r["yards_line"] and (norm(r["player"]), 2025) in pw and pw[(norm(r["player"]), 2025)] > 0], pw)
    d26("WR  FanDuel", [float(r["line"]) - pw[(norm(r["player"]), 2025)]
        for r in csv.DictReader(open(FD))
        if r["position"] == "WR" and r["stat"] == "rec_yds" and (norm(r["player"]), 2025) in pw and pw[(norm(r["player"]), 2025)] > 0], pw)
    pr = PR["rb"]
    d26("RB  First Down Studio", [float(r["line"]) - pr[(norm(r["player"]), 2025)]
        for r in csv.DictReader(open(RB_P))
        if r["year"] == "2026" and r["stat"] == "rush_yds" and r["source"] == "firstdown.studio"
        and (norm(r["player"]), 2025) in pr and pr[(norm(r["player"]), 2025)] > 0], pr)
    d26("RB  FanDuel", [float(r["line"]) - pr[(norm(r["player"]), 2025)]
        for r in csv.DictReader(open(FD))
        if r["position"] == "RB" and r["stat"] == "rush_yds" and (norm(r["player"]), 2025) in pr and pr[(norm(r["player"]), 2025)] > 0], pr)

    print("""
  Read:
  - WR over rate 2022-25:  46% -> 54% -> 40% -> 35%.  Trends AWAY from 50%,
    not toward it -- the WR overs got harder, not fairer.  And the 2026 WR
    lines sit ~AT last year's total (discount ~0), vs a -90 to -124 discount
    in 2022-24 -- the book got LESS conservative, not more.  (Partly an
    artifact: 2025 was an injury-hit WR year, so "at last year" is a low
    number for a bounce-back guy.)
  - RB over rate:  36% -> 35% -> 55% -> 50%.  This one DID move toward 50%.
    But the 2025->2026 lines are cut hard off a monster 2025 (JT/Henry/Cook
    all 1,600+), which reads as regression pricing after an outlier season,
    not a bias fix.
  - Every year the median miss is still 40-130 yards.  The market is noisy,
    not dialed in.
  - The fade edges that survived the z-test (RB 5-8.5 TD, RB31+ committee,
    WR weak-QB, RB line-raised-off-last-year) are STRUCTURAL -- the book
    over-weights the preseason narrative in specific spots.  Shading the
    whole board down 5% wouldn't touch them.
  - FanDuel prices every season yardage O/U at a flat -114/-114 (untraded).
    A book that had "corrected the bias" would have a view and price it.
""")


if __name__ == "__main__":
    main()
