"""
Merge every data/raw/*.json source into one long-format CSV:
one row per (season, qb_name, source).

Sources:
  - qbtiers_2026_parsed.json  - The Athletic's 2026 QB Tiers page. Each of
    the 35 currently-surveyed QBs' card includes a "share of votes by
    tier" trend chart back to their debut season, so this one page covers
    2014-2026 for all QBs still active in the survey.
  - athletic_2019.json        - The Athletic's first QB Tiers page (2019,
    55 voters), prose-format; tier per QB inferred via name-matching
    against each ranked block (see note field in the file).
  - overthecap_2014/2016/2017.json - Over The Cap's transcriptions of
    Sando's original ESPN Insider tiers for those years (ESPN's own pages
    are paywalled; these tables were verified by direct page load, not
    LLM-summarized).
  - reddit_2015_partial.json  - Partial 2015 data (Tier 1's top 4 only)
    pasted into a Reddit thread from the original ESPN Insider piece.

Run:
  python3 nfl/sources/qb_tiers/build_csv.py
"""
import csv
import json
import os

HERE = os.path.dirname(__file__)
RAW_DIR = os.path.join(HERE, "data", "raw")
OUT_PATH = os.path.join(HERE, "data", "qb_tiers.csv")

FIELDS = ["season", "qb_name", "team", "tier", "rank_in_season", "source", "source_url"]


def rows_from_2026_page():
    with open(os.path.join(RAW_DIR, "qbtiers_2026_parsed.json")) as f:
        records = json.load(f)

    out = []
    for r in records:
        history = dict(r["history"])
        if "2026" not in history and r["tier_2026"]:
            history["2026"] = r["tier_2026"]
        for season, tier_label in history.items():
            if tier_label == "Not in survey":
                continue
            out.append({
                "season": int(season),
                "qb_name": r["name"],
                "team": r["team"] if season == "2026" else "",
                "tier": int(tier_label.replace("Tier ", "")),
                "rank_in_season": r["rank_2026"] if season == "2026" else "",
                "source": "athletic_2026_page",
                "source_url": "https://www.nytimes.com/athletic/interactive/nfl-quarterback-tiers-insider-rankings-2026/",
            })
    return out


def rows_from_flat_source(filename):
    with open(os.path.join(RAW_DIR, filename)) as f:
        data = json.load(f)
    out = []
    for name, team, tier, rank in data["rows"]:
        out.append({
            "season": data["season"],
            "qb_name": name,
            "team": team,
            "tier": tier,
            "rank_in_season": rank,
            "source": data["source"],
            "source_url": data["source_url"],
        })
    return out


def rows_from_per_row_season_source(filename):
    """For sources like the Brady retrospective where each row carries its
    own season (a multi-year table in one article), rather than one season
    for the whole file."""
    with open(os.path.join(RAW_DIR, filename)) as f:
        data = json.load(f)
    out = []
    for season, name, team, tier, rank in data["rows"]:
        out.append({
            "season": season,
            "qb_name": name,
            "team": team,
            "tier": tier,
            "rank_in_season": rank,
            "source": data["source"],
            "source_url": data["source_url"],
        })
    return out


def main():
    rows = rows_from_2026_page()
    for fname in [
        "athletic_2019.json",
        "athletic_2020.json",
        "athletic_2021.json",
        "athletic_2022.json",
        "athletic_2023.json",
        "athletic_2024.json",
        "athletic_2025.json",
        "overthecap_2014.json",
        "overthecap_2016.json",
        "overthecap_2017.json",
        "reddit_2015_full.json",
        "reddit_2016_avg_ratings.json",
        "reddit_2018_full.json",
    ]:
        rows.extend(rows_from_flat_source(fname))
    rows.extend(rows_from_per_row_season_source("athletic_brady_retrospective.json"))

    rows.sort(key=lambda r: (r["qb_name"], r["season"], r["source"]))

    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS)
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")

    # Flag disagreements where the same QB+season appears from >1 source
    # with a different tier, so they can be checked by hand.
    by_key = {}
    for r in rows:
        key = (r["qb_name"], r["season"])
        by_key.setdefault(key, set()).add(r["tier"])
    conflicts = {k: v for k, v in by_key.items() if len(v) > 1}
    if conflicts:
        print(f"\n{len(conflicts)} season/QB conflicts across sources:")
        for (name, season), tiers in sorted(conflicts.items()):
            print(f"  {name} {season}: tiers {sorted(tiers)}")


if __name__ == "__main__":
    main()
