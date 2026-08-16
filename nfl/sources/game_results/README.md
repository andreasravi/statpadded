# game_results

Every NFL regular-season game's final score, 2015–2025 (2,895 games) — plus
two datasets derived from it: point differential (with a Pythagorean win
estimate) and strength of schedule.

- **Source:** Pro-Football-Reference season schedule pages —
  `https://www.pro-football-reference.com/years/{year}/games.htm`
- **Final scores only** — no box scores, no play-by-play, one page per
  season (11 requests total for the whole range).

## Fetching (manual — PFR is Cloudflare-protected)

Unlike the other `nfl/sources/` pipelines, this one can't auto-fetch: PFR
sits behind a JS challenge that blocks plain HTTP clients (`curl` gets a
403; a real browser passes it fine). To populate a missing year:

1. Navigate a browser to `https://www.pro-football-reference.com/years/{year}/games.htm`
2. Grab `document.querySelector('#games').outerHTML`
3. Save it to `data/raw/pfr_games_{year}.html`
4. Re-run `python3 pipeline.py` — parsing and everything downstream is pure
   Python from there, no more network calls needed.

All 11 years (2015–2025) are already cached.

## Outputs

- **`data/game_results.csv`** — `year, week, date, home_team, away_team,
  home_score, away_score`. One row per game (2,895 total — 256 games × 6
  seasons (16-game era) + 272 × 5 (17-game era) − 1 canceled game: the
  Bills–Bengals Week 17 game in 2022, called off and never replayed after
  Damar Hamlin's on-field cardiac arrest).
- **`data/team_point_diff.csv`** — `year, team, games, points_for,
  points_against, point_diff, avg_point_diff, pyth_win_pct, pyth_wins`.
  Pythagorean win% uses the standard NFL exponent (2.37): a team that wins a
  lot of close games outperforms its point differential and tends to
  regress the following year, so this separates "actually good" from "won
  the close ones."
- **`data/strength_of_schedule.csv`** — `year, team, n_games,
  sos_this_year_line, n_opponents_with_line, sos_prior_year_wins,
  n_opponents_with_prior_wins`. Two schedule-strength metrics, both averaged
  across every game (a twice-played division rival counts twice):
    - `sos_this_year_line` — average of opponents' *Vegas win-total line for
      that same season* (needs `nfl/sources/win_totals`). Reads as "how good
      did the market expect my opponents to be this year."
    - `sos_prior_year_wins` — average of opponents' *actual wins the prior
      season*. A backward-looking proxy usable before this season's lines
      exist. Blank for 2015 team-seasons (no 2014 win-totals data pulled).

## Run

```bash
source venv/bin/activate
python3 nfl/sources/game_results/pipeline.py [start_year] [end_year]
```
