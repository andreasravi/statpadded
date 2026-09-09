"""
Is the 2026 TD-line slate comparable to prior years, and -- if we assume
every line is a fair coin flip (books post season yardage O/Us at
-114/-114 and TD props near pick-em) -- does the historical fade still pay?

  edge under "lines are even"  =  0.5 - (historical over rate)
  fair-price EV per $1 at -110 =  p_win * (100/110) - (1 - p_win)

WR TD lines: nfl/sources/wr_prop_totals (Fantasy Alarm grid, no price).
RB TD lines: nfl/sources/rb_prop_totals (2022, 2024-25) + the live
FanDuel snapshot for 2026, which DOES carry a price -- shown alongside so
the "assume even" number can be compared to what the book is really doing.

Prints two tables; writes nothing.
Run: python3 projects/prop-accuracy/scripts/td_lines.py
"""
import csv
import os
from collections import Counter

HERE = os.path.dirname(__file__)
ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
DATA = os.path.join(os.path.dirname(HERE), "data")
WR_P = os.path.join(ROOT, "nfl/sources/wr_prop_totals/data/wr_prop_totals.csv")
RB_P = os.path.join(ROOT, "nfl/sources/rb_prop_totals/data/rb_prop_totals.csv")
FD = os.path.join(ROOT, "nfl/sources/fanduel_season_props/data/fanduel_season_props.csv")
QB = {"Josh Allen", "Jalen Hurts", "Lamar Jackson", "Jaxson Dart", "Drake Maye"}

BANDS = ["<4.5", "4.5-5.5", "6-7.5", "8-8.5", "9-10.5", "11+"]


def band(v):
    return ("11+" if v >= 11 else "9-10.5" if v >= 9 else "8-8.5" if v >= 8
            else "6-7.5" if v >= 6 else "4.5-5.5" if v >= 4.5 else "<4.5")


def ev_at(p_win, american=-110):
    b = 100 / -american if american < 0 else american / 100
    return round(p_win * b - (1 - p_win), 3)


# historical over rates on the TD line (from the grades), by position/band
def hist_rate(grades, rush_only=False):
    out = {}
    for r in csv.DictReader(open(os.path.join(DATA, grades))):
        if rush_only and r.get("yards_kind") != "rush":
            continue
        if not r["td_result"] or not r["td_line"]:
            continue
        bd = band(float(r["td_line"]))
        o, n = out.get(bd, (0, 0))
        out[bd] = (o + (r["td_result"] == "over"), n + 1)
    return out


def dist_table(title, series):
    print(f"\n=== {title} ===")
    print(f"  {'slate':<26} {'n':>3} | " + " ".join(f"{b:>7}" for b in BANDS) + "  | 8+  9+")
    for name, lines in series:
        c = Counter(band(v) for v in lines)
        print(f"  {name:<26} {len(lines):>3} | " + " ".join(f"{c.get(b, 0):>7}" for b in BANDS)
              + f"  | {sum(1 for v in lines if v >= 8):>2}  {sum(1 for v in lines if v >= 9):>2}")


def main():
    wr = list(csv.DictReader(open(WR_P)))
    rb = list(csv.DictReader(open(RB_P)))
    fd = [x for x in csv.DictReader(open(FD))
          if x["position"] == "RB" and x["stat"] == "rush_td" and x["player"] not in QB]

    dist_table("WR TD lines by year (Fantasy Alarm grid)", [
        (yr, [float(r["td_line"]) for r in wr if r["year"] == yr and r["td_line"]])
        for yr in ("2023", "2024", "2025", "2026")])
    dist_table("RB rushing-TD lines by year", [
        ("2022 SportsBetting.ag", [float(x["line"]) for x in rb if x["year"] == "2022" and x["stat"] == "rush_td"]),
        ("2024 FantasyPoints", [float(x["line"]) for x in rb if x["year"] == "2024" and x["stat"] == "rush_td"]),
        ("2025 FantasyPoints (top-17)", [float(x["line"]) for x in rb if x["year"] == "2025" and x["stat"] == "rush_td"]),
        ("2026 FanDuel", [float(x["line"]) for x in fd])])

    wrh, rbh = hist_rate("wr_prop_grades.csv"), hist_rate("rb_prop_grades.csv", rush_only=True)
    print("\n=== assume every line is a fair 50/50 -> historical over rate IS the edge ===")
    print(f"  {'pos / band':<20} {'over rate (n)':>16} {'edge':>7} {'EV @ -110':>10}")
    for pos, h in (("WR", wrh), ("RB", rbh)):
        for bd in BANDS:
            if bd not in h:
                continue
            o, n = h[bd]
            p = o / n
            side = "under" if p < .5 else "over"
            pw = 1 - p if side == "under" else p
            print(f"  {pos+' '+bd:<20} {f'{round(100*p)}% ({o}/{n})':>16} "
                  f"{('+' if pw > .5 else '')+str(round(100*(pw-.5)))+'pp '+side:>7}  {ev_at(pw):>+8.2f}")

    print("\n=== 2026 RB rushing-TD: 'assume even' vs the actual FanDuel price ===")
    print(f"  {'player':<22} {'line':>5} {'FD no-vig P(under)':>18} {'hist under% (band)':>18}")
    for x in sorted(fd, key=lambda r: -float(r["line"])):
        def ap(a):
            a = float(a)
            return (-a) / (-a + 100) if a < 0 else 100 / (a + 100)
        pu = 1 - ap(x["over_odds"]) / (ap(x["over_odds"]) + ap(x["under_odds"]))
        bd = band(float(x["line"]))
        o, n = rbh.get(bd, (0, 0))
        hu = f"{round(100*(1-o/n))}% ({bd})" if n else "-"
        print(f"  {x['player']:<22} {x['line']:>5} {pu:>18.3f} {hu:>18}")


if __name__ == "__main__":
    main()
