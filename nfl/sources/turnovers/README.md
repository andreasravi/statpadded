# turnovers

Team turnover differential per season, 2014–2025 — takeaways, giveaways,
the interception/fumble split of each, and two derived "luck" lenses.

- **Source:** The Football Database —
  `https://www.footballdb.com/statistics/turnovers.html?lg=NFL&yr={year}&type=reg`
- **Output:** `data/turnovers.csv` — `year, team, games, take_int, take_fum,
  take_tot, give_int, give_fum, give_tot, turnover_diff,
  turnover_diff_per_game, fumble_recovery_rate`

## Fetching (manual — footballdb.com is Cloudflare-protected)

Same situation as [`game_results`](../game_results/): plain HTTP gets a 403
from Cloudflare's JS challenge, and it's aggressive enough that even
same-origin `fetch()` calls fired from inside an already-loaded footballdb.com
page get re-challenged (confirmed — rapid successive requests look bot-like
even with a valid browser session/cookies). So every year had to be a real
browser navigation:

1. Navigate to `https://www.footballdb.com/statistics/turnovers.html?lg=NFL&yr={year}&type=reg`
2. Extract `table.statistics tbody tr` rows into structured JSON (team name,
   games, takeaway/giveaway INT/fumble/total splits)
3. Save to `data/raw/turnovers_{year}.json`
4. Re-run `python3 pipeline.py` — pure parsing from there, no more network
   calls needed

All 12 years (2014–2025) are already cached. `data/raw/*.json` stores the
already-extracted rows rather than raw HTML (unlike `game_results`) — the
table markup itself is mostly sortable-header layout divs with nothing
extra once the actual cell values are pulled out.

## Derived columns

- **`turnover_diff`** — matches the site's own "Diff" column (takeaways
  total − giveaways total).
- **`turnover_diff_per_game`** — `turnover_diff / games`. Two team-seasons
  in this data (CIN and BUF, 2022) played only 16 of 17 games due to a
  postponed/cancelled game, so this exists for fair cross-team comparison
  within a season.
- **`fumble_recovery_rate`** — `take_fum / (take_fum + give_fum)`. The
  "luck" lens: recovering a live fumble is close to a 50/50 coin flip
  regardless of team skill (mostly about which team's bodies happen to be
  closest when the ball bounces), while interception rate has a real,
  sticky skill/scheme component (pass rush, coverage scheme, QB
  aggressiveness of opponents faced). A team recovering, say, 65% of all
  fumbles in its games one season is a much stronger regression-to-the-mean
  candidate the next than a team with a similarly inflated interception
  rate — this column isolates that piece instead of lumping it into overall
  turnover margin.

## Run

```bash
source venv/bin/activate
python3 nfl/sources/turnovers/pipeline.py [start_year] [end_year]
```
