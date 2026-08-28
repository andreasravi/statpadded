# underdog_adp

Player-level fantasy-football ADP from Underdog Network's "Fantasy
Rankings — August Update" articles, one per season. Each article embeds a
`Rank`/`ADP`/`Team`/`Pos` table, plus (where the site included it) a
`Diff` column and — 2025 only — a short free-text `Notes` tag
(injury/suspension/trade/rookie/etc.) per player.

- **What it is:** early/mid-August ADP for that season's fantasy draft
  season, i.e. mid-preseason — after OTAs/minicamp/most of the NFL Draft
  buzz has settled, but before final roster cuts and Week 1.
- **Source:** underdognetwork.com. These are Next.js pages that
  server-embed their rankings table as JSON in a `__NEXT_DATA__` script
  tag, so a plain HTML fetch already has the full table — no browser
  rendering needed.
  - 2023: [`2023-fantasy-football-rankings-and-adp-august-update`](https://underdognetwork.com/football/fantasy-rankings/2023-fantasy-football-rankings-and-adp-august-update)
  - 2024: [`2024-fantasy-football-rankings-august-update`](https://underdognetwork.com/football/fantasy-rankings/2024-fantasy-football-rankings-august-update)
  - 2025: [`2025-fantasy-football-rankings-with-preseason-and-training-camp-news`](https://underdognetwork.com/football/fantasy-rankings/2025-fantasy-football-rankings-with-preseason-and-training-camp-news)
- **Run:** `python3 pipeline.py`
- **Output:** `data/underdog_adp.csv` —
  `year, rank, player, team, pos, pos_rank, adp, diff, finish_prev_year, notes`

## Schema drift across years — read before using `diff`/`notes`

Underdog's table columns aren't consistent year to year:

| Year | Has `Diff`? | Has `Notes`? | Has `pos_rank`? |
|---|---|---|---|
| 2023 | no | no | yes |
| 2024 | yes | no | no |
| 2025 | yes | yes | yes |

Missing columns come through as blank in the output CSV rather than being
backfilled or estimated.

**`diff` is not the preseason ADP move.** It looked at first like exactly
what you'd want — a per-player ADP delta — but it turns out to be a small
same-page/last-update tick (mean |diff| ≈ 0.13–0.15 ADP picks, max ~1.1
across both 2024 and 2025), not cumulative movement since earlier in the
offseason. Season-ending injuries that happened well before each article's
cutoff barely move it: Brandon Aiyuk (torn ACL+MCL) sits at `diff = +0.03`
in the 2025 data, Chris Godwin (dislocated ankle) at `diff = -0.24`.
[`projects/preseason-adp-moves`](../../../projects/preseason-adp-moves/)
uses a different ADP source as an independent "after" read instead of this
column — see that project's README for why and how.

`notes` (2025 only) is a short editorial tag, not a controlled vocabulary
— seen values include injury descriptions ("Torn ACL + MCL", "Dislocated
ankle"), "N-M game suspension likely", "Trade Candidate", "Free Agent",
and "Rookie" (used liberally, for every rookie regardless of any news).

## Other normalization notes

- 2023's article embeds a second, unrelated table ("August Capped" —
  Underdog's Capped tournament rankings). The pipeline picks the larger,
  non-"Capped"-titled table as the real rankings.
- Team values use three different conventions across years — bare
  abbreviations (2023, 2025, except `LA` for the Rams), and nickname-only
  with no city (2024, e.g. `"49ers"`). `FA`/`"Free Agent"` isn't a team.
  All normalized to the canonical abbreviation (or blank) by
  `nfl/common/team_codes.py`'s `normalize_underdog_team()`.
- `finish_prev_year` is read from whichever prior-season-finish column
  that year's table has (`"{year-1} Finish"` or `"Finish{year-1}"`).
