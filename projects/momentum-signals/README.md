# Momentum Signals, Borrowed from Finance

Does a finance-style momentum (or reversal) construction, applied to NFL
win-total `beat_margin` (`actual_wins - win_total_line`), find anything the
simpler lag-1 test in [`win-total-signals`](../win-total-signals/) didn't?
Three standard constructions, applied here for the first time in this repo:

1. **Time-series momentum/reversal** — the classic "does an asset's own
   past return predict its own future return" test, at lags of 1, 2, and 3
   years, plus trailing 2- and 3-year rolling averages (not just a binary
   streak flag). Equities famously show short-term reversal (~1 month),
   intermediate momentum (~3–12 months), and long-term reversal (~3–5
   years) — multiple lags are checked here for the same reason, to see if a
   sign flip shows up at any horizon.
2. **Fundamental ("earnings") momentum** — instead of the market-relative
   `beat_margin`, use the trend in the team's own underlying quality
   (`pyth_wins` year-over-year) to predict this year's `beat_margin`. Analog:
   does an accelerating fundamental trend predict returns beyond what the
   price (here, the market's line) already reflects?
3. **Cross-sectional relative momentum** — the actual winners-minus-losers
   portfolio from Jegadeesh & Titman (1993): each season, rank all 32 teams
   against **each other** (not against their own history) by trailing
   `beat_margin`, form winner/loser terciles, and test betting *with* the
   trend vs. *fading* it against real odds.

Unlike [`pyth-win-signal`](../pyth-win-signal/), every input here is
legitimately known before the season starts (all trailing/lagged), so these
are genuine candidate betting signals, not just diagnostics — each one is
carried through to an actual odds-priced backtest.

## Data sources

All shared, all reused — nothing scraped for this project:

- [`nfl/sources/win_totals`](../../nfl/sources/win_totals/) — line, actual wins, odds, result, 2015–2025
- [`nfl/sources/game_results`](../../nfl/sources/game_results/) — `pyth_wins`, 2015–2025

## Pipeline

```bash
source venv/bin/activate
python3 projects/momentum-signals/scripts/analyze.py
```

Writes `data/cross_sectional_groups.csv`, prints all stats.

## Findings

**1) Time-series momentum/reversal — nothing at any lag or window.**

| | n | r | p |
|---|---|---|---|
| lag 1yr | 320 | −0.088 | 0.115 |
| lag 2yr | 288 | +0.021 | 0.723 |
| lag 3yr | 256 | −0.050 | 0.429 |
| trailing 2yr avg | 288 | −0.036 | 0.545 |
| trailing 3yr avg | 256 | −0.054 | 0.392 |

No sign pattern resembling equities' reversal→momentum→reversal progression
across horizons — everything just sits near zero. The lag-1 number matches
`win-total-signals`' earlier finding almost exactly; extending to longer
lags and multi-year windows doesn't surface anything it missed.

**2) Fundamental momentum — nothing.** `pyth_wins` trend (`y-1` minus `y-2`)
vs. this year's `beat_margin`: n=288, r=−0.043, p=0.463. An accelerating or
decelerating trend in a team's real quality doesn't predict beating the line
beyond what the line already captures — consistent with
[`pyth-win-signal`](../pyth-win-signal/)'s finding that the market prices
quality about as well as it can be priced from public data.

**3) Cross-sectional relative momentum — a directional hint at the 1-year
horizon, gone by 2 years, and unprofitable either way.**

| Window | Winners' next beat_margin | Losers' next beat_margin | Winners−Losers |
|---|---|---|---|
| Trailing 1yr | −0.33 (p=0.22) | +0.13 (p=0.61) | p=0.215 |
| Trailing 2yr | +0.21 (p=0.47) | +0.16 (p=0.57) | p=0.911 |

At the 1-year lookback, last year's biggest overperformers (trailing
beat_margin +2.90 on average) trend slightly *negative* the following
season, and last year's biggest underperformers (−3.20) trend slightly
positive — a mean-reversion lean, same direction as everything else in this
repo. It vanishes once you extend the lookback to 2 years, and neither gap
clears significance on its own.

**Backtest — betting either direction loses money:**

| Window | Strategy | n | Win% | ROI% | p |
|---|---|---|---|---|---|
| 1yr | Momentum (with the trend) | 200 | 47.5% | −5.3% | 0.443 |
| 1yr | Reversal (fade the trend) | 200 | 50.0% | −2.3% | 0.738 |
| 2yr | Momentum (with the trend) | 180 | 50.0% | +0.1% | 0.992 |
| 2yr | Reversal (fade the trend) | 180 | 45.6% | −9.2% | 0.193 |

The one directionally "right" strategy (reversal at the 1yr lookback, since
that's the horizon with the reversal lean) still loses money once real odds
are applied — the market's line already sits at prices that absorb the
tendency, same pattern found for every other signal tested in this repo.

## Bottom line

None of the three standard finance momentum constructions — own-history
time-series momentum at any lag/window, fundamental trend momentum, or
cross-sectional relative momentum — produce a result that's both
statistically real and beats the market once priced correctly. The
strongest thing here (1-year cross-sectional reversal) is the same weak,
non-significant mean-reversion lean this repo keeps finding from different
angles (lag-1 autocorrelation, 3-year streak fades, big line-drop buckets) —
it shows up faintly every time you look for it, never survives a real
backtest, and is exactly the size you'd expect from a market that's
efficient enough not to leave momentum or reversal sitting in a single
public number.
