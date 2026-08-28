# qb_starters

Primary starting QB per team per season, 2014–2025, plus that QB's
Sando/Athletic [QB Tier](../qb_tiers/) for the same season where available.

**Why this exists:** [`qb_tiers/data/qb_tiers.csv`](../qb_tiers/data/qb_tiers.csv)
is long-format by QB+season, and 36% of its rows have a blank `team` field
(worse in recent seasons — the `athletic_2026_page` trend-chart source,
which supplies most of 2019–2025, doesn't carry team at all), so it can't
be turned into a team-season table on its own. This source supplies the
missing half — who actually started for which team each season — so QB
tier can join in cleanly by `(season, qb_name)`.

- **Source:** Pro-Football-Reference season passing tables —
  `https://www.pro-football-reference.com/years/{year}/passing.htm`.
  Same Cloudflare-protected situation as
  [`game_results`](../game_results/) — pulled via browser, not
  auto-fetched; cached as `data/raw/passing_{year}.json` (QB rows with
  ≥50 pass attempts only — a mop-up 3-attempt backup can't be the primary
  starter, so this just keeps the cache small, not a modeling threshold).
- **"Primary starter"** = the QB with the most `games_started` for that
  team that season, tie-broken by pass attempts. Multi-team aggregate rows
  (PFR's `2TM`/`3TM` rows for a QB traded/cut mid-season) are skipped in
  favor of that QB's separate per-team rows.

## Outputs

- **`data/qb_starters.csv`** — `year, team, qb_name, games_started,
  pass_att`. One row per team-season, 2014–2025 (376 rows — 12 seasons ×
  ~31–32 teams; a couple of 2022 team-seasons list fewer games due to that
  season's Bills–Bengals cancellation, same as `game_results`).
- **`data/qb_starter_tiers.csv`** — `year, team, qb_name, games_started,
  tier, rank_in_season, tier_source`. The subset of the above (298/376 =
  79%) whose starter matched a `qb_tiers.csv` row for that season by
  normalized name (case/punctuation/Jr.-Sr.-II-III stripped). **Rows with
  no tier are simply absent, not filled with a placeholder** — running
  `pipeline.py` prints every unmatched (year, team, QB) so gaps are
  visible rather than silently defaulted. Checked the full unmatched list
  by hand: it's almost entirely rookie-season starters (their debut year
  usually predates their first Sando Tiers appearance — the survey skews
  veteran) and a handful of journeymen/backups-turned-starters who never
  made the survey at all (e.g. Cooper Rush, Nick Mullens, Taylor
  Heinicke) — not a name-matching bug. If you need every team-season
  covered, the fallback for the unmatched rows would be a proxy like
  "worst tier" or "no tier = replacement level," a modeling choice best
  made explicitly in the project that consumes this, not silently here.

## Run

```bash
source venv/bin/activate
python3 nfl/sources/qb_starters/pipeline.py [start_year] [end_year]
```

No network calls — pure parsing of the cached `data/raw/passing_{year}.json`
files (and a join against `qb_tiers.csv`). Extending to a future season
means repeating the manual PFR fetch (see `game_results`' README for the
browser-fetch procedure) for that year's passing table.
