"""
Magnitude of preseason ADP moves: early-August ADP (Underdog Network's
August-update rankings) as the "before" vs. late-August ADP (FantasyData's
2QB/superflex top-100 ADP, already fetched by nfl/sources/adp/) as the
"after" — do the biggest movers cluster around injury/suspension/trade news
(Underdog's Notes column, 2025 only), and does a team's ADP volatility that
preseason track its actual in-season injury toll (nfl/sources/agl)?

Why not just use Underdog's own per-page "Diff" column? It turns out to be
noise for this purpose — a small same-page/last-update tick (mean |Diff|
~0.13 picks), not the cumulative preseason move. Proof: Brandon Aiyuk (torn
ACL+MCL) has a 2025 Diff of +0.03; Chris Godwin (dislocated ankle) has
-0.24. Neither looks like a "mover" by that column. See README.

Why FantasyData 2QB ADP as the "after" instead of matching format? It's
what's already in this repo (nfl/sources/adp), it's a genuinely independent
later read (captured for the current season, i.e. later in the same
preseason each of these years), and it has real reason/news data attached
via Underdog's Notes. The format mismatch (single-QB best ball vs.
2QB/superflex) inflates *QB* ADP hugely for structural reasons that have
nothing to do with news — so QBs are excluded entirely, and non-QB movement
is measured as a *rank-within-skill-position-pool* shift rather than a raw
ADP-point delta, which cancels out the systematic "QBs crowd out early
picks in 2QB formats" level shift instead of confusing it for news-driven
movement.

Inputs:
  nfl/sources/underdog_adp/data/underdog_adp.csv   "before" — early/mid
                                                     August ADP + Notes
                                                     (2025 only)
  nfl/sources/adp/data/adp.csv                      "after" — FantasyData
                                                     2QB top-100 ADP,
                                                     captured later same
                                                     preseason
  nfl/sources/agl/data/agl.csv                      team-season Adjusted
                                                     Games Lost (injury
                                                     severity)

Outputs (data/):
  moves.csv                    every matched (or censored-dropout) player,
                                before/after skill-position rank + the move
  top_movers_<year>.csv        biggest movers per year
  notes_category_summary.csv   2025: move magnitude by news-tag category
  team_volatility_vs_agl.csv   team-level move volatility vs AGL

Run:
  python3 projects/preseason-adp-moves/scripts/analyze.py
"""
import os
import re

import pandas as pd
from scipy import stats

HERE = os.path.dirname(__file__)
ROOT = os.path.join(HERE, "..", "..", "..")
UD_PATH = os.path.join(ROOT, "nfl", "sources", "underdog_adp", "data", "underdog_adp.csv")
FD_PATH = os.path.join(ROOT, "nfl", "sources", "adp", "data", "adp.csv")
AGL_PATH = os.path.join(ROOT, "nfl", "sources", "agl", "data", "agl.csv")
OUT_DIR = os.path.join(HERE, "..", "data")

TOP_N = 25
SKILL_POS = {"RB", "WR", "TE"}

NOTE_RULES = [
    ("suspension", ["suspen"]),
    ("injury", [
        "acl", "mcl", "torn", "injur", "ankle", "hamstring", "knee",
        "shoulder", "achilles", "fracture", "surgery", "pup", "concussion",
        "out for season", "ir ",
    ]),
    ("trade", ["trade"]),
    ("free_agent", ["free agent"]),
    ("rookie", ["rookie"]),
]


def tag_note(note):
    if not isinstance(note, str) or not note.strip():
        return "none"
    low = note.lower()
    for label, keywords in NOTE_RULES:
        if any(k in low for k in keywords):
            return label
    return "other"


def norm_name(name):
    name = (name or "").strip()
    name = re.sub(r"[.']", "", name)
    name = re.sub(r"\s+(Jr|Sr|II|III|IV|V)$", "", name, flags=re.I)
    return re.sub(r"\s+", " ", name).lower().strip()


def pos_rank(df, adp_col):
    """Re-rank a year's RB/WR/TE players 1..n *within each position* by
    ADP, in that source's own list. Ranking within position (rather than
    across all skill positions) matters: FantasyData's ADP is 2QB/superflex
    format, which systematically pulls RBs earlier and WRs later relative
    to single-QB best ball, regardless of any news — a cross-position rank
    would read that format shift as "movement." Within-position ranking
    cancels it out, so the diff between sources reflects this player's
    standing among same-position peers, not a format artifact."""
    out = df[df["pos"].isin(SKILL_POS)].copy()
    out = out.sort_values(adp_col).reset_index(drop=True)
    out["pos_rank_"] = out.groupby("pos").cumcount() + 1
    out["pos_pool_size"] = out.groupby("pos")["pos_rank_"].transform("max")
    return out


def build_year(year, ud, fd):
    ud_y = pos_rank(ud[ud.year == year], "adp")
    fd_y = pos_rank(fd[fd.year == year], "adp")
    ud_y["key"] = ud_y["player"].apply(norm_name)
    fd_y["key"] = fd_y["name"].apply(norm_name)

    pool_size = fd_y.groupby("pos")["pos_pool_size"].first().to_dict()
    merged = ud_y.merge(
        fd_y[["key", "pos_rank_", "adp"]].rename(
            columns={"pos_rank_": "after_rank", "adp": "after_adp"}
        ),
        on="key", how="left",
    )
    merged = merged.rename(columns={
        "pos_rank_": "before_rank", "adp": "before_adp",
    })
    merged["year"] = year

    # Players Underdog had inside FantasyData's eventual position pool size
    # but who never show up in the "after" read at all: they didn't move
    # *within* the top-N at that position, they fell out of it. Treat that
    # as censored at "just past the bottom" of the after-pool rather than
    # dropping them silently — undercounts the true fall but keeps them
    # visible as movers.
    after_pool = merged["pos"].map(pool_size)
    censored = merged["after_rank"].isna() & (merged["before_rank"] <= after_pool)
    merged["censored_dropout"] = censored
    merged.loc[censored, "after_rank"] = after_pool[censored] + 1

    matched = merged.dropna(subset=["after_rank"]).copy()
    matched["move"] = matched["after_rank"] - matched["before_rank"]
    return matched


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    ud = pd.read_csv(UD_PATH)
    fd = pd.read_csv(FD_PATH)

    all_years = []
    for year in (2023, 2024, 2025):
        yr = build_year(year, ud, fd)
        all_years.append(yr)
        print(f"\n=== {year}: {len(yr)} skill-position players matched "
              f"before->after ({yr['censored_dropout'].sum()} fell out of "
              f"the after-read entirely) ===")
        print(yr["move"].abs().describe())

        cols = ["player", "team", "pos", "before_adp", "before_rank",
                "after_adp", "after_rank", "move", "censored_dropout"]
        if "notes" in yr.columns and yr["notes"].notna().any():
            cols.append("notes")
        top = yr.reindex(yr["move"].abs().sort_values(ascending=False).index).head(TOP_N)
        top[cols].to_csv(os.path.join(OUT_DIR, f"top_movers_{year}.csv"), index=False)
        print(top[cols].to_string(index=False))

    moves = pd.concat(all_years, ignore_index=True)
    moves.to_csv(os.path.join(OUT_DIR, "moves.csv"), index=False)

    # --- 2025 only: does a Notes tag predict a bigger move? ------------
    y25 = moves[moves.year == 2025].copy()
    y25["abs_move"] = y25["move"].abs()
    y25["note_category"] = y25["notes"].apply(tag_note)

    summary = (
        y25.groupby("note_category")["abs_move"]
        .agg(n="size", mean_abs_move="mean", median_abs_move="median")
        .sort_values("mean_abs_move", ascending=False)
    )
    summary.to_csv(os.path.join(OUT_DIR, "notes_category_summary.csv"))
    print("\n=== 2025: |move| (skill-position ranks) by news-tag category ===")
    print(summary)

    news_cats = {"injury", "suspension", "trade", "free_agent"}
    top_n = y25.reindex(y25["abs_move"].sort_values(ascending=False).index).head(TOP_N)
    n_news_in_top = top_n["note_category"].isin(news_cats).sum()
    base_rate = y25["note_category"].isin(news_cats).mean()
    print(f"\nTop {TOP_N} 2025 movers: {n_news_in_top}/{TOP_N} carry an "
          f"injury/suspension/trade/free-agent tag "
          f"({n_news_in_top / TOP_N:.0%}), vs a {base_rate:.0%} base rate "
          f"across all {len(y25)} matched skill-position players.")

    # --- Team-level: ADP move volatility vs. that season's actual AGL --
    agl = pd.read_csv(AGL_PATH)
    vol = (
        moves.assign(abs_move=moves["move"].abs())
        .dropna(subset=["team"])
        .groupby(["year", "team"])
        .agg(sum_abs_move=("abs_move", "sum"), n_players=("abs_move", "size"))
        .reset_index()
    )
    merged = vol.merge(agl[["year", "team", "agl", "agl_rank"]], on=["year", "team"], how="left")
    merged.to_csv(os.path.join(OUT_DIR, "team_volatility_vs_agl.csv"), index=False)

    clean = merged.dropna(subset=["agl"])
    r, p = stats.pearsonr(clean["sum_abs_move"], clean["agl"])
    print(f"\n=== Team ADP move volatility (sum |move|, 2023-2025) vs. "
          f"that season's AGL ===")
    print(f"n={len(clean)} team-seasons, Pearson r={r:.3f}, p={p:.3f}")
    print("-> data/team_volatility_vs_agl.csv")


if __name__ == "__main__":
    main()
