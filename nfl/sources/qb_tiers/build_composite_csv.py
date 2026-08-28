"""
Build data/qb_tiers_10yr_composite.csv from data/raw/athletic_10yr_composite.json.

This is a SEPARATE, differently-shaped dataset from qb_tiers.csv/db: not a
season-by-season snapshot, but Sando's own single retrospective ranking
(published August 2023) of the 35 QBs who appeared most often across all
10 years of the survey (2014-2023), each with their career-to-date median
tier vote. See the `note` field in the source JSON for details.

Run:
  python3 nfl/sources/qb_tiers/build_composite_csv.py
"""
import csv
import json
import os

HERE = os.path.dirname(__file__)
IN_PATH = os.path.join(HERE, "data", "raw", "athletic_10yr_composite.json")
OUT_PATH = os.path.join(HERE, "data", "qb_tiers_10yr_composite.csv")


def main():
    with open(IN_PATH) as f:
        data = json.load(f)

    rows = [
        {
            "rank": rank,
            "qb_name": name,
            "team_2023": team,
            "tier": tier,
            "voting_median_2014_2023": avg,
            "source": data["source"],
            "source_url": data["source_url"],
        }
        for rank, name, team, tier, avg in data["rows"]
    ]

    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "rank", "qb_name", "team_2023", "tier",
            "voting_median_2014_2023", "source", "source_url",
        ])
        writer.writeheader()
        writer.writerows(rows)

    print(f"Wrote {len(rows)} rows to {OUT_PATH}")


if __name__ == "__main__":
    main()
