# Pinescript Bot

**Pinescript Bot** is an independent Python trading bot for Delta Exchange India, rebuilt from the supplied Pine Script strategy with the user's requested **EMA Fast = 20 / EMA Trend = 50** configuration.

The same product name is used in the backend, dashboard, service files, logs, and reference Pine script.

## Source of truth

The canonical TradingView reference is:

`pine/Pinescript_Bot_EMA20_50.pine`

The Python strategy defaults mirror that supplied Pine logic:

- Timeframe: 30 minutes
- EMA Fast: 20
- EMA Trend: 50
- ATR: 14
- RSI: 14
- DI length: 14
- ADX smoothing: 14
- ADX EMA: 5
- Trend regime: ADX > 20
- Range regime: ADX < 18
- ATR filter: ATR < SMA(ATR, 50) × 1.6
- Volume filter: Volume > SMA(Volume, 20)
- Body filter: abs(Close - Open) > ATR × 0.4
- Trend RR: 5.0
- Range RR: 3.0
- Trend initial SL: 0.9 × ATR
- Range initial SL: 0.7 × ATR
- Max-SL: min(2.0 × ATR, 1500 points)
- Breakeven trigger: > 1.0 × ATR profit
- Trail stages: `(1.0,.70,.55)`, `(2.0,.55,.45)`, `(3.0,.45,.35)`, `(5.0,.30,.25)`, `(8.0,.20,.15)`

TradingView interprets `trail_points` and `trail_offset` as **ticks**, so the bot converts those values using `PINE_MINTICK`.

## What was fixed

The repo no longer uses the conflicting legacy strategy tuning. Major fixes include:

- EMA defaults changed to **20/50** everywhere.
- Exact Pine ADX/filter/RR/ATR-stop/breakeven/trailing values restored.
- Signal logic matches the supplied Pine: DI direction + previous high/low breakout for Trend, RSI for Range.
- Pine-style EMA/RMA/RSI/DMI/ADX calculations.
- SL/TP anchored to the actual filled entry price, matching `strategy.position_avg_price` semantics.
- TradingView-style next-tick market-entry convention in the parity backtester.
- Trailing activation/offset converted from Pine ticks to price distance.
- **Live-tick risk engine:** S1→S5 stage upgrades, breakeven, TP, initial SL, trailing movement, trailing exit, and Max-SL are evaluated on running live ticks after entry.
- Static SL/TP are active immediately after the actual fill in live-tick mode.
- Entries remain confirmed 30-minute-bar signals; only risk/trailing management is continuous intrabar.
- Legacy wick filters, confirmation delays, and adaptive source-offset changes are disabled in strict parity mode.
- Current Delta India REST/public/private WebSocket endpoints are used.
- Public WS subscription uses the current `ticker` channel; private authentication uses `key-auth` and the low-latency `v2/user_trades` fill channel.
- Restart recovery preserves Trend vs Range from the trade journal.
- First legitimate live signal after startup is no longer skipped.
- One canonical environment template replaces contradictory configurations.
- Dashboard/backend/service naming changed to **Pinescript Bot**.
- Dashboard uses the configured signal source for its candles and does not display a fake live BTC price when the API is unavailable.
- Secrets and old strategy/webhook identifiers were removed from the deliverable.

See `docs/FIX_REPORT.md` and `docs/PARITY_NOTES.md` for more detail.

## Important: historical parity vs live execution

There are two different targets:

1. **Historical bar backtest:** OHLCV-only tests can validate entries and approximate exits, but they cannot reproduce the exact order of realtime ticks inside each 30-minute candle.
2. **Live-tick execution:** the production bot manages stages and exits continuously on incoming prices. Actual Delta fills, spread, latency, slippage, fees, partial fills, and exchange behavior can make live PnL different from TradingView.

The repo reference Pine now uses `calc_on_every_tick=true` so realtime risk management follows the same intended live-tick model. TradingView historical bars still do not contain the full realtime tick sequence, so exact historical equality is not a valid certification target for this mode unless equivalent lower-timeframe/tick replay data is supplied.

## 1. Environment setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
nano .env
python validate_setup.py
python -m unittest tests/test_parity_core.py -v
```

The supplied environment template defaults to:

```text
DELTA_TESTNET=true
PINE_PARITY_MODE=true
LIVE_TICK_RISK_ENGINE=true
EMA_FAST_LEN=20
EMA_TREND_LEN=50
```

Do not commit `.env`.

### Required `.env` values

At minimum replace:

```text
DELTA_API_KEY=YOUR_DELTA_API_KEY
DELTA_API_SECRET=YOUR_DELTA_API_SECRET
DASHBOARD_PASS=CHANGE_THIS_PASSWORD
```

Keep testnet enabled until parity and shadow testing are complete.

## 2. Match the TradingView data source

The **same candle source is mandatory** for meaningful parity.

If the TradingView chart that produced the reference strategy result is Delta `BTCUSD.P`:

```text
BINANCE_SIGNAL_FEED=false
PINE_MINTICK=0.5
```

If the reference chart is Binance `BTCUSDT`, enable Binance and set the chart's actual minimum tick:

```text
BINANCE_SIGNAL_FEED=true
BINANCE_SYMBOL=BTC/USDT
PINE_MINTICK=<TradingView chart mintick>
```

Do not mix Binance OHLCV with Delta volume or vice versa.

## 3. Confirm quantity / point value

The supplied Pine code uses a strategy fixed quantity of 30 and its live alert quantity is 30. This repo therefore defaults to:

```text
ALERT_QTY=30
PINE_ORDER_QTY=30
PINE_POINT_VALUE=0.001
```

If the TradingView Strategy Properties used a quantity override, update the parity values to the exact settings used for that run before comparing PnL.

## 4. Run the parity backtester

Prepare an OHLCV CSV from the **same chart/source** with:

```text
timestamp,open,high,low,close,volume
```

Run:

```bash
python parity_backtest.py data/ohlcv.csv --out data/parity_trades.csv
```

If you normalize the TradingView EMA-20/50 trade export to contain `entry_ts` and `exit_ts`:

```bash
python parity_backtest.py data/ohlcv.csv \
  --out data/parity_trades.csv \
  --expected-trades data/tradingview_trades.csv
```

Do not approve the bot because total PnL is merely “close.” Compare signal, direction, entry timestamp, entry price, trail behavior, exit timestamp, exit price, and reason trade-by-trade.

## 5. Run the bot

```bash
python main.py
```

`main.py` starts both the trading engine and the dashboard. The dashboard default is:

```text
http://<server>:8081
```

Change:

```text
DASHBOARD_USER=admin
DASHBOARD_PASS=CHANGE_THIS_PASSWORD
CLIENT_DASHBOARD_PORT=8081
```

For dashboard-only development:

```bash
uvicorn dashboard.main:app --host 0.0.0.0 --port 8081
```

## 6. Emergency bracket

By default:

```text
EMERGENCY_BRACKET_ENABLED=true
```

This places a **wider exchange-side crash/disconnect stop**. Python still owns the Pine exits. This is intentionally a production safety layer and is not part of the Pine strategy; if the emergency bracket itself is hit, live behavior can differ from Pine.

For controlled testnet parity experiments only, it can be disabled:

```text
EMERGENCY_BRACKET_ENABLED=false
```

## 7. Deployment

### systemd

```bash
sudo cp systemd/pinescript_bot.service /etc/systemd/system/pinescript_bot.service
sudo systemctl daemon-reload
sudo systemctl enable pinescript_bot
sudo systemctl start pinescript_bot
sudo systemctl status pinescript_bot
```

### PM2 alternative

```bash
pm2 start ecosystem.config.js
pm2 save
```

Use systemd **or** PM2, not both.

### Docker

```bash
docker build -t pinescript-bot .
docker run --env-file .env -p 8081:8081 pinescript-bot
```

## Current Delta endpoints used

- Production REST: `https://api.india.delta.exchange`
- Demo/Testnet REST: `https://cdn-ind.testnet.deltaex.org`
- Production public WS: `wss://public-socket.india.delta.exchange`
- Production private WS: `wss://socket.india.delta.exchange`
- Testnet public WS: `wss://socket-ind-pub.testnet.deltaex.org`
- Testnet private WS: `wss://socket-ind.testnet.deltaex.org`

## Files you will normally edit

- `.env` — credentials, source selection, deployment settings
- `pine/Pinescript_Bot_EMA20_50.pine` — TradingView reference
- `data/` — OHLCV and comparison exports during parity testing

`config.py` contains the canonical defaults and should normally not be changed directly.

## Pre-live gate

Do not turn `DELTA_TESTNET=false` until all of these are complete:

- `validate_setup.py` passes.
- Unit tests pass.
- TradingView chart source is confirmed.
- EMA-20/50 TradingView trade export is captured.
- Python backtest is compared trade-by-trade.
- Testnet entry/exit/trail behavior is observed.
- Shadow/live-data operation is compared with TradingView signals.
- Dashboard password and API-key IP restrictions are configured.
- Emergency/manual kill procedure is tested.

No backtest or parity test guarantees future profitability.

## Live account + Google Sheets

This build supports an explicit execution switch:

- `EXECUTION_MODE=paper` — use the configured Delta environment/live prices but send **no orders**.
- `EXECUTION_MODE=live` — order routing is enabled; production also requires `LIVE_TRADING_ENABLED=true`.

Google Sheets logs both `Order Log` events (entry/exit/failure) and completed trades in `Trade Log`. See `docs/LIVE_ACCOUNT_AND_GOOGLE_SHEETS.md`.

Recommended first production-market run:

```env
DELTA_TESTNET=false
EXECUTION_MODE=paper
LIVE_TRADING_ENABLED=false
GSHEET_ENABLED=true
```

Run `python scripts/verify_integrations.py` before starting `main.py`. The verification script is read-only for Delta and writes only an `INTEGRATION_TEST` row to Google Sheets.

---

## Final GitHub -> Hostinger deployment

This final package includes:

- `Pinescript-Bot.final.env` — production environment template (no real secrets)
- `docker-compose.yml` — Hostinger Docker deployment
- `.github/workflows/deploy-hostinger.yml` — official Hostinger GitHub Actions flow
- `deploy/hostinger_systemd_install.sh` — Ubuntu/systemd alternative
- `deploy/update_from_github.sh` — manual VPS update script
- `deploy/GITHUB_TO_HOSTINGER.md` — complete deployment checklist

Never commit `.env` or Google service-account JSON. The repo `.gitignore` already excludes them.
