"""
Two things happen here:

1. KICKER "opportunity-adjusted ability" -- regress each kicker-season's
   fantasy points/game on that team's points/game that season (more scoring
   drives = more FGA/PAT = more opportunity). The residual (actual - what a
   league-average kicker would have scored with that same offense) is the
   kicker's own skill, stripped of how good their offense was. Recency-
   weighted (decay 0.6/year) across each kicker's available seasons ->
   data/kicker_ability.csv.

   A candidate improvement was tried and NOT adopted: swapping in the
   kicker's own recency-weighted 50+ yard FG-attempt history (a coach's
   known trust in that kicker's leg from distance -- real points under this
   league's yardage-scored FG formula) as a second predictor. A first pass
   at this looked like a big win (out-of-sample r² roughly doubled), but
   that test had a real information leak: it computed each player's
   long-range-history feature using their FULL prior-seasons average
   relative to the target year and applied that SAME number to every one of
   that player's training rows -- so an early training row could "see"
   data from a later training row for the same player. Once rebuilt with a
   proper expanding window (each row uses strictly-earlier seasons only,
   see backtest.py's `fit_and_predict(..., long_range_col=...)` for the
   corrected version), the improvement mostly disappeared and even hurt the
   top tier on the 2 years of data available for testing it (this feature
   needs 2+ prior seasons per kicker, which only leaves 2 of the 3 backtest
   years usable). `nfl/sources/kickers/data/kicking_stats.csv` still
   carries the fga_50plus/fgm_50plus columns (they're informative on their
   own, and cheap to keep), and backtest.py still supports testing this
   properly -- but there isn't enough data on hand yet to call it either a
   real improvement or noise, so the production model here stays the
   single-variable version, not this candidate.

2. PUNTER exploration + ability -- the brief asked to "explore openly" since
   it's not obvious a punter's scoring should track team offense at all
   (more like the opposite: a bad offense punts more, so more opportunity
   for PT20 volume, independent of leg skill). punter_exploration() prints:
     - correlation of punter fantasy points/game, punts/game, and points/punt
       (skill, not volume) against team points-for/game, points-against/game,
       and point differential/game
     - year-over-year autocorrelation of fantasy points/game, PLAYER-level
       (same punter, consecutive years) vs TEAM-level (same team, whoever
       punted for them, consecutive years) -- which one actually predicts
       next year's number better tells you whether to project the player or
       the depth chart slot.

   punter_ability() originally built a team-offense-regression-plus-residual
   model, same shape as kicker_ability(). That was replaced after a
   walk-forward test found it loses to a random-pick baseline on 3 of 4
   top-tier metrics (see README). The natural next candidate -- team PUNT
   VOLUME specifically, which unlike PT20 rate has real year-over-year
   persistence (team-level r=0.36) -- was tested properly (leak-free, no
   OLS self-reference) via an ablation: team-volume-only, player-skill-only,
   and both combined. Player skill ALONE won clearly (r²=0.106 vs 0.048
   combined vs 0.005 team-volume-only) -- team punt volume is real and
   persistent as its own number, but too noisy a translation into an
   individual punter's score to help. So the model here is now: each
   punter's own recency-weighted avg_bucket_points_per_game (skill) plus a
   FLAT (not team-specific) league-average PT20 contribution -- team offense
   doesn't drive the punter prediction at all anymore, only the exploration
   diagnostics above (which are still useful in their own right) -> writes
   data/punter_ability.csv.

Inputs:
  nfl/sources/kickers/data/kicking_stats.csv
  nfl/sources/punters/data/punting_stats.csv
  nfl/sources/game_results/data/team_point_diff.csv

Outputs:
  data/kicker_ability.csv
  data/punter_ability.csv
  prints the punter exploration to stdout (see README for the write-up)
"""
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

HERE = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))

KICKING_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "kickers", "data", "kicking_stats.csv")
PUNTING_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "punters", "data", "punting_stats.csv")
POINT_DIFF_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "game_results", "data", "team_point_diff.csv")

KICKER_ABILITY_CSV = os.path.join(HERE, "data", "kicker_ability.csv")
PUNTER_ABILITY_CSV = os.path.join(HERE, "data", "punter_ability.csv")

RECENCY_DECAY = 0.6  # weight multiplier per year of age; most-recent season gets the most weight
MIN_GAMES = 4  # drop cameo stints (injury replacements, one-game emergency kicks) from ability calc


def recency_weighted_mean(group, value_col, year_col="year", decay=RECENCY_DECAY):
    max_year = group[year_col].max()
    weights = decay ** (max_year - group[year_col])
    return float(np.average(group[value_col], weights=weights))


def load_team_points():
    pd_df = pd.read_csv(POINT_DIFF_CSV)
    pd_df["points_for_pg"] = pd_df["points_for"] / pd_df["games"]
    pd_df["points_against_pg"] = pd_df["points_against"] / pd_df["games"]
    pd_df["point_diff_pg"] = pd_df["avg_point_diff"]
    return pd_df[["year", "team", "points_for_pg", "points_against_pg", "point_diff_pg"]]


def kicker_ability(team_points: pd.DataFrame) -> dict:
    k = pd.read_csv(KICKING_CSV)
    k = k[k["games"] >= MIN_GAMES].copy()
    k = k.merge(team_points, on=["year", "team"], how="left")

    slope, intercept, r, p, se = stats.linregress(k["points_for_pg"], k["fantasy_points_per_game"])
    print(f"[kicker] fantasy_pts/gm ~ team points_for/gm: slope={slope:.3f} intercept={intercept:.3f} "
          f"r={r:.3f} r2={r*r:.3f} p={p:.4f}  (n={len(k)})")

    k["predicted_fp_per_game"] = intercept + slope * k["points_for_pg"]
    k["ability_residual"] = k["fantasy_points_per_game"] - k["predicted_fp_per_game"]

    rows = []
    for player, g in k.groupby("player"):
        rows.append({
            "player": player,
            "seasons": len(g),
            "years": ",".join(str(y) for y in sorted(g["year"])),
            "last_team": g.sort_values("year").iloc[-1]["team"],
            "career_fp_per_game": round(recency_weighted_mean(g, "fantasy_points_per_game"), 2),
            "ability_residual": round(recency_weighted_mean(g, "ability_residual"), 2),
        })
    out = pd.DataFrame(rows).sort_values("ability_residual", ascending=False)
    os.makedirs(os.path.dirname(KICKER_ABILITY_CSV), exist_ok=True)
    out.to_csv(KICKER_ABILITY_CSV, index=False)
    print(f"Wrote {len(out)} kickers -> {KICKER_ABILITY_CSV}")
    return {"intercept": intercept, "slope": slope, "r2": r * r, "ability": out.set_index("player")}


def punter_exploration(p: pd.DataFrame):
    print("\n[punter] correlation exploration (team var vs punter outcome, pearson r):")
    for outcome in ["fantasy_points_per_game", "punts", "avg_bucket_points_per_game"]:
        p["_per_game"] = p[outcome] / p["games"] if outcome == "punts" else p[outcome]
        for team_var in ["points_for_pg", "points_against_pg", "point_diff_pg"]:
            r, pv = stats.pearsonr(p["_per_game"], p[team_var])
            print(f"    {outcome:>24s} vs {team_var:<18s} r={r:+.3f} (p={pv:.3f})")

    print("\n[punter] year-over-year autocorrelation of fantasy_points_per_game:")
    p_sorted = p.sort_values(["player", "year"])
    p_sorted["next_year"] = p_sorted["year"] + 1

    # player-level: same punter, consecutive years
    merged_player = p_sorted.merge(
        p_sorted[["player", "year", "fantasy_points_per_game"]].rename(
            columns={"year": "next_year", "fantasy_points_per_game": "fp_next"}),
        on=["player", "next_year"], how="inner")
    if len(merged_player) >= 3:
        r_player, pv_player = stats.pearsonr(merged_player["fantasy_points_per_game"], merged_player["fp_next"])
        print(f"    PLAYER-level (same punter, yr t vs t+1): r={r_player:+.3f} (p={pv_player:.3f}, n={len(merged_player)})")
    else:
        r_player = None
        print(f"    PLAYER-level: n too small ({len(merged_player)})")

    # team-level: same team, whoever punted, consecutive years (aggregate to team-year first)
    team_year = p.groupby(["team", "year"])[["fantasy_points_per_game", "games"]].apply(
        lambda g: pd.Series({"fantasy_points_per_game": np.average(g["fantasy_points_per_game"], weights=g["games"])})
    ).reset_index()
    team_year["next_year"] = team_year["year"] + 1
    merged_team = team_year.merge(
        team_year[["team", "year", "fantasy_points_per_game"]].rename(
            columns={"year": "next_year", "fantasy_points_per_game": "fp_next"}),
        on=["team", "next_year"], how="inner")
    r_team, pv_team = stats.pearsonr(merged_team["fantasy_points_per_game"], merged_team["fp_next"])
    print(f"    TEAM-level (same team slot, yr t vs t+1):   r={r_team:+.3f} (p={pv_team:.3f}, n={len(merged_team)})")

    return {"r_player_yoy": r_player, "r_team_yoy": r_team}


def punter_ability(team_points: pd.DataFrame, team_var="point_diff_pg") -> dict:
    """Predicts fantasy_points_per_game as:

        player's own recency-weighted avg_bucket_points_per_game (skill)
      + league-average punts/game * league-average PT20-rate/punt (a flat
        constant, same for everyone -- NOT team-specific)

    This replaced an original team-offense-regression-plus-residual model
    (same shape as kicker_ability()) after a walk-forward test found it
    doesn't hold up well against a random-pick baseline for the top tier
    (see README's "did I just get lucky" section for the exact comparison).
    A natural next idea -- swap in team PUNT VOLUME specifically, since it
    has real year-over-year persistence (r=0.36, team-level) unlike PT20
    RATE (r=0.06-0.09, unpredictable either way) -- was tested properly and
    is NOT used here either: an ablation (team-volume-only vs
    player-skill-only vs both combined) found player skill alone clearly
    wins on every tier metric, and adding team volume back in on top of it
    makes it WORSE, not better (r² 0.106 skill-only vs 0.048 combined vs
    0.005 team-volume-only) -- team punt volume is real and persistent as
    its own number, but too noisy a translation into an individual punter's
    score to help this model. So team offense doesn't factor into the
    punter ability calculation at all anymore; `team_points`/`team_var` are
    still accepted (and used by punter_exploration for the diagnostic
    correlations, which remain informative) but no longer drive the
    prediction.
    """
    p = pd.read_csv(PUNTING_CSV)
    p = p[p["games"] >= MIN_GAMES].copy()
    p = p.merge(team_points, on=["year", "team"], how="left")

    explore_result = punter_exploration(p)

    league_avg_pt20_rate = (p["pt20_points"] / p["punts"]).mean()
    team_punts_pg = p.groupby(["team", "year"]).apply(
        lambda g: g["punts"].sum() / g["games"].max(), include_groups=False)
    league_avg_punts_pg = team_punts_pg.mean()
    flat_pt20_component = league_avg_punts_pg * league_avg_pt20_rate
    print(f"\n[punter] skill-based model: flat PT20 component = {league_avg_punts_pg:.1f} punts/gm "
          f"* {league_avg_pt20_rate:.3f} pts/punt = {flat_pt20_component:.2f} pts/gm (same for every punter); "
          f"the rest comes from each punter's own avg_bucket_points_per_game history")

    p["predicted_fp_per_game"] = p["avg_bucket_points_per_game"] + flat_pt20_component
    r, pv = stats.pearsonr(p["predicted_fp_per_game"], p["fantasy_points_per_game"])
    print(f"[punter] same-season fit check: r={r:.3f} r2={r*r:.3f}  (n={len(p)}) "
          f"-- see README for the real out-of-sample walk-forward number")

    rows = []
    for player, g in p.groupby("player"):
        rows.append({
            "player": player,
            "seasons": len(g),
            "years": ",".join(str(y) for y in sorted(g["year"])),
            "last_team": g.sort_values("year").iloc[-1]["team"],
            "career_fp_per_game": round(recency_weighted_mean(g, "fantasy_points_per_game"), 2),
            "own_bucket_skill_history": round(recency_weighted_mean(g, "avg_bucket_points_per_game"), 3),
        })
    out = pd.DataFrame(rows).sort_values("own_bucket_skill_history", ascending=False)
    os.makedirs(os.path.dirname(PUNTER_ABILITY_CSV), exist_ok=True)
    out.to_csv(PUNTER_ABILITY_CSV, index=False)
    print(f"Wrote {len(out)} punters -> {PUNTER_ABILITY_CSV}")
    return {
        "flat_pt20_component": flat_pt20_component,
        "league_avg_bucket": p["avg_bucket_points_per_game"].mean(),
        "ability": out.set_index("player"),
        **explore_result,
    }


if __name__ == "__main__":
    tp = load_team_points()
    kicker_fit = kicker_ability(tp)
    punter_fit = punter_ability(tp, team_var="point_diff_pg")
