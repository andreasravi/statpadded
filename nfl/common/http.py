"""Shared fetch-and-cache helper for NFL data sources.

Every source under nfl/sources/<name>/ calls this to pull a page once and
cache the raw HTML to disk (data/raw/<prefix>_<year>.html) so re-running a
pipeline never re-hits the site for a year already fetched.
"""
import os
import time
import urllib.request

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36",
    "Accept-Language": "en-US,en;q=0.9",
}


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def get_cached_or_fetch(raw_dir: str, prefix: str, year: int, url: str, sleep: float = 1.0) -> str:
    """Return path to cached HTML for (prefix, year), fetching+caching if needed."""
    os.makedirs(raw_dir, exist_ok=True)
    path = os.path.join(raw_dir, f"{prefix}_{year}.html")
    if os.path.exists(path) and os.path.getsize(path) > 1000:
        return path
    print(f"Fetching {prefix} {year} ...")
    html = fetch(url)
    with open(path, "w", encoding="utf-8") as f:
        f.write(html)
    time.sleep(sleep)  # be polite
    return path
