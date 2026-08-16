"""
NFL regular-season game-by-game final scores, 2015-2025 (final scores only --
no box scores, no play-by-play).

Source: Pro-Football-Reference season schedule pages
  https://www.pro-football-reference.com/years/{year}/games.htm

PFR sits behind a Cloudflare JS challenge that a plain HTTP client can't
pass (confirmed: curl gets a 403 here, but the same request succeeds through
a real browser). So unlike the other nfl/sources/ pipelines, this one does
NOT auto-fetch: data/raw/pfr_games_{year}.html must be populated by
navigating there with a browser tool and saving the #games table's HTML.
Re-run this script any time after that to reparse -- it's pure parsing from
here, no network calls.

Outputs:
  data/game_results.csv        one row per game: year, week, date,
                                home_team, away_team, home_score, away_score
  data/team_point_diff.csv     one row per team-season: points for/against,
                                point differential, Pythagorean win estimate
  data/strength_of_schedule.csv  two SOS metrics per team-season (see below)
"""
import csv
import os
import sys

from bs4 import BeautifulSoup

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
RAW_DIR = os.path.join(HERE, "data", "raw")
GAMES_CSV = os.path.join(HERE, "data", "game_results.csv")
POINT_DIFF_CSV = os.path.join(HERE, "data", "team_point_diff.csv")
SOS_CSV = os.path.join(HERE, "data", "strength_of_schedule.csv")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "win_totals", "data", "win_totals.csv")

sys.path.insert(0, REPO_ROOT)
from nfl.common.team_codes import TEAM_NAME_TO_ABBR

DEFAULT_START, DEFAULT_END = 2015, 2025


def parse_year(year: int, rows_out: list):
    path = os.path.join(RAW_DIR, f"pfr_games_{year}.html")
    if not os.path.exists(path):
        raise FileNotFoundError(
            f"{path} missing. PFR is Cloudflare-protected -- fetch it with a "
            f"browser tool (navigate to https://www.pro-football-reference.com/"
            f"years/{year}/games.htm, grab document.querySelector('#games').outerHTML, "
            f"save it there), then re-run this script."
        )
    with open(path, encoding="utf-8") as f:
        soup = BeautifulSoup(f.read(), "lxml")

    for tr in soup.find_all("tr"):
        week_cell = tr.find(["td", "th"], {"data-stat": "week_num"})
        if week_cell is None:
            continue
        week = week_cell.get_text(strip=True)
        if not week.isdigit():
            continue  # skips repeated header rows and playoff rows (non-numeric week)

        def cell(stat):
            c = tr.find(["td", "th"], {"data-stat": stat})
            return c.get_text(strip=True) if c else ""

        winner = TEAM_NAME_TO_ABBR.get(cell("winner"))
        loser = TEAM_NAME_TO_ABBR.get(cell("loser"))
        if not winner or not loser:
            continue
        loc = cell("game_location")  # '@' means the winner was the away team
        pts_win, pts_lose = cell("pts_win"), cell("pts_lose")
        if not pts_win or not pts_lose:
            continue  # unplayed/canceled game with no final score

        if loc == "@":
            away_team, home_team = winner, loser
            away_score, home_score = int(pts_win), int(pts_lose)
        else:
            home_team, away_team = winner, loser
            home_score, away_score = int(pts_win), int(pts_lose)

        rows_out.append({
            "year": year,
            "week": int(week),
            "date": cell("game_date"),
            "home_team": home_team,
            "away_team": away_team,
            "home_score": home_score,
            "away_score": away_score,
        })


def build_game_results(start_year=DEFAULT_START, end_year=DEFAULT_END):
    rows = []
    for year in range(start_year, end_year + 1):
        parse_year(year, rows)
    rows.sort(key=lambda r: (r["year"], r["week"], r["date"]))

    os.makedirs(os.path.dirname(GAMES_CSV), exist_ok=True)
    fieldnames = ["year", "week", "date", "home_team", "away_team", "home_score", "away_score"]
    with open(GAMES_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} games -> {GAMES_CSV}")
    return rows


def build_point_diff(games: list):
    """Points for/against, point differential, and Pythagorean win estimate
    (exponent 2.37, the standard NFL constant) per team-season."""
    stats = {}  # (year, team) -> {pf, pa, games}
    for g in games:
        for team, pf, pa in [
            (g["home_team"], g["home_score"], g["away_score"]),
            (g["away_team"], g["away_score"], g["home_score"]),
        ]:
            key = (g["year"], team)
            s = stats.setdefault(key, {"pf": 0, "pa": 0, "games": 0})
            s["pf"] += pf
            s["pa"] += pa
            s["games"] += 1

    rows = []
    for (year, team), s in sorted(stats.items()):
        pf, pa, gp = s["pf"], s["pa"], s["games"]
        pyth_pct = (pf ** 2.37) / (pf ** 2.37 + pa ** 2.37) if (pf or pa) else 0.5
        rows.append({
            "year": year,
            "team": team,
            "games": gp,
            "points_for": pf,
            "points_against": pa,
            "point_diff": pf - pa,
            "avg_point_diff": round((pf - pa) / gp, 3) if gp else 0,
            "pyth_win_pct": round(pyth_pct, 4),
            "pyth_wins": round(pyth_pct * gp, 2),
        })

    os.makedirs(os.path.dirname(POINT_DIFF_CSV), exist_ok=True)
    fieldnames = ["year", "team", "games", "points_for", "points_against",
                  "point_diff", "avg_point_diff", "pyth_win_pct", "pyth_wins"]
    with open(POINT_DIFF_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} team-seasons -> {POINT_DIFF_CSV}")
    return rows


def build_strength_of_schedule(games: list):
    """Two SOS metrics per team-season, both averaged across every game on
    the schedule (a twice-played division rival counts twice, matching how
    SOS is conventionally computed):

      sos_this_year_line  = avg of opponents' Vegas win-total LINE for the
                             SAME season -- "how good was the market expecting
                             my opponents to be this year"
      sos_prior_year_wins = avg of opponents' ACTUAL wins the PRIOR season --
                             "how good were my opponents last year" (usable
                             as a proxy before this season's lines exist)
    """
    with open(WIN_TOTALS_CSV) as f:
        wt_rows = list(csv.DictReader(f))
    line_by_key = {(int(r["year"]), r["team"]): float(r["win_total_line"]) for r in wt_rows}
    wins_by_key = {(int(r["year"]), r["team"]): int(r["actual_wins"]) for r in wt_rows}

    opponents = {}  # (year, team) -> list of opponent teams
    for g in games:
        opponents.setdefault((g["year"], g["home_team"]), []).append(g["away_team"])
        opponents.setdefault((g["year"], g["away_team"]), []).append(g["home_team"])

    rows = []
    for (year, team), opps in sorted(opponents.items()):
        this_year_lines = [line_by_key[(year, o)] for o in opps if (year, o) in line_by_key]
        prior_year_wins = [wins_by_key[(year - 1, o)] for o in opps if (year - 1, o) in wins_by_key]

        rows.append({
            "year": year,
            "team": team,
            "n_games": len(opps),
            "sos_this_year_line": round(sum(this_year_lines) / len(this_year_lines), 3)
                                   if this_year_lines else "",
            "n_opponents_with_line": len(this_year_lines),
            "sos_prior_year_wins": round(sum(prior_year_wins) / len(prior_year_wins), 3)
                                    if prior_year_wins else "",
            "n_opponents_with_prior_wins": len(prior_year_wins),
        })

    os.makedirs(os.path.dirname(SOS_CSV), exist_ok=True)
    fieldnames = ["year", "team", "n_games", "sos_this_year_line", "n_opponents_with_line",
                  "sos_prior_year_wins", "n_opponents_with_prior_wins"]
    with open(SOS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} team-seasons -> {SOS_CSV}")
    return rows


def main(start_year=DEFAULT_START, end_year=DEFAULT_END):
    games = build_game_results(start_year, end_year)
    build_point_diff(games)
    build_strength_of_schedule(games)


if __name__ == "__main__":
    args = sys.argv[1:]
    start = int(args[0]) if len(args) > 0 else DEFAULT_START
    end = int(args[1]) if len(args) > 1 else DEFAULT_END
    main(start, end)
