# win_totals

Vegas preseason win-total odds per team per season: the line, over/under
odds, actual wins, and result.

- **Source:** Covers.com Sports Odds History —
  `https://www.covers.com/sportsoddshistory/nfl-win/?y={year}&sa=nfl&t=win`
- **Run:** `python3 pipeline.py [start_year] [end_year]` (default 2015–2025)
- **Output:** `data/win_totals.csv` — `year, team, win_total_line, over_odds,
  under_odds, actual_wins, result`

Covers.com labels each team by its name *that season* (e.g. "Oakland
Raiders" for 2015); `pipeline.py` normalizes via
[`nfl/common/team_codes.py`](../../common/team_codes.py) to the current
3-letter abbreviation so it joins cleanly with other sources.
