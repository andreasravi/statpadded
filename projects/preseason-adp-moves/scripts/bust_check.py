"""
Which players busted hardest relative to their preseason (August) ADP by
the *end* of that same season — and how many of those busts are explained
by a preseason (i.e. before Week 1) injury?

Unlike analyze.py (which compares two different ADP reads to each other),
this compares Underdog's August ADP for season Y straight to that same
season Y's actual fantasy finish (nfl/sources/fantasy_finish) — both same
source, same format, so no cross-source correction is needed, and QBs can
be included.

For 2025, Underdog's own `Notes` column already tags some players as
already dealing with a preseason injury/suspension as of the August
article — i.e. *before* the season even started. Joining that against the
actual 2025 finish directly answers the question: did the players already
flagged hurt in August go on to bust, and by how much? For 2023/2024
(no `Notes` column that year), the biggest unexplained busts are listed
for manual/external verification instead of guessed at.

2025 also has a `per_game_finish` in addition to `season_finish` — a big
gap between the two (good per-game finish, bad season/total finish) is
itself a signature of missed games rather than a talent bust, so it's
reported as a secondary check.

Inputs:
  nfl/sources/underdog_adp/data/underdog_adp.csv
  nfl/sources/fantasy_finish/data/fantasy_finish.csv

Outputs (data/):
  busts_<year>.csv

Run:
  python3 projects/preseason-adp-moves/scripts/bust_check.py
"""
import os
import re

import pandas as pd

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..", "..")
UD_PATH = os.path.join(ROOT, "nfl", "sources", "underdog_adp", "data", "underdog_adp.csv")
FINISH_PATH = os.path.join(ROOT, "nfl", "sources", "fantasy_finish", "data", "fantasy_finish.csv")
OUT_DIR = os.path.join(HERE, "..", "data")

TOP_N = 25


def norm_name(name):
    name = (name or "").strip()
    name = re.sub(r"[.']", "", name)
    name = re.sub(r"\s+(Jr|Sr|II|III|IV|V)$", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).lower().strip()


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ud = pd.read_csv(UD_PATH)
    finish = pd.read_csv(FINISH_PATH)
    ud["key"] = ud["player"].apply(norm_name)
    finish["key"] = finish["player"].apply(norm_name)

    for year in (2023, 2024, 2025):
        pre = ud[ud.year == year].copy()
        post = finish[finish.year == year][["key", "season_finish", "per_game_finish"]]
        merged = pre.merge(post, on="key", how="inner")

        # Players ranked in Underdog's preseason top 200 who never post a
        # ranked finish at all that season didn't just bust, they
        # vanished (season-ending or near-total loss). Flag those
        # separately rather than dropping them — they're the clearest
        # preseason-injury candidates of all, and an inner-join miss
        # already excludes anyone else this note applies to.
        matched_keys = set(merged["key"])
        vanished = pre[(pre["rank"] <= 200) & (~pre["key"].isin(matched_keys))]

        merged["miss"] = merged["season_finish"] - merged["rank"]
        merged = merged.sort_values("miss", ascending=False)

        cols = ["rank", "player", "team", "pos", "adp", "season_finish", "miss"]
        if "per_game_finish" in merged.columns and merged["per_game_finish"].notna().any():
            merged["missed_time_gap"] = merged["season_finish"] - merged["per_game_finish"]
            cols += ["per_game_finish", "missed_time_gap"]
        if "notes" in merged.columns and merged["notes"].notna().any():
            cols.append("notes")

        top = merged.head(TOP_N)
        top[cols].to_csv(os.path.join(OUT_DIR, f"busts_{year}.csv"), index=False)

        print(f"\n=== {year}: top {TOP_N} busts (August ADP rank vs. actual "
              f"season finish) ===")
        print(top[cols].to_string(index=False))

        if len(vanished):
            print(f"\n{year}: {len(vanished)} preseason top-200 player(s) with "
                  f"no ranked finish at all that season (likely missed "
                  f"most/all of it):")
            vcols = ["rank", "player", "team", "pos", "adp"]
            if "notes" in vanished.columns and vanished["notes"].notna().any():
                vcols.append("notes")
            print(vanished[vcols].sort_values("rank").to_string(index=False))

        if "notes" in merged.columns and merged["notes"].notna().any():
            flagged_in_top = top["notes"].notna().sum()
            flagged_overall = merged["notes"].notna().sum()
            print(f"\n{year}: {flagged_in_top}/{TOP_N} of the biggest busts "
                  f"were already Notes-flagged in August "
                  f"(injury/suspension/etc.), vs {flagged_overall}/{len(merged)} "
                  f"flagged overall.")


if __name__ == "__main__":
    main()
