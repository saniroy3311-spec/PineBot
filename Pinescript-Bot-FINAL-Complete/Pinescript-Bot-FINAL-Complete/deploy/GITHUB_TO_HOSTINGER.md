# GitHub -> Hostinger VPS deployment

## Recommended: Hostinger GitHub Actions deployment

1. Create a private GitHub repository and push this project to branch `main`.
2. In Hostinger hPanel, use a Docker-capable VPS (Hostinger's Docker template is supported).
3. Generate a Hostinger API key and obtain the VPS VM ID.
4. In GitHub -> Settings -> Secrets and variables -> Actions, configure:

### Secrets
- `HOSTINGER_API_KEY`
- `PERSONAL_ACCESS_TOKEN` (needed for a private repository)
- `DELTA_API_KEY`
- `DELTA_API_SECRET`
- `GSHEET_SPREADSHEET_ID`
- `GSHEET_CREDENTIALS_JSON`
- `DASHBOARD_USER`
- `DASHBOARD_PASS`

### Variables
- `HOSTINGER_VM_ID`
- `BOT_NAME=Pinescript Bot`
- `BOT_VERSION=1.3.0-final`
- `PINE_PARITY_MODE=true`
- `LIVE_TICK_RISK_ENGINE=true`
- `EXECUTION_MODE=live`
- `LIVE_TRADING_ENABLED=false`
- `DELTA_TESTNET=false`
- `SYMBOL=BTC/USD:USD`
- `DELTA_PRODUCT_SYMBOL=BTCUSD`
- `ALERT_QTY=30`
- `CANDLE_TIMEFRAME=30m`
- `EMA_FAST_LEN=20`
- `EMA_TREND_LEN=50`
- `GSHEET_ENABLED=true`
- `GSHEET_AUTO_CREATE=true`

The included `.github/workflows/deploy-hostinger.yml` deploys on pushes to `main` and can also be run manually.

Keep `LIVE_TRADING_ENABLED=false` for the first deployment. After integration verification, change it deliberately to `true` in GitHub Actions variables and redeploy.

## Alternative: plain Ubuntu VPS + systemd

On the VPS, create a GitHub deploy key for the private repository, then run:

```bash
REPO_URL=git@github.com:OWNER/REPO.git bash deploy/hostinger_systemd_install.sh
```

Edit `/opt/pinescript-bot/.env`, then validate and start:

```bash
cd /opt/pinescript-bot
.venv/bin/python validate_setup.py
.venv/bin/python scripts/verify_integrations.py
systemctl start pinescript_bot
systemctl status pinescript_bot
journalctl -u pinescript_bot -f
```

Dashboard defaults to port 8081.
