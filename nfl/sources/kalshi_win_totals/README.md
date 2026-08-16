# kalshi_win_totals

Live NFL win-total odds from [Kalshi](https://kalshi.com/category/sports/football/nfl/win-totals),
a regulated prediction market — via their **public REST API, no auth
required**.

- **API:** `https://api.elections.kalshi.com/trade-api/v2/markets?series_ticker=KXNFLWINS`
  (found via the site's own network requests — `KXNFLWINS-27{team}` event
  tickers, e.g. `KXNFLWINS-27ARI`; the `27` is the settlement year, i.e. this
  is the *2026* season)

## Why this needs its own logic

Kalshi doesn't post a single sportsbook-style "win total line." Each team
gets a **ladder of binary contracts** — "will they win ≥1 game," "≥2," …
up to "≥17" — each with its own market-implied probability (from
`yes_bid`/`yes_ask`). `pipeline.py` reconstructs two sportsbook-comparable
numbers from that ladder:

- **`implied_line`** — the half-integer threshold where the ladder crosses
  50% (interpolated), e.g. if P(≥9 wins) is just under 50%, the implied
  line is ~8.5 — directly comparable to a traditional "Over/Under 8.5."
- **`expected_wins`** — the market's actual mean, `sum(P(X≥k))` for
  k=1..17 (the standard expectation identity for a non-negative integer
  variable), which can differ slightly from the median-based `implied_line`
  if the distribution is skewed.

## This is a live snapshot, not a historical archive

Unlike the other `nfl/sources/` pipelines, there's no year parameter and no
`data/raw/` per-year cache — it always pulls whatever season Kalshi
currently has open. Re-run any time for a fresher read; each run
overwrites `data/kalshi_win_totals.csv` (copy it first if you want to keep
a point-in-time snapshot).

## Output

`data/kalshi_win_totals.csv` — `team, implied_line, expected_wins,
n_thresholds, fetched_at`. Team codes are normalized to the same
abbreviations used everywhere else in `nfl/sources/` (Kalshi's own codes
differ in two spots: `WSH`→`WAS`, `JAC`→`JAX`).

## Run

```bash
source venv/bin/activate
python3 nfl/sources/kalshi_win_totals/pipeline.py
```
