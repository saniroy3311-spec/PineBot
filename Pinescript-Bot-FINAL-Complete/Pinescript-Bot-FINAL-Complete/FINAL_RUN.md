# Pinescript Bot - Final Run Profile

Use `.env.example` or `Pinescript-Bot.env` for the first live-market dry run.

Default safety state:

- `DELTA_TESTNET=false` - production market/account endpoint
- `EXECUTION_MODE=paper` - no exchange orders sent
- `LIVE_TRADING_ENABLED=false`
- EMA Fast 20 / EMA Trend 50
- live-tick trailing stage upgrades and intrabar SL/TP/trail exits
- Google Sheets trade logging enabled after credentials + Sheet ID are supplied

Run:

```bash
cp Pinescript-Bot.env .env
# edit .env and add Delta + Google credentials
python validate_setup.py
python scripts/verify_integrations.py
python main.py
```

For real execution later, start from `Pinescript-Bot.production-live.env`. Real orders require BOTH:

```env
EXECUTION_MODE=live
LIVE_TRADING_ENABLED=true
```

Do not commit `.env` or Google service-account credentials.
