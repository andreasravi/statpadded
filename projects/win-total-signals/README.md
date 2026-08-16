# Win-Total Line Signals: Jumps & Streaks

Two questions on the market's own history, using only the shared
[`nfl/sources/win_totals`](../../nfl/sources/win_totals/) dataset (2015–2025,
no new scraping):

1. **Line jumps.** When Vegas moves a team's win-total line sharply
   year-over-year (implying a big expected improvement or decline), is that
   new number more or less reliable than a stable line? Does the market
   overreact (big moves tend to get partially reversed) or underreact
   (big moves tend to continue)?
2. **Streak persistence.** If a team beat the over (or missed under the
   under) for one, two, or three years running, does that predict the same
   result again — momentum — or the opposite — mean reversion, i.e. fade the
   streak?

## Pipeline

No fetching needed — this is pure analysis on the existing shared dataset:

```bash
source venv/bin/activate
python3 projects/win-total-signals/scripts/analyze.py
```

Writes `data/line_change_merged.csv`, `data/backtest_results.csv`, and prints all stats.

## Baseline

Worth knowing before reading anything else: this sample is **not** a clean
50/50 over/under split. Across all 352 team-seasons: **Over 44.3% / Under
51.7% / Push 4.0%**. Every over%/under% below should be read against that
baseline, not against 50%.

## Findings

**1) Line jumps — no reliable linear signal, one notable bucket.**
Pearson r(line_change, beat_margin) = **−0.015** (p=0.79) — essentially zero
across the full range. Bucketed, one group stands out: teams whose line
**dropped 2.5+ points** (big bad-news adjustment) went on to beat the
*already-lowered* number at a **52.0% over rate** (vs the 44.3% baseline)
and a +0.52 average beat-margin — directionally consistent with "the market
overcorrects to bad news," but n=25, so treat as a lead, not a conclusion.
Every other bucket (moderate rise/drop, stable, big rise) sits close to
baseline noise.

**2) Streak persistence — weak mean-reversion hint, not statistically
significant at this sample size.**
Lag-1 autocorrelation of beat_margin is **r = −0.088** (p=0.11) — a small
mean-reversion lean (last year's overs trend down, last year's unders trend
up) but doesn't clear p<0.05. Two-year streaks show essentially nothing
(both groups sit within noise of a zero beat-margin, p=0.87 / p=0.73).
Three-year streaks are the most interesting: teams that **missed the under
three years running** go on to beat the over at **52.8%** the 4th year
(vs 44.3% baseline, avg beat-margin +0.43) — but p=0.36 on a one-sample
t-test, and this number is one of several buckets/streaks tested in the same
script without a multiple-comparisons correction, so it should not be
treated as a demonstrated edge. It's the strongest-looking pattern in the
data, but "strongest-looking out of many things tested" is exactly the
setup where noise masquerades as signal.

## 3) Odds-weighted backtest — win-rate alone is misleading

Every finding above uses win-rate and beat-margin, which treat every bet as
worth the same. Real bets settle at real prices (this dataset already has
`over_odds`/`under_odds` per team-season, e.g. `-140`, `+120`), so
[`nfl/common/betting.py`](../../nfl/common/betting.py) actually settles each
strategy flat-1-unit-per-bet at its recorded price:

| Strategy | n | Win% | ROI% | p (vs 0) |
|---|---|---|---|---|
| **Bet the OVER, every time** | 352 | 44.3% | **−11.6%** | **0.021 — significant** |
| Bet the UNDER, every time | 352 | 51.7% | +3.5% | 0.49 |
| Big line drop → bet OVER | 25 | 52.0% | −0.1% | 0.99 |
| Big line rise → bet UNDER | 31 | 45.2% | −4.1% | 0.81 |
| Fade 3yr OVER streak (bet under) | 24 | 50.0% | +6.1% | 0.74 |
| Fade 3yr UNDER streak (bet over) | 36 | 52.8% | +5.0% | 0.75 |

The headline isn't any of the streak/jump strategies — it's the naive
baseline: **blindly betting the over on every NFL win total, every year,
2015–2025, lost money at a level that clears statistical significance**
(p=0.021). Betting the under instead would have profited, but that edge
does *not* clear significance on its own (p=0.49). This is consistent with
a well-known phenomenon in win-total markets: public bettors skew toward
overs (fans want to believe their team will be good), and the market prices
around that demand rather than the true probability, leaving the under
side very slightly generous on average.

Just as importantly: **the "big line drop → beat the over" signal that
looked real in win-rate terms (52.0% vs 44.3% baseline) evaporates once
priced correctly** — ROI −0.1%, essentially breakeven. Those wins came at
worse average odds (the market was already pricing in the expected
bounce-back), so the win-rate number alone was misleading. This is exactly
why odds-weighting matters, not just win/loss counting.

## Honest bottom line

Nothing here clears the bar for an actual betting edge. The two most
interesting numbers — the big-line-drop bucket beating over at 52% (n=25),
and the 3-year-under-streak bouncing to 52.8% over the next year (n=36) —
both point the same intuitive direction (fade extreme moves, expect
reversion toward the mean) but neither is statistically significant on its
own, and both come from a small set of buckets that make the multiple-
comparisons problem real. This dataset would need several more years, or a
pooled multi-sport-book sample, before "fade the extreme streak" is
anything more than a plausible hypothesis worth re-testing as more seasons
land.
