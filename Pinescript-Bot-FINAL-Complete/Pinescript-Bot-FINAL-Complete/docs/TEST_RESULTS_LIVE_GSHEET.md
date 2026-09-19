# Pinescript Bot 1.2.0 — Live Account / Paper Execution / Google Sheets Test Results

Validated in the build environment on 2026-09-19.

## Passed

- Python compile-all: PASS
- Existing Pine/EMA 20/50 parity core tests: 10/10 PASS
- Setup validator: PASS with safe defaults
- Old embedded Delta webhook strategy ID scan: CLEAN
- Google service-account secret directory is git-ignored
- Production order routing requires both `EXECUTION_MODE=live` and `LIVE_TRADING_ENABLED=true`
- Paper mode code path returns simulated entry/exit fills and maintains an internal paper position without intentionally calling exchange order endpoints

## Environment limitation

The build environment does not have `ccxt` installed and cannot install packages from the internet here, so the new paper-order network-bound unit test is skipped in this environment. The repo keeps `ccxt==4.4.57` in `requirements.txt`; install dependencies on the deployment host before running `scripts/verify_integrations.py`.

## Recommended deployment verification

1. Copy `Pinescript-Bot.paper-live.env` to `.env`.
2. Add your live Delta credentials and Google Sheet/service-account values.
3. Run `pip install -r requirements.txt`.
4. Run `python validate_setup.py`.
5. Run `python scripts/verify_integrations.py` (read-only Delta; Google integration-test row only).
6. Run `python main.py` in paper mode and wait for a valid EMA 20/50 strategy signal.
7. Confirm both `Order Log` and `Trade Log` in Google Sheets.
8. Only then consider switching to production live order routing.
