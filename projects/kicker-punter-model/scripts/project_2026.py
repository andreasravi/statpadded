"""
Combine team_offense_proxy_2026 (build_team_offense.py) + current_rosters_2026
(build_current_rosters.py) + per-player ability signals (analyze_ability.py)
into a final 2026 fantasy point projection per team's kicker and punter.

  KICKER: projected_fp_per_game = league_fit(team_2026_proxy) + player_ability_residual
  PUNTER: projected_fp_per_game = player's own bucket-skill history + flat_pt20_component
  projected_fp_season = projected_fp_per_game * PROJECTED_GAMES

Kickers and punters use different-shaped formulas on purpose. Both started
from the same team-offense-regression-plus-residual shape; a walk-forward
backtest found that shape works reasonably for kickers (beats a random pick
for the top 5) but loses to random picking for punters on 3 of 4 top-tier
metrics. The punter model was rebuilt around what actually survived
scrutiny: each punter's own skill history predicts real out-of-sample
signal (r²=0.106, beats random on every tier), while folding team offense
back in -- even switched to the more mechanistically-direct team PUNT
VOLUME feature -- made it WORSE, not better. So punters get a fixed,
non-team-specific PT20 expectation added to their own skill number; team
offense doesn't factor into the punter projection at all. (A kicker-specific
two-variable upgrade -- team offense + the kicker's own long-range-FG-
attempt history -- was also tried and rejected on kickers; a leak-free
walk-forward test didn't show a reliable improvement there.) See
analyze_ability.py and the README for both stories in full, including the
information-leak bug that made an early version of the kicker upgrade look
better than it really was.

For a player with no ability history (new_player with no career row, or an
"OPEN" job), the missing term defaults to the league average (ability
residual -> 0 for kickers, bucket-skill history -> league average for
punters) -- i.e. the projection is just "whatever a league-average
kicker/punter would score," the most defensible number for an unknown, and
the flag makes clear that's what happened.

Inputs:
  data/team_offense_proxy.csv
  data/current_rosters_2026.csv
  data/kicker_ability.csv
  data/punter_ability.csv

Output:
  data/projections_2026.csv
"""
import csv
import os
import sys

import pandas as pd

from analyze_ability import kicker_ability, punter_ability, load_team_points  # noqa: E402

HERE = os.path.dirname(os.path.dirname(__file__))
OUT_CSV = os.path.join(HERE, "data", "projections_2026.csv")

TEAM_OFFENSE_CSV = os.path.join(HERE, "data", "team_offense_proxy.csv")
ROSTERS_CSV = os.path.join(HERE, "data", "current_rosters_2026.csv")
KICKER_ABILITY_CSV = os.path.join(HERE, "data", "kicker_ability.csv")
PUNTER_ABILITY_CSV = os.path.join(HERE, "data", "punter_ability.csv")

PROJECTED_GAMES = 17


def build():
    team_offense = pd.read_csv(TEAM_OFFENSE_CSV)
    rosters = pd.read_csv(ROSTERS_CSV)

    # (re)derive the two league-wide fits AND their per-player ability
    # tables in one pass -- this also (re)writes kicker_ability.csv /
    # punter_ability.csv, so the ability lookups below always use the
    # freshest data, not a possibly-stale on-disk copy from a prior run.
    tp = load_team_points()
    k_fit = kicker_ability(tp)
    p_fit = punter_ability(tp, team_var="point_diff_pg")
    kicker_ab = k_fit["ability"]
    punter_ab = p_fit["ability"]

    rows = []
    for _, roster_row in rosters.iterrows():
        team = roster_row["team"]
        offense_row = team_offense[team_offense["team"] == team]
        if offense_row.empty:
            continue
        offense_row = offense_row.iloc[0]
        team_ppg_2026 = offense_row["team_offense_proxy_2026"] / PROJECTED_GAMES

        # kicker
        kicker = roster_row["kicker"]
        k_residual = 0.0
        k_has_history = False
        if kicker != "OPEN" and kicker in kicker_ab.index:
            k_residual = kicker_ab.loc[kicker, "ability_residual"]
            k_has_history = True
        k_pred_pg = k_fit["intercept"] + k_fit["slope"] * team_ppg_2026 + k_residual
        k_pred_season = round(k_pred_pg * PROJECTED_GAMES, 1)

        # punter -- own skill history + a flat (non-team-specific) PT20
        # expectation; team offense does not factor in here, see docstring
        punter = roster_row["punter"]
        p_bucket_skill = p_fit["league_avg_bucket"]
        p_has_history = False
        if punter != "OPEN" and punter in punter_ab.index:
            p_bucket_skill = punter_ab.loc[punter, "own_bucket_skill_history"]
            p_has_history = True
        p_pred_pg = p_bucket_skill + p_fit["flat_pt20_component"]
        p_pred_season = round(p_pred_pg * PROJECTED_GAMES, 1)

        rows.append({
            "team": team,
            "kicker": kicker,
            "kicker_new_player": roster_row["kicker_new_player"],
            "kicker_unstable_team": roster_row["kicker_unstable_team"],
            "kicker_has_ability_history": k_has_history,
            "kicker_ability_residual": round(k_residual, 2),
            "kicker_projected_fp_per_game": round(k_pred_pg, 2),
            "kicker_projected_fp_season": k_pred_season,
            "punter": punter,
            "punter_new_player": roster_row["punter_new_player"],
            "punter_unstable_team": roster_row["punter_unstable_team"],
            "punter_has_ability_history": p_has_history,
            "punter_own_bucket_skill_history": round(p_bucket_skill, 3),
            "punter_projected_fp_per_game": round(p_pred_pg, 2),
            "punter_projected_fp_season": p_pred_season,
        })

    out = pd.DataFrame(rows).sort_values("kicker_projected_fp_season", ascending=False)
    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    out.to_csv(OUT_CSV, index=False)
    print(f"Wrote {len(out)} teams -> {OUT_CSV}")
    return out


if __name__ == "__main__":
    sys.path.insert(0, os.path.dirname(__file__))
    build()
