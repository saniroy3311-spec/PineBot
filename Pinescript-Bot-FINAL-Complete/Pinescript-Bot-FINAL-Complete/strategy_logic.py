"""Compatibility facade for Pinescript Bot strategy logic.

All indicator and entry logic lives in indicators.engine. Risk math lives in
risk.calculator. Keeping one implementation prevents the old Pinescript-Bot problem
where live and backtest paths silently used different filters/parameters.
"""
from __future__ import annotations
from typing import Optional

from config import (
    TRAIL_STAGES, PINE_MINTICK, BE_MULT, MAX_SL_MULT, MAX_SL_POINTS,
    COMMISSION_PCT, ALERT_QTY,
)
from indicators.engine import (
    compute, compute_full_series, evaluate as evaluate_entry,
    SignalType, Signal, IndicatorSnapshot,
)
from risk.calculator import RiskLevels, TrailState, calc_levels


def get_trail_params(stage: int, atr: float) -> tuple[float, float]:
    """Return activation and offset PRICE distances for the active Pine stage."""
    idx = max(stage - 1, 0)
    _, pts_mult, off_mult = TRAIL_STAGES[idx]
    return atr * pts_mult * PINE_MINTICK, atr * off_mult * PINE_MINTICK


def upgrade_trail_stage(current_stage: int, close_profit_dist: float, atr: float) -> int:
    """Pine upgrades trailStage only when the script executes at bar close."""
    new_stage = current_stage
    for i in range(len(TRAIL_STAGES) - 1, -1, -1):
        trigger_mult, _, _ = TRAIL_STAGES[i]
        if close_profit_dist >= atr * trigger_mult:
            new_stage = max(new_stage, i + 1)
            break
    return new_stage


def compute_trail_sl(
    stage: int,
    best_price: float,
    favorable_dist: float,
    is_long: bool,
    atr: float,
) -> Optional[float]:
    """Replicate strategy.exit(trail_points=, trail_offset=) price distances.

    Pine interprets trail_points and trail_offset as tick counts. The Pine code
    passes ATR*multipliers to those parameters, so TradingView converts them to
    price distance by multiplying by syminfo.mintick.
    """
    activation, offset = get_trail_params(stage, atr)
    if favorable_dist < activation:
        return None
    return best_price - offset if is_long else best_price + offset


def should_trigger_be(close_profit_dist: float, atr: float) -> bool:
    # Pine uses `>`, not `>=`, in the breakeven block.
    return close_profit_dist > atr * BE_MULT


def max_sl_threshold(atr: float) -> float:
    return min(atr * MAX_SL_MULT, MAX_SL_POINTS)


def max_sl_hit(current_close: float, entry_price: float, atr: float, is_long: bool) -> bool:
    threshold = max_sl_threshold(atr)
    return current_close <= entry_price - threshold if is_long else current_close >= entry_price + threshold


def calc_real_pl(entry_price: float, exit_price: float, is_long: bool, qty: float = ALERT_QTY) -> float:
    contract_value = 0.001
    raw = ((exit_price - entry_price) if is_long else (entry_price - exit_price)) * qty * contract_value
    fees = (entry_price + exit_price) * qty * contract_value * COMMISSION_PCT
    return raw - fees


def signal_log_record(snap: IndicatorSnapshot, sig: Signal, reason: str = "") -> dict:
    return {
        "timestamp": int(snap.timestamp),
        "candle_open": snap.open,
        "candle_high": snap.high,
        "candle_low": snap.low,
        "candle_close": snap.close,
        "signal_type": sig.signal_type.value,
        "reason": reason,
        "indicator_values": {
            "ema_fast": snap.ema_fast,
            "ema_trend": snap.ema_trend,
            "atr": snap.atr,
            "rsi": snap.rsi,
            "dip": snap.dip,
            "dim": snap.dim,
            "adx": snap.adx,
            "filters_ok": snap.filters_ok,
        },
    }
