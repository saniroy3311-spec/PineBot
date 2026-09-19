"""
risk/calculator.py — Pinescript Bot
══════════════════════════════════════════════════════════════════════════════

SL calculation matches Pine Script exactly:
    stopDist = math.min(atr * atrMultActive, maxSLPoints)
    Trend: atrMultActive = 0.9
    Range: atrMultActive = 0.7

    longSL  = entryPrice - stopDist
    longTP  = entryPrice + stopDist * rrActive
    shortSL = entryPrice + stopDist
    shortTP = entryPrice - stopDist * rrActive

CHANGE: TrailState now includes trail_armed and best_price fields.
  Previously these were set as dynamic attributes on the TrailState
  instance in trail_loop.py. Declaring them explicitly in the dataclass
  is cleaner and avoids AttributeError if the fields are accessed before
  trail_loop.start() runs.

  trail_armed — True once activation_price is crossed (trail engine is live)
  best_price  — Running lowest (short) or highest (long) since trail armed
══════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

from dataclasses import dataclass, field

from config import (
    TREND_ATR_MULT, RANGE_ATR_MULT,
    TREND_RR, RANGE_RR,
    MAX_SL_POINTS,
    COMMISSION_PCT,
)


# ─── Dataclasses ───────────────────────────────────────────────────────────────

@dataclass
class RiskLevels:
    """
    Immutable snapshot of SL / TP levels for one trade.

    entry_price  — actual fill price
    sl           — initial stop loss  (entry_price ± ATR × atr_mult)
    tp           — take-profit price  (entry_price ± stopDist × R:R)
    stop_dist    — abs distance from entry_price to SL (pts)
    atr          — entry-bar ATR (used for Max SL and trail math)
    is_long      — True = long, False = short
    is_trend     — True = trend regime, False = range regime
    signal_close — retained for diagnostics only; Pine SL/TP anchor is entry_price
    """
    entry_price:     float
    sl:              float
    tp:              float
    stop_dist:       float
    atr:             float
    is_long:         bool
    is_trend:        bool
    entry_bar_open:  float = 0.0
    signal_close:    float = 0.0  # bar close that generated the signal


@dataclass
class TrailState:
    """
    Mutable per-trade trailing stop state.

    stage        — current trail stage (0 = pre-arm, 1–5 active)
    current_sl   — live stop loss level (initial SL → trail SL once armed)
    peak_price   — legacy field (kept for DB/recovery compat; use best_price)
    be_done      — True once breakeven activated (once per trade)
    max_sl_fired — True once Max SL circuit breaker fired
    trail_armed  — True once activation_price is crossed (Pine trail active)
    best_price   — running extreme since trail armed (min for short, max for long)
    """
    stage:         int   = 0
    current_sl:    float = 0.0
    peak_price:    float = 0.0
    be_done:       bool  = False
    max_sl_fired:  bool  = False
    # Trail engine runtime state (set/reset by trail_loop.start() each trade)
    trail_armed:   bool  = False
    best_price:    float = 0.0


# ─── Core helpers ──────────────────────────────────────────────────────────────

def calc_levels(
    entry_price:    float,
    atr:            float,
    is_long:        bool,
    is_trend:       bool,
    entry_bar_open: float = 0.0,
    signal_close:   float = 0.0,  # diagnostics only; not the SL/TP anchor
) -> RiskLevels:
    """
    Compute initial SL and TP — Pine-exact formula.

    Pine Script:
        entryPrice := strategy.position_avg_price
        stopDist   = math.min(atr * atrMultActive, maxSLPoints)
        shortSL    = entryPrice + stopDist
        shortTP    = entryPrice - stopDist * rrActive

    The supplied Pine file explicitly anchors SL/TP to strategy.position_avg_price.
    signal_close is kept only for audit/debug output and never anchors risk levels.
    """
    atr_mult  = TREND_ATR_MULT if is_trend else RANGE_ATR_MULT
    rr        = TREND_RR       if is_trend else RANGE_RR
    stop_dist = min(atr * atr_mult, MAX_SL_POINTS)

    anchor = entry_price

    if is_long:
        sl = anchor - stop_dist
        tp = anchor + stop_dist * rr
    else:
        sl = anchor + stop_dist
        tp = anchor - stop_dist * rr

    return RiskLevels(
        entry_price    = entry_price,
        sl             = sl,
        tp             = tp,
        stop_dist      = stop_dist,
        atr            = atr,
        is_long        = is_long,
        is_trend       = is_trend,
        entry_bar_open = entry_bar_open,
        signal_close   = signal_close if signal_close > 0 else entry_price,
    )


def recalc_levels_from_fill(risk: RiskLevels, fill_price: float) -> RiskLevels:
    """
    Shift SL / TP by the fill-vs-signal-close difference.
    Used ONLY in the startup recovery path — NOT for new live entries.
    """
    delta = fill_price - risk.entry_price
    return RiskLevels(
        entry_price    = fill_price,
        sl             = risk.sl  + delta,
        tp             = risk.tp  + delta,
        stop_dist      = risk.stop_dist,
        atr            = risk.atr,
        is_long        = risk.is_long,
        is_trend       = risk.is_trend,
        entry_bar_open = risk.entry_bar_open,
        signal_close   = risk.signal_close,
    )


def calc_real_pl(
    entry_price: float,
    exit_price:  float,
    is_long:     bool,
    qty:         int,
) -> float:
    """
    Commission-adjusted P&L using Pine strategy() commission_value=0.05% per fill.
    Delta BTCUSD contract size = 0.001 BTC per contract.
    rawPL = price_points * qty * 0.001
    comm  = (entryPx + exitPx) * qty * 0.001 * COMMISSION_PCT
    """
    contract_value = 0.001
    raw_pl = (
        (exit_price - entry_price) * qty * contract_value if is_long
        else (entry_price - exit_price) * qty * contract_value
    )
    comm = (entry_price + exit_price) * qty * contract_value * COMMISSION_PCT
    return raw_pl - comm


def calc_gross_pl(
    entry_price: float,
    exit_price:  float,
    is_long:     bool,
    qty:         int,
) -> float:
    """
    Gross P&L — no commission. Delta inverse-perp formula:
        points = exitPx - entryPx  (long)
               = entryPx - exitPx  (short)
        gross  = points * qty * 0.001
    """
    points = (
        (exit_price - entry_price) if is_long
        else (entry_price - exit_price)
    )
    return points * qty * 0.001


def lots_to_btc(lots: int, price: float = 0.0) -> float:
    """Delta BTCUSD: one contract/lot represents 0.001 BTC."""
    return lots * 0.001


def calc_pl_breakdown(
    entry_price: float,
    exit_price:  float,
    qty:         int,
    is_long:     bool,
) -> dict:
    """Return raw_pl, commission, net_pl. Used by gsheet.py."""
    contract_value = 0.001
    raw_pl = (
        (exit_price - entry_price) * qty * contract_value if is_long
        else (entry_price - exit_price) * qty * contract_value
    )
    comm   = (entry_price + exit_price) * qty * contract_value * COMMISSION_PCT
    net_pl = raw_pl - comm
    return {"raw_pl": raw_pl, "commission": comm, "net_pl": net_pl}
