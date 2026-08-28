"""
Which top-30-by-ADP running backs are missing a season-long rushing-yards
line in nfl/sources/rb_prop_totals (and therefore from the graded set)?

Same idea as coverage_wr.py. The prop sources are editors'/one-book picks,
not a mechanical top-N, so they drop some draftable backs each year --
usually rookies, committee backs, or injury-cloud names. This flags them
so the hit rates aren't read as a complete top-30 census.

ADP: nfl/sources/underdog_adp (2023-25 only; no 2022 RB ADP source in the
repo, so 2022's SportsBetting.ag list can't be coverage-checked here).

Run: python3 projects/prop-accuracy/scripts/coverage_rb.py
"""
import csv
import os
import re

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))

PROPS = os.path.join(REPO_ROOT, "nfl/sources/rb_prop_totals/data/rb_prop_totals.csv")
UD_ADP = os.path.join(REPO_ROOT, "nfl/sources/underdog_adp/data/underdog_adp.csv")
OUT = os.path.join(PROJECT, "data", "rb_adp_coverage_gaps.csv")

TOP_N = 30
ALIASES = {"isaiah pacheco": "isiah pacheco"}


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def have_yards_line():
    """year -> set of norm names with a rush_yds or rush_rec_yds line."""
    out = {}
    for r in csv.DictReader(open(PROPS)):
        if r["stat"] in ("rush_yds", "rush_rec_yds"):
            out.setdefault(int(r["year"]), set()).add(norm(r["player"]))
    return out


def rb_adp(year):
    rows = [(r["player"], float(r["adp"]))
            for r in csv.DictReader(open(UD_ADP))
            if r["year"] == str(year) and r["pos"] == "RB" and r["adp"]]
    return sorted(rows, key=lambda x: x[1])


def main():
    have = have_yards_line()
    gaps = []
    for year in sorted(y for y in have if y >= 2023):
        top = rb_adp(year)[:TOP_N]
        if not top:
            print(f"{year}: no ADP source")
            continue
        missing = [(i + 1, nm, adp) for i, (nm, adp) in enumerate(top)
                   if norm(nm) not in have[year]]
        print(f"\n{year}  (top-{TOP_N} RB by Underdog ADP) — {len(missing)} with no rushing-yards line:")
        for rank, nm, adp in missing:
            print(f"   RB{rank:<2}  {nm:<24}  ADP {adp}")
            gaps.append({"year": year, "rb_adp_rank": rank, "player": nm, "adp": adp})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "rb_adp_rank", "player", "adp"])
        w.writeheader()
        w.writerows(gaps)
    print(f"\nwrote {len(gaps)} gaps -> {os.path.relpath(OUT, REPO_ROOT)}")


if __name__ == "__main__":
    main()
