"""
One coherent model instead of a bag of hand-weighted signals.

The observations from grade/explore/context all say the same three things:

  1. Whether a season clears its yards line is dominated by AVAILABILITY,
     and availability is partly forecastable from injury history.
  2. Given a full season, the miss has structure: for WR it's the QB tier
     and the re-rate direction; for RB it's the re-rate direction, the
     1,000-1,200 dead zone, and how deep the back goes in drafts.
  3. Year-over-year carryover is ~zero, so last year's *result* is not a
     feature -- only last year's box score and games.

So model it in two stages, per position:

  P(healthy)          logit ~ prior_injury + prior_games         (all rows)
  P(over | healthy)   logit ~ position-specific structural feats (healthy rows)
  P(over)  =  P(over|healthy)*P(healthy) + p_inj*(1 - P(healthy))

  p_inj = empirical P(over | <14 games) for the position (RB ~0.03, WR ~).

Both logits are L2-regularised (small n). Honest evaluation is
leave-one-season-out: fit on 3 seasons, predict the 4th, never peek.

Recommendation = P_hat(over) - P_market(over).  Season yardage O/Us are
posted -114/-114 (no-vig prob 0.5), so edge = P_hat - 0.5; TD props carry
real vig and use FanDuel's no-vig number. Size with fractional Kelly.

Writes data/model_2026.json + data/model_report.txt, prints the summary.
Run: venv/bin/python projects/prop-accuracy/scripts/model.py
"""
import csv
import json
import os
import re

import numpy as np
from sklearn.linear_model import LogisticRegression

HERE = os.path.dirname(__file__)
PROJECT = os.path.dirname(HERE)
ROOT = os.path.dirname(os.path.dirname(PROJECT))
DATA = os.path.join(PROJECT, "data")
import sys
sys.path.insert(0, HERE)
import _ctx26  # noqa: E402

RECV = os.path.join(ROOT, "nfl/sources/receiving_stats/data/receiving_stats.csv")
RUSH = os.path.join(ROOT, "nfl/sources/rushing_stats/data/rushing_stats.csv")
QBW = os.path.join(ROOT, "nfl/sources/qb_starters/data/qb_starter_tiers.csv")
WT = os.path.join(ROOT, "nfl/sources/win_totals/data/win_totals.csv")
FD = os.path.join(ROOT, "nfl/sources/fanduel_season_props/data/fanduel_season_props.csv")
UD = os.path.join(ROOT, "nfl/sources/underdog_adp/data/underdog_adp.csv")
WR_G = os.path.join(DATA, "wr_prop_grades.csv")
RB_G = os.path.join(DATA, "rb_prop_grades.csv")
FDS26 = os.path.join(ROOT, "nfl/sources/firstdown_studio_2026/data/firstdown_2026.csv")
RB_PROPS = os.path.join(ROOT, "nfl/sources/rb_prop_totals/data/rb_prop_totals.csv")
WR_PROPS = os.path.join(ROOT, "nfl/sources/wr_prop_totals/data/wr_prop_totals.csv")


def norm(s):
    s = (s or "").lower().replace(".", "").replace("'", "").replace("-", " ")
    s = re.sub(r"\b(jr|sr|ii|iii|iv|v)\b", "", s)
    return re.sub(r"\s+", " ", s).strip()


# ----------------------------------------------------------------- ref data
def prior_yards(path, yfield):
    d = {}
    for r in csv.DictReader(open(path)):
        d[(norm(r["player"]), int(r["year"]))] = {
            "y": int(r[yfield] or 0), "g": int(r["games"] or 0)}
    return d


QB_TIER = {(int(r["year"]), r["team"]): int(r["tier"])
           for r in csv.DictReader(open(QBW)) if r["tier"]}
WIN_TOT = {(int(r["year"]), r["team"]): float(r["win_total_line"])
           for r in csv.DictReader(open(WT))}
PRECV = prior_yards(RECV, "receiving_yards")
PRUSH = prior_yards(RUSH, "rushing_yards")
RB_ADP = {}
for r in csv.DictReader(open(UD)):
    if r["pos"] == "RB" and r["adp"]:
        RB_ADP.setdefault(int(r["year"]), []).append((norm(r["player"]), float(r["adp"])))
RB_RANK = {y: {n: i for i, (n, _) in enumerate(sorted(v, key=lambda t: t[1]), 1)}
           for y, v in RB_ADP.items()}


# ----------------------------------------------------------------- features
def wr_rows():
    out = []
    for r in csv.DictReader(open(WR_G)):
        if not r["yards_result"]:
            continue
        y = int(r["year"]); tm = r["team_start"] or r["team"]
        p = PRECV.get((norm(r["player"]), y - 1))
        if p is None:
            continue
        line = float(r["yards_line"])
        out.append({
            "year": y, "player": r["player"], "over": int(r["yards_result"] == "over"),
            "games": int(r["games"]), "healthy": int(r["games"]) >= 14,
            "prior_g": p["g"], "prior_injury": int(p["g"] < 14),
            "qb_tier": QB_TIER.get((y, tm), 3),          # 3 = median when unknown
            "rerate": line - p["y"],                      # line minus last year's box score
            "deadzone": int(1000 <= line < 1200),
            "win_total": WIN_TOT.get((y, tm), 8.5),
        })
    return out


def rb_rows():
    out = []
    for r in csv.DictReader(open(RB_G)):
        if r["yards_kind"] != "rush" or not r["yards_result"]:
            continue
        y = int(r["year"])
        p = PRUSH.get((norm(r["player"]), y - 1))
        line = float(r["yards_line"])
        rank = RB_RANK.get(y, {}).get(norm(r["player"]))
        out.append({
            "year": y, "player": r["player"], "over": int(r["yards_result"] == "over"),
            "games": int(r["games"] or 0), "healthy": int(r["games"] or 0) >= 14,
            "prior_g": p["g"] if p else 15, "prior_injury": int(bool(p) and p["g"] < 14),
            "rerate": (line - p["y"]) if p else 0.0,
            "deadzone": int(1000 <= line < 1200),
            "rb31": int(rank is not None and rank >= 31),
            "line": line,
        })
    return out


WR_FEATS = ["qb_tier", "rerate", "deadzone", "prior_injury"]
RB_FEATS = ["rerate", "deadzone", "rb31", "line"]
HEALTH_FEATS = ["prior_injury", "prior_g"]


def _mat(rows, feats):
    return np.array([[r[f] for f in feats] for r in rows], float)


class Standard:
    def fit(self, X):
        self.mu = X.mean(0); self.sd = X.std(0); self.sd[self.sd == 0] = 1
        return self
    def tx(self, X):
        return (X - self.mu) / self.sd


def fit_logit(X, y, C=1.0):
    s = Standard().fit(X)
    m = LogisticRegression(C=C, max_iter=2000)
    m.fit(s.tx(X), y)
    return m, s


def predict_over(rows, mH, sH, mO, sO, p_inj):
    XH = _mat(rows, HEALTH_FEATS)
    ph = mH.predict_proba(sH.tx(XH))[:, 1]
    XO = _mat(rows, feats_for(rows))
    po_h = mO.predict_proba(sO.tx(XO))[:, 1]
    return po_h * ph + p_inj * (1 - ph)


def feats_for(rows):
    return RB_FEATS if "line" in rows[0] else WR_FEATS


# ----------------------------------------------------------------- evaluation
def brier(p, y):
    return float(np.mean((np.asarray(p) - np.asarray(y)) ** 2))


def logloss(p, y):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6); y = np.asarray(y)
    return float(-np.mean(y * np.log(p) + (1 - y) * np.log(1 - p)))


def auc(p, y):
    p = np.asarray(p); y = np.asarray(y)
    pos, neg = p[y == 1], p[y == 0]
    if len(pos) == 0 or len(neg) == 0:
        return float("nan")
    return float(np.mean([(a > b) + 0.5 * (a == b) for a in pos for b in neg]))


def loso(rows, C):
    """leave-one-season-out out-of-sample predictions"""
    yrs = sorted({r["year"] for r in rows})
    oos = {}
    for hold in yrs:
        tr = [r for r in rows if r["year"] != hold]
        te = [r for r in rows if r["year"] == hold]
        p_inj = np.mean([r["over"] for r in tr if not r["healthy"]]) if any(not r["healthy"] for r in tr) else 0.05
        mH, sH = fit_logit(_mat(tr, HEALTH_FEATS), [r["healthy"] for r in tr], C=1.0)
        trh = [r for r in tr if r["healthy"]]
        mO, sO = fit_logit(_mat(trh, feats_for(rows)), [r["over"] for r in trh], C=C)
        for r, pv in zip(te, predict_over(te, mH, sH, mO, sO, p_inj)):
            oos[(r["year"], r["player"])] = pv
    return oos


def best_blend(p_model, p_mkt, y):
    """w* that minimises Brier of  w*p_model + (1-w)*p_mkt  on OOS preds.
    w -> 0 means the signals add nothing beyond the market."""
    ws = np.linspace(0, 1, 41)
    b = [brier(w * p_model + (1 - w) * p_mkt, y) for w in ws]
    i = int(np.argmin(b))
    return float(ws[i]), float(b[i])


def calib(p, y, bins=(0, .35, .45, .55, .65, 1.01)):
    p = np.asarray(p); y = np.asarray(y); lines = []
    for lo, hi in zip(bins[:-1], bins[1:]):
        m = (p >= lo) & (p < hi)
        if m.sum() == 0:
            continue
        lines.append(f"    pred {lo:.2f}-{hi:.2f}: n={m.sum():>3}  predicted {p[m].mean():.0%}  actual {y[m].mean():.0%}")
    return "\n".join(lines)


# ----------------------------------------------------------------- 2026
def kelly(p, dec_odds, frac=0.25):
    b = dec_odds - 1
    f = (p * b - (1 - p)) / b
    return max(0.0, f * frac)


def rb_2026():
    team26, _, _ = _ctx26.load()
    fd = {norm(r["player"]): r for r in csv.DictReader(open(FD))
          if r["position"] == "RB" and r["stat"] == "rush_yds"}
    proj, rnk = {}, {}
    fds = [r for r in csv.DictReader(open(RB_PROPS))
           if r["year"] == "2026" and r["stat"] == "rush_yds" and r["source"] == "firstdown.studio"]
    for i, r in enumerate(sorted(fds, key=lambda x: -float(x["line"])), 1):
        proj[norm(r["player"])] = (float(r["line"]), r["player"]); rnk[norm(r["player"])] = i
    rows = []
    for k, (pl, name) in proj.items():
        f = fd.get(k)
        line = f and float(f["line"]) or pl
        p = PRUSH.get((k, 2025))
        rows.append({
            "player": name, "team": team26.get(k, ""), "line": line,
            "fd_line": float(f["line"]) if f else None,
            "market_p": float(f["no_vig_over"]) if f else 0.5,
            "prior_g": p["g"] if p else 15, "prior_injury": int(bool(p) and p["g"] < 14),
            "prior_y": p["y"] if p else None,
            "rerate": (line - p["y"]) if p else 0.0,
            "deadzone": int(1000 <= line < 1200),
            "rb31": int(rnk.get(k, 99) >= 31),
        })
    return rows


def wr_2026():
    team26, qb26, wt26 = _ctx26.load()
    fd = {norm(r["player"]): r for r in csv.DictReader(open(FD))
          if r["position"] == "WR" and r["stat"] == "rec_yds"}
    fa = {norm(r["player"]): r for r in csv.DictReader(open(WR_PROPS)) if r["year"] == "2026"}
    TE = {norm(x) for x in ["Brock Bowers", "Travis Kelce", "Trey McBride", "Mark Andrews",
          "George Kittle", "Kyle Pitts", "Colston Loveland", "Tyler Warren"]}
    rows = []
    for k in set(fd) | set(fa):
        if k in TE:
            continue
        f = fd.get(k); g = fa.get(k)
        line = (float(f["line"]) if f else float(g["yards_line"])) if (f or g) else None
        if line is None:
            continue
        tm = team26.get(k, "")
        p = PRECV.get((k, 2025))
        q = qb26.get(tm)
        rows.append({
            "player": (f or {}).get("player") or g["player"], "team": tm, "line": line,
            "fd_line": float(f["line"]) if f else None,
            "market_p": float(f["no_vig_over"]) if f else 0.5,
            "prior_g": p["g"] if p else 15, "prior_injury": int(bool(p) and p["g"] < 14),
            "prior_y": p["y"] if p else None,
            "qb_tier": q[0] if q else 3,
            "rerate": (line - p["y"]) if p else 0.0,
            "deadzone": int(1000 <= line < 1200),
            "win_total": wt26.get(tm, 8.5),
        })
    return rows


# ----------------------------------------------------------------- run
def run_position(name, rows, feats, C):
    yrs = sorted({r["year"] for r in rows})
    oos = loso(rows, C)
    p = np.array([oos[(r["year"], r["player"])] for r in rows])
    y = np.array([r["over"] for r in rows])
    base = y.mean()
    # how much to trust the model vs a fair-line prior (0.5), chosen on OOS
    w, wbrier = best_blend(p, np.full_like(p, 0.5), y)
    pb = w * p + (1 - w) * 0.5
    verdict = ("the signals add real out-of-sample skill" if w >= 0.35 else
               "the signals add a little" if w >= 0.15 else
               "the signals add essentially nothing beyond a fair line")
    lines = [
        f"=== {name}  (n={len(rows)}, {yrs[0]}-{yrs[-1]}, base over rate {base:.0%}) ===",
        f"leave-one-season-out (fit on 3 seasons, predict the 4th):",
        f"    Brier   raw model {brier(p, y):.3f}   fair-line(.5) {brier(np.full_like(p, .5), y):.3f}   base({base:.2f}) {brier(np.full_like(p, base), y):.3f}",
        f"    LogLoss raw model {logloss(p, y):.3f}   fair-line {logloss(np.full_like(p, .5), y):.3f}",
        f"    AUC {auc(p, y):.3f}   directional acc {np.mean((p > .5) == (y == 1)):.0%}",
        f"    optimal blend  w={w:.2f}  ->  P = {w:.2f}*model + {1-w:.2f}*0.5   (Brier {wbrier:.3f})",
        f"    VERDICT: {verdict}.",
        f"  calibration of the blended prediction:",
        calib(pb, y),
    ]
    p_inj = np.mean([r["over"] for r in rows if not r["healthy"]])
    mH, sH = fit_logit(_mat(rows, HEALTH_FEATS), [r["healthy"] for r in rows], C=1.0)
    rh = [r for r in rows if r["healthy"]]
    mO, sO = fit_logit(_mat(rh, feats), [r["over"] for r in rh], C=C)
    lines.append(f"  P(over | healthy) logit coefficients (standardised, full-sample):")
    for f_, c in zip(feats, mO.coef_[0]):
        lines.append(f"    {f_:<12} {c:+.2f}")
    lines.append(f"    (intercept {mO.intercept_[0]:+.2f})   p_inj(over|<14g) = {p_inj:.2f}")
    return "\n".join(lines), (mH, sH, mO, sO, p_inj, w)


def score_2026(rows, models, feats):
    mH, sH, mO, sO, p_inj, w = models
    for r in rows:
        for f in feats + HEALTH_FEATS:
            r.setdefault(f, 0)
    ph = mH.predict_proba(sH.tx(_mat(rows, HEALTH_FEATS)))[:, 1]
    po_h = mO.predict_proba(sO.tx(_mat(rows, feats)))[:, 1]
    out = []
    for r, a, b in zip(rows, po_h, ph):
        p_raw = float(a * b + p_inj * (1 - b))
        # shrink toward the market by the CV-chosen weight
        p_over = w * p_raw + (1 - w) * r["market_p"]
        edge = p_over - r["market_p"]
        dec = 100 / 114 + 1  # -114 both sides
        out.append({
            "player": r["player"], "team": r["team"], "line": r["line"],
            "fd_line": r["fd_line"], "prior_y": r.get("prior_y"),
            "p_healthy": round(float(b), 3), "p_over_raw": round(p_raw, 3),
            "p_over": round(p_over, 3),
            "market_p": round(r["market_p"], 3), "edge": round(edge, 3),
            "side": "OVER" if edge > 0 else "UNDER",
            "kelly_frac": round(kelly(p_over if edge > 0 else 1 - p_over, dec), 3),
        })
    out.sort(key=lambda r: -abs(r["edge"]))
    return out


def main():
    rep = []
    wr, rb = wr_rows(), rb_rows()
    t1, mWR = run_position("WIDE RECEIVERS — receiving yards", wr, WR_FEATS, C=0.5)
    t2, mRB = run_position("RUNNING BACKS — rushing yards", rb, RB_FEATS, C=0.5)
    rep += [t1, "", t2, ""]

    wr26 = score_2026(wr_2026(), mWR, WR_FEATS)
    rb26 = score_2026(rb_2026(), mRB, RB_FEATS)

    def block(title, rows, w, thr=0.06):
        if w < 0.15:
            return (f"=== 2026 {title} ===\n  The {title.split()[0].lower()} signals show no out-of-sample skill "
                    f"(blend w={w:.2f}), so the model makes NO recommendation here -- every line is a fair 50/50.")
        live = [r for r in rows if r["fd_line"] is not None and abs(r["edge"]) >= thr]
        proj = [r for r in rows if r["fd_line"] is None and abs(r["edge"]) >= thr]
        L = [f"=== 2026 {title}  (blend w={w:.2f};  edge = P_model(over) - P_market;  |edge| >= {thr:.02f}) ==="]

        def fmt(r):
            pr = f"'25 {r['prior_y']}y" if r["prior_y"] is not None else "'25 n/a"
            return (f"  {r['side']:<5} {r['player']:<22} {str(r['team'] or '--'):<4} "
                    f"line {r['line']:>6.0f}  P(over) {r['p_over']:.2f}/{r['p_over_raw']:.2f}raw  "
                    f"edge {r['edge']:+.2f}  ¼-Kelly {r['kelly_frac']:.1%}  [{pr}]")
        L.append("  -- vs a LIVE FanDuel posted line (real, if soft, market edge) --")
        L += [fmt(r) for r in live] or ["    (none)"]
        L.append("  -- vs the First Down Studio projection only (no posted book line; treat as directional) --")
        L += [fmt(r) for r in proj[:12]] or ["    (none)"]
        if len(proj) > 12:
            L.append(f"    ... +{len(proj)-12} more")
        return "\n".join(L)

    rep.append(block("RUNNING BACKS", rb26, mRB[-1]))
    rep.append("")
    rep.append(block("WIDE RECEIVERS", wr26, mWR[-1]))

    text = "\n".join(rep)
    print(text)
    open(os.path.join(DATA, "model_report.txt"), "w").write(text + "\n")
    json.dump({"wr": wr26, "rb": rb26}, open(os.path.join(DATA, "model_2026.json"), "w"), indent=1)
    print(f"\nwrote data/model_2026.json + data/model_report.txt")


if __name__ == "__main__":
    main()
