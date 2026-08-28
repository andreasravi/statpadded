"""
Shared team-identity mapping for NFL data sources.

Different sites label a franchise differently depending on era: FantasyData
always uses the *current* city/name; Covers.com and most historical sources
use whatever the team was called *that season*. Every source under
nfl/sources/ should normalize to this same 3-letter abbreviation so datasets
join cleanly on (year, team).
"""

# Historical/alternate name -> canonical current-franchise abbreviation.
TEAM_NAME_TO_ABBR = {
    "Arizona Cardinals": "ARI",
    "Atlanta Falcons": "ATL",
    "Baltimore Ravens": "BAL",
    "Buffalo Bills": "BUF",
    "Carolina Panthers": "CAR",
    "Chicago Bears": "CHI",
    "Cincinnati Bengals": "CIN",
    "Cleveland Browns": "CLE",
    "Dallas Cowboys": "DAL",
    "Denver Broncos": "DEN",
    "Detroit Lions": "DET",
    "Green Bay Packers": "GB",
    "Houston Texans": "HOU",
    "Indianapolis Colts": "IND",
    "Jacksonville Jaguars": "JAX",
    "Kansas City Chiefs": "KC",
    "Las Vegas Raiders": "LV",
    "Oakland Raiders": "LV",
    "Los Angeles Chargers": "LAC",
    "San Diego Chargers": "LAC",
    "Los Angeles Rams": "LAR",
    "St Louis Rams": "LAR",
    "St. Louis Rams": "LAR",
    "Miami Dolphins": "MIA",
    "Minnesota Vikings": "MIN",
    "New England Patriots": "NE",
    "New Orleans Saints": "NO",
    "New York Giants": "NYG",
    "New York Jets": "NYJ",
    "Philadelphia Eagles": "PHI",
    "Pittsburgh Steelers": "PIT",
    "San Francisco 49ers": "SF",
    "Seattle Seahawks": "SEA",
    "Tampa Bay Buccaneers": "TB",
    "Tennessee Titans": "TEN",
    "Washington Redskins": "WAS",
    "Washington Football Team": "WAS",
    "Washington Commanders": "WAS",
}

# All 32 canonical abbreviations, for sanity checks.
ALL_TEAMS = sorted(set(TEAM_NAME_TO_ABBR.values()))
assert len(ALL_TEAMS) == 32

# Pro-Football-Reference's own short codes (used in its per-season stat
# tables' `team_name_abbr` column) differ from our canonical abbreviation
# for a handful of teams. Multi-team stint rows ("2TM", "3TM") aren't a
# real team and are handled by the caller, not mapped here.
PFR_ABBR_TO_ABBR = {
    "GNB": "GB",
    "KAN": "KC",
    "LVR": "LV",
    "NWE": "NE",
    "NOR": "NO",
    "SFO": "SF",
    "TAM": "TB",
}


def normalize_pfr_abbr(code: str) -> str:
    """Map a PFR-style team code (e.g. 'GNB', 'KAN') to our canonical
    abbreviation. Most codes already match and pass through unchanged."""
    return PFR_ABBR_TO_ABBR.get(code, code)


# nflverse (play-by-play) uses 'LA' for the Rams where every other source
# here uses 'LAR'; everything else already matches our canonical codes.
NFLVERSE_ABBR_TO_ABBR = {
    "LA": "LAR",
}


def normalize_nflverse_abbr(code: str) -> str:
    """Map an nflverse-style team code (e.g. 'LA') to our canonical
    abbreviation. Most codes already match and pass through unchanged."""
    return NFLVERSE_ABBR_TO_ABBR.get(code, code)


# Underdog's 2024 rankings table labels teams by nickname only (no city,
# no abbreviation) — e.g. "49ers" instead of "SF" or "San Francisco 49ers".
# "Free Agent" isn't a team; callers should treat it as None.
NICKNAME_TO_ABBR = {
    "49ers": "SF",
    "Bears": "CHI",
    "Bengals": "CIN",
    "Bills": "BUF",
    "Broncos": "DEN",
    "Browns": "CLE",
    "Bucs": "TB",
    "Cardinals": "ARI",
    "Chargers": "LAC",
    "Chiefs": "KC",
    "Colts": "IND",
    "Commanders": "WAS",
    "Cowboys": "DAL",
    "Dolphins": "MIA",
    "Eagles": "PHI",
    "Falcons": "ATL",
    "Giants": "NYG",
    "Jaguars": "JAX",
    "Jets": "NYJ",
    "Lions": "DET",
    "Packers": "GB",
    "Panthers": "CAR",
    "Patriots": "NE",
    "Raiders": "LV",
    "Rams": "LAR",
    "Ravens": "BAL",
    "Saints": "NO",
    "Seahawks": "SEA",
    "Steelers": "PIT",
    "Texans": "HOU",
    "Titans": "TEN",
    "Vikings": "MIN",
}


def normalize_underdog_team(team: str):
    """Map an Underdog Network rankings-table team value to our canonical
    abbreviation. Underdog has used three different conventions across
    years: bare canonical abbreviations (2023, 2025 — except 'LA' for the
    Rams), and nickname-only (2024). 'FA'/'Free Agent' means no team;
    returns None for those."""
    team = (team or "").strip()
    if team in ("FA", "Free Agent", ""):
        return None
    team = NFLVERSE_ABBR_TO_ABBR.get(team, team)
    return NICKNAME_TO_ABBR.get(team, team)
