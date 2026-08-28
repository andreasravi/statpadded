# preseason-adp-moves

Do the biggest preseason fantasy-football ADP moves cluster around
injury/suspension/trade news, and does a team's ADP volatility that
preseason track its actual in-season injury toll?

Two angles, in order below:
- **Part 1** — within the preseason itself, do the biggest ADP *movers*
  carry injury/news tags?
- **Part 2** — looking back from the *end* of the season, do the biggest
  ADP *busts* (players who cratered relative to their August draft
  position) turn out to have been hurt in August, before the season even
  started?

## Part 1: preseason ADP movers

### The idea, and why the obvious approach didn't work

Underdog Network's August-update rankings articles (2023–2025) include a
per-player `Diff` column that looks, at a glance, like exactly the metric
this question needs — an ADP delta per player. It isn't. It's a small
same-page/last-update tick: mean |Diff| ≈ 0.13–0.15 ADP picks across both
2024 and 2025, max ~1.1. It doesn't reflect cumulative movement over the
preseason. Proof: **Brandon Aiyuk (torn ACL+MCL) has a 2025 `Diff` of
+0.03**; **Chris Godwin (dislocated ankle) has -0.24**. Both should be
among the biggest fallers of the preseason by any real measure, and the
site's own column barely registers them. (Full detail in
[`nfl/sources/underdog_adp/README.md`](../../nfl/sources/underdog_adp/README.md).)

So this instead treats Underdog's August-update ADP as a **"before"**
snapshot and this repo's existing `nfl/sources/adp` (FantasyData 2QB/
superflex top-100 ADP, captured later in the same preseason) as an
independent **"after"** snapshot, and measures the move between the two.

### Method

1. **Before:** [`nfl/sources/underdog_adp`](../../nfl/sources/underdog_adp/)
   — early/mid-August ADP, 2023–2025, plus Underdog's `Notes` tag
   (injury/suspension/trade/rookie/etc.) for 2025 only.
2. **After:** [`nfl/sources/adp`](../../nfl/sources/adp/) — FantasyData's
   2QB/superflex top-100 ADP for the same season, a later, independent
   read.
3. **QBs excluded entirely.** FantasyData's ADP is 2QB/superflex format;
   Underdog's is single-QB best ball. That difference sends QBs off the
   board a full 2–3 rounds earlier in the "after" source for purely
   structural reasons — nothing to do with news. Comparing QB ADP across
   these two sources would just measure the format gap.
4. **Movement is measured as a rank shift *within position* (RB/WR/TE
   separately), not a raw ADP-point delta.** Even excluding QBs, 2QB
   format still systematically reorders RB vs. WR value (RB scarcity
   matters more when two QBs also come off the board) — an early version
   of this analysis that ranked all skill positions together showed almost
   every RB "moving up" and every WR/TE "moving down" between the two
   sources, which is the format artifact, not news. Ranking within
   position in each source separately, then diffing those two ranks,
   cancels that shift out.
5. **FantasyData is capped at the top 100** (its free tier). A player
   Underdog had ranked within that season's eventual top-100-by-position
   size, but who never appears in FantasyData's list at all, is treated as
   a *censored dropout* — they didn't move within the after-list, they
   fell out of it. That's flagged as `censored_dropout=True` and the move
   is measured to "just past the bottom of the after-pool" — an
   undercount of the real fall, but it keeps real news players
   (suspensions especially) visible as movers instead of silently vanishing.
6. Player names are matched between sources on a normalized key
   (punctuation/suffix-stripped, lowercased); match rate is ~99% for the
   FantasyData top 100 for all three years.

Run:
```bash
source venv/bin/activate
python3 nfl/sources/underdog_adp/pipeline.py
python3 nfl/sources/adp/pipeline.py 2023 2025
python3 projects/preseason-adp-moves/scripts/analyze.py
```

### Findings

**Magnitude.** Once the format artifacts are stripped out, real preseason
movement is modest for most players — median move is 2–3 spots within
position, and only the top ~10% of movers exceed 5–9 spots (max 30 in
2023, 23 in 2024, 10 in 2025 — see `data/top_movers_<year>.csv`).
2025 also has the smallest spread of the three years, but with `Notes`
coverage only starting that year and a 3-year sample, that's not enough to
call a trend.

**Do the biggest movers carry a news tag?** Only 2025 has Underdog's
`Notes` column to check this directly. The single biggest 2025 mover *is*
news-driven — **Rashee Rice**, suspended, fell out of FantasyData's top
100 at his position entirely (`censored_dropout`, an 8-spot move by the
capped measure, understating the real fall). But he's also the *only* one:
of the top 25 movers, just 1/25 (4%) carry an injury/suspension/trade/
free-agent tag, barely above the ~1% base rate across all 77 matched
players (`data/notes_category_summary.csv`). The other 24 of the top 25
have no news tag at all — they're ordinary preseason value drift (depth
chart battles, hype, format noise that survived the within-position
correction) rather than anything a note would flag.

Read this as a **negative result for Underdog's own `Notes` field as a
detector**, not necessarily for the underlying hypothesis: `Notes` is
Hayden Winks' editorial shorthand, applied inconsistently (mostly to
rookies and a handful of headline injuries/suspensions), not a systematic
injury log. A cleaner test would tag known preseason injuries from an
actual injury-report source and check whether *those* players show up
disproportionately among the biggest movers — that's a natural next step
this project doesn't yet do.

**Team-level: does preseason ADP volatility predict that team's
in-season injury toll?** Summed |move| per team, matched against that same
season's Adjusted Games Lost ([`nfl/sources/agl`](../../nfl/sources/agl/)):
**r = 0.081, p = 0.435, n = 95 team-seasons** (`data/team_volatility_vs_agl.csv`).
No relationship. Two honest reasons this could be a real null rather than
a broken test: (a) preseason ADP volatility is dominated by *depth-chart*
and *hype* churn, not injuries specifically, so it's a noisy proxy even
before it's matched to a season-long injury metric; (b) n=95 is a small
sample for a correlation this weak to reach significance either way — this
should be read as "no signal found here," not "no relationship exists."

## Part 2: end-of-season busts vs. preseason injuries

Part 1 asks whether an ADP move *within* the preseason carries a news tag.
This part asks the more direct question: looking back from the *end* of
the season, which players busted hardest relative to their August draft
position — and, of those, how many turn out to have actually been hurt in
August (before Week 1), rather than during the season itself?

### Method

This uses Underdog against itself, so there's no cross-source format
problem this time (see Part 1) — QBs stay in.

1. **Preseason:** [`nfl/sources/underdog_adp`](../../nfl/sources/underdog_adp/)
   — August ADP + rank for season *Y*, plus `Notes` (2025 only).
2. **Outcome:** [`nfl/sources/fantasy_finish`](../../nfl/sources/fantasy_finish/)
   — that same season *Y*'s actual final fantasy finish. There's no
   dedicated "final standings" page on Underdog; instead each season's
   finish gets published as a reference column on *next* year's rankings
   article, so this source reads it back out of there (2023's finish from
   the 2024 article, 2024's from the 2025 article, 2025's from the 2026
   article — the first year that article split total-season finish from
   per-game finish).
3. `miss = season_finish − preseason_rank`. A large positive miss means
   the player finished the season far worse than their August draft slot
   implied.
4. Players ranked in the preseason top 200 who **never post a ranked
   finish at all** that season are the strongest candidates of all — they
   didn't just bust, they were largely absent. These are flagged
   separately (`data/busts_<year>.csv` prints them as "vanished").
5. For 2025, a large gap between `per_game_finish` (rate while playing)
   and `season_finish` (total, missed games included) is a secondary
   signature of *missed time* specifically, as opposed to a healthy player
   just being bad.

Run:
```bash
python3 nfl/sources/fantasy_finish/pipeline.py
python3 projects/preseason-adp-moves/scripts/bust_check.py
```

### Findings

**The "vanished" list is a real screen, but it's not automatically
"preseason injury."** It also catches players hurt well into the regular
season — anyone who misses enough of the year ends up with no ranked
finish either way, whether the injury happened in training camp or in
Week 12. Underdog's `Notes` column (2025 only) catches some preseason
cases directly (e.g. Brandon Aiyuk's "Torn ACL + MCL" is right there in
the August data), but it's incomplete — real preseason injuries that
Underdog didn't tag don't show up as `Notes`-flagged, they just show up as
unflagged "vanished" rows alongside in-season injuries. Telling the two
apart isn't something the scraped data alone can do; it takes checking
what actually happened to each candidate.

I checked 8 of the highest-profile unflagged "vanished"/biggest-miss cases
across all three years against news coverage
(`data/verified_preseason_injury_cases.csv`):

| Player | Season | In Notes? | Actually a preseason (before Week 1) injury? |
|---|---|---|---|
| Christian McCaffrey (SF, RB, preseason ADP rank 1) | 2024 | no (no `Notes` column that year) | **Yes** — missed all of camp/preseason with what was announced as a calf issue, later revealed as bilateral Achilles tendinitis; missed the first 8 games |
| Brandon Aiyuk (SF, WR) | 2025 | **yes** — "Torn ACL + MCL" | **Yes** |
| Joe Mixon (HOU, RB) | 2025 | no | **Yes** — undisclosed foot injury, missed all offseason workouts and training camp, missed the entire season, released |
| Najee Harris (then-LAC, RB) | 2025 | no | **Yes** — eye injury from a July 4 fireworks accident, missed all of camp/preseason |
| Kyler Murray (ARI, QB) | 2025 | no | No — foot injury in Week 5 of the regular season |
| Rashee Rice (KC, WR) | 2024 | no (no `Notes` column that year) | No — knee injury (LCL) in Week 4 of the regular season |
| J.K. Dobbins (BAL, RB) | 2023 | no (no `Notes` column that year) | No — torn Achilles in the Week 1 regular-season opener (healthy through preseason) |
| Michael Thomas (NO, WR) | 2023 | no (no `Notes` column that year) | No — knee injury in Week 10 of the regular season |

Half of these (4/8) were genuine preseason injuries; the other half were
in-season injuries that happen to produce the same "vanished from the
finish table" signature. And **3 of the 4 confirmed preseason-injury
cases were never flagged by Underdog's own `Notes` column** — Aiyuk is the
only one of the four that shows up as tagged. So `Notes` catches some real
cases but misses more than it catches, at least in this small sample.

**The clearest example of what this project set out to find** is Christian
McCaffrey's 2024: the single highest-drafted player that preseason (ADP
rank 1 overall), sidelined the entire training camp and preseason by an
injury the team downplayed as a calf issue, out for the first 8 games,
then re-injured and lost for the year — about as large and as clean a
"big preseason injury tanked a big preseason ADP investment" case as
exists in this sample.

## Bottom line

Real (format-corrected) preseason ADP movement is measurable and mostly
modest (Part 1) — a long tail of a handful of big movers per year, and
those movers mostly don't carry a news tag, whether because they're
genuinely un-newsworthy roster churn or because Underdog's `Notes` column
isn't a complete injury log. Team-level, preseason volatility doesn't
predict a team's actual-season injury toll (`agl`).

Looking from the other direction (Part 2) — screening end-of-season busts
for a preseason cause — does surface real, large cases (Christian
McCaffrey's 2024 is the standout), but confirming any individual case
takes checking the news, not just the ADP numbers: about half of the
biggest unexplained preseason-drafted-then-vanished players in this sample
were hurt in the regular season, not the preseason, and Underdog's own
injury notes miss more real preseason-injury cases than they catch.
