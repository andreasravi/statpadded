# Win-Total Model

A basic multi-feature model for NFL win totals, combining everything built
this session — ADP, coaching changes, streak history, and point
differential/strength of schedule — then backtested as a betting strategy
and applied to the 2026 season.

## Data sources (all shared, all reused — nothing scraped just for this project)

- [`nfl/sources/win_totals`](../../nfl/sources/win_totals/) — market line, actual wins, over/under result, 2015–2025
- [`nfl/sources/game_results`](../../nfl/sources/game_results/) — point differential, Pythagorean wins, strength of schedule, 2015–2025
- [`nfl/sources/coaches`](../../nfl/sources/coaches/) — new-coach flag per team-season
- [`nfl/sources/adp`](../../nfl/sources/adp/) — fantasy-ADP roster star power (used in feature-building, not in the final 6-feature model — see below)
- [`nfl/sources/kalshi_win_totals`](../../nfl/sources/kalshi_win_totals/) — live 2026 market lines, for the current-season predictions

## The model

`actual_wins ~ new_coach + sos_this_year_line + prior_year_under + prior_beat_margin + prior_actual_wins + prior_pyth_wins`

Deliberately excludes the current season's own market line as an input —
the question is what team fundamentals alone can predict, to compare
against what Vegas already captures.

| Feature | What | In-sample coef | p-value |
|---|---|---|---|
| `new_coach` | coaching change this year (0/1) | −0.21 | 0.627 |
| `sos_this_year_line` | avg of 2026 opponents' own Kalshi/Vegas line | **−1.12** | **0.022** |
| `prior_year_under` | missed the under last year (binary) | −0.94 | 0.130 |
| `prior_beat_margin` | last year's actual wins − line | **−0.35** | **0.016** |
| `prior_actual_wins` | last year's real win total | +0.20 | 0.175 |
| `prior_pyth_wins` | last year's Pythagorean win estimate (point-diff based) | **+0.44** | **0.005** |

n=320 (2016–2025), R²=0.19. For context: the market's own line alone gets
R²=0.28 on the same target — Vegas still captures more than these six
fundamentals do, which is expected (they see injuries, personnel moves,
practice-squad depth, etc. that this model doesn't).

**Reading the coefficients:** schedule difficulty and last year's point
differential move in the expected direction and are the only individually
significant predictors. `new_coach` washes out once you already control for
how good the team actually was (`prior_actual_wins`, `prior_pyth_wins`) —
teams fire coaches *because* they were bad, and "was bad" is already in the
model twice, so the coaching change itself adds no further information.
`prior_beat_margin`'s negative sign is a real mean-reversion effect:
holding wins and point differential fixed, a team that beat a *surprisingly
low* line last year tends to do worse this year than one that didn't —
consistent with the market having priced in something not captured by wins
or point differential alone.

## Backtest: does it work as a betting strategy?

Walk-forward, expanding window — refit on strictly prior seasons only, no
look-ahead, tested on 2020–2025 (192 predictions):

| Min. edge to bet | n | Win% | ROI% | p-value |
|---|---|---|---|---|
| Any disagreement | 192 | 46.4% | −9.1% | 0.18 |
| ≥1 win | 105 | 47.6% | −7.0% | 0.44 |
| ≥2 wins | 32 | 56.2% | +5.3% | 0.75 |

**No demonstrated edge at any threshold.** The high-edge bucket is
nominally profitable but n=32 and p=0.75 — indistinguishable from noise.
Model MAE (2.62 wins) is also worse than just using the market line itself
(2.25 wins) as a predictor. Consistent with everything else this session
found: the market is efficient enough that a handful of public fundamentals
don't produce a reliable, tradeable edge.

## 2026 predictions

Applied the model (refit on all of 2016–2025) to the 2026 season, using
Kalshi's live implied lines (see [`kalshi_win_totals`](../../nfl/sources/kalshi_win_totals/))
for both the current-year strength of schedule and the comparison
benchmark. `new_coach` for 2026 uses a confirmed, user-supplied list of
hires rather than a scraped source (myfootballtoolbox.com hadn't posted
2026 yet, and an initial web search returned self-contradictory results) —
low-stakes either way since `new_coach` wasn't significant in the model.

Full ranked table: `data/predictions_2026.csv`. Biggest disagreements with
the market:

- **Model higher than Kalshi:** Miami (+2.1), Arizona (+2.1), Indianapolis
  (+1.2), Cleveland (+1.0), NY Jets (+0.9)
- **Model lower than Kalshi:** Dallas (−2.7), LA Rams (−1.8), Cincinnati
  (−1.8), Baltimore (−1.6), Green Bay (−1.3)

Given the backtest above, **treat this as "what a basic 6-feature model
thinks," not a betting recommendation** — the identical strategy wasn't
statistically distinguishable from noise on five years of historical bets.

## Pipeline

```bash
source venv/bin/activate
python3 projects/win-total-model/scripts/build_features.py   # -> data/features.csv
python3 projects/win-total-model/scripts/model.py             # in-sample fit + walk-forward backtest
python3 projects/win-total-model/scripts/predict_2026.py      # -> data/predictions_2026.csv
```

`predict_2026.py` needs `nfl/sources/kalshi_win_totals/data/kalshi_win_totals.csv`
(re-run its pipeline for a fresh snapshot) and the 2026 schedule cached at
`nfl/sources/game_results/data/raw_future/pfr_games_2026.html` (fetched via
browser the same way as the historical `game_results` seasons — see that
source's README).
