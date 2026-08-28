"""
Motivating question: national narrative says the Patriots' 2026 schedule is
much tougher than their 2025 one, after a 14-win season -- how worried
should that actually make you, in wins?

This project measures, historically, what happens to a team's win total
(and Pythagorean win total) the season after its strength of schedule (SOS)
swings hard in either direction, and sizes the effect against the much
bigger force already at work: ordinary mean reversion (good teams regress,
bad teams bounce back, regardless of schedule).

Three SOS measures, all on a "wins" scale so they're directly comparable:

  1. sos_actual_wins  -- retrospective. Average ACTUAL wins of a team's
     opponents in that SAME season. "How hard did this schedule really
     turn out to be." Computed here from game_results + win_totals
     (not precomputed anywhere else in nfl/sources/).
  2. sos_pyth_wins    -- retrospective, luck-adjusted. Same idea, but
     opponents' Pythagorean wins instead of their actual win-loss record,
     so a schedule doesn't look "hard" just because 3 opponents won a lot
     of one-score games. Also computed here.
  3. sos_next_yr_line -- prospective. Average Vegas preseason win-total
     line of a team's opponents in the FOLLOWING season -- the market's
     own forecast of how hard the upcoming schedule is. This one already
     exists as `sos_this_year_line` in
     nfl/sources/game_results/data/strength_of_schedule.csv; we just shift
     it back a year to attach season Y+1's schedule strength to season Y's
     row.

schedule_delta_actual = sos_next_yr_line - sos_actual_wins
schedule_delta_pyth   = sos_next_yr_line - sos_pyth_wins

Positive = schedule is projected to get harder than it actually was.

Outcomes:
  win_change      = actual_wins(Y+1) - actual_wins(Y)
  pyth_win_change = pyth_wins(Y+1)   - pyth_wins(Y)

Sample: seasons 2015-2024 paired with their following season (2016-2025),
32 teams/year -- every team-season where both years' data exist.
"""
import csv
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
NFL = os.path.join(REPO_ROOT, "nfl", "sources")

sys.path.insert(0, REPO_ROOT)


def load():
    games = pd.read_csv(os.path.join(NFL, "game_results", "data", "game_results.csv"))
    pyth = pd.read_csv(os.path.join(NFL, "game_results", "data", "team_point_diff.csv"))
    sos = pd.read_csv(os.path.join(NFL, "game_results", "data", "strength_of_schedule.csv"))
    wt = pd.read_csv(os.path.join(NFL, "win_totals", "data", "win_totals.csv"))
    return games, pyth, sos, wt


def build_same_season_sos(games, wt, pyth):
    """For every (year, team), avg opponent actual_wins and pyth_wins in
    that SAME season -- retrospective 'how hard was this schedule really.'"""
    home = games.rename(columns={"home_team": "team", "away_team": "opp"})[["year", "team", "opp"]]
    away = games.rename(columns={"away_team": "team", "home_team": "opp"})[["year", "team", "opp"]]
    long = pd.concat([home, away], ignore_index=True)

    wt_small = wt[["year", "team", "actual_wins"]].rename(columns={"team": "opp", "actual_wins": "opp_actual_wins"})
    pyth_small = pyth[["year", "team", "pyth_wins"]].rename(columns={"team": "opp", "pyth_wins": "opp_pyth_wins"})

    long = long.merge(wt_small, on=["year", "opp"], how="left")
    long = long.merge(pyth_small, on=["year", "opp"], how="left")

    agg = long.groupby(["year", "team"]).agg(
        n_games=("opp", "count"),
        sos_actual_wins=("opp_actual_wins", "mean"),
        sos_pyth_wins=("opp_pyth_wins", "mean"),
    ).reset_index()
    return agg


def main():
    games, pyth, sos, wt = load()

    same_season_sos = build_same_season_sos(games, wt, pyth)

    base = wt.merge(pyth, on=["year", "team"]).merge(same_season_sos, on=["year", "team"])
    base = base.merge(
        sos[["year", "team", "sos_this_year_line"]],
        on=["year", "team"],
        how="left",
    )

    # attach next season's own row (actual_wins, pyth_wins, sos_this_year_line)
    nxt = base[["year", "team", "actual_wins", "pyth_wins", "win_total_line", "sos_this_year_line"]].copy()
    nxt["year"] = nxt["year"] - 1  # shift back so it joins onto season Y as "Y+1 outcome"
    nxt = nxt.rename(columns={
        "actual_wins": "next_actual_wins",
        "pyth_wins": "next_pyth_wins",
        "win_total_line": "next_win_total_line",
        "sos_this_year_line": "sos_next_yr_line",
    })

    df = base.merge(nxt, on=["year", "team"], how="inner")

    df["win_change"] = df["next_actual_wins"] - df["actual_wins"]
    df["pyth_win_change"] = df["next_pyth_wins"] - df["pyth_wins"]
    df["schedule_delta_actual"] = df["sos_next_yr_line"] - df["sos_actual_wins"]
    df["schedule_delta_pyth"] = df["sos_next_yr_line"] - df["sos_pyth_wins"]
    df["luck"] = df["actual_wins"] - df["pyth_wins"]  # + = overperformed point diff

    df = df.sort_values(["team", "year"]).reset_index(drop=True)
    df.to_csv(os.path.join(DATA_DIR, "merged.csv"), index=False)

    print(f"n team-season pairs: {len(df)}  (years {df.year.min()}-{df.year.max()} -> {df.year.min()+1}-{df.year.max()+1})")
    print()

    # ---- 1. raw correlations ----
    print("=== Correlations with win_change ===")
    for col in ["schedule_delta_actual", "schedule_delta_pyth", "actual_wins", "pyth_wins", "luck"]:
        r = df[col].corr(df["win_change"])
        print(f"  {col:24s} r={r:+.3f}")
    print()
    print("=== Correlations with pyth_win_change ===")
    for col in ["schedule_delta_actual", "schedule_delta_pyth", "actual_wins", "pyth_wins", "luck"]:
        r = df[col].corr(df["pyth_win_change"])
        print(f"  {col:24s} r={r:+.3f}")
    print()

    # ---- 2. univariate: win_change ~ schedule_delta_actual ----
    def ols(y, X_cols, label):
        X = sm.add_constant(df[X_cols])
        model = sm.OLS(df[y], X, missing="drop").fit()
        print(f"--- {label} ---")
        print(f"  n={int(model.nobs)}  R2={model.rsquared:.3f}")
        for c in X_cols:
            print(f"  {c:24s} coef={model.params[c]:+.3f}  p={model.pvalues[c]:.3f}")
        print(f"  {'const':24s} coef={model.params['const']:+.3f}  p={model.pvalues['const']:.3f}")
        print()
        return model

    print("=== Regressions ===")
    ols("win_change", ["schedule_delta_actual"], "win_change ~ schedule_delta_actual (univariate)")
    ols("win_change", ["schedule_delta_actual", "actual_wins"],
        "win_change ~ schedule_delta_actual + actual_wins (mean-reversion controlled)")
    ols("pyth_win_change", ["schedule_delta_pyth"], "pyth_win_change ~ schedule_delta_pyth (univariate)")
    ols("pyth_win_change", ["schedule_delta_pyth", "pyth_wins"],
        "pyth_win_change ~ schedule_delta_pyth + pyth_wins (mean-reversion controlled)")

    # ---- 3. outlier scan: won a lot on an easy schedule, then schedule got much harder ----
    # Matched thresholds on both sides (bottom quartile of "how easy was the
    # schedule" x top quartile of "how much harder is it projected to get") --
    # an earlier version of this mixed a tercile cut with a quartile cut with
    # no principled reason for the two different splits. The result is stable
    # across quartile/tercile/median cuts (win_change in this bucket lands
    # -2.3 to -2.4 regardless), but the matched quartile/quartile cut below is
    # the one actually reported.
    print("=== Outlier scan: >=10 wins, bottom-quartile SOS (easy), top-quartile schedule_delta_actual (got much harder) ===")
    easy_thresh = df["sos_actual_wins"].quantile(0.25)
    delta_thresh = df["schedule_delta_actual"].quantile(0.75)
    cand = df[(df["actual_wins"] >= 10) & (df["sos_actual_wins"] <= easy_thresh) & (df["schedule_delta_actual"] >= delta_thresh)]
    cand = cand.sort_values("schedule_delta_actual", ascending=False)
    cols = ["team", "year", "actual_wins", "sos_actual_wins", "sos_next_yr_line", "schedule_delta_actual",
            "next_actual_wins", "win_change", "pyth_win_change"]
    print(cand[cols].to_string(index=False))
    print()
    print(f"  avg win_change in this bucket: {cand['win_change'].mean():+.2f}  (n={len(cand)})")

    league_avg_at_that_win_level = df[df["actual_wins"] >= 10]["win_change"].mean()
    print(f"  avg win_change for ALL >=10-win teams regardless of schedule: {league_avg_at_that_win_level:+.2f}  (n={len(df[df.actual_wins>=10])})")
    print()

    # ---- 4. reverse outlier: easy schedule -> stayed easy or got easier ----
    print("=== For contrast: >=10 wins, schedule got EASIER (bottom-quartile schedule_delta_actual) ===")
    delta_thresh_lo = df["schedule_delta_actual"].quantile(0.25)
    cand2 = df[(df["actual_wins"] >= 10) & (df["schedule_delta_actual"] <= delta_thresh_lo)]
    print(f"  avg win_change: {cand2['win_change'].mean():+.2f}  (n={len(cand2)})")
    print()

    # ---- 5. bucket table: schedule_delta_actual quartile x avg win_change, controlling roughly for start wins ----
    print("=== schedule_delta_actual quartile -> avg win_change (all teams) ===")
    df["delta_q"] = pd.qcut(df["schedule_delta_actual"], 4, labels=["Q1 (got easier)", "Q2", "Q3", "Q4 (got harder)"])
    print(df.groupby("delta_q", observed=True)["win_change"].agg(["mean", "count"]))
    print()

    # ---- 6. case study: Patriots 2025 -> 2026 ----
    # 2025 is a completed season (game_results/win_totals/team_point_diff all
    # have it). 2026's schedule isn't in game_results.csv yet (PFR future
    # schedule not fetched), so this section is hand-built from the public
    # 2026 opponent list -- see projects/schedule-swing-signal/README.md for
    # the source -- and priced with the live current-season market
    # (nfl/sources/kalshi_win_totals), not a Vegas preseason line (doesn't
    # exist yet for 2026).
    print("=== Case study: Patriots 2025 -> 2026 ===")
    ne_2025 = same_season_sos[(same_season_sos.year == 2025) & (same_season_sos.team == "NE")].iloc[0]
    ne_actual_wins_2025 = 14
    ne_pyth_wins_2025 = 12.46
    print(f"  2025 actual wins: {ne_actual_wins_2025}, pyth wins: {ne_pyth_wins_2025} (overperformed point diff by {ne_actual_wins_2025-ne_pyth_wins_2025:+.2f})")
    print(f"  2025 sos_actual_wins: {ne_2025.sos_actual_wins:.3f}  (league avg {same_season_sos[same_season_sos.year==2025].sos_actual_wins.mean():.3f}) -- rank 1/32 easiest")
    print(f"  2025 sos_pyth_wins:   {ne_2025.sos_pyth_wins:.3f}  (league avg {same_season_sos[same_season_sos.year==2025].sos_pyth_wins.mean():.3f}) -- rank 1/32 easiest")

    kalshi = pd.read_csv(os.path.join(NFL, "kalshi_win_totals", "data", "kalshi_win_totals.csv")).set_index("team")["expected_wins"]
    # 2026 opponents per patriots.com / NESN schedule release (AFC East x2,
    # full AFC West, full NFC North, plus PIT/JAX/SEA)
    ne_2026_opponents = ["BUF", "MIA", "NYJ"] * 2 + ["DEN", "LV", "GB", "MIN", "PIT"] + ["CHI", "DET", "KC", "LAC", "JAX", "SEA"]
    sos_next_market = np.mean([kalshi[t] for t in ne_2026_opponents])
    print(f"  2026 opponent avg Kalshi expected_wins: {sos_next_market:.3f}  (n={len(ne_2026_opponents)} games)")

    delta_actual = sos_next_market - ne_2025.sos_actual_wins
    delta_pyth = sos_next_market - ne_2025.sos_pyth_wins
    pct_actual = (df["schedule_delta_actual"] < delta_actual).mean() * 100
    pct_pyth = (df["schedule_delta_pyth"] < delta_pyth).mean() * 100
    print(f"  schedule_delta_actual: {delta_actual:+.3f}  ({pct_actual:.0f}th percentile of {len(df)} historical team-seasons)")
    print(f"  schedule_delta_pyth:   {delta_pyth:+.3f}  ({pct_pyth:.0f}th percentile)")

    m1 = ols("win_change", ["schedule_delta_actual", "actual_wins"], "(refit) win_change ~ schedule_delta_actual + actual_wins")
    pred_change = m1.params["const"] + m1.params["schedule_delta_actual"] * delta_actual + m1.params["actual_wins"] * ne_actual_wins_2025
    baseline_change = m1.params["const"] + m1.params["actual_wins"] * ne_actual_wins_2025
    print(f"  model-implied 2026 win_change: {pred_change:+.2f}  -> projected wins ~{ne_actual_wins_2025+pred_change:.1f}")
    print(f"    of which pure mean-reversion (schedule flat): {baseline_change:+.2f}")
    print(f"    incremental hit from this specific schedule swing: {pred_change-baseline_change:+.2f} wins")
    print(f"  (for reference, Kalshi's own live 2026 NE line is currently ~9.8 expected wins)")
    print()

    # ---- 7. level regression: pyth_wins(T) ~ opp_pyth_delta(T vs T-1) + pyth_wins(T-1) ----
    # Unlike section 2's models (which predict the CHANGE, and use a Vegas-line
    # proxy for one side of the schedule delta), this predicts the LEVEL of
    # pyth_wins(T) directly, and uses fully-hindsight opponent pyth-wins on
    # BOTH sides of the delta -- both T and T-1 are seasons that already
    # happened, so there's no market-forecast noise contaminating the
    # predictor. Cleaner estimate of the true historical relationship;
    # applying it to a not-yet-played season (2026) still requires swapping
    # in a market proxy for the unrealized side, same as section 6.
    print("=== Level regression: pyth_wins(T) ~ opp_pyth_delta + pyth_wins(T-1) ===")
    cur = pyth[["year", "team", "pyth_wins"]].merge(
        same_season_sos[["year", "team", "sos_pyth_wins"]], on=["year", "team"]
    ).rename(columns={"pyth_wins": "pyth_wins_T", "sos_pyth_wins": "sos_pyth_T"})
    prior = pyth[["year", "team", "pyth_wins"]].merge(
        same_season_sos[["year", "team", "sos_pyth_wins"]], on=["year", "team"]
    )
    prior["year"] = prior["year"] + 1
    prior = prior.rename(columns={"pyth_wins": "pyth_wins_T1", "sos_pyth_wins": "sos_pyth_T1"})
    lvl = cur.merge(prior, on=["year", "team"], how="inner")
    lvl["opp_pyth_delta"] = lvl["sos_pyth_T"] - lvl["sos_pyth_T1"]

    Xl = sm.add_constant(lvl[["opp_pyth_delta", "pyth_wins_T1"]])
    lm = sm.OLS(lvl["pyth_wins_T"], Xl).fit()
    print(f"  n={int(lm.nobs)} (seasons {lvl.year.min()}-{lvl.year.max()})  R2={lm.rsquared:.3f}")
    print(f"  const            {lm.params['const']:+.3f}  p={lm.pvalues['const']:.3f}")
    print(f"  opp_pyth_delta   {lm.params['opp_pyth_delta']:+.3f}  p={lm.pvalues['opp_pyth_delta']:.3f}")
    print(f"  pyth_wins_T1     {lm.params['pyth_wins_T1']:+.3f}  p={lm.pvalues['pyth_wins_T1']:.3f}")
    lvl.to_csv(os.path.join(DATA_DIR, "level_regression.csv"), index=False)

    ne_sos_pyth_2025 = same_season_sos[(same_season_sos.year == 2025) & (same_season_sos.team == "NE")]["sos_pyth_wins"].iloc[0]
    ne_opp_delta_2026 = sos_next_market - ne_sos_pyth_2025
    pct_lvl = (lvl["opp_pyth_delta"] < ne_opp_delta_2026).mean() * 100
    newX = pd.DataFrame({"const": [1], "opp_pyth_delta": [ne_opp_delta_2026], "pyth_wins_T1": [ne_pyth_wins_2025]})
    pi = lm.get_prediction(newX).summary_frame(alpha=0.10)
    pred_lvl = pi["mean"].iloc[0]
    baseline_lvl = lm.params["const"] + lm.params["pyth_wins_T1"] * ne_pyth_wins_2025
    print()
    print(f"  NE opp_pyth_delta 2026: {ne_opp_delta_2026:+.3f}  ({pct_lvl:.0f}th pct; exceeds the historical max of {lvl['opp_pyth_delta'].max():.3f} -- an out-of-sample extrapolation)")
    print(f"  predicted 2026 pyth_wins: {pred_lvl:.2f}  (90% prediction interval {pi['obs_ci_lower'].iloc[0]:.1f}-{pi['obs_ci_upper'].iloc[0]:.1f})")
    print(f"    of which pure mean-reversion off 2025 (delta=0): {baseline_lvl:.2f}")
    print(f"    incremental hit from this specific schedule swing: {pred_lvl-baseline_lvl:+.2f} wins")
    print()

    return df


if __name__ == "__main__":
    main()
