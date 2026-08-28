"""
Join preseason RB season-long prop lines (nfl/sources/rb_prop_totals) to
actual regular-season rushing production (nfl/sources/rushing_stats) and
grade each line over/under. Underdog ADP (nfl/sources/underdog_adp) is
joined where it exists (2023-25). The RB counterpart of grade_wr.py.

Output: projects/prop-accuracy/data/rb_prop_grades.csv
  year, player, matched_name, team, team_start, traded, games,
  adp, adp_pos_rank, top30, source,
  yards_kind,                       # "rush" or "rush+rec" -- what the line measures
  yards_line, yards_low, yards_high, yards_actual, yards_diff, yards_result,
  td_line, td_actual, td_diff, td_result

`yards_actual` is rushing yards when yards_kind == "rush", rush+rec yards
when "rush+rec", so it always matches what the line was priced on.
`games` < 14 flags a partial season (injury) -- filter before drawing
per-game conclusions, same as the WR analysis.

Run: python3 projects/prop-accuracy/scripts/grade_rb.py
"""
import csv
import os
import re

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))

PROPS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "rb_prop_totals", "data", "rb_prop_totals.csv")
STATS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "rushing_stats", "data", "rushing_stats.csv")
ADP_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "underdog_adp", "data", "underdog_adp.csv")
OUT_PATH = os.path.join(PROJECT, "data", "rb_prop_grades.csv")

TOP_N = 30

FIELDNAMES = [
    "year", "player", "matched_name", "team", "team_start", "traded", "games",
    "adp", "adp_pos_rank", "top30", "source",
    "yards_kind",
    "yards_line", "yards_low", "yards_high", "yards_actual", "yards_diff", "yards_result",
    "td_line", "td_actual", "td_diff", "td_result",
]

ALIASES = {"isaiah pacheco": "isiah pacheco"}

# Backs who had a prop line but did not play a single regular-season snap
# that year (so they're absent from rushing_stats, which needs >=1 carry).
# A zero-play season is a real graded outcome -- a max under -- not a gap.
KNOWN_DNP = {
    (2025, "joe mixon"),  # foot injury, on IR all season
}


def norm(s):
    s = (s or "").lower().strip().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return ALIASES.get(s, s)


def load_props():
    """(year -> {norm_name -> {stat -> row}})"""
    by_year = {}
    with open(PROPS_CSV) as f:
        for r in csv.DictReader(f):
            by_year.setdefault(int(r["year"]), {}).setdefault(norm(r["player"]), {})[r["stat"]] = r
    return by_year


def load_stats():
    by_year = {}
    with open(STATS_CSV) as f:
        for r in csv.DictReader(f):
            by_year.setdefault(int(r["year"]), []).append(r)
    return by_year


def load_adp():
    """(year -> {norm_name -> (pos, adp)}) + (year -> {norm_name -> rb_rank})"""
    pos_adp, rb_rows = {}, {}
    with open(ADP_CSV) as f:
        for r in csv.DictReader(f):
            if not r["adp"]:
                continue
            y = int(r["year"])
            pos_adp.setdefault(y, {})[norm(r["player"])] = (r["pos"], float(r["adp"]))
            if r["pos"] == "RB":
                rb_rows.setdefault(y, []).append((norm(r["player"]), float(r["adp"])))
    rb_rank = {}
    for y, rs in rb_rows.items():
        rs.sort(key=lambda t: t[1])
        rb_rank[y] = {n: i for i, (n, _) in enumerate(rs, 1)}
    return pos_adp, rb_rank


def match(name, pool):
    key = norm(name)
    exact = [r for r in pool if norm(r["player"]) == key]
    if exact:
        return max(exact, key=lambda r: int(r["carries"] or 0))
    parts = key.split()
    first, last = parts[0], parts[-1]
    pat = re.compile(rf"{re.escape(first[0])}\w* {re.escape(last)}$")
    cand = [r for r in pool if pat.fullmatch(norm(r["player"]))
            and r.get("position") in ("RB", "FB", "")]
    if cand:
        return max(cand, key=lambda r: int(r["carries"] or 0))
    return None


def grade(line, actual):
    if line == "" or line is None or actual is None:
        return "", "", ""
    lf = float(line)
    return line, round(actual - lf, 1), ("over" if actual > lf else "under")


def main():
    props = load_props()
    stats = load_stats()
    pos_adp, rb_rank = load_adp()

    out, misses = [], []
    pending = sorted(y for y in props if y not in stats)

    for year in sorted(props):
        if year not in stats:
            continue
        for k, by_stat in props[year].items():
            yline = by_stat.get("rush_yds")
            rrline = by_stat.get("rush_rec_yds")
            tdline = by_stat.get("rush_td")
            ykind = "rush" if yline else ("rush+rec" if rrline else "")
            yrow = yline or rrline
            name = (yrow or tdline)["player"]

            m = match(name, stats[year])
            if m is None and (year, k) not in KNOWN_DNP:
                misses.append((year, name))
                continue
            dnp = m is None
            if dnp:
                m = {"player": name, "team": "", "team_start": "", "traded": "",
                     "games": 0, "rushing_yards": 0, "rush_rec_yards": 0, "rushing_tds": 0}

            ry, rry = int(m["rushing_yards"] or 0), int(m["rush_rec_yards"] or 0)
            rtd = int(m["rushing_tds"] or 0)
            y_actual = ry if ykind == "rush" else rry if ykind == "rush+rec" else None

            pa = pos_adp.get(year, {}).get(k)
            rank = rb_rank.get(year, {}).get(k, "")

            row = dict.fromkeys(FIELDNAMES, "")
            row.update(
                year=year, player=name, matched_name=m["player"],
                team=m["team"], team_start=m.get("team_start", m["team"]),
                traded=m.get("traded", ""), games=m["games"],
                adp=f"{pa[1]:g}" if pa else "", adp_pos_rank=rank,
                top30="Y" if rank and rank <= TOP_N else "",
                source=(yrow or tdline)["source"],
                yards_kind=ykind,
                yards_low=yrow["line_low"] if yrow else "",
                yards_high=yrow["line_high"] if yrow else "",
                yards_actual=y_actual if y_actual is not None else "",
                td_actual=rtd if tdline else "",
            )
            row["yards_line"], row["yards_diff"], row["yards_result"] = grade(
                yrow["line"] if yrow else "", y_actual)
            row["td_line"], row["td_diff"], row["td_result"] = grade(
                tdline["line"] if tdline else "", rtd if tdline else None)
            out.append(row)

    out.sort(key=lambda r: (r["year"], -float(r["yards_line"] or r["yards_low"] or 0)))
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(out)

    gy = [r for r in out if r["yards_result"]]
    over = sum(1 for r in gy if r["yards_result"] == "over")
    gt = [r for r in out if r["td_result"]]
    tover = sum(1 for r in gt if r["td_result"] == "over")
    print(f"graded {len(out)} RB-seasons ({len(misses)} unmatched)")
    print(f"rushing-yards O/U: {over}/{len(gy)} over ({100*over/len(gy):.0f}%)   "
          f"[{sum(1 for r in gy if r['yards_kind']=='rush')} rush, "
          f"{sum(1 for r in gy if r['yards_kind']=='rush+rec')} rush+rec]")
    print(f"rushing-TD O/U:    {tover}/{len(gt)} over ({100*tover/len(gt):.0f}%)")
    if pending:
        print(f"pending (season not played): {pending}")
    if misses:
        print("UNMATCHED:", misses)
    print(f"wrote {os.path.relpath(OUT_PATH, REPO_ROOT)}")


if __name__ == "__main__":
    main()
