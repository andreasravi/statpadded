"""
Shared 2026 context: post-trade team per player, projected Week-1 starter
per team, and that starter's preseason QB tier + the Kalshi win total.

Team / starter come from nfl/sources/firstdown_studio_2026 (the FDS boards,
which reflect the 2026 offseason moves); tier is looked up in
nfl/sources/qb_tiers by QB NAME (qb_tiers' own team column is stale for
QBs who moved). Import from any picks_/watch_/context_ script.
"""
import csv
import os
import re

_HERE = os.path.dirname(__file__)
_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(_HERE)))
_FDS = os.path.join(_ROOT, "nfl/sources/firstdown_studio_2026/data/firstdown_2026.csv")
_QBT = os.path.join(_ROOT, "nfl/sources/qb_tiers/data/qb_tiers.csv")
_KAL = os.path.join(_ROOT, "nfl/sources/kalshi_win_totals/data/kalshi_win_totals.csv")


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


def load():
    """returns (team_by_player, qb26, wt26)
      team_by_player: norm(name) -> team abbr (2026)
      qb26:           team abbr  -> (tier:int, qb_name)
      wt26:           team abbr  -> Kalshi implied win total (float)
    """
    team_by_player, starter = {}, {}
    for r in csv.DictReader(open(_FDS)):
        team_by_player[norm(r["player"])] = r["team"]
        if r["pos"] == "QB":
            starter.setdefault(r["team"], r["player"])
    tier_by_name = {norm(r["qb_name"]): int(r["tier"])
                    for r in csv.DictReader(open(_QBT)) if r["season"] == "2026"}
    qb26 = {tm: (tier_by_name[norm(nm)], nm)
            for tm, nm in starter.items() if norm(nm) in tier_by_name}
    wt26 = {r["team"]: round(float(r["implied_line"]), 1)
            for r in csv.DictReader(open(_KAL))}
    return team_by_player, qb26, wt26
