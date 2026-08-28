"""
Merge every shared nfl/sources/ dataset (plus schedule-swing-signal's
schedule_delta_pyth) into one team-season feature table, targeting
PYTHAGOREAN wins (not actual_wins) -- see README for why.

Timing discipline, same convention as projects/win-total-model:
  - qb_tier, coach_tenure_bucket, new_coach use the CURRENT season (T) --
    legitimately known before the season (roster/coaching moves happen in
    the offseason; the Sando QB Tiers survey and its analogues are
    themselves preseason publications).
  - Everything else ("prior_*") uses season T-1 or earlier. In particular
    prior_turnover_diff_per_game/fumble_recovery_rate and prior_agl are
    OUTCOMES of the T-1 season -- they can't be known before T is played,
    so they only enter as lagged (mean-reversion) predictors, never as
    same-season inputs. See README for the same point made at more length.

Output: data/features.csv, one row per team-season, 2016-2025 (bounded by
schedule_delta_pyth's availability, itself bounded by needing both T-1's
own schedule and T's opponents' preseason lines).
"""
import csv
import os
import sys

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT_DIR))
DATA_DIR = os.path.join(PROJECT_DIR, "data")
NFL = os.path.join(REPO_ROOT, "nfl", "sources")
SCHEDULE_SWING_CSV = os.path.join(REPO_ROOT, "projects", "schedule-swing-signal", "data", "merged.csv")

sys.path.insert(0, REPO_ROOT)


def load_csv(path):
    with open(path) as f:
        return list(csv.DictReader(f))


def build_coach_tenure(coaches):
    """Consecutive years with the same team, walked forward from 2014 (the
    first pulled coaches.csv year). This UNDERCOUNTS true tenure for any
    coach already in place before 2014 (e.g. a coach hired in 2011 reads
    as 'year 4' here in 2014, not year 4 of their real tenure) -- flagged
    in the README. Bucketed into Yr1 / Yr2-3 / Yr4+ per the user's request."""
    by_team_year = {(int(r["year"]), r["team"]): r["head_coach"] for r in coaches}
    years = sorted(set(y for y, _ in by_team_year))
    teams = sorted(set(t for _, t in by_team_year))

    tenure = {}
    for team in teams:
        running = 0
        prev_coach = None
        for year in years:
            coach = by_team_year.get((year, team))
            if coach is None:
                continue
            if coach != prev_coach:
                running = 1
            else:
                running += 1
            tenure[(year, team)] = running
            prev_coach = coach
    return tenure


def tenure_bucket(tenure_years):
    if tenure_years == 1:
        return "Yr1"
    if tenure_years in (2, 3):
        return "Yr2-3"
    return "Yr4+"


def main():
    win_totals = load_csv(os.path.join(NFL, "win_totals", "data", "win_totals.csv"))
    point_diff = load_csv(os.path.join(NFL, "game_results", "data", "team_point_diff.csv"))
    coaches = load_csv(os.path.join(NFL, "coaches", "data", "coaches.csv"))
    qb_tiers = load_csv(os.path.join(NFL, "qb_starters", "data", "qb_starter_tiers.csv"))
    turnovers = load_csv(os.path.join(NFL, "turnovers", "data", "turnovers.csv"))
    agl = load_csv(os.path.join(NFL, "agl", "data", "agl.csv"))
    sched = load_csv(SCHEDULE_SWING_CSV)

    wt_by_key = {(int(r["year"]), r["team"]): r for r in win_totals}
    pd_by_key = {(int(r["year"]), r["team"]): r for r in point_diff}
    coach_by_key = {(int(r["year"]), r["team"]): r for r in coaches}
    qbtier_by_key = {(int(r["year"]), r["team"]): r for r in qb_tiers}
    turnover_by_key = {(int(r["year"]), r["team"]): r for r in turnovers}
    agl_by_key = {(int(r["year"]), r["team"]): r for r in agl}
    # sched rows are indexed at year=T-1, with schedule_delta_pyth already
    # built from T's opponents' preseason lines (sos_next_yr_line) minus
    # this team's own T-1 realized SOS -- see schedule-swing-signal/README.
    sched_by_key = {(int(r["year"]), r["team"]): r for r in sched}

    tenure = build_coach_tenure(coaches)

    rows = []
    for (year, team), wt in wt_by_key.items():
        prior_wt = wt_by_key.get((year - 1, team))
        this_pd = pd_by_key.get((year, team))
        prior_pd = pd_by_key.get((year - 1, team))
        two_prior_wt = wt_by_key.get((year - 2, team))
        this_coach = coach_by_key.get((year, team))
        this_qbtier = qbtier_by_key.get((year, team))
        prior_turnover = turnover_by_key.get((year - 1, team))
        prior_agl = agl_by_key.get((year - 1, team))
        this_sched = sched_by_key.get((year - 1, team))

        if not (prior_wt and this_pd and prior_pd and this_sched):
            continue  # need a full prior season + the schedule-delta join to exist

        prior_actual_wins = int(prior_wt["actual_wins"])
        prior_win_total_line = float(prior_wt["win_total_line"])
        prior_beat_margin = prior_actual_wins - prior_win_total_line
        prior_pyth_wins = float(prior_pd["pyth_wins"])

        two_prior_beat_margin = None
        if two_prior_wt:
            two_prior_beat_margin = int(two_prior_wt["actual_wins"]) - float(two_prior_wt["win_total_line"])
        trailing_beat_margin_2yr = (
            round((prior_beat_margin + two_prior_beat_margin) / 2, 3)
            if two_prior_beat_margin is not None else ""
        )

        this_tenure = tenure.get((year, team), "")
        row = {
            "year": year,
            "team": team,
            "win_total_line": float(wt["win_total_line"]),
            "actual_wins": int(wt["actual_wins"]),
            "target_pyth_wins": float(this_pd["pyth_wins"]),
            "beat_margin": int(wt["actual_wins"]) - float(wt["win_total_line"]),

            # current-season, preseason-knowable
            "qb_tier": this_qbtier["tier"] if this_qbtier else "",
            "new_coach": int(this_coach["new_coach"]) if this_coach and this_coach["new_coach"] != "" else "",
            "coach_tenure": this_tenure,
            "coach_tenure_bucket": tenure_bucket(this_tenure) if this_tenure != "" else "",
            "schedule_delta_pyth": float(this_sched["schedule_delta_pyth"]) if this_sched["schedule_delta_pyth"] != "" else "",

            # prior-season (mean-reversion / momentum framing)
            "prior_pyth_wins": prior_pyth_wins,
            "prior_actual_wins": prior_actual_wins,
            "prior_beat_margin": round(prior_beat_margin, 3),
            "trailing_beat_margin_2yr": trailing_beat_margin_2yr,
            "prior_turnover_diff_per_game": float(prior_turnover["turnover_diff_per_game"]) if prior_turnover else "",
            "prior_fumble_recovery_rate": float(prior_turnover["fumble_recovery_rate"]) if prior_turnover and prior_turnover["fumble_recovery_rate"] != "" else "",
            "prior_agl": float(prior_agl["agl"]) if prior_agl else "",
        }
        rows.append(row)

    rows.sort(key=lambda r: (r["year"], r["team"]))

    out_path = os.path.join(DATA_DIR, "features.csv")
    os.makedirs(DATA_DIR, exist_ok=True)
    fieldnames = list(rows[0].keys())
    with open(out_path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)

    n_qb = sum(1 for r in rows if r["qb_tier"] != "")
    n_agl = sum(1 for r in rows if r["prior_agl"] != "")
    n_to = sum(1 for r in rows if r["prior_turnover_diff_per_game"] != "")
    print(f"Wrote {len(rows)} team-season rows -> {out_path}")
    print(f"Years covered: {rows[0]['year']}-{rows[-1]['year']}")
    print(f"Coverage: qb_tier {n_qb}/{len(rows)}, prior_agl {n_agl}/{len(rows)}, prior_turnover {n_to}/{len(rows)}")


if __name__ == "__main__":
    main()
