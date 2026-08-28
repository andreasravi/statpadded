"""
Walk-forward backtest: how predictive is the model, actually?

For each target year Y in {2023, 2024, 2025}, everything is refit using
ONLY seasons strictly before Y (no lookahead). Kickers use the league-wide
points-for -> fantasy-points regression plus each kicker's recency-weighted
ability residual (fit_and_predict), with the team offense proxy scaled
toward that year's ACTUAL preseason market win total from
nfl/sources/win_totals (known before Y kicks off, so this isn't leakage
either). Punters use a different, team-offense-FREE model
(fit_and_predict_punter_skill) -- each punter's own recency-weighted skill
history plus a flat league-average PT20 expectation -- after team-offense
and team-punt-volume versions were both tested and found to underperform
it; see analyze_ability.py and the README for that whole story. Either way,
the prediction is compared against what actually happened in year Y, for
every kicker/punter who actually played that year.

Two things get scored:

1. TOTAL POINTS -- predicted fp/game * that player's actual games played
   in Y, vs. their actual season fantasy_points. Reported as Pearson r,
   R^2, and RMSE, alongside two naive baselines for context:
     - "last year"    -- literally that player's prior-season fp/game * this
                          year's games (only defined for players with a
                          prior season -- most useful, most literal baseline)
     - "league average" -- the flat league-average fp/game that period,
                          * this year's games (a *make no distinctions at
                          all* floor -- beating this is the low bar)

2. VORP -- fantasy value is relative, not absolute: a good kicker projection
   matters for how it ranks against the replacement-level option (whoever
   you can add off waivers), not its raw point total. Replacement level is
   set at REPLACEMENT_RANK (default 12th-best that year -- a reasonable
   single-K/single-P, ~12-team league assumption; change the constant if
   your league is sized differently) among that year's ACTUAL performers
   for actual VORP, and among that year's PREDICTED performers for
   predicted VORP. Reports Pearson r, Spearman rank correlation (arguably
   the more relevant number for "does this get draft value right"), and a
   top-10-VORP overlap count.

Run: python3 backtest.py
"""
import os
import sys

import numpy as np
import pandas as pd
import statsmodels.api as sm
from scipy import stats

HERE = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.dirname(__file__))

KICKING_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "kickers", "data", "kicking_stats.csv")
PUNTING_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "punters", "data", "punting_stats.csv")
POINT_DIFF_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "game_results", "data", "team_point_diff.csv")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")

TARGET_YEARS = [2023, 2024, 2025]
MIN_GAMES = 4
RECENCY_DECAY = 0.6
SCALE_MIN, SCALE_MAX = 0.7, 1.4
REPLACEMENT_RANK = 12  # single-K/single-P, ~12-team league assumption -- change to fit your league size


def recency_weighted_mean(group, value_col, year_col, target_year, decay=RECENCY_DECAY):
    weights = decay ** (target_year - 1 - group[year_col])  # most recent prior year gets weight decay^0
    return float(np.average(group[value_col], weights=weights))


def team_proxy_for_year(target_year: int, team_var: str) -> pd.DataFrame:
    """Recency-weighted avg of `team_var` (points_for_pg or point_diff_pg)
    over years < target_year, scaled toward that year's ACTUAL preseason
    win-total line (known before the season -- not lookahead)."""
    pf = pd.read_csv(POINT_DIFF_CSV)
    pf["points_for_pg"] = pf["points_for"] / pf["games"]
    pf["point_diff_pg"] = pf["avg_point_diff"]
    wt = pd.read_csv(WIN_TOTALS_CSV)[["year", "team", "win_total_line", "actual_wins"]]

    prior = pf[pf["year"] < target_year].copy()
    if prior.empty:
        return pd.DataFrame(columns=["team", f"{team_var}_proxy"])
    prior["weight"] = RECENCY_DECAY ** (target_year - 1 - prior["year"])
    # cap history depth implicitly via decay; just use last 3 prior years like the real pipeline
    prior = prior[prior["year"] >= target_year - 3]

    wins_by_key = wt.set_index(["year", "team"])["actual_wins"]

    def _team_recency(g):
        team = g.name
        wins = wins_by_key.reindex([(yr, team) for yr in g["year"]]).to_numpy()
        return pd.Series({
            f"{team_var}_recency": np.average(g[team_var], weights=g["weight"]),
            "recency_wins": np.average(wins, weights=g["weight"]),
        })

    recency = prior.groupby("team")[[team_var, "weight", "year"]].apply(_team_recency).reset_index()

    line_this_year = wt[wt["year"] == target_year][["team", "win_total_line"]].rename(
        columns={"win_total_line": "line_2026_equivalent"})
    m = recency.merge(line_this_year, on="team", how="inner")

    if team_var == "points_for_pg":
        scale = (m["line_2026_equivalent"] / m["recency_wins"]).clip(SCALE_MIN, SCALE_MAX)
        m[f"{team_var}_proxy"] = m[f"{team_var}_recency"] * scale
    else:
        # point_diff: additive shift using the league-wide wins-per-point-of-diff slope, fit on prior data only
        prior_all = pf[pf["year"] < target_year].merge(wt[["year", "team", "actual_wins"]], on=["year", "team"])
        slope, intercept, r, p, se = stats.linregress(prior_all["point_diff_pg"], prior_all["actual_wins"])
        win_delta = m["line_2026_equivalent"] - m["recency_wins"]
        m[f"{team_var}_proxy"] = m[f"{team_var}_recency"] + win_delta / slope

    return m[["team", f"{team_var}_proxy"]]


def _expanding_recency_mean(g_sorted, value_col, as_of_year, decay=RECENCY_DECAY):
    prior = g_sorted[g_sorted["year"] < as_of_year]
    if prior.empty:
        return None
    weights = decay ** (as_of_year - 1 - prior["year"])
    return float(np.average(prior[value_col], weights=weights))


def fit_and_predict(stats_csv, team_var, target_year, long_range_col=None):
    """long_range_col=None is the production model for both positions
    (team-offense-fit-plus-residual). Passing a column name (e.g. kickers'
    "fga_50plus") switches to an experimental two-variable team-offense +
    own-long-range-history model instead, with a proper no-lookahead
    expanding window on the history feature. This was tried as a kicker
    upgrade -- an earlier, leakier version of this same idea looked like a
    clear win, but the corrected version here didn't reliably beat the
    production model on the ~2 years of data available to test it (needs
    2+ prior seasons per kicker, which drops one of the three backtest
    years). Kept here, unused by run() by default, in case more seasons of
    history make this worth revisiting later -- see analyze_ability.py and
    the README for the full story."""
    df = pd.read_csv(stats_csv)
    df = df[df["games"] >= MIN_GAMES].copy()

    pf = pd.read_csv(POINT_DIFF_CSV)
    pf["points_for_pg"] = pf["points_for"] / pf["games"]
    pf["point_diff_pg"] = pf["avg_point_diff"]
    df = df.merge(pf[["year", "team", team_var]], on=["year", "team"], how="left")

    prior = df[df["year"] < target_year].dropna(subset=[team_var])
    actual = df[df["year"] == target_year].copy()
    if len(prior) < 10 or actual.empty:
        return None

    last_year_fp_pg = {player: g.sort_values("year").iloc[-1]["fantasy_points_per_game"]
                        for player, g in prior.groupby("player")}
    league_avg_fp_pg = prior["fantasy_points_per_game"].mean()

    team_proxy = team_proxy_for_year(target_year, team_var)
    actual = actual.merge(team_proxy, on="team", how="left")
    proxy_col = f"{team_var}_proxy"
    actual = actual.dropna(subset=[proxy_col])

    if long_range_col is None:
        slope, intercept, r, p, se = stats.linregress(prior[team_var], prior["fantasy_points_per_game"])
        prior = prior.copy()
        prior["predicted_fp_per_game"] = intercept + slope * prior[team_var]
        prior["ability_residual"] = prior["fantasy_points_per_game"] - prior["predicted_fp_per_game"]
        ability = {player: recency_weighted_mean(g, "ability_residual", "year", target_year)
                   for player, g in prior.groupby("player")}
        actual["predicted_fp_per_game"] = intercept + slope * actual[proxy_col] + actual["player"].map(ability).fillna(0.0)
        actual["had_prior_history"] = actual["player"].isin(ability)
    else:
        df["long_pg"] = df[long_range_col] / df["games"]
        prior = df[df["year"] < target_year].dropna(subset=[team_var]).copy()
        prior["own_long_hist_prior"] = pd.to_numeric(pd.Series([
            _expanding_recency_mean(df[df["player"] == row["player"]], "long_pg", row["year"])
            for _, row in prior.iterrows()
        ], index=prior.index))
        train = prior.dropna(subset=["own_long_hist_prior"])
        if len(train) < 10:
            # not enough seasons of history yet to build the expanding-window
            # feature (e.g. the first target year, with only one prior season
            # on record for anyone) -- nothing to fit, skip this year cleanly
            return None
        X = sm.add_constant(train[[team_var, "own_long_hist_prior"]])
        model = sm.OLS(train["fantasy_points_per_game"], X).fit()
        own_long_full = {player: recency_weighted_mean(g, "long_pg", "year", target_year)
                          for player, g in prior.groupby("player")}
        league_avg_long = prior["long_pg"].mean()
        actual["predicted_fp_per_game"] = (
            model.params["const"] + model.params[team_var] * actual[proxy_col]
            + model.params["own_long_hist_prior"] * actual["player"].map(own_long_full).fillna(league_avg_long)
        )
        actual["had_prior_history"] = actual["player"].isin(own_long_full)

    actual["predicted_fp_season"] = actual["predicted_fp_per_game"] * actual["games"]
    actual["naive_last_year_fp_pg"] = actual["player"].map(last_year_fp_pg)
    actual["naive_last_year_fp_season"] = actual["naive_last_year_fp_pg"] * actual["games"]
    actual["naive_league_avg_fp_season"] = league_avg_fp_pg * actual["games"]
    return actual


def fit_and_predict_punter_skill(target_year):
    """The production punter model (see analyze_ability.py's punter_ability
    for the full story of how this was chosen over a team-offense-based
    model): each punter's own recency-weighted avg_bucket_points_per_game
    (skill) plus a FLAT, non-team-specific PT20 expectation. No OLS fit at
    all -- both components are direct prior-years-only averages -- so
    there's no self-reference/leakage risk the way the kicker long-range
    candidate had."""
    p = pd.read_csv(PUNTING_CSV)
    p = p[p["games"] >= MIN_GAMES].copy()

    prior = p[p["year"] < target_year]
    actual = p[p["year"] == target_year].copy()
    if len(prior) < 10 or actual.empty:
        return None

    last_year_fp_pg = {player: g.sort_values("year").iloc[-1]["fantasy_points_per_game"]
                        for player, g in prior.groupby("player")}
    league_avg_fp_pg = prior["fantasy_points_per_game"].mean()

    league_avg_pt20_rate = (prior["pt20_points"] / prior["punts"]).mean()
    team_punts_pg = prior.groupby(["team", "year"]).apply(
        lambda g: g["punts"].sum() / g["games"].max(), include_groups=False)
    flat_pt20_component = team_punts_pg.mean() * league_avg_pt20_rate

    bucket_hist = {player: recency_weighted_mean(g, "avg_bucket_points_per_game", "year", target_year)
                   for player, g in prior.groupby("player")}
    league_avg_bucket = prior["avg_bucket_points_per_game"].mean()

    actual["predicted_fp_per_game"] = actual["player"].map(bucket_hist).fillna(league_avg_bucket) + flat_pt20_component
    actual["predicted_fp_season"] = actual["predicted_fp_per_game"] * actual["games"]
    actual["naive_last_year_fp_pg"] = actual["player"].map(last_year_fp_pg)
    actual["naive_last_year_fp_season"] = actual["naive_last_year_fp_pg"] * actual["games"]
    actual["naive_league_avg_fp_season"] = league_avg_fp_pg * actual["games"]
    actual["had_prior_history"] = actual["player"].isin(bucket_hist)
    return actual


def _corr(a, pred_col, actual_col):
    d = a.dropna(subset=[pred_col, actual_col])
    if len(d) < 3:
        return None
    r, p = stats.pearsonr(d[pred_col], d[actual_col])
    rmse = float(np.sqrt(np.mean((d[pred_col] - d[actual_col]) ** 2)))
    return {"r": r, "r2": r * r, "rmse": rmse, "n": len(d)}


def score_predictions(label, actual):
    """Total-points comparison. NOTE: both the model's and the naive
    baselines' season totals are (predicted rate) * (that player's ACTUAL
    games played in year Y) -- i.e. real playing time is known in hindsight
    for everyone here, which flatters all three approaches roughly equally
    (a real preseason projection wouldn't get that) and is exactly why the
    naive "league average rate" baseline does about as well as the model on
    total points below -- most of the swing in total points is just "who
    stayed healthy/employed," not who scored fast per game. See the
    game-per-game RATE comparison for the part the model actually earns."""
    a = actual.dropna(subset=["fantasy_points"])

    model = _corr(a, "predicted_fp_season", "fantasy_points")
    naive_last = _corr(a, "naive_last_year_fp_season", "fantasy_points")
    naive_avg = _corr(a, "naive_league_avg_fp_season", "fantasy_points")
    print(f"  [{label}] TOTAL POINTS -- model:        r={model['r']:+.3f} r2={model['r2']:.3f} "
          f"rmse={model['rmse']:.1f}  (n={model['n']})")
    if naive_last:
        print(f"  [{label}] TOTAL POINTS -- naive last-yr: r={naive_last['r']:+.3f} r2={naive_last['r2']:.3f} "
              f"rmse={naive_last['rmse']:.1f}  (n={naive_last['n']})")
    print(f"  [{label}] TOTAL POINTS -- naive lg-avg:  r={naive_avg['r']:+.3f} r2={naive_avg['r2']:.3f} "
          f"rmse={naive_avg['rmse']:.1f}  (n={naive_avg['n']})")

    # RATE comparison -- no games-played denominator at all on either side,
    # so this isolates whether the model actually predicts SKILL LEVEL, not
    # just whether it benefits from (or is dragged down by) knowing playing
    # time, which even the naive baselines above got a free pass on.
    rate_model = _corr(a, "predicted_fp_per_game", "fantasy_points_per_game")
    rate_naive_last = _corr(a, "naive_last_year_fp_pg", "fantasy_points_per_game")
    print(f"  [{label}] PER-GAME RATE -- model:        r={rate_model['r']:+.3f} r2={rate_model['r2']:.3f} "
          f"rmse={rate_model['rmse']:.2f}  (n={rate_model['n']})")
    if rate_naive_last:
        print(f"  [{label}] PER-GAME RATE -- naive last-yr: r={rate_naive_last['r']:+.3f} r2={rate_naive_last['r2']:.3f} "
              f"rmse={rate_naive_last['rmse']:.2f}  (n={rate_naive_last['n']})")
    return model, naive_last, naive_avg, rate_model


def score_vorp(label, actual):
    a = actual.dropna(subset=["fantasy_points", "predicted_fp_season"]).copy()
    if len(a) < REPLACEMENT_RANK + 3:
        print(f"  [{label}] VORP -- not enough players (n={len(a)}) for replacement rank {REPLACEMENT_RANK}")
        return None

    a_sorted_actual = a.sort_values("fantasy_points", ascending=False).reset_index(drop=True)
    a_sorted_pred = a.sort_values("predicted_fp_season", ascending=False).reset_index(drop=True)
    replacement_actual = a_sorted_actual.loc[REPLACEMENT_RANK - 1, "fantasy_points"]
    replacement_pred = a_sorted_pred.loc[REPLACEMENT_RANK - 1, "predicted_fp_season"]

    a["vorp_actual"] = a["fantasy_points"] - replacement_actual
    a["vorp_predicted"] = a["predicted_fp_season"] - replacement_pred

    r, p = stats.pearsonr(a["vorp_predicted"], a["vorp_actual"])
    rho, ps = stats.spearmanr(a["vorp_predicted"], a["vorp_actual"])

    top10_actual = set(a.sort_values("vorp_actual", ascending=False).head(10)["player"])
    top10_pred = set(a.sort_values("vorp_predicted", ascending=False).head(10)["player"])
    overlap = len(top10_actual & top10_pred)

    print(f"  [{label}] VORP (replacement rank {REPLACEMENT_RANK}) -- pearson r={r:+.3f}, "
          f"spearman rho={rho:+.3f} (p={ps:.3f}), top-10 overlap={overlap}/10  (n={len(a)})")
    return {"r": r, "rho": rho, "overlap": overlap, "n": len(a)}


def add_ranks(actual, target_year):
    """WITHIN-YEAR ranks only (a top-10 pick means top 10 that season, not
    across pooled years): predicted_rank from predicted_fp_per_game (the
    real preseason-only signal -- no actual-games-played info leaks in
    here, unlike the season-total columns), actual_rank from the real
    season's fantasy_points."""
    a = actual.dropna(subset=["fantasy_points", "predicted_fp_per_game"]).copy()
    a["year"] = target_year
    a["predicted_rank"] = a["predicted_fp_per_game"].rank(ascending=False, method="first").astype(int)
    a["actual_rank"] = a["fantasy_points"].rank(ascending=False, method="first").astype(int)
    a["above_median"] = a["actual_rank"] <= (len(a) // 2)
    return a


def _band_stats(picks):
    return {
        "n": len(picks),
        "above_avg": picks["above_median"].mean(),
        "top10": (picks["actual_rank"] <= 10).mean(),
        "top5": (picks["actual_rank"] <= 5).mean(),
        "top3": (picks["actual_rank"] <= 3).mean(),
    }


def tier_hit_rates(label, pooled):
    n_years = pooled["year"].nunique()
    print(f"\n[{label}] TIER HIT RATES -- pooled across {n_years} backtest years "
          f"(n={len(pooled)} player-seasons, ~{len(pooled)//n_years}/year)")
    header = f"  {'model picked...':<22s} {'n picks':>8s} {'above avg':>10s} {'actual top10':>13s} {'actual top5':>12s} {'actual top3':>12s}"
    print(header)
    out = {"cumulative": {}, "band": {}}
    for tier in [3, 5, 10]:
        picks = pooled[pooled["predicted_rank"] <= tier]
        if picks.empty:
            continue
        s = _band_stats(picks)
        print(f"  {'predicted top-' + str(tier):<22s} {s['n']:>8d} {s['above_avg']*100:>9.0f}% {s['top10']*100:>12.0f}% "
              f"{s['top5']*100:>11.0f}% {s['top3']*100:>11.0f}%")
        out["cumulative"][tier] = s

    print(f"  {'(exclusive draft-slot bands, i.e. would this specific pick have been worth it)':<90s}")
    bands = [(1, 3, "predicted rank 1-3"), (4, 5, "predicted rank 4-5"), (6, 10, "predicted rank 6-10")]
    for lo, hi, band_label in bands:
        picks = pooled[(pooled["predicted_rank"] >= lo) & (pooled["predicted_rank"] <= hi)]
        if picks.empty:
            continue
        s = _band_stats(picks)
        print(f"  {band_label:<22s} {s['n']:>8d} {s['above_avg']*100:>9.0f}% {s['top10']*100:>12.0f}% "
              f"{s['top5']*100:>11.0f}% {s['top3']*100:>11.0f}%")
        out["band"][(lo, hi)] = s
    return out


def run():
    results = {"kicker": [], "punter": []}
    ranked = {"kicker": [], "punter": []}
    for target_year in TARGET_YEARS:
        print(f"\n===== target year {target_year} =====")
        k = fit_and_predict(KICKING_CSV, "points_for_pg", target_year)
        if k is not None:
            print(f" -- kickers (n={len(k)}, {(~k['had_prior_history']).sum()} with no prior history) --")
            model, naive_last, naive_avg, rate_model = score_predictions("kicker", k)
            vorp = score_vorp("kicker", k)
            results["kicker"].append({"year": target_year, "model": model, "rate_model": rate_model, "vorp": vorp})
            ranked["kicker"].append(add_ranks(k, target_year))

        p = fit_and_predict_punter_skill(target_year)
        if p is not None:
            print(f" -- punters (n={len(p)}, {(~p['had_prior_history']).sum()} with no prior history) --")
            model, naive_last, naive_avg, rate_model = score_predictions("punter", p)
            vorp = score_vorp("punter", p)
            results["punter"].append({"year": target_year, "model": model, "rate_model": rate_model, "vorp": vorp})
            ranked["punter"].append(add_ranks(p, target_year))

    print("\n===== summary (avg across target years) =====")
    for pos in ["kicker", "punter"]:
        rs = [x["model"]["r"] for x in results[pos] if x["model"]]
        r2s = [x["model"]["r2"] for x in results[pos] if x["model"]]
        rate_r2s = [x["rate_model"]["r2"] for x in results[pos] if x["rate_model"]]
        vorp_rhos = [x["vorp"]["rho"] for x in results[pos] if x["vorp"]]
        if rs and vorp_rhos:
            print(f"  {pos:>7s}: total-points avg r2={np.mean(r2s):.3f}  |  "
                  f"per-game RATE avg r2={np.mean(rate_r2s):.3f}  |  "
                  f"VORP avg spearman rho={np.mean(vorp_rhos):+.3f}")
        else:
            print(f"  {pos}: insufficient data")

    print("\n===== elite-tier hit rates (does the model call the best guys?) =====")
    tier_results = {}
    for pos in ["kicker", "punter"]:
        pooled = pd.concat(ranked[pos], ignore_index=True)
        tier_results[pos] = tier_hit_rates(pos, pooled)

    return results, tier_results


if __name__ == "__main__":
    run()
