# Pinescript Bot — Fix Report

## Reference configuration

This repository is based on the supplied Pine v5 strategy with the requested input change:

- EMA Fast = 20
- EMA Trend = 50

No alternative legacy tuning is treated as authoritative.

## Strategy corrections

| Area | Corrected behavior |
|---|---|
| EMA | 20 fast / 50 trend |
| Trend regime | ADX > 20 |
| Range regime | ADX < 18 |
| ATR filter | ATR < SMA(ATR,50) × 1.6 |
| Volume filter | Volume > SMA(Volume,20) |
| Body filter | abs(C-O) > ATR × 0.4 |
| Trend Long | trend + fast>trend + DI+>DI- + close>prev high + filters |
| Trend Short | mirror of Trend Long |
| Range Long | range + RSI<30 + filters |
| Range Short | range + RSI>70 + filters |
| Trend RR | 5.0 |
| Range RR | 3.0 |
| Trend initial stop | 0.9 ATR |
| Range initial stop | 0.7 ATR |
| Breakeven | >1.0 ATR at confirmed close |
| Max SL | min(2 ATR, 1500 points), bar-close condition |
| Trail stages | 1/2/3/5/8 ATR triggers with Pine point/offset values |
| SL/TP anchor | actual fill / position average price |

## Execution corrections

- Entry signal evaluated only from a confirmed 30-minute candle.
- Live market entry is sent after the candle is confirmed, corresponding to the next available-tick concept used by TradingView's broker emulator.
- Static stop/limit orders are not considered active before Pine would have a valid `entryPrice` recalculation.
- The trailing order can be active from the entry because the Pine `strategy.exit` call is tied to the active entry order.
- Stage upgrades and breakeven are close-based; active stop/limit/trailing orders are intrabar execution mechanisms.
- Max-SL is not converted into a tick-level stop.
- Existing position recovery preserves Trend/Range regime when the journal contains the original signal.
- The first genuinely new post-startup signal is no longer discarded.

## Delta connectivity corrections

- Current India production/testnet REST hosts.
- Current public/private WebSocket hosts.
- Current public `ticker` channel.
- Current `key-auth` private WebSocket authentication.
- `v2/user_trades` used for low-latency fill reconciliation.
- Dashboard historical candles use the configured strategy source.

## Operational corrections

- One canonical `.env.example`.
- Testnet and Pine-parity mode are safe defaults.
- Optional emergency exchange-side crash bracket is explicitly separated from Pine strategy logic.
- Dashboard uses the `Pinescript Bot` name.
- systemd and PM2 configs run the same backend entrypoint and are alternatives, not duplicate dashboard processes.
- Placeholder secrets only; no exchange credential is included.

## Verification completed in this build

- Python compilation: passed.
- Core unit tests: 8 passed.
- Setup validator: passed with expected placeholder/safety warnings.
- Parity backtester smoke test: passed on synthetic OHLCV and generated completed trades.
- Bash deployment/status syntax checks: passed.

## Verification still required with user data

The repo cannot truthfully claim proven 1:1 TradingView parity until these exact artifacts from the user's EMA-20/50 run are supplied:

1. Exact TradingView chart/exchange symbol.
2. Exact Strategy Properties used for quantity, slippage, commission and any other overrides.
3. TradingView trade-list export for the EMA-20/50 run.
4. Matching OHLCV data/source for the same period.

Once supplied, run `parity_backtest.py` and investigate every first mismatch rather than comparing only aggregate PnL.

## Live-market limitation

Even after historical strategy parity is proven, live Delta PnL can differ from TradingView because real fills, spread, latency, fees, partial fills, outages and order-book conditions are not the same as a broker emulator.


## Live-tick risk engine update

The requested execution model was changed from bar-close stage management to continuous live-tick management. With `LIVE_TICK_RISK_ENGINE=true`, stage upgrades, breakeven, initial SL, TP, Max-SL, trail arming, best-price movement, trail updates and exits are evaluated on incoming ticks. Entries remain based on confirmed 30-minute strategy signals. The repo Pine reference was changed to `calc_on_every_tick=true` to align realtime behavior.
