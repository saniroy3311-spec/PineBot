# Pinescript Bot — Build Verification

Build date: 2026-09-19

## Passed

- Python `compileall`: PASS
- `tests/test_parity_core.py`: 8/8 PASS
- `validate_setup.py`: PASS
- Synthetic OHLCV parity-backtester smoke run: PASS, 212 closed trades generated
- `scripts/deploy.sh` shell syntax: PASS
- `scripts/status.sh` shell syntax: PASS
- Dashboard inline JavaScript `node --check`: PASS
- Dashboard route import check: PASS
- Secret/old webhook ID scan: no supplied exchange secret or original webhook strategy ID included

## Expected validator warnings

- Delta credentials are placeholders.
- Emergency bracket is enabled as a production crash/disconnect safety layer and is not Pine logic.

## Runtime dependency installation note

The build environment did not have `ccxt` preinstalled. An isolated `pip install -r requirements.txt` verification was attempted, but this container could not reach PyPI because outbound package-network DNS was unavailable. Therefore the full exchange-connected startup was not executed here. The repository includes `requirements.txt`; install it on the target VPS before running `main.py`.

## Parity certification still pending

Historical 1:1 certification requires the user's actual EMA-20/50 TradingView trade-list export and matching OHLCV/chart source. The included parity harness is ready for that comparison, but aggregate parity must not be claimed before that data is tested.


## Live-tick update validation

- Core tests: 10/10 PASS after enabling `LIVE_TICK_RISK_ENGINE`.
- Added explicit test confirming an intrabar tick upgrades Stage 0→1, activates breakeven and arms the trail without a bar-close call.
