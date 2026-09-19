"""TradingView-style parity backtester for Pinescript Bot.

This simulator is designed around the supplied Pine v5 strategy:
- calc_on_every_tick = false
- pyramiding = 0
- market entries created at bar close and filled on the next bar open
- default TradingView historical intrabar path assumptions
- strategy.exit stop/limit/trailing orders
- stage and breakeven updates only at confirmed bar close
- Max-SL strategy.close_all condition evaluated at confirmed bar close

It cannot guarantee byte-for-byte TradingView parity unless the OHLCV dataset,
chart symbol, tick size, slippage, point value, and TradingView strategy settings
are identical. Use --expected-trades to produce a trade-by-trade comparison.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Optional
import json
import math
import pandas as pd

from config import (
    ADX_TREND_TH, ADX_RANGE_TH, FILTER_ATR_MULT, FILTER_BODY_MULT,
    FILTER_VOL_ENABLED, FILTER_VOL_MULT, RSI_OB, RSI_OS,
    PINE_MINTICK, PINE_SLIPPAGE_TICKS, PINE_POINT_VALUE, PINE_ORDER_QTY,
    COMMISSION_PCT, TRAIL_STAGES, TREND_RR, RANGE_RR,
    TREND_ATR_MULT, RANGE_ATR_MULT, MAX_SL_MULT, MAX_SL_POINTS, BE_MULT,
)
from indicators.engine import compute_full_series, IndicatorSnapshot, evaluate, SignalType


@dataclass
class Trade:
    trade_no: int
    signal_type: str
    is_long: bool
    signal_ts: int
    entry_ts: int
    entry_price: float
    exit_ts: int
    exit_price: float
    exit_reason: str
    max_stage: int
    gross_pnl: float
    commission: float
    net_pnl: float


@dataclass
class Position:
    signal_type: str
    is_long: bool
    is_trend: bool
    signal_ts: int
    entry_ts: int
    entry_price: float
    qty: float
    point_value: float
    # orders active for the current bar
    atr: float
    sl: Optional[float] = None
    tp: Optional[float] = None
    be_stop: Optional[float] = None
    stage: int = 0
    trail_armed: bool = False
    trail_best: Optional[float] = None
    trail_activation: Optional[float] = None
    trail_offset: Optional[float] = None
    max_stage: int = 0
    first_bar: bool = True


SLIP = PINE_SLIPPAGE_TICKS * PINE_MINTICK


def _market_fill(price: float, is_buy: bool) -> float:
    return price + SLIP if is_buy else price - SLIP


def _stop_fill(stop: float, is_long: bool) -> float:
    # Exit long = sell stop, adverse slippage lower. Exit short = buy stop, higher.
    return stop - SLIP if is_long else stop + SLIP


def _pnl(entry: float, exit_: float, is_long: bool, qty: float, point_value: float) -> tuple[float, float, float]:
    points = (exit_ - entry) if is_long else (entry - exit_)
    gross = points * qty * point_value
    fees = (entry + exit_) * qty * point_value * COMMISSION_PCT
    return gross, fees, gross - fees


def _row_to_snap(row: pd.Series, prev: pd.Series) -> IndicatorSnapshot:
    atr = float(row.atr)
    atr_sma = float(row.atr_sma)
    vol_sma = float(row.vol_sma)
    vol = float(row.volume)
    atr_ok = atr < atr_sma * FILTER_ATR_MULT
    vol_ok = (vol > vol_sma * FILTER_VOL_MULT) if FILTER_VOL_ENABLED else True
    body_ok = abs(float(row.close) - float(row.open)) > atr * FILTER_BODY_MULT
    adx = float(row.adx)
    return IndicatorSnapshot(
        ema_trend=float(row.ema200), ema_fast=float(row.ema50), atr=atr,
        rsi=float(row.rsi), dip=float(row.dip), dim=float(row.dim),
        adx=adx, adx_raw=float(row.adx_raw), vol_sma=vol_sma,
        atr_sma=atr_sma, trend_regime=adx > ADX_TREND_TH,
        range_regime=adx < ADX_RANGE_TH,
        filters_ok=bool(atr_ok and vol_ok and body_ok), atr_ok=bool(atr_ok),
        vol_ok=bool(vol_ok), body_ok=bool(body_ok), open=float(row.open),
        high=float(row.high), low=float(row.low), close=float(row.close),
        volume=vol, prev_high=float(prev.high), prev_low=float(prev.low),
        timestamp=int(row.timestamp),
    )


def _stage_for_close(current: int, close_profit: float, atr: float) -> int:
    out = current
    for idx in range(len(TRAIL_STAGES) - 1, -1, -1):
        trig, _, _ = TRAIL_STAGES[idx]
        if close_profit >= atr * trig:
            out = max(out, idx + 1)
            break
    return out


def _trail_params(stage: int, atr: float) -> tuple[float, float]:
    idx = max(stage - 1, 0)
    _, pts, off = TRAIL_STAGES[idx]
    return atr * pts * PINE_MINTICK, atr * off * PINE_MINTICK


def _set_trail_order(pos: Position, atr: float) -> None:
    activation_dist, offset = _trail_params(pos.stage, atr)
    pos.atr = atr
    pos.trail_activation = pos.entry_price + activation_dist if pos.is_long else pos.entry_price - activation_dist
    pos.trail_offset = offset
    if pos.trail_armed and pos.trail_best is not None:
        # Updating strategy.exit changes the active trailing offset. Preserve the
        # best favorable price already reached and recompute the live stop.
        pass


def _trail_stop(pos: Position) -> Optional[float]:
    if not pos.trail_armed or pos.trail_best is None or pos.trail_offset is None:
        return None
    return pos.trail_best - pos.trail_offset if pos.is_long else pos.trail_best + pos.trail_offset


def _protective_stop(pos: Position) -> Optional[float]:
    levels = [x for x in (pos.sl, pos.be_stop, _trail_stop(pos)) if x is not None and math.isfinite(x)]
    if not levels:
        return None
    return max(levels) if pos.is_long else min(levels)


def _gap_exit(pos: Position, open_: float) -> Optional[tuple[float, str]]:
    stop = _protective_stop(pos)
    if pos.is_long:
        if stop is not None and open_ <= stop:
            return _stop_fill(open_, True), "Stop gap"
        if pos.tp is not None and open_ >= pos.tp:
            return open_, "TP gap"
    else:
        if stop is not None and open_ >= stop:
            return _stop_fill(open_, False), "Stop gap"
        if pos.tp is not None and open_ <= pos.tp:
            return open_, "TP gap"
    return None


def _walk_segment(pos: Position, a: float, b: float) -> Optional[tuple[float, str]]:
    """Walk one monotonic historical broker-emulator segment from a to b."""
    if a == b:
        return None
    up = b > a

    # LONG
    if pos.is_long:
        if up:
            # Favorable path: TP and trail activation can occur.
            while True:
                events: list[tuple[float, str]] = []
                if pos.tp is not None and a < pos.tp <= b:
                    events.append((pos.tp, "tp"))
                if (not pos.trail_armed and pos.trail_activation is not None
                        and a < pos.trail_activation <= b):
                    events.append((pos.trail_activation, "arm"))
                if not events:
                    if pos.trail_armed:
                        pos.trail_best = max(pos.trail_best or a, b)
                    return None
                px, kind = min(events, key=lambda x: x[0])
                if kind == "tp":
                    return px, "TP"
                pos.trail_armed = True
                pos.trail_best = px
                a = px
        else:
            stop = _protective_stop(pos)
            if stop is not None and b <= stop < a:
                reason = "Trail SL" if _trail_stop(pos) is not None and abs(stop - _trail_stop(pos)) < 1e-9 else ("Breakeven" if pos.be_stop is not None and abs(stop-pos.be_stop)<1e-9 else "SL")
                return _stop_fill(stop, True), reason
            return None

    # SHORT
    else:
        if not up:
            while True:
                events = []
                if pos.tp is not None and b <= pos.tp < a:
                    events.append((pos.tp, "tp"))
                if (not pos.trail_armed and pos.trail_activation is not None
                        and b <= pos.trail_activation < a):
                    events.append((pos.trail_activation, "arm"))
                if not events:
                    if pos.trail_armed:
                        pos.trail_best = min(pos.trail_best if pos.trail_best is not None else a, b)
                    return None
                # Moving down: highest crossed level occurs first.
                px, kind = max(events, key=lambda x: x[0])
                if kind == "tp":
                    return px, "TP"
                pos.trail_armed = True
                pos.trail_best = px
                a = px
        else:
            stop = _protective_stop(pos)
            if stop is not None and a < stop <= b:
                reason = "Trail SL" if _trail_stop(pos) is not None and abs(stop - _trail_stop(pos)) < 1e-9 else ("Breakeven" if pos.be_stop is not None and abs(stop-pos.be_stop)<1e-9 else "SL")
                return _stop_fill(stop, False), reason
            return None


def _process_bar_path(pos: Position, open_: float, high: float, low: float, close: float) -> Optional[tuple[float, str]]:
    gap = _gap_exit(pos, open_)
    if gap:
        return gap
    # TradingView default broker emulator path.
    path = [open_, high, low, close] if abs(open_ - high) < abs(open_ - low) else [open_, low, high, close]
    for a, b in zip(path, path[1:]):
        hit = _walk_segment(pos, a, b)
        if hit:
            return hit
    return None


def _activate_static_orders_at_close(pos: Position, atr: float, close: float) -> Optional[str]:
    atr_mult = TREND_ATR_MULT if pos.is_trend else RANGE_ATR_MULT
    rr = TREND_RR if pos.is_trend else RANGE_RR
    dist = min(atr * atr_mult, MAX_SL_POINTS)
    pos.sl = pos.entry_price - dist if pos.is_long else pos.entry_price + dist
    pos.tp = pos.entry_price + dist * rr if pos.is_long else pos.entry_price - dist * rr

    profit = close - pos.entry_price if pos.is_long else pos.entry_price - close
    pos.stage = _stage_for_close(pos.stage, profit, atr)
    pos.max_stage = max(pos.max_stage, pos.stage)
    _set_trail_order(pos, atr)
    if profit > atr * BE_MULT:
        pos.be_stop = pos.entry_price

    # strategy.close_all() condition: create a market close for next available tick.
    max_dist = min(atr * MAX_SL_MULT, MAX_SL_POINTS)
    max_hit = close <= pos.entry_price - max_dist if pos.is_long else close >= pos.entry_price + max_dist
    return "Max SL" if max_hit else None


def run(df: pd.DataFrame) -> list[Trade]:
    data = compute_full_series(df).reset_index(drop=True)
    trades: list[Trade] = []
    pos: Optional[Position] = None
    pending_entry = None  # (signal, snap)
    pending_market_exit_reason: Optional[str] = None
    trade_no = 0

    for i in range(1, len(data)):
        row = data.iloc[i]
        prev = data.iloc[i-1]
        ts = int(row.timestamp)
        o, h, l, c = map(float, (row.open, row.high, row.low, row.close))

        # Market exit generated by strategy.close_all() at the previous close.
        if pos is not None and pending_market_exit_reason:
            exit_px = _market_fill(o, is_buy=not pos.is_long)
            gross, fees, net = _pnl(pos.entry_price, exit_px, pos.is_long, pos.qty, pos.point_value)
            trade_no += 1
            trades.append(Trade(trade_no, pos.signal_type, pos.is_long, pos.signal_ts, pos.entry_ts,
                                pos.entry_price, ts, exit_px, pending_market_exit_reason, pos.max_stage,
                                gross, fees, net))
            pos = None
            pending_market_exit_reason = None

        # Market entry generated by signal at previous close.
        if pos is None and pending_entry is not None:
            sig, sig_snap = pending_entry
            fill = _market_fill(o, is_buy=sig.is_long)
            pos = Position(
                signal_type=sig.signal_type.value, is_long=sig.is_long, is_trend=sig.is_trend,
                signal_ts=int(sig_snap.timestamp), entry_ts=ts, entry_price=fill,
                qty=PINE_ORDER_QTY, point_value=PINE_POINT_VALUE, atr=sig_snap.atr,
            )
            # On the signal bar, strategy.exit already exists with trail_points /
            # trail_offset, while stop/limit are na because entryPrice is na.
            _set_trail_order(pos, sig_snap.atr)
            pending_entry = None

        # Existing price orders operate through the historical bar.
        if pos is not None:
            hit = _process_bar_path(pos, o, h, l, c)
            if hit:
                exit_px, reason = hit
                gross, fees, net = _pnl(pos.entry_price, exit_px, pos.is_long, pos.qty, pos.point_value)
                trade_no += 1
                trades.append(Trade(trade_no, pos.signal_type, pos.is_long, pos.signal_ts, pos.entry_ts,
                                    pos.entry_price, ts, exit_px, reason, pos.max_stage, gross, fees, net))
                pos = None

        # Pine script executes once at confirmed close.
        if pos is not None:
            # First close after fill initializes entryPrice and activates static exits.
            pending_market_exit_reason = _activate_static_orders_at_close(pos, float(row.atr), c)
            pos.first_bar = False

        # If flat at this close, Pine may generate a new entry market order.
        if pos is None and pending_market_exit_reason is None:
            snap = _row_to_snap(row, prev)
            sig = evaluate(snap, has_position=False)
            if sig.signal_type != SignalType.NONE:
                pending_entry = (sig, snap)

    return trades


def summary(trades: list[Trade]) -> dict:
    if not trades:
        return {"trades": 0, "net_pnl": 0.0, "win_rate": 0.0, "profit_factor": 0.0}
    wins = [t.net_pnl for t in trades if t.net_pnl > 0]
    losses = [t.net_pnl for t in trades if t.net_pnl <= 0]
    gp = sum(wins)
    gl = -sum(losses)
    return {
        "trades": len(trades),
        "net_pnl": sum(t.net_pnl for t in trades),
        "gross_profit": gp,
        "gross_loss": gl,
        "win_rate": 100 * len(wins) / len(trades),
        "profit_factor": gp / gl if gl > 0 else float("inf"),
    }


def compare(bot: pd.DataFrame, expected_path: str) -> dict:
    exp = pd.read_csv(expected_path)
    result = {"expected_trades": len(exp), "bot_trades": len(bot)}
    for col in ("entry_ts", "exit_ts"):
        if col in exp.columns and col in bot.columns:
            a = set(pd.to_numeric(exp[col], errors="coerce").dropna().astype("int64"))
            b = set(pd.to_numeric(bot[col], errors="coerce").dropna().astype("int64"))
            result[f"{col}_missing_in_bot"] = len(a-b)
            result[f"{col}_extra_in_bot"] = len(b-a)
    return result


def main() -> None:
    ap = argparse.ArgumentParser(description="Pinescript Bot TradingView parity backtest")
    ap.add_argument("ohlcv_csv", help="CSV with timestamp,open,high,low,close,volume")
    ap.add_argument("--out", default="data/parity_trades.csv")
    ap.add_argument("--expected-trades", default=None, help="Optional TradingView exported trade CSV")
    args = ap.parse_args()

    df = pd.read_csv(args.ohlcv_csv)
    required = {"timestamp","open","high","low","close","volume"}
    missing = required - set(df.columns)
    if missing:
        raise SystemExit(f"Missing columns: {sorted(missing)}")
    trades = run(df)
    out = pd.DataFrame([asdict(t) for t in trades])
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    out.to_csv(args.out, index=False)
    report = summary(trades)
    if args.expected_trades:
        report["comparison"] = compare(out, args.expected_trades)
    print(json.dumps(report, indent=2))
    print(f"Trades written to {args.out}")


if __name__ == "__main__":
    main()
