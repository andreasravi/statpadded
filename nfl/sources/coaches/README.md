# coaches

Head coach per team per season, plus a `new_coach` flag (1 = this team's
season-opening coach differs from the prior season's).

- **Source:** MyFootballToolbox.com —
  `https://myfootballtoolbox.com/nfl/coaches/years/{year}/`
- **Run:** `python3 pipeline.py [start_year] [end_year]` (default 2014–2025 —
  2014 is pulled as a lookback year so `new_coach` can be computed starting
  in 2015)
- **Output:** `data/coaches.csv` — `year, team, head_coach, new_coach`

A team can list more than one coach in a season if the original was fired
mid-year (an interim coach gets their own row on the site); `pipeline.py`
keeps only the **first** listed coach per team per year — the one who
started the season — since that's who a preseason win-total line is
actually priced against. `new_coach` is left blank for a team's first
pulled year, since there's no prior year in the data to compare against.
