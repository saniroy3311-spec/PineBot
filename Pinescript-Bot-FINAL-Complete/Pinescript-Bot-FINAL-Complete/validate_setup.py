"""Pre-flight validation for Pinescript Bot."""
from __future__ import annotations
import sys
import config

EXPECTED = {
    "EMA_FAST_LEN": 20, "EMA_TREND_LEN": 50,
    "ADX_TREND_TH": 20.0, "ADX_RANGE_TH": 18.0,
    "FILTER_ATR_MULT": 1.6, "FILTER_BODY_MULT": 0.4,
    "TREND_RR": 5.0, "RANGE_RR": 3.0,
    "TREND_ATR_MULT": 0.9, "RANGE_ATR_MULT": 0.7,
    "MAX_SL_MULT": 2.0, "MAX_SL_POINTS": 1500.0, "BE_MULT": 1.0,
}

def main() -> int:
    errors=[]; warnings=[]
    for k,v in EXPECTED.items():
        if getattr(config,k) != v:
            errors.append(f"{k}={getattr(config,k)!r}; Pine reference requires {v!r}")
    if config.BREAKOUT_BUFFER_PTS != 0:
        errors.append("BREAKOUT_BUFFER_PTS must be 0 for Pine parity")
    if config.ADX_TOLERANCE != 0:
        errors.append("ADX_TOLERANCE must be 0 for Pine parity")
    if not config.FILTER_VOL_ENABLED:
        errors.append("FILTER_VOL_ENABLED must be true for supplied Pine")
    if not config.TP_HARD_EXIT:
        errors.append("TP_HARD_EXIT must be true; supplied Pine uses strategy.exit(limit=...)")
    if config.BAR_CLOSE_SL_EVAL:
        errors.append("BAR_CLOSE_SL_EVAL must be false; all risk exits are live-tick in this build")
    if not config.LIVE_TICK_RISK_ENGINE:
        errors.append("LIVE_TICK_RISK_ENGINE must be true for the requested live-tick stage/exit model")
    if config.DELTA_API_KEY.startswith(("YOUR_", "PASTE_")) or config.DELTA_API_SECRET.startswith(("YOUR_", "PASTE_")):
        warnings.append("Delta API credentials are placeholders")
    if config.EXECUTION_MODE == "live" and (not config.DELTA_TESTNET) and (not config.LIVE_TRADING_ENABLED):
        errors.append("Production live mode is locked: set LIVE_TRADING_ENABLED=true deliberately")
    if config.EXECUTION_MODE == "paper":
        warnings.append("EXECUTION_MODE=paper: no exchange orders will be sent")
    elif not config.DELTA_TESTNET:
        warnings.append("PRODUCTION LIVE MODE: real orders can be placed")
    if config.GSHEET_ENABLED and not config.GSHEET_SPREADSHEET_ID:
        warnings.append("GSHEET_ENABLED=true but GSHEET_SPREADSHEET_ID is empty")
    if config.PINE_MINTICK <= 0:
        errors.append("PINE_MINTICK must be > 0 and match the TradingView chart")
    if config.PINE_POINT_VALUE <= 0:
        errors.append("PINE_POINT_VALUE must be > 0 and match the TradingView instrument")
    if config.PINE_PARITY_MODE and config.EMERGENCY_BRACKET_ENABLED:
        warnings.append("Emergency bracket is enabled: this is crash protection, not Pine logic, and can diverge only if that wider bracket is hit")

    print(f"{config.BOT_NAME} {config.BOT_VERSION}")
    print(f"EMA {config.EMA_FAST_LEN}/{config.EMA_TREND_LEN} | timeframe {config.CANDLE_TIMEFRAME}")
    print(f"signal feed={'Binance' if config.BINANCE_SIGNAL_FEED else 'Delta'} | mintick={config.PINE_MINTICK}")
    print(f"risk engine={'LIVE TICK' if config.LIVE_TICK_RISK_ENGINE else 'BAR CLOSE'}")
    print(f"execution={config.EXECUTION_MODE.upper()} | delta={'TESTNET' if config.DELTA_TESTNET else 'PRODUCTION'} | live_switch={config.LIVE_TRADING_ENABLED}")
    print(f"google_sheets={'ON' if config.GSHEET_ENABLED else 'OFF'}")
    for w in warnings: print(f"WARNING: {w}")
    for e in errors: print(f"ERROR: {e}")
    if errors:
        return 1
    print("Core Pinescript Bot live-tick configuration: OK")
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
