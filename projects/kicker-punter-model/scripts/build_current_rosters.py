"""
Which kicker and punter is on each team going into the 2026 season.

Base case: each team's primary kicker/punter is whoever had the most
games/attempts for that team in the 2025 (most recent complete) season, from
our own nfl/sources/{kickers,punters}/data/*.csv.

That base case is then overridden for offseason 2026 moves confirmed by
web search (free-agent signings, releases, trades) -- see KICKER_OVERRIDES
/ PUNTER_OVERRIDES below, each with its own sourcing note. Punters in
particular saw a long real chain of moves this offseason (one trade set off
BAL -> NYG, and separately NO -> HOU -> TEN -> MIN, plus a straight
MIA <-> ATL punter swap) -- verified per-team against multiple independent
sources (team beat writers, contract trackers) rather than a single search
pass, since an early draft of this list had a wrong destination for one of
these chains (a "Kai Kroeger to NYJ" claim, sourced from an unreliable
search summary, that didn't hold up on closer verification).

Every row gets two independent flags:
  new_player   True if this exact person has no usable prior-team history to
               draw an ability estimate from (rookie/UDFA, or a team change
               where we do have career history elsewhere -- still flagged so
               it's visible, but the projection uses their portable career
               ability residual). If no name could be confirmed at all
               ("OPEN"), there's no ability history by definition.
  unstable     True if the team ran through 2+ kickers/punters with
               meaningful volume (>=5 FGA / >=5 punts) in 2025 -- teams
               with a real in-season competition/injury carousel, where next
               year's incumbent is less certain than a clean depth chart.

Output: data/current_rosters_2026.csv
"""
import csv
import os
import sys

HERE = os.path.dirname(os.path.dirname(__file__))
REPO_ROOT = os.path.dirname(os.path.dirname(HERE))
OUT_CSV = os.path.join(HERE, "data", "current_rosters_2026.csv")

KICKING_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "kickers", "data", "kicking_stats.csv")
PUNTING_CSV = os.path.join(REPO_ROOT, "nfl", "sources", "punters", "data", "punting_stats.csv")

sys.path.insert(0, REPO_ROOT)

# Teams that ran multiple kickers/punters with >=5 FGA / >=5 punts in 2025 --
# computed from the raw data (see README): kicker carousel is far more common
# than punter carousel across the league.
UNSTABLE_K_TEAMS = {"ATL", "CHI", "IND", "LAR", "NO", "NYG", "WAS"}
# ARI/BUF: ran multiple punters with real volume in 2025 (data-driven, see README).
# HOU/MIA/PIT: confirmed genuine open competitions for the 2026 job specifically
# (see PUNTER_OVERRIDES notes below) -- added on top of the 2025 data-driven set.
UNSTABLE_P_TEAMS = {"ARI", "BUF", "HOU", "MIA", "PIT"}

# Confirmed 2026-offseason moves (name, team, new_player, note). Anything not
# listed here falls back to the 2025 primary starter, unflagged as new.
# player names use nflverse's "F.Lastname" convention (matches the `player`
# column produced by nfl/sources/{kickers,punters}/pipeline.py) so these key
# straight into kicker_ability.csv / punter_ability.csv.
KICKER_OVERRIDES = {
    "NYG": ("J.Sanders", True,
            "Signed by NYG in 2026 FA -- was MIA's kicker 2018-2024 but missed all of 2025 with a hip injury "
            "(so his ability history is necessarily anchored on his last active season, 2024, plus a real "
            "return-from-injury question mark this doesn't otherwise capture)"),
    "IND": ("B.Grupe", True,
            "2025 was a Badgley/Grupe/Shrader carousel; Blake Grupe (10/10 XP, 11/11 FG, including four 50+ "
            "yarders, in relief duty) is favored to keep the job over Spencer Shrader (returning from a "
            "season-ending knee injury) but this is a real, ongoing 2026 competition, not a settled job"),
    # NOTE: this override exists because of a real bug the default logic below
    # can't handle -- B.Grupe played MORE 2025 games/attempts for NO (weeks
    # 1-12) than for IND (weeks 14-18), so the naive "most 2025 attempts"
    # fallback assigns him to NO even though IND was his actual final/current
    # team (see IND override above) and NO has since moved on to someone
    # else entirely. Caught by cross-checking chronological week data in the
    # raw play-by-play cache, not just season totals -- see README.
    "NO": ("C.Smyth", True,
           "Grupe (see IND override) actually finished 2025 with IND, not NO -- NO's real 2025 finisher was "
           "Charlie Smyth (12/16 FG, 13/13 XP over the final 6 games after taking over in Week 13), who enters "
           "2026 camp as the favorite but is competing with Tanner Brown (no NFL history) for the job"),
}
#
# NOTE: an earlier version of this override list had NYJ/BAL/NO wrong (had
# guessed "Kai Kroeger to NYJ" from an unreliable search summary). Verified
# against multiple independent sources per team below before finalizing --
# there was a long real chain of moves here (Kroeger's trade in particular
# set off BAL -> NYG -> BAL, and separately NO -> HOU -> TEN -> MIN), so
# each entry was checked individually rather than trusting one search pass.
PUNTER_OVERRIDES = {
    "NYG": ("J.Stout", True,
            "Signed by NYG in 2026 FA after 4 years as BAL's punter (Pro Bowl, led NFL in net avg in 2025); "
            "career history is portable, new team"),
    "BAL": ("R.Eckley", True,
            "Incumbent Jordan Stout left for NYG; BAL drafted Ryan Eckley (Michigan State) in the 2026 draft "
            "to replace him -- true rookie, no NFL history"),
    "HOU": ("K.Kroeger", True,
            "Incumbent Tommy Townsend left for TEN; HOU traded for Kai Kroeger from NO. Reportedly competing "
            "with a rookie (Jack Stonehouse) for the job -- career history (NO, 2025) is portable but this is "
            "an open competition, not a settled job"),
    "NO": ("R.Wright", True,
            "Traded away incumbent Kai Kroeger to HOU; signed Ryan Wright away from MIN as the replacement. "
            "Career history is portable, new team"),
    "MIN": ("J.Hekker", True,
            "Incumbent Ryan Wright left for NO; MIN signed veteran Johnny Hekker (from TEN) as the replacement. "
            "Career history is portable, new team"),
    "TEN": ("T.Townsend", True,
            "Replaced incumbent Johnny Hekker (who left for MIN) with Tommy Townsend, signed away from HOU. "
            "Career history is portable, new team"),
    "MIA": ("B.Pinion", True,
            "Incumbent Jake Bailey left for ATL; MIA brought in veteran Bradley Pinion (from ATL, in effect a "
            "straight swap) but also signed UDFA/UFL punter Seth Vernon as camp competition -- treated as an "
            "open competition, Pinion favored as the established veteran"),
    "ATL": ("J.Bailey", True,
            "Lost incumbent Bradley Pinion to MIA; signed Jake Bailey away from MIA as the replacement "
            "(in effect a straight team swap with MIA). Career history is portable, new team"),
    "SF": ("C.Waitman", True,
            "Incumbent Thomas Morstead departed; SF signed Corliss Waitman away from PIT. Career history is "
            "portable, new team"),
    "PIT": ("C.Johnston", True,
            "Lost incumbent Corliss Waitman to SF; re-signed Cameron Johnston, but his 2025 (11 total punts "
            "across two teams due to injury/roster churn) is too thin to trust, and PIT was reportedly still "
            "shopping for more competition (veteran or UDFA) as of this writing -- treat as a real open "
            "question, not a settled job"),
}


def _primary_by_team(csv_path, volume_col):
    import csv as _csv
    rows_by_team = {}
    with open(csv_path) as f:
        for r in _csv.DictReader(f):
            if int(r["year"]) != 2025:
                continue
            team = r["team"]
            vol = int(r[volume_col])
            cur = rows_by_team.get(team)
            if cur is None or vol > cur[1]:
                rows_by_team[team] = (r["player"], vol)
    return {t: name for t, (name, _) in rows_by_team.items()}


def build():
    primary_k = _primary_by_team(KICKING_CSV, "fga")
    primary_p = _primary_by_team(PUNTING_CSV, "punts")
    teams = sorted(set(primary_k) | set(primary_p))

    rows = []
    for team in teams:
        k_override = KICKER_OVERRIDES.get(team)
        if k_override:
            kicker, k_new, k_note = k_override
        else:
            kicker, k_new, k_note = primary_k.get(team), False, "2025 primary starter, no confirmed 2026 change"

        p_override = PUNTER_OVERRIDES.get(team)
        if p_override:
            punter, p_new, p_note = p_override
        else:
            punter, p_new, p_note = primary_p.get(team), False, "2025 primary starter, no confirmed 2026 change"

        rows.append({
            "team": team,
            "kicker": kicker or "OPEN",
            "kicker_new_player": k_new,
            "kicker_unstable_team": team in UNSTABLE_K_TEAMS,
            "kicker_note": k_note,
            "punter": punter or "OPEN",
            "punter_new_player": p_new,
            "punter_unstable_team": team in UNSTABLE_P_TEAMS,
            "punter_note": p_note,
        })

    os.makedirs(os.path.dirname(OUT_CSV), exist_ok=True)
    fieldnames = ["team", "kicker", "kicker_new_player", "kicker_unstable_team", "kicker_note",
                  "punter", "punter_new_player", "punter_unstable_team", "punter_note"]
    with open(OUT_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        w.writerows(rows)
    print(f"Wrote {len(rows)} teams -> {OUT_CSV}")
    return rows


if __name__ == "__main__":
    build()
