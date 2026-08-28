"""
2026 RB watch -- run the patterns from explore_rb.py / analyze_rb.py /
context_rb.py against this year's rushing-yards lines. Nothing here is
graded; the season hasn't started.

Lines: nfl/sources/rb_prop_totals 2026 rows (source = firstdown.studio,
a Vegas-prop-driven projection, ~within 25 yds of posted DK season O/U).
Context: 2026 QB tier (The Athletic survey via nfl/sources/qb_tiers) and
the current Kalshi win-total line. Prior-year = 2025 regular-season
rushing totals from nfl/sources/rushing_stats.

Writes data/rb_watch_2026.json (embed in the report) + prints the groups.
Run: python3 projects/prop-accuracy/scripts/watch_rb.py
"""
import csv
import json
import os
import re
import sys

HERE = os.path.dirname(__file__)
sys.path.insert(0, HERE)
import _ctx26  # noqa: E402

PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")

PROPS = os.path.join(REPO_ROOT, "nfl/sources/rb_prop_totals/data/rb_prop_totals.csv")
RUSH = os.path.join(REPO_ROOT, "nfl/sources/rushing_stats/data/rushing_stats.csv")

# FDS abbreviated names -> the spelling nflverse rushing_stats uses (2025)
NAME_FIX = {
    "C. McCaffrey": "Christian McCaffrey", "D'Andre Swift": "D'Andre Swift",
    "David Montgomery": "David Montgomery", "Quinshon Judkins": "Quinshon Judkins",
    "TreVeyon Henderson": "TreVeyon Henderson", "Rhamondre Stevenson": "Rhamondre Stevenson",
    "Kenneth Gainwell": "Kenneth Gainwell", "Javonte Williams": "Javonte Williams",
    "Jacory Croskey-Merritt": "Jacory Croskey-Merritt", "M. Washington Jr.": "M. Washington Jr.",
}


def _norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_prior():
    idx = {}
    for r in csv.DictReader(open(RUSH)):
        if r["year"] != "2025":
            continue
        for k in ("games", "carries", "rushing_yards", "rushing_tds", "rush_rec_yards", "receiving_yards"):
            r[k] = int(r[k]) if r[k] not in ("", None) else 0
        idx[_norm(r["player"])] = r
    return idx


def main():
    prior = load_prior()
    team26, qb26, wt26 = _ctx26.load()

    backs = []
    for r in csv.DictReader(open(PROPS)):
        if r["year"] != "2026" or r["stat"] != "rush_yds":
            continue
        line = float(r["line"])
        nm = NAME_FIX.get(r["player"], r["player"])
        p = prior.get(_norm(nm))
        tm = team26.get(_norm(r["player"])) or r["team"]
        q = qb26.get(tm)
        py = p["rushing_yards"] if p else None
        pg = p["games"] if p else None
        backs.append({
            "player": r["player"], "team": tm, "line": line,
            "prior_rush_yds": py, "prior_games": pg,
            "prior_rush_tds": p["rushing_tds"] if p else None,
            "prior_rush_rec_yds": p["rush_rec_yards"] if p else None,
            "rookie_or_no_prior": p is None,
            "qb_tier": q[0] if q else None, "qb_name": q[1] if q else None,
            "win_total": wt26.get(tm),
            "line_minus_prior": round(line - py) if py is not None else None,
        })
    backs.sort(key=lambda b: -b["line"])
    for i, b in enumerate(backs, 1):
        b["fds_rank"] = i

    def grp(rows, key=lambda b: -b["line"]):
        return sorted(rows, key=key)

    groups = {
        "club_1000": {
            "title": "The 1,000-yard club",
            "hist": "history: 33% over, 43% healthy; the 1,000-1,200 band is the dead zone, 1,200+ has held up",
            "rows": grp([b for b in backs if b["line"] >= 1000]),
        },
        "bounceback": {
            "title": "Bounce-back backs (missed time in 2025)",
            "hist": "history: 64% over, 85% when healthy, median +108 -- the market over-discounts a back's injury year",
            "rows": grp([b for b in backs if b["prior_games"] is not None and b["prior_games"] < 14 and b["line"] >= 550]),
        },
        "bullish_rerate": {
            "title": "Line set well above last year (bullish re-rate)",
            "hist": "history: 57% over, 8-for-8 when healthy -- for backs, a raise has still been too low",
            "rows": grp([b for b in backs if b["line_minus_prior"] is not None and b["line_minus_prior"] >= 150],
                        key=lambda b: -b["line_minus_prior"]),
        },
        "dead_zone_800_1000": {
            "title": "The 800-1,000 bimodal band",
            "hist": "history: 71% over when healthy, but the misses (injuries) run ~1.4x the size of the beats",
            "rows": grp([b for b in backs if 800 <= b["line"] < 1000]),
        },
        "committee_trap": {
            "title": "Deep backs with a real line -- the committee trap",
            "hist": "history: RB31+ by draft cost cleared 1 of 11 (9%)",
            "rows": grp([b for b in backs if b["fds_rank"] >= 31 and b["line"] >= 450],
                        key=lambda b: b["fds_rank"]),
        },
        "elite_qb": {
            "title": "Elite-QB backfields (lean over, unlike WR)",
            "hist": "history: tier-1-QB RBs cleared 58% (73% healthy) -- the opposite of the WR finding",
            "rows": grp([b for b in backs if b["qb_tier"] == 1]),
        },
        "new_team": {
            "title": "New team or new role in 2026",
            "hist": "priced on a situation with no shared history -- treat the line as a wider guess",
            "rows": grp([b for b in backs if b["player"] in (
                "Kenneth Walker", "Javonte Williams", "David Montgomery", "Travis Etienne",
                "Rico Dowdle", "Ashton Jeanty", "Omarion Hampton", "Jeremiyah Love",
                "Jacory Croskey-Merritt", "Aaron Jones")]),
        },
    }

    out = {"backs": backs, "groups": groups,
           "source_note": "2026 rushing-yards numbers are First Down Studio's Vegas-prop-driven projection (~within 25 yds of posted DK season O/U); QB tier from The Athletic's 2026 survey; win total is the current Kalshi line; 2025 figures are actual regular-season totals."}
    with open(os.path.join(DATA, "rb_watch_2026.json"), "w") as f:
        json.dump(out, f, indent=1)

    print(f"{len(backs)} RBs with a 2026 rushing-yards line\n")
    for g in groups.values():
        print(f"## {g['title']}   [{g['hist']}]")
        for b in g["rows"]:
            ctx = (f"QB T{b['qb_tier']}" if b["qb_tier"] else "QB -")
            ctx += f" / {b['win_total']}w" if b["win_total"] is not None else ""
            pr = (f"'25: {b['prior_games']}G {b['prior_rush_yds']}y/{b['prior_rush_tds']}td"
                  if b["prior_rush_yds"] is not None else "'25: rookie / no carries")
            mv = f"  (line {'+' if b['line_minus_prior'] and b['line_minus_prior']>0 else ''}{b['line_minus_prior']} vs '25)" if b["line_minus_prior"] is not None else ""
            print(f"   {b['player']:<24} {b['team']:<4} {b['line']:>6.0f}  {ctx:<12}  {pr}{mv}")
        print()
    print(f"wrote {os.path.relpath(os.path.join(DATA, 'rb_watch_2026.json'), REPO_ROOT)}")


if __name__ == "__main__":
    main()
