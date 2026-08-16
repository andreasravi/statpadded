# adp

Fantasy football average draft position (ADP), 2QB/superflex format, per
season. Capped at the top 100 players (FantasyData's free-tier limit).

- **Source:** FantasyData —
  `https://fantasydata.com/nfl/2qb-adp?season={year}&team=`
- **Run:** `python3 pipeline.py [start_year] [end_year]` (default 2015–2025)
- **Output:** `data/adp.csv` — `year, rank, name, team, pos, pos_rank, adp`

FantasyData always labels a franchise by its *current* city/name regardless
of season (e.g. "LV" even for a 2015 row), which already matches the
canonical abbreviation used across `nfl/sources/` — no remapping needed here.
