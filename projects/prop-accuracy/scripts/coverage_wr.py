"""
Which top-25-by-ADP wide receivers are missing from the Fantasy Alarm prop
grid (and therefore from this project's graded set)?

The grid is an editor's pick of "fantasy-relevant" WRs, not a mechanical
top-N by ADP, so it drops a few draftable names each year -- usually
contract holdouts, players on new teams, or rookies the author skipped.
This flags them so the hit-rate numbers aren't read as a complete census.

ADP sources (independent of the grid):
  2023-2025  nfl/sources/underdog_adp   (standard 1-QB, player-level)
  2022       nfl/sources/adp            (FantasyData 2QB/superflex top 100 --
                                         only ~33 WRs make the top 100, so
                                         "top 25 WR" reaches ~overall pick 90)

Run: python3 projects/prop-accuracy/scripts/coverage_wr.py
"""
import csv
import os
import re

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))

PROPS = os.path.join(REPO_ROOT, "nfl/sources/wr_prop_totals/data/wr_prop_totals.csv")
UD_ADP = os.path.join(REPO_ROOT, "nfl/sources/underdog_adp/data/underdog_adp.csv")
FD_ADP = os.path.join(REPO_ROOT, "nfl/sources/adp/data/adp.csv")
OUT = os.path.join(PROJECT, "data", "adp_coverage_gaps.csv")

TOP_N = 25


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def grid_by_year():
    out = {}
    for r in csv.DictReader(open(PROPS)):
        out.setdefault(int(r["year"]), set()).add(norm(r["player"]))
    return out


def wr_adp(year):
    """[(name, adp, source_tag)] sorted by adp, WRs only."""
    if year >= 2023:
        rows = [(r["player"], float(r["adp"]), "underdog")
                for r in csv.DictReader(open(UD_ADP))
                if r["year"] == str(year) and r["pos"] == "WR" and r["adp"]]
    else:
        rows = [(r["name"], float(r["adp"]), "fantasydata")
                for r in csv.DictReader(open(FD_ADP))
                if r["year"] == str(year) and r["pos"] == "WR" and r["adp"]]
    return sorted(rows, key=lambda x: x[1])


def main():
    grid = grid_by_year()
    gaps = []
    for year in sorted(grid):
        top = wr_adp(year)[:TOP_N]
        if not top:
            print(f"{year}: no ADP source")
            continue
        missing = [(rank + 1, nm, adp) for rank, (nm, adp, _) in enumerate(top)
                   if norm(nm) not in grid[year]]
        src = top[0][2]
        print(f"\n{year}  (top-{TOP_N} WR by {src} ADP) — {len(missing)} missing from the grid:")
        for wr_rank, nm, adp in missing:
            print(f"   WR{wr_rank:<2}  {nm:<22}  ADP {adp}")
            gaps.append({"year": year, "wr_adp_rank": wr_rank, "player": nm,
                         "adp": adp, "adp_source": src})
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["year", "wr_adp_rank", "player", "adp", "adp_source"])
        w.writeheader()
        w.writerows(gaps)
    print(f"\nwrote {len(gaps)} gaps -> {os.path.relpath(OUT, REPO_ROOT)}")


if __name__ == "__main__":
    main()
