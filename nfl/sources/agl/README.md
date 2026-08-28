# agl — Adjusted Games Lost

Team injury-severity per season, 2013–2025 — Football Outsiders'/FTN's
Adjusted Games Lost (AGL) metric.

- **What it is:** not a simple "games missed" count. AGL weights (1)
  injuries to starters and important situational reserves more heavily
  than bench players, and (2) players who take the field *through* an
  injury-report designation (questionable/doubtful) at a reduced weight
  rather than counting them as either fully available or fully out.
  Originated by Bill Barnwell at Football Outsiders in the early 2000s;
  produced today by Aaron Schatz at FTN. Regular season only.
- **Output:** `data/agl.csv` — `year, team, agl, agl_rank, off_agl, def_agl`
  (rank 1 = fewest injuries/healthiest, 32 = most). `off_agl`/`def_agl` are
  blank for seasons whose source article didn't publish (or wasn't
  captured with) an offense/defense split — see coverage table below.

## Sources

Football Outsiders (`footballoutsiders.com`) shut down in 2023 and the
domain no longer resolves at all — its archive is only reachable via the
Wayback Machine now. Aaron Schatz continued the metric at FTN Fantasy
(`ftnfantasy.com`) starting with the 2023 season. Both sites are also
Cloudflare-protected (footballdb.com-style), so every year here was pulled
by navigating a browser to the live page (FTN) or a `web.archive.org`
snapshot (Football Outsiders) and reading the results table out of the
rendered page — same manual-fetch situation as `game_results` and
`turnovers`. Cached as `data/raw/agl_{year}.json`, one file per season,
each with a `source_article` URL and a `source_note` on which article's
table it came from.

| Season(s) | Article | Author, published |
|---|---|---|
| 2013, 2014 | [2014 Adjusted Games Lost](https://www.footballoutsiders.com/stat-analysis/2015/2014-adjusted-games-lost) | Scott Kacsmar, Mar 2015 |
| 2015, 2016 | [2016 Adjusted Games Lost](https://www.footballoutsiders.com/stat-analysis/2017/2016-adjusted-games-lost) | Scott Kacsmar, Apr 2017 |
| 2017, 2018 | [2018 Adjusted Games Lost: Part I](https://www.footballoutsiders.com/stat-analysis/2019/2018-adjusted-games-lost-part-i) | Vincent Verhei, May 2019 |
| 2019 | [2019 Adjusted Games Lost: Part I](https://www.footballoutsiders.com/stat-analysis/2020/2019-adjusted-games-lost-part-i) | Vincent Verhei, Apr 2020 |
| 2020 | [2020 Adjusted Games Lost: Part I](https://www.footballoutsiders.com/stat-analysis/2021/2020-adjusted-games-lost-part-i) | Scott Spratt, Mar 2021 |
| 2021, 2022 | [AGL 2022: Injuries Help Lead to Broncos Trainwreck](https://www.footballoutsiders.com/stat-analysis/2023/agl-2022-injuries-help-lead-broncos-trainwreck) | Aaron Schatz, Mar 2023 |
| 2023 | [Texans Lead 2023 AGL Numbers with OL Injury Record](https://ftnfantasy.com/nfl/texans-lead-2023-agl-numbers-with-ol-injury-record) | Aaron Schatz, Mar 2024 |
| 2024 | [2024 AGL: 49ers Get Smacked Down by Injuries](https://ftnfantasy.com/nfl/2024-agl-49ers-get-smacked-down-by-injuries) | Aaron Schatz, Mar 2025 |
| 2025 | [Adjusted Games Lost 2025: No Team Suffered Like the Cardinals](https://ftnfantasy.com/nfl/adjusted-games-lost-2025-no-team-suffered-like-the-cardinals) | Aaron Schatz, Mar 2026 |

## Methodology drift — read before using this for anything precise

The formula wasn't perfectly static over 13 years: the "probable" injury
designation was removed from NFL reports in 2016 (recalibrating the
weights), and Football Outsiders re-derived "situational reserve" by
actual snap counts starting in 2019 (a bigger, one-time jump in how
reserves get counted). Most articles that cover season *N* also republish
season *N-1*'s total under the then-current methodology, which is usually
a few tenths to a few points off the number that same season's *own*
original article reported. Where more than one vintage of a season's
number exists in the source material, **this dataset uses the most
recently-published restatement** (e.g. 2021's Baltimore total is 180.2,
*without* COVID, from the 2022-season article — not the original
2021-season article's 191.2 *with* COVID; 2018's numbers come from the
2019 article's comparison column, not 2018's own since-corrected table).
The exact vintage used for each season is documented in that season's
`data/raw/agl_{year}.json` `source_note`. **2016 is a known exception**:
the original 155.1 for the record-setting Bears was later restated to
~171.5–171.6 in leaderboard blurbs in 2022+ articles, but no full
32-team restated 2016 table was ever published, so this dataset keeps
2016 at its original (pre-2019-methodology) vintage — treat 2016 AGL
values as not quite comparable to 2019+ seasons.

COVID-19 (2020–2021) is its own wrinkle: 2020's total includes COVID-list
absences (the source article's main published ranking); 2021 is
explicitly *without* COVID per the most recent restatement (matching how
Schatz's own historical leaderboards footnote it). Both seasons will read
somewhat differently from a normal year for reasons that have nothing to
do with playing-field injury luck.

## Coverage

- 2013, 2015–2022: total AGL + rank only (source articles for these
  seasons/vintages didn't publish an offense/defense split I captured).
- 2014, 2023, 2024, 2025: total + offense/defense split.
- Team abbreviations are normalized from each outlet's era-specific codes
  (`JAC`→`JAX`, `LARM`/`STL`→`LAR`, `SD`→`LAC`, `OAK`→`LV`) to the same
  canonical codes used across `nfl/sources/` — see `pipeline.py`'s
  `ABBR_ALIAS`.

## Rebuild

```bash
source venv/bin/activate
python3 nfl/sources/agl/pipeline.py [start_year] [end_year]
```

No network calls — pure parsing of the cached `data/raw/agl_{year}.json`
files. There's no automated fetch step (both source sites are
Cloudflare-protected / one is entirely offline); extending this to future
seasons means repeating the manual browser-fetch process above for the
next year's article.
