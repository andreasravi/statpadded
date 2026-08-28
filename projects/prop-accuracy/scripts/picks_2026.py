"""
2026 picks -- turn the strongest historical relationships into a call on
who to be HIGH or LOW on versus this year's season-long yardage lines.

Line, in priority order:
  1. FanDuel's live posted O/U   (nfl/sources/fanduel_season_props)
  2. RB: First Down Studio proj  (nfl/sources/rb_prop_totals, 2026)
     WR: Fantasy Alarm grid      (nfl/sources/wr_prop_totals, 2026)
The FD-vs-fallback gap is reported -- a big gap means our earlier scrape
was off and the pick may need a second look.

Signals (only the relationships that actually showed up in the grades):
  RB, lean OVER   bounce-back off a <14 g 2025 (64%/85% healthy)
                  line set >=150 over 2025 rushing yds (57%, 8-for-8 hlt)
                  posted line <= 1000 (healthy sub-1k back ~65-70% over)
                  RB19-30 by rank (80% healthy over)
  RB, lean UNDER  1000-1200 "dead zone" (43% healthy)
                  RB31+ with a real line (1-for-11)
                  line cut >=150 below 2025 (41% over)
  WR, lean OVER   tier-4/5 QB (64% over, +88 yds/tier-step, p=.014)
                  line cut >=150 below 2025 (51%/69% healthy)
                  moderate 2025 down year, -150..-300 vs a full season
  WR, lean UNDER  line set >=150 over 2025 (37%/46% healthy)
                  coming off a <14 g 2025 (36%/47% healthy)
                  tier-1/2 QB + 9.5+ win team + line >= 1000 (mean -43)
                  1000-1200 dead zone

Writes data/picks_2026.json + prints the ranked lists.
Run: python3 projects/prop-accuracy/scripts/picks_2026.py
"""
import csv
import json
import os
import re

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")

FD = os.path.join(ROOT, "nfl/sources/fanduel_season_props/data/fanduel_season_props.csv")
RB_PROPS = os.path.join(ROOT, "nfl/sources/rb_prop_totals/data/rb_prop_totals.csv")
WR_PROPS = os.path.join(ROOT, "nfl/sources/wr_prop_totals/data/wr_prop_totals.csv")
RUSH = os.path.join(ROOT, "nfl/sources/rushing_stats/data/rushing_stats.csv")
RECV = os.path.join(ROOT, "nfl/sources/receiving_stats/data/receiving_stats.csv")
QB_TIERS = os.path.join(ROOT, "nfl/sources/qb_tiers/data/qb_tiers.csv")
KALSHI = os.path.join(ROOT, "nfl/sources/kalshi_win_totals/data/kalshi_win_totals.csv")
FDS_2026 = os.path.join(ROOT, "nfl/sources/firstdown_studio_2026/data/firstdown_2026.csv")


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load_actuals(path, yfield, tdfield):
    out = {}
    for r in csv.DictReader(open(path)):
        if r["year"] != "2025":
            continue
        out[norm(r["player"])] = {
            "team": r["team_start"] or r["team"], "g": int(r["games"] or 0),
            "yds": int(r[yfield] or 0), "td": int(r[tdfield] or 0),
        }
    return out


def load_fd():
    out = {}
    for r in csv.DictReader(open(FD)):
        out.setdefault(r["position"], {}).setdefault(r["stat"], {})[norm(r["player"])] = {
            "line": float(r["line"]), "over": int(r["over_odds"]),
            "under": int(r["under_odds"]), "no_vig_over": float(r["no_vig_over"]),
            "player": r["player"],
        }
    return out


def load_fds_2026():
    """team-2026 per player + projected Week-1 starter per team, from the
    First Down Studio 2026 boards (post-trade, authoritative)."""
    team = {}
    starter = {}  # team -> qb name (highest-ranked QB on the board)
    for r in csv.DictReader(open(FDS_2026)):
        team[norm(r["player"])] = r["team"]
        if r["pos"] == "QB":
            starter.setdefault(r["team"], r["player"])
    return team, starter


def qb26(starter):
    """team -> (tier, qb_name) for 2026: the FDS-projected starter, tier
    looked up in qb_tiers by NAME (qb_tiers' own team column is unreliable
    for players who moved)."""
    tier_by_name = {norm(r["qb_name"]): int(r["tier"])
                    for r in csv.DictReader(open(QB_TIERS)) if r["season"] == "2026"}
    qb = {}
    for tm, name in starter.items():
        t = tier_by_name.get(norm(name))
        if t:
            qb[tm] = (t, name)
    return qb


def main():
    fd = load_fd()
    rush25 = load_actuals(RUSH, "rushing_yards", "rushing_tds")
    recv25 = load_actuals(RECV, "receiving_yards", "receiving_tds")
    TEAM26, STARTER26 = load_fds_2026()
    QB = qb26(STARTER26)
    WT = {r["team"]: round(float(r["implied_line"]), 1) for r in csv.DictReader(open(KALSHI))}

    # ---- RB ----
    rb_proj, rb_rank = {}, {}
    fds_rows = [r for r in csv.DictReader(open(RB_PROPS))
                if r["year"] == "2026" and r["stat"] == "rush_yds" and r["source"] == "firstdown.studio"]
    for i, r in enumerate(sorted(fds_rows, key=lambda x: -float(x["line"])), 1):
        rb_proj[norm(r["player"])] = (float(r["line"]), r["player"], r["team"])
        rb_rank[norm(r["player"])] = i

    rb = []
    # RBs only -- the FDS 2026 board is running-backs-only, so it is the RB whitelist
    keys = set(rb_proj)
    for k in keys:
        f = fd.get("RB", {}).get("rush_yds", {}).get(k)
        p = rb_proj.get(k)
        name = (f or {}).get("player") or (p[1] if p else k)
        line = f["line"] if f else (p[0] if p else None)
        proj = p[0] if p else None
        team = TEAM26.get(k) or (p[2] if p else None) or (rush25.get(k, {}).get("team"))
        a = rush25.get(k)
        q = QB.get(team)
        rank = rb_rank.get(k)
        sig = []
        if a and a["g"] < 14 and line and line >= 550:
            sig.append(("OVER", "bounce-back: <14 g in 2025", 3))
        if a and line and line - a["yds"] >= 150:
            sig.append(("OVER", f"bullish re-rate: line +{round(line-a['yds'])} vs 2025", 2))
        if rank and 19 <= rank <= 30 and line and line <= 1000:
            sig.append(("OVER", f"mid-round back (rank ~{rank}), catchable line", 2))
        if line and 1000 <= line < 1200:
            sig.append(("UNDER", "1,000-1,200 dead zone", 2))
        if rank and rank >= 31 and line and line >= 450:
            sig.append(("UNDER", f"deep back (proj rank ~{rank}) with a real line", 3))
        # bearish re-rate is ~a coin flip for a healthy back (41% all / 59% hlt);
        # only flag an extreme cut, and lightly
        if a and line and a["g"] >= 14 and a["yds"] - line >= 350:
            sig.append(("UNDER", f"line cut hard ({round(a['yds']-line)}) off 2025", 1))
        rb.append({
            "player": name, "team": team, "line": line, "fd_line": f["line"] if f else None,
            "proj_line": proj, "line_gap": (round(f["line"] - proj) if f and proj else None),
            "prior": a, "qb_tier": q[0] if q else None, "win_total": WT.get(team),
            "rank": rank, "signals": sig,
            "score": sum(s[2] if s[0] == "OVER" else -s[2] for s in sig),
        })

    # ---- WR ----
    fa = {}
    for i, r in enumerate(sorted([x for x in csv.DictReader(open(WR_PROPS)) if x["year"] == "2026"],
                                 key=lambda x: -float(x["yards_line"])), 1):
        fa[norm(r["player"])] = {"yl": float(r["yards_line"]), "tl": float(r["td_line"] or 0),
                                 "adp_rank": int(r["adp_rank"] or 0), "player": r["player"]}
    # FanDuel's "receiving yards" markets include tight ends; the historical
    # model is WR-only, so tag TEs and keep them out of the ranked lists
    TE = {norm(x) for x in ["Brock Bowers", "Travis Kelce", "Trey McBride", "Mark Andrews",
          "George Kittle", "Kyle Pitts", "Colston Loveland", "Tyler Warren", "Tucker Kraft",
          "T.J. Hockenson", "David Njoku", "Dallas Goedert", "Sam LaPorta", "Tyler Higbee"]}
    wr = []
    keys = set(fd.get("WR", {}).get("rec_yds", {})) | set(fa)
    for k in keys:
        if k in TE:
            continue
        f = fd.get("WR", {}).get("rec_yds", {}).get(k)
        g = fa.get(k)
        name = (f or {}).get("player") or (g["player"] if g else k)
        line = f["line"] if f else (g["yl"] if g else None)
        gridl = g["yl"] if g else None
        a = recv25.get(k)
        team = TEAM26.get(k) or (a["team"] if a else None)
        q = QB.get(team)
        td_line = g["tl"] if g else None
        sig = []
        if q and q[0] >= 4:
            sig.append(("OVER", f"weak/unproven QB (tier {q[0]})", 3))
        if a and line and a["g"] >= 14 and a["yds"] - line >= 150:
            sig.append(("OVER", f"line cut {round(a['yds']-line)} below a full 2025", 2))
        if a and line and a["g"] >= 14 and 50 <= (a["yds"] - line) < 150 and a["yds"] < gridl if gridl else False:
            pass
        if a and a["g"] < 14 and line:
            sig.append(("UNDER", f"coming off {a['g']} g in 2025", 3))
        if a and line and line - a["yds"] >= 150:
            sig.append(("UNDER", f"bullish re-rate: line +{round(line-a['yds'])} vs 2025", 2))
        if q and q[0] <= 2 and WT.get(team, 0) >= 9.5 and line and line >= 1000:
            sig.append(("UNDER", f"elite QB + {WT.get(team)}-win team + 1,000+ line", 2))
        if line and 1000 <= line < 1200:
            sig.append(("UNDER", "1,000-1,200 dead zone", 1))
        if td_line and td_line >= 8:
            sig.append(("UNDER", f"{td_line} TD line (fade the TD number)", 1))
        wr.append({
            "player": name, "team": team, "line": line, "fd_line": f["line"] if f else None,
            "grid_line": gridl, "line_gap": (round(f["line"] - gridl) if f and gridl else None),
            "td_line": td_line, "prior": a, "qb_tier": q[0] if q else None,
            "win_total": WT.get(team), "signals": sig,
            "score": sum(s[2] if s[0] == "OVER" else -s[2] for s in sig),
        })

    def ranklist(rows):
        hi = sorted([r for r in rows if r["score"] >= 2], key=lambda r: -r["score"])
        lo = sorted([r for r in rows if r["score"] <= -2], key=lambda r: r["score"])
        return hi, lo

    rb_hi, rb_lo = ranklist(rb)
    wr_hi, wr_lo = ranklist(wr)

    out = {"rb": {"high": rb_hi, "low": rb_lo, "all": rb},
           "wr": {"high": wr_hi, "low": wr_lo, "all": wr}}
    with open(os.path.join(DATA, "picks_2026.json"), "w") as f:
        json.dump(out, f, indent=1)

    def show(title, hi, lo, unit):
        print(f"\n{'='*70}\n{title}\n{'='*70}")
        for tag, rows in (("HIGH ON (lean over)", hi), ("LOW ON (lean under)", lo)):
            print(f"\n  {tag}")
            for r in rows:
                gap = f"  [FD {r['line']:.0f} vs scrape {r.get('proj_line') or r.get('grid_line') or '–'}, Δ{r['line_gap']:+d}]" if r.get("line_gap") else ""
                pr = r["prior"]
                prs = f"'25 {pr['g']}G {pr['yds']}{unit}" if pr else "'25 n/a"
                print(f"   {r['player']:<24} {str(r['team'] or '--'):<4} line {str(r['line'] or '–'):>7}  ({prs})  score {r['score']:+d}{gap}")
                for s in r["signals"]:
                    print(f"        {s[0]:<5} {s[1]}")

    show("RUNNING BACKS — 2026 rushing yards", rb_hi, rb_lo, "y")
    show("WIDE RECEIVERS — 2026 receiving yards", wr_hi, wr_lo, "y")
    print(f"\nwrote {os.path.relpath(os.path.join(DATA, 'picks_2026.json'), ROOT)}")


if __name__ == "__main__":
    main()
