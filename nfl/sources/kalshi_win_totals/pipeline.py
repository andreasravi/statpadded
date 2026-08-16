"""
Live NFL win-total odds from Kalshi's prediction market (public REST API,
no auth needed): https://api.elections.kalshi.com/trade-api/v2/markets

Kalshi doesn't post a single "win total line" like a sportsbook -- each team
gets a LADDER of binary "will they win >= K games" contracts (K = 1..17),
each with its own market-implied probability. This pipeline reconstructs a
sportsbook-style number from that ladder:

  implied_line   = the half-integer threshold where the ladder crosses 50%
                    (interpolated between the two straddling contracts) --
                    directly comparable to a traditional "Over/Under 8.5"
                    line, since P(X >= 9) = P(X > 8.5).
  expected_wins  = sum of P(X >= k) for k=1..17 (the standard identity for
                    the expectation of a non-negative integer variable) --
                    the market's actual mean, not just its median crossover.

This is a LIVE snapshot, not a historical archive like the other
nfl/sources/ pipelines -- there's no year parameter; it always pulls
whatever season Kalshi currently has open and stamps the pull time.
Re-run it any time you want a fresher read; each run overwrites the output
(the old snapshot isn't preserved unless you copy it first).
"""
import csv
import json
import os
import sys
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
OUT_PATH = os.path.join(HERE, "data", "kalshi_win_totals.csv")
RAW_PATH = os.path.join(HERE, "data", "raw_snapshot.json")

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
sys.path.insert(0, REPO_ROOT)

API_BASE = "https://api.elections.kalshi.com/trade-api/v2/markets"
SERIES_TICKER = "KXNFLWINS"

# Kalshi event tickers use the team's own abbreviation, but a couple diverge
# from our canonical scheme (nfl/common/team_codes.py) -- map those here.
KALSHI_ABBR_FIX = {
    "WSH": "WAS",
    "LA": "LAR",   # if Kalshi ever uses bare "LA" for the Rams
    "JAC": "JAX",
}


def fetch_all_markets():
    all_markets = []
    cursor = ""
    while True:
        url = f"{API_BASE}?series_ticker={SERIES_TICKER}&limit=200"
        if cursor:
            url += f"&cursor={cursor}"
        req = urllib.request.Request(url, headers={"Accept": "application/json"})
        with urllib.request.urlopen(req, timeout=30) as resp:
            d = json.load(resp)
        all_markets.extend(d["markets"])
        cursor = d.get("cursor")
        if not cursor:
            break
    return all_markets


def implied_line_and_expected_wins(thresholds: dict):
    """thresholds: {k: prob_yes} for 'wins >= k'. Returns (implied_line, expected_wins)."""
    ks = sorted(thresholds)
    expected_wins = sum(thresholds.values())  # E[X] = sum P(X>=k), k=1..max

    implied_line = None
    for i in range(len(ks) - 1):
        k, k_next = ks[i], ks[i + 1]
        p, p_next = thresholds[k], thresholds[k_next]
        if p >= 0.5 >= p_next:
            if p == p_next:
                implied_line = k - 0.5
            else:
                # linear interpolation between k-0.5 (prob=p) and k_next-0.5 (prob=p_next)
                frac = (p - 0.5) / (p - p_next)
                implied_line = (k - 0.5) + frac * ((k_next - 0.5) - (k - 0.5))
            break
    return implied_line, expected_wins


def build():
    markets = fetch_all_markets()
    os.makedirs(os.path.dirname(RAW_PATH), exist_ok=True)
    with open(RAW_PATH, "w") as f:
        json.dump(markets, f)

    by_team = {}
    for m in markets:
        event = m["event_ticker"]  # e.g. "KXNFLWINS-27ARI"
        abbr = event.split("-27")[-1] if "-27" in event else event.rsplit("-", 1)[-1]
        abbr = KALSHI_ABBR_FIX.get(abbr, abbr)
        k = m["floor_strike"]
        yes_bid = float(m["yes_bid_dollars"])
        yes_ask = float(m["yes_ask_dollars"])
        prob = (yes_bid + yes_ask) / 2
        by_team.setdefault(abbr, {})[k] = prob

    fetched_at = datetime.now(timezone.utc).isoformat()
    rows = []
    for team in sorted(by_team):
        thresholds = by_team[team]
        implied_line, expected_wins = implied_line_and_expected_wins(thresholds)
        rows.append({
            "team": team,
            "implied_line": round(implied_line, 2) if implied_line is not None else "",
            "expected_wins": round(expected_wins, 2),
            "n_thresholds": len(thresholds),
            "fetched_at": fetched_at,
        })

    with open(OUT_PATH, "w", newline="") as f:
        fieldnames = ["team", "implied_line", "expected_wins", "n_thresholds", "fetched_at"]
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} teams -> {OUT_PATH}")
    return rows


if __name__ == "__main__":
    build()
