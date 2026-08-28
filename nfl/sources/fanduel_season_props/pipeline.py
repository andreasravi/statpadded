"""
Live FanDuel season-long player prop O/U lines -- rushing yards, rushing
TDs, receiving yards, passing yards, passing TDs -- with the actual posted
odds on each side.

FanDuel's sportsbook web app is served by a public JSON API
(sbapi.<state>.sportsbook.fanduel.com) with a stable web key. The NFL
custom page carries every "Regular Season <stat> 2026-27" market as a
two-runner Over/Under market; the line is in the runner name, the price is
`winRunnerOdds`.

This is a LIVE snapshot, like nfl/sources/kalshi_win_totals -- no year
param, always the season FanDuel currently has up, stamped with the pull
time. Each run overwrites the output and refreshes data/raw_snapshot.json.

Run:    python3 nfl/sources/fanduel_season_props/pipeline.py
Output: data/fanduel_season_props.csv --
        fetched_at, player, position, stat, line, over_odds, under_odds,
        over_implied, under_implied, no_vig_over, market_id
        stat in {rush_yds, rush_td, rec_yds, pass_yds, pass_td}
"""
import csv
import json
import os
import re
import urllib.request
from datetime import datetime, timezone

HERE = os.path.dirname(__file__)
OUT_PATH = os.path.join(HERE, "data", "fanduel_season_props.csv")
RAW_PATH = os.path.join(HERE, "data", "raw_snapshot.json")

# public FanDuel web API key + a state host that answers from anywhere
AK = "FhMFpcPWXMeyZxOx"
URL = ("https://sbapi.nj.sportsbook.fanduel.com/api/content-managed-page"
       "?page=CUSTOM&customPageId=nfl&pbHorizontal=false"
       f"&_ak={AK}&timezone=America%2FNew_York")
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36")

STAT = {
    "Rushing Yards": ("rush_yds", None),
    "Rushing TDs": ("rush_td", None),
    "Receiving Yards": ("rec_yds", None),
    "Rookie Receiving Yards": ("rec_yds", None),
    "Passing Yards": ("pass_yds", None),
    "Passing TDs": ("pass_td", None),
}
POS = {
    "REGULAR_SEASON_PROPS_-_RUNNING_BACKS": "RB",
    "REGULAR_SEASON_PROPS_-_WIDE_RECEIVERS": "WR",
    "REGULAR_SEASON_PROPS_-_QUARTERBACKS": "QB",
}
FIELDNAMES = ["fetched_at", "player", "position", "stat", "line",
              "over_odds", "under_odds", "over_implied", "under_implied",
              "no_vig_over", "market_id"]

_LINE_RE = re.compile(r"(?:Over|Under)\s+([\d.]+)\s*$")
_MKT_RE = re.compile(r"^(.*?)\s+Regular Season\s+(.*?)\s+20\d\d")


def fetch():
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.load(r)


def _am_to_prob(a):
    a = float(a)
    return (-a) / (-a + 100) if a < 0 else 100 / (a + 100)


def parse(doc):
    markets = doc.get("attachments", {}).get("markets", {})
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = []
    for m in markets.values():
        pos = POS.get(m.get("marketType"))
        if not pos:
            continue
        mm = _MKT_RE.match(m.get("marketName", ""))
        if not mm:
            continue
        player, statname = mm.group(1).strip(), mm.group(2).strip()
        if statname not in STAT:
            continue
        stat = STAT[statname][0]
        over = under = line = None
        for rn in m.get("runners", []):
            price = rn.get("winRunnerOdds", {}).get("americanDisplayOdds", {}).get("americanOdds")
            lm = _LINE_RE.search(rn.get("runnerName", ""))
            if lm:
                line = float(lm.group(1))
            if rn.get("runnerName", "").split(f"{player} ")[-1].startswith("Over"):
                over = price
            elif rn.get("runnerName", "").split(f"{player} ")[-1].startswith("Under"):
                under = price
        if line is None or over is None or under is None:
            continue
        po, pu = _am_to_prob(over), _am_to_prob(under)
        rows.append({
            "fetched_at": now, "player": player, "position": pos, "stat": stat,
            "line": f"{line:g}", "over_odds": int(over), "under_odds": int(under),
            "over_implied": round(po, 4), "under_implied": round(pu, 4),
            "no_vig_over": round(po / (po + pu), 4), "market_id": m.get("marketId", ""),
        })
    rows.sort(key=lambda r: (r["position"], r["stat"], -float(r["line"])))
    return rows


def main():
    doc = fetch()
    os.makedirs(os.path.dirname(OUT_PATH), exist_ok=True)
    with open(RAW_PATH, "w") as f:
        json.dump(doc, f)
    rows = parse(doc)
    with open(OUT_PATH, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=FIELDNAMES)
        w.writeheader()
        w.writerows(rows)
    from collections import Counter
    by = Counter((r["position"], r["stat"]) for r in rows)
    for k, v in sorted(by.items()):
        print(f"  {k[0]:<3} {k[1]:<9} {v}")
    print(f"wrote {len(rows)} rows -> {os.path.relpath(OUT_PATH, os.path.dirname(os.path.dirname(os.path.dirname(HERE))))}")


if __name__ == "__main__":
    main()
