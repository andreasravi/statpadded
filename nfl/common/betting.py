"""
Shared odds-weighted backtest helpers.

A win-rate or an average beat-margin treats every bet as worth the same,
but a -180 favorite and a +150 underdog pay off completely differently.
These helpers convert American odds to actual profit so a strategy's
performance can be measured the way it would really be settled: flat
1-unit stakes, win/loss/push resolved against the real price.
"""


def american_odds_profit(odds: str, stake: float = 1.0) -> float:
    """Profit (not including the returned stake) if a bet at these American
    odds wins. E.g. '+120' on a 1-unit stake profits 1.20; '-140' profits
    100/140 = 0.714."""
    odds = odds.strip()
    value = int(odds)
    if value > 0:
        return stake * (value / 100)
    return stake * (100 / abs(value))


def settle_bet(side: str, result: str, over_odds: str, under_odds: str, stake: float = 1.0) -> float:
    """Profit/loss for a single flat-stake bet.

    side:   'over' or 'under' -- which side was bet
    result: 'Over' / 'Under' / 'Push' -- what actually happened
    Returns +profit on a win, -stake on a loss, 0.0 on a push (stake is
    simply returned, no gain/loss).
    """
    if result == "Push":
        return 0.0
    side = side.lower()
    won = (side == "over" and result == "Over") or (side == "under" and result == "Under")
    if won:
        odds = over_odds if side == "over" else under_odds
        return american_odds_profit(odds, stake)
    return -stake


def backtest(bets, stake: float = 1.0):
    """bets: iterable of dicts each with side, result, over_odds, under_odds.
    Returns a summary dict plus the per-bet profit list (for a cumulative
    bankroll chart) and a running-total series.

    Includes a one-sample t-test of the per-bet profits against 0 -- i.e.
    is this strategy's average profit per bet distinguishable from noise?
    Not corrected for multiple comparisons if you're testing several
    strategies from the same dataset; treat p > ~0.05 as unproven.
    """
    profits = []
    for b in bets:
        profits.append(settle_bet(b["side"], b["result"], b["over_odds"], b["under_odds"], stake))

    n = len(profits)
    wins = sum(1 for p in profits if p > 0)
    losses = sum(1 for p in profits if p < 0)
    pushes = sum(1 for p in profits if p == 0)
    total_profit = sum(profits)
    total_staked = n * stake
    roi_pct = (total_profit / total_staked * 100) if total_staked else 0.0

    cumulative = []
    running = 0.0
    for p in profits:
        running += p
        cumulative.append(running)

    p_value = None
    if n >= 2:
        from scipy import stats as _stats
        _, p_value = _stats.ttest_1samp(profits, 0)

    return {
        "n": n,
        "wins": wins,
        "losses": losses,
        "pushes": pushes,
        "win_pct": wins / n * 100 if n else 0.0,
        "total_profit_units": total_profit,
        "total_staked_units": total_staked,
        "roi_pct": roi_pct,
        "profit_per_bet": total_profit / n if n else 0.0,
        "p_value": p_value,
        "cumulative": cumulative,
    }
