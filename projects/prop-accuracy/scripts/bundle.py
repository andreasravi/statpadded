"""
Consolidate every view the two-position report (prop-report.html) needs
into one JSON, so the artifact can embed it and stay self-contained.

Reads the outputs of grade_/analyze_/explore_/context_/watch_ for both
positions and writes data/report_bundle.json.
Run: python3 projects/prop-accuracy/scripts/bundle.py
     (after the grade/analyze/explore/context/watch scripts)
"""
import csv
import json
import os

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
REPO_ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")


def rd(name):
    return list(csv.DictReader(open(os.path.join(DATA, name))))


def jload(name):
    return json.load(open(os.path.join(DATA, name)))


def num(x):
    if x in ("", None):
        return None
    try:
        f = float(x)
        return int(f) if f == int(f) else round(f, 1)
    except ValueError:
        return x


def grades_wr():
    out = []
    for r in rd("wr_prop_grades.csv"):
        out.append({
            "yr": int(r["year"]), "p": r["player"], "tm": r["team_start"] or r["team"],
            "g": int(r["games"]), "traded": r["traded"] == "yes",
            "yl": num(r["yards_line"]), "ya": num(r["yards_actual"]), "yd": num(r["yards_diff"]),
            "rl": num(r["rec_line"]), "ra": num(r["rec_actual"]), "rdi": num(r["rec_diff"]),
            "tl": num(r["td_line"]), "ta": num(r["td_actual"]), "td": num(r["td_diff"]),
        })
    return out


def grades_rb():
    out = []
    for r in rd("rb_prop_grades.csv"):
        out.append({
            "yr": int(r["year"]), "p": r["player"], "tm": r["team_start"] or r["team"],
            "g": int(r["games"]) if r["games"] else None, "traded": r["traded"] == "yes",
            "kind": r["yards_kind"], "adp_rank": num(r["adp_pos_rank"]),
            "yl": num(r["yards_line"]), "ya": num(r["yards_actual"]), "yd": num(r["yards_diff"]),
            "tl": num(r["td_line"]), "ta": num(r["td_actual"]), "td": num(r["td_diff"]),
        })
    return out


def tiers(prefix):
    out = {}
    for metric, fn in (("yards", f"{prefix}hit_rate_by_yards_line.csv"),
                       ("rec", f"{prefix}hit_rate_by_rec_line.csv"),
                       ("td", f"{prefix}hit_rate_by_td_line.csv")):
        path = os.path.join(DATA, fn)
        if not os.path.exists(path):
            continue
        out[metric] = [{k: num(v) for k, v in row.items()} for row in rd(fn)]
    return out


def yoy(fn):
    return [{k: num(v) for k, v in row.items()} for row in rd(fn)]


bundle = {
    "wr": {
        "grades": grades_wr(),
        "explore": jload("wr_explore_summary.json"),
        "ctx": jload("context_summary.json"),
        "tiers": tiers(""),
        "yoy": yoy("year_over_year_reversion.csv"),
        "coverage": [{k: num(v) for k, v in r.items()} for r in rd("adp_coverage_gaps.csv")],
        "watch": [],  # filled from the artifact's own W26 (kept there, has 2026 lines + tags)
    },
    "rb": {
        "grades": grades_rb(),
        "explore": jload("rb_explore_summary.json"),
        "ctx": {
            **jload("rb_context_summary.json"),
            "yards_by_qb_tier": [{k: num(v) for k, v in r.items()}
                                 for r in rd("rb_context_by_qb_tier.csv")],
            "yards_by_win_total": [{k: num(v) for k, v in r.items()}
                                   for r in rd("rb_context_by_win_total.csv")],
        },
        "tiers": tiers("rb_"),
        "yoy": yoy("rb_year_over_year_reversion.csv"),
        "draft_cost": [{k: num(v) for k, v in r.items()} for r in rd("rb_hit_rate_by_draft_cost.csv")],
        "coverage": [{k: num(v) for k, v in r.items()} for r in rd("rb_adp_coverage_gaps.csv")],
        "watch": jload("rb_watch_2026.json"),
    },
}

with open(os.path.join(DATA, "report_bundle.json"), "w") as f:
    json.dump(bundle, f, separators=(",", ":"))

kb = os.path.getsize(os.path.join(DATA, "report_bundle.json")) / 1024
print(f"wrote data/report_bundle.json  ({kb:.0f} KB)  "
      f"wr={len(bundle['wr']['grades'])} rows  rb={len(bundle['rb']['grades'])} rows")
