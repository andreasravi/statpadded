# qb_tiers

Mike Sando's annual "QB Tiers" survey — ~35-55 NFL execs/coaches
anonymously sort every veteran starting QB into 5 tiers (1 = best). Ran
at ESPN Insider 2014–2018, and at [The Athletic](https://www.nytimes.com/athletic/)
(NYT-owned) from 2019 on.

## Sources and how this was built

Both ESPN Insider and The Athletic are paywalled. The Athletic also
doesn't use a predictable per-year URL (confirmed by testing), so each
year's article had to be found individually — mostly via web search
for fan/beat-writer posts that link back to the original as a source.
Data came from five kinds of sources, each recorded per-row in the
`source` / `source_url` columns:

1. **`athletic_2026_page`** — The Athletic's 2026 QB Tiers page, pulled
   via the account holder's own logged-in browser session. Each of the
   35 QBs still in the 2026 survey has a "share of votes by tier" trend
   chart on that one page going back to their debut season — so this
   single page yielded full 2014–2026 history for everyone still
   currently surveyed, without needing 12 years of separate paywalled
   archives.
2. **`athletic_2019_page` / `athletic_2020_page`** — The Athletic's
   2019 (55 voters) and 2020 (50 voters) pages, also pulled via the
   logged-in session. Both are older, prose-only layouts with no
   trend-chart widget, so each QB's tier was inferred by matching
   surnames against the text following each tier's vote-count marker.
   A few name-matching false positives were caught and hand-corrected
   by reading the actual paragraph (e.g. 2020's block about Tyrod
   Taylor initially misfired on "Rivers," who was only mentioned there
   as a point of comparison — see the `note` field in
   `athletic_2020.json` for the full list of corrections).
3. **`athletic_2021_page` / `athletic_2022_page`** — The Athletic's 2021
   and 2022 pages (URLs supplied directly by the account holder). Both
   have explicit numbered name headers per QB (e.g. `31. Drew Lock`,
   `T-7. Lamar Jackson` for ties), so extraction read those headers
   directly rather than name-matching — high confidence, every QB
   positively identified by name.
4. **`athletic_2023_page` / `athletic_2024_page` / `athletic_2025_page`**
   — The Athletic's 2023, 2024 (URL also supplied directly) and 2025
   pages. These use a newer structured module layout (explicit
   rank/name/team/tier/voting-average fields per QB) that parses
   directly and reliably, no name-matching heuristic needed.
5. **`overthecap_2014` / `overthecap_2016` / `overthecap_2017`** — Over
   The Cap (a public, non-paywalled salary-cap site) republishes a
   player/tier/rank table each year alongside their own salary
   analysis of Sando's ESPN Insider results. These were loaded directly
   in-browser and the actual `<table>` markup read, **not** taken from
   an automated summary — an earlier pass at this that trusted a
   fast-model page summary mislabeled columns for the 2015 page (had
   Brady in Tier 4, contradicted by Sando's own recap text saying he
   was a *unanimous Tier 1* that year), so every table used here was
   re-verified against the live DOM. **Important caveat**: Over The Cap
   explicitly strips every QB still on a rookie contract before
   publishing their table (their own text: *"I only wanted to look at
   veteran players (that means no Luck, Bradford, Newton, etc…)"*) —
   those players were still in Sando's actual original survey, just not
   in OTC's republished table. So these years are correct for who they
   include, but structurally undercount the real season: 2017 is
   missing Prescott/Watson/Wentz/Goff/Winston/Mariota, and 2016 was
   missing Carr/Winston/Mariota/Bortles/Bridgewater until
   `reddit_2016_avg_ratings` (below) filled 5 of them in.
6. **`reddit_2015_thread_full`** — a Redditor pasted the full text of
   Sando's original 2015 ESPN Insider piece into a series of top-level
   comments (Over The Cap's own 2015 page has a broken embed,
   `[table id=18 /]` never rendered, so this is the only 2015 source).
   The thread's comment tree is virtualized/deeply nested and couldn't
   be fully expanded through normal navigation — the account holder
   supplied direct permalinks to the specific comments needed, which
   loaded the surrounding context in full. **All 32 QBs recovered with
   exact rank**, matching the article's own per-tier counts exactly
   (6/8/10/8). Supersedes an earlier partial pass that only got Tier
   1's top 4.
7. **`reddit_2016_avg_ratings`** — a different Redditor posted the
   exact average rating (not tier bucket) every QB received in the 2016
   survey, covering 33 QBs — 5 more than `overthecap_2016`'s
   veteran-only table (Carr, Winston, Mariota, Bortles, Bridgewater),
   all excluded there as still technically on rookie-scale deals. The
   28 names shared between the two sources match in exact rank order,
   confirming `overthecap_2016`'s tier boundaries precisely (e.g.
   Roethlisberger's 1.21 is the last Tier 1, Newton's 1.57 the first
   Tier 2). Only the 5 new names were added from this source — their
   tier was **inferred** from where their rating falls relative to
   those confirmed boundaries (the source gives a number, not a tier
   label), so treat those 5 rows as somewhat lower confidence than the
   rest of this dataset; see the `note` field in
   `reddit_2016_avg_ratings.json` for the exact reasoning per QB.
8. **`reddit_2018_thread`** — similarly, a Redditor's post body on
   r/nfl is a full plain-text transcription of Sando's original 2018
   ESPN Insider piece (paywalled at source, with only Tier 1 visible
   without a subscription on ESPN directly). The account holder linked
   this thread directly. **All 32 QBs recovered with exact rank**,
   closing what had been the only season with no real per-QB source at
   all.
8. **`athletic_brady_retrospective`** — a dedicated piece ("Where would
   Tom Brady rank in 2023 Quarterback Tiers?") that happens to publish a
   literal `YEAR / TIER / AVG / RANK` table covering Brady's full
   2014–2022 history in one place. This closed the only gap in Brady's
   coverage (2018) and, as a bonus, gave an independent cross-check for
   every other year he's already in this dataset — all matched exactly,
   including rank.

Every QB+season covered by more than one independent source agrees on
the tier **and** the rank (checked programmatically on every rebuild —
see `build_csv.py`'s conflict check, which would print any
disagreement; there are none as of this build, spanning Brady's 8
overlapping years, Rodgers' 6+, and every other QB with 2+ sources for
a season).

One real inconsistency *was* caught and fixed: `athletic_2022_page`
spelled Mitchell Trubisky as "Mitch Trubisky," which silently created a
second, disconnected QB record until it was normalized to match every
other year's spelling.

One **unresolved, low-stakes discrepancy** remains: `athletic_2026_page`'s
trend chart has Jacoby Brissett flagged Tier 4 for 2018 (no rank given),
but he does not appear anywhere in the independently-transcribed,
exact-32-QB `reddit_2018_thread` list for that year. This isn't a
disagreement in the strict sense — no source contradicts another's
*value* for a shared fact, one source just doesn't mention him — but it
couldn't be independently confirmed either way, so both rows are kept
as-is rather than one being silently dropped.

**Only structured facts were extracted from every source — season, QB,
team, tier, rank — never Sando's written analysis or the anonymous
voter quotes.** That prose is the copyrighted, proprietary part of each
piece; none of it is reproduced or cached anywhere in this repo (which
is public on GitHub).

## Coverage / limitations

**Data quality by year, roughly best to worst:**

| Tier | Seasons | Distinct QBs | Basis |
|---|---|---|---|
| A — solid | 2015, 2018, 2021–2026 | 32–35/yr | Full rosters, explicit structured fields or exact-count verified transcriptions, no guessing |
| B — good, heuristic | 2019, 2020 | 32, 35 | Full rosters, but tier-per-QB inferred by name-matching in prose (no structured markup on these old page layouts); hand-corrected a few misfires in 2020, 2019 checked out clean |
| C — incomplete by design | 2014, 2017 | 21, 27 | Real verified tables, but Over The Cap's source strips every QB still on a rookie contract that year (see note above) — undercounts the true season |
| B+ — mostly complete | 2016 | 34 | 28 QBs at Tier confidence via Over The Cap, plus 5 more (Carr/Winston/Mariota/Bortles/Bridgewater) with an *inferred* tier from a separate exact-rating source — still missing whichever true rookie-contract exclusions neither source caught |

2015 and 2018 were upgraded from thin/partial to full 32-QB coverage
once direct Reddit permalinks (supplied by the account holder) bypassed
the virtualized-comment-tree problem that blocked full extraction
before. **There is no longer a "thin" tier** — every season now has
either a full verified roster or a known, documented reason for a
partial one (rookie-contract exclusions in 2014/2016/2017).

If you're looking at a QB still in the league today, expect clean,
complete data across nearly every year. If you're looking at someone
who retired mid-2010s and was on a rookie deal specifically in
2014/2016/2017, expect a gap in those specific years only.

- Seasons 2014–2026, **95** distinct QBs, 571 rows (verified — every
  overlapping QB+season across every source agrees on both tier and
  rank; one name-spelling bug was caught and fixed, see above). Full
  year-by-year history exists for the 35 QBs still in the 2026 survey,
  Tom Brady has a complete 2014–2022 record, and 2015/2018 are now
  complete 32-QB seasons in their own right. Everyone else (Manning,
  Brees, Roethlisberger, Rivers, Kaepernick, etc.) is only covered for
  the specific years a source was found for — **not** a continuous run
  for their whole career.
- **Peyton Manning is now fully covered for both of his final two
  seasons** (2014 and 2015 — Tier 1, ranks 1 and 5 respectively,
  reflecting the decline the article's own text describes). His only
  real gap is 2016 onward, since he retired after the 2015 season.
- 2021, 2022, 2024 (Athletic) and 2015, 2018 (Reddit) were all
  initially unfound or incomplete via search/navigation, and closed out
  once the account holder supplied exact URLs or comment permalinks
  directly.
- `team` is blank for some `overthecap_2016`/`2017` rows — those pages'
  tables didn't include a team column.
- Where the same QB+season is covered by more than one source, the CSV
  keeps both rows rather than picking one (`build_csv.py` prints any
  case where sources actually *disagree* on the tier — there were none
  as of this build).
- A `tier` of 1 in `athletic_2026_page` rows for older seasons reflects
  that QB's *average tier* that year per the 2026 page's trend chart,
  which can occasionally read as one tier off from a same-year table
  from another source doing its own rounding — check `source` if you
  need the original methodology for a given row.

## Output

- `data/qb_tiers.csv` / `data/qb_tiers.db` (`qb_tiers` table) —
  `season, qb_name, team, tier, rank_in_season, source, source_url`.
  Long format: one row per QB per season per source.
- `data/qb_tiers_10yr_composite.csv` — a **separate, differently-shaped**
  supplementary dataset: `rank, qb_name, team_2023, tier,
  voting_median_2014_2023, source, source_url`. This is Sando's own
  single retrospective ranking (published Aug. 2023) of the 35 QBs who
  appeared most often across all 10 years of the survey to that point,
  by career-to-date median tier vote — not a season snapshot, so it's
  kept out of the main long-format table. Source:
  `athletic_10yr_composite.json`.
- `data/raw/*.json` — the per-source structured extracts that
  `build_csv.py` / `build_composite_csv.py` read from (see the `note`
  field in each file for source-specific caveats).

## Rebuild

```bash
source venv/bin/activate
python3 nfl/sources/qb_tiers/build_csv.py           # data/raw/*.json -> qb_tiers.csv
python3 nfl/sources/qb_tiers/build_db.py            # csv -> qb_tiers.db
python3 nfl/sources/qb_tiers/build_composite_csv.py # raw/athletic_10yr_composite.json -> qb_tiers_10yr_composite.csv
```

There's no automated fetch step — every source here is either
paywalled (requires an authenticated browser session) or a one-off
third-party page. `data/raw/*.json` is checked in as the cached,
already-extracted structured data.

## Extending this further

Every season 2014–2026 now has real per-QB coverage. What's left is
depth for QBs outside the current 2026 survey in 2014/2016/2017 (the
Over The Cap rookie-contract exclusions) — closing those would mean
finding a source for those specific players' 2014/2016/2017 placements
elsewhere (the original ESPN Insider pieces are paywalled with no
known non-paywalled mirror for any of the three).
