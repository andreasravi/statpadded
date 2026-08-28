"""
NFL primary starting QB per team per season, 2014-2025, plus that QB's
Sando/Athletic QB Tier for the same season where available.

Source: Pro-Football-Reference season passing tables --
  https://www.pro-football-reference.com/years/{year}/passing.htm
Same Cloudflare-protected situation as nfl/sources/game_results -- pulled
via browser, filtered client-side to pos=="QB" rows with pass_att>=50 (a
plain backup with a handful of mop-up attempts can't be the primary
starter; the >=50 cut just keeps the cached JSON small, not a modeling
threshold), and cached as data/raw/passing_{year}.json.

Why this exists: nfl/sources/qb_tiers/data/qb_tiers.csv is long-format by
QB+season and 36% of its rows have a blank `team` field (worse in recent
years -- the athletic_2026_page trend-chart source, which supplies most of
2019-2025, doesn't carry team at all), so it can't be grouped into a
team-season table on its own. This source supplies the missing half: who
started for which team each season, from games_started (ties broken by
pass attempts) -- which then lets qb_tiers join in cleanly by (season,
qb_name).

Output:
  data/qb_starters.csv       -- year, team, qb_name, games_started, pass_att
  data/qb_starter_tiers.csv  -- year, team, qb_name, games_started, tier,
                                 rank_in_season, tier_source
                                 (only rows where the starter matched a
                                 qb_tiers.csv row for that season; a QB with
                                 no tier coverage that year -- usually a
                                 rookie or journeyman -- is simply absent,
                                 not filled with a placeholder)

Rebuild (parsing only, no network):
  python3 nfl/sources/qb_starters/pipeline.py
"""
import csv
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", ".."))
from nfl.common.team_codes import normalize_pfr_abbr

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
STARTERS_OUT = os.path.join(HERE, "data", "qb_starters.csv")
TIERS_OUT = os.path.join(HERE, "data", "qb_starter_tiers.csv")
QB_TIERS_CSV = os.path.join(HERE, "..", "qb_tiers", "data", "qb_tiers.csv")

DEFAULT_START, DEFAULT_END = 2014, 2025

# PFR's current-style codes (KAN/TAM/GNB/NWE/SFO/NOR/LVR) are handled by
# the shared nfl.common.team_codes.normalize_pfr_abbr(). Its pre-relocation
# codes (SDG/OAK/STL) aren't a PFR stylistic quirk -- they're genuine
# former franchise identities -- so they're mapped here, same as
# nfl.common.team_codes.TEAM_NAME_TO_ABBR does for other sources' full
# team names.
RELOCATION_ABBR_ALIAS = {"SDG": "LAC", "OAK": "LV", "STL": "LAR"}

SUFFIX_RE = re.compile(r"\b(jr|sr|ii|iii|iv|v)\.?$", re.IGNORECASE)


def normalize_name(name: str) -> str:
    """Best-effort match key between PFR names and qb_tiers.csv names --
    strips periods/punctuation, generational suffixes, and case."""
    n = name.lower().replace(".", "").replace("'", "")
    n = SUFFIX_RE.sub("", n).strip()
    n = re.sub(r"\s+", " ", n)
    return n


def load_starters(start_year, end_year):
    rows = []
    for year in range(start_year, end_year + 1):
        path = os.path.join(RAW_DIR, f"passing_{year}.json")
        if not os.path.exists(path):
            print(f"  (missing {path}, skipping {year})")
            continue
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        by_team = {}
        for r in data:
            team = r["team"]
            if team.endswith("TM"):  # multi-team aggregate row (e.g. "2TM") -- skip, per-team rows exist separately
                continue
            team = normalize_pfr_abbr(RELOCATION_ABBR_ALIAS.get(team, team))
            gs, att = int(r["gs"]), int(r["att"])
            cur = by_team.get(team)
            if cur is None or (gs, att) > (cur["gs"], cur["att"]):
                by_team[team] = {"name": r["name"], "gs": gs, "att": att}

        for team, best in by_team.items():
            rows.append({
                "year": year, "team": team, "qb_name": best["name"],
                "games_started": best["gs"], "pass_att": best["att"],
            })
    return rows


def load_qb_tiers():
    with open(QB_TIERS_CSV, encoding="utf-8") as f:
        tier_rows = list(csv.DictReader(f))
    # Index by (season, normalized name) -> first matching row. qb_tiers'
    # own build already verifies every multi-source overlap agrees on tier,
    # so any matching row for a given (season, name) is as good as another.
    by_key = {}
    for r in tier_rows:
        key = (int(r["season"]), normalize_name(r["qb_name"]))
        if key not in by_key:
            by_key[key] = r
    return by_key


def build(start_year=DEFAULT_START, end_year=DEFAULT_END):
    starters = load_starters(start_year, end_year)
    tiers_by_key = load_qb_tiers()

    starters.sort(key=lambda r: (r["year"], r["team"]))
    os.makedirs(os.path.dirname(STARTERS_OUT), exist_ok=True)
    with open(STARTERS_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "team", "qb_name", "games_started", "pass_att"])
        w.writeheader()
        w.writerows(starters)
    print(f"Wrote {len(starters)} team-season starters -> {STARTERS_OUT}")

    matched = []
    unmatched = []
    for r in starters:
        key = (r["year"], normalize_name(r["qb_name"]))
        tier_row = tiers_by_key.get(key)
        if tier_row is None:
            unmatched.append(r)
            continue
        matched.append({
            "year": r["year"], "team": r["team"], "qb_name": r["qb_name"],
            "games_started": r["games_started"],
            "tier": tier_row["tier"],
            "rank_in_season": tier_row["rank_in_season"],
            "tier_source": tier_row["source"],
        })

    with open(TIERS_OUT, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=["year", "team", "qb_name", "games_started", "tier", "rank_in_season", "tier_source"])
        w.writeheader()
        w.writerows(matched)
    print(f"Wrote {len(matched)} starter-with-tier rows -> {TIERS_OUT}")
    print(f"{len(unmatched)}/{len(starters)} team-season starters had no qb_tiers match (rookies / pre-2014 vets / journeymen with thin coverage):")
    for r in unmatched:
        print(f"  {r['year']} {r['team']}: {r['qb_name']}")

    return STARTERS_OUT, TIERS_OUT


if __name__ == "__main__":
    args = sys.argv[1:]
    start = int(args[0]) if len(args) > 0 else DEFAULT_START
    end = int(args[1]) if len(args) > 1 else DEFAULT_END
    build(start, end)
