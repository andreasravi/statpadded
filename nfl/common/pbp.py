"""
Shared play-by-play fetch-and-cache helper, sourced from nflverse-data's
public GitHub release (not PFR -- no Cloudflare wall, no browser tool
needed, plain HTTPS works fine and auto-fetches like win_totals/adp/coaches).

  https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.csv.gz

Each season's file has ~370 columns (every play, every stat nflfastR
tracks); callers only need a handful (which team, which player, made/missed,
exact kick distance), so this fetches with `usecols` and callers are
expected to cache their own lean CSV subset under their own source's
data/raw/ rather than persist the full pbp file.
"""
import pandas as pd

PBP_URL_TMPL = "https://github.com/nflverse/nflverse-data/releases/download/pbp/play_by_play_{year}.csv.gz"


def fetch_pbp_columns(year: int, columns: list) -> pd.DataFrame:
    """Download one season's play-by-play, keeping only `columns`. No local
    caching here -- callers filter to their own rows/columns and cache that
    (much smaller) result themselves."""
    url = PBP_URL_TMPL.format(year=year)
    return pd.read_csv(url, usecols=columns, low_memory=False)
