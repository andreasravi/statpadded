"""
Fetch and cache raw HTML for:
  - FantasyData 2QB ADP (top 100, free tier) per season
  - Covers.com NFL regular season win totals (line + actual wins) per season

Caches raw HTML to data/raw/ so we never re-hit the sites once pulled.
Run again any time; it skips years already cached.
"""
import os
import time
import urllib.request

YEARS = range(2015, 2026)  # 2015-2025 completed seasons

PROJECT_DIR = os.path.dirname(os.path.dirname(__file__))
RAW_DIR = os.path.join(PROJECT_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def cache_path(kind: str, year: int) -> str:
    return os.path.join(RAW_DIR, f"{kind}_{year}.html")


def get_cached_or_fetch(kind: str, year: int, url: str) -> str:
    path = cache_path(kind, year)
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    print(f"Fetching {kind} {year} ...")
    html = fetch(url)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    time.sleep(1)  # be polite
    return path


def main():
    for year in YEARS:
        get_cached_or_fetch(
            "fd_adp",
            year,
            f"https://fantasydata.com/nfl/2qb-adp?season={year}&team=",
        )
        get_cached_or_fetch(
            "covers_win",
            year,
            f"https://www.covers.com/sportsoddshistory/nfl-win/?y={year}&sa=nfl&t=win",
        )
    print("Done. Cached HTML in", RAW_DIR)


if __name__ == "__main__":
    main()
