# Pinescript Bot — live-tick execution notes

1. EMA defaults are Fast=20 and Trend=50.
2. Entries are still generated from confirmed 30-minute bars.
3. The repo Pine reference uses `calc_on_every_tick=true`.
4. Once a position is open, S1→S5 stage upgrades are evaluated on every live tick.
5. Breakeven is evaluated on every live tick.
6. Initial SL, TP, Max-SL, trail arming, best-price tracking, trail movement and trail exit are live-tick decisions.
7. SL/TP are anchored to the actual filled entry price.
8. `trail_points` and `trail_offset` are converted using `PINE_MINTICK`.
9. `LIVE_TICK_RISK_ENGINE=true` is the required production setting for this behavior.
10. A 30-minute OHLCV backtest cannot prove exact tick-by-tick exit parity because it does not preserve the full sequence of prices within the candle. For exact replay, use tick data or sufficiently granular lower-timeframe data from the same market source.
11. Real exchange PnL can differ from TradingView because of actual spread, slippage, latency, fees, partial fills and order-book liquidity.
