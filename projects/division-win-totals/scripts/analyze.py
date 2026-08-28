import csv
import os
import statistics as stats

HERE = os.path.dirname(__file__)
REPO_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))

KALSHI_CSV = os.path.join(REPO_ROOT, "nfl/sources/kalshi_win_totals/data/kalshi_win_totals.csv")
WIN_TOTALS_CSV = os.path.join(REPO_ROOT, "nfl/sources/win_totals/data/win_totals.csv")

# NFL divisions, stable since the 2002 realignment (canonical abbrs).
DIVISIONS = {
    "AFC East":  ["BUF", "MIA", "NE", "NYJ"],
    "AFC North": ["BAL", "CIN", "CLE", "PIT"],
    "AFC South": ["HOU", "IND", "JAX", "TEN"],
    "AFC West":  ["DEN", "KC", "LV", "LAC"],
    "NFC East":  ["DAL", "NYG", "PHI", "WAS"],
    "NFC North": ["CHI", "DET", "GB", "MIN"],
    "NFC South": ["ATL", "CAR", "NO", "TB"],
    "NFC West":  ["ARI", "LAR", "SF", "SEA"],
}
TEAM_TO_DIV = {t: d for d, ts in DIVISIONS.items() for t in ts}

# ---- Load 2026 Kalshi lines (current season, going in) ----
kalshi = {}
with open(KALSHI_CSV) as f:
    for r in csv.DictReader(f):
        kalshi[r["team"]] = {
            "implied_line": float(r["implied_line"]),
            "expected_wins": float(r["expected_wins"]),
        }
fetched_at = None
with open(KALSHI_CSV) as f:
    rows = list(csv.DictReader(f))
    fetched_at = rows[0]["fetched_at"]

# ---- Load historical sportsbook win-total lines, 2015-2025 ----
hist_by_year_div = {}  # year -> div -> {"line_sum":..., "teams":{}}
years = set()
with open(WIN_TOTALS_CSV) as f:
    for r in csv.DictReader(f):
        year = int(r["year"])
        team = r["team"]
        div = TEAM_TO_DIV.get(team)
        if div is None:
            continue
        years.add(year)
        hist_by_year_div.setdefault(year, {}).setdefault(div, []).append(float(r["win_total_line"]))

years = sorted(years)

# ---- Division sums, historical, per year ----
print("=" * 78)
print("DIVISION WIN-TOTAL-LINE SUMS BY SEASON (sportsbook lines, Covers.com)")
print("=" * 78)
header = "Division".ljust(11) + "".join(f"{y:>7}" for y in years)
print(header)
div_hist_sums = {d: [] for d in DIVISIONS}
for d in DIVISIONS:
    line = d.ljust(11)
    for y in years:
        vals = hist_by_year_div.get(y, {}).get(d, [])
        s = sum(vals) if len(vals) == 4 else None
        if s is not None:
            div_hist_sums[d].append(s)
        line += f"{s:7.1f}" if s is not None else f"{'--':>7}"
    print(line)

print()
print("=" * 78)
print(f"2026 SEASON -- KALSHI-IMPLIED DIVISION SUMS  (fetched {fetched_at})")
print("=" * 78)
print(f"{'Division':<11}{'Sum(line)':>10}{'Sum(exp)':>10}{'Hist mean':>11}{'Hist std':>10}{'Z-score':>9}   Teams (implied_line)")

rows_out = []
for d, teams in DIVISIONS.items():
    sum_line = sum(kalshi[t]["implied_line"] for t in teams)
    sum_exp = sum(kalshi[t]["expected_wins"] for t in teams)
    hist = div_hist_sums[d]
    mean = stats.mean(hist)
    sd = stats.pstdev(hist) if len(hist) > 1 else 0.0
    z = (sum_line - mean) / sd if sd > 0 else float("nan")
    team_str = ", ".join(f"{t} {kalshi[t]['implied_line']:.1f}" for t in teams)
    print(f"{d:<11}{sum_line:>10.2f}{sum_exp:>10.2f}{mean:>11.2f}{sd:>10.2f}{z:>9.2f}   {team_str}")
    rows_out.append({
        "division": d, "sum_implied_line": round(sum_line, 2),
        "sum_expected_wins": round(sum_exp, 2),
        "hist_mean": round(mean, 2), "hist_std": round(sd, 2), "z_score": round(z, 2) if sd > 0 else "",
    })

# sanity check: league-wide sum of expected wins should land near 272 (17 games x 32 teams / 2)
league_sum_exp = sum(v["expected_wins"] for v in kalshi.values())
league_sum_line = sum(v["implied_line"] for v in kalshi.values())
print()
print(f"League-wide sum of expected_wins: {league_sum_exp:.1f}  (target: 272.0 = 17 games x 32 teams / 2)")
print(f"League-wide sum of implied_line:  {league_sum_line:.1f}")

out_csv = os.path.join(HERE, "..", "data", "division_sums.csv")
with open(out_csv, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["division", "sum_implied_line", "sum_expected_wins", "hist_mean", "hist_std", "z_score"])
    w.writeheader()
    w.writerows(rows_out)
print(f"\nWrote {out_csv}")

print()
print("=" * 78)
print("OUTLIERS (|z| >= 1.5 vs 2015-2025 division-sum history)")
print("=" * 78)
outliers = sorted(rows_out, key=lambda r: -abs(r["z_score"]) if r["z_score"] != "" else 0)
for r in outliers:
    if r["z_score"] != "" and abs(r["z_score"]) >= 1.5:
        direction = "STRONGER than usual" if r["z_score"] > 0 else "WEAKER than usual"
        print(f"  {r['division']}: sum={r['sum_implied_line']} vs hist mean {r['hist_mean']} (z={r['z_score']}) -> {direction}")

# ---- also dump full JSON for the artifact (history series + current) ----
import json
out_json = os.path.join(HERE, "..", "data", "division_data.json")
payload = {
    "fetched_at": fetched_at,
    "years": years,
    "divisions": {},
}
for d, teams in DIVISIONS.items():
    hist_series = []
    for y in years:
        vals = hist_by_year_div.get(y, {}).get(d, [])
        hist_series.append(round(sum(vals), 2) if len(vals) == 4 else None)
    payload["divisions"][d] = {
        "teams": [{"team": t, "implied_line": kalshi[t]["implied_line"], "expected_wins": kalshi[t]["expected_wins"]} for t in teams],
        "sum_implied_line": round(sum(kalshi[t]["implied_line"] for t in teams), 2),
        "sum_expected_wins": round(sum(kalshi[t]["expected_wins"] for t in teams), 2),
        "hist_series": hist_series,
        "hist_mean": round(stats.mean(div_hist_sums[d]), 2),
        "hist_std": round(stats.pstdev(div_hist_sums[d]), 2) if len(div_hist_sums[d]) > 1 else 0.0,
    }
with open(out_json, "w") as f:
    json.dump(payload, f, indent=2)
print(f"Wrote {out_json}")
