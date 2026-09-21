"""Canonical configuration for Pinescript Bot.

Source of truth: the current user-supplied Shiva Sniper Pine Script.
The current strategy uses Fast EMA=50, Trend EMA=200 and bar-close state
updates (calc_on_every_tick=false). Strategy parameters in this file match that
script unless an environment variable explicitly overrides them.

For strict parity, keep PINE_PARITY_MODE=true and do not add execution buffers.
Live fills can still differ from TradingView because TradingView uses a broker
emulator while Delta uses a real order book.
"""
from __future__ import annotations
import os

try:
    from dotenv import load_dotenv
    load_dotenv(override=True)
except ImportError:
    pass


def _b(name: str, default: bool) -> bool:
    return os.environ.get(name, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _i(name: str, default: int) -> int:
    return int(os.environ.get(name, str(default)))


def _f(name: str, default: float) -> float:
    return float(os.environ.get(name, str(default)))


BOT_NAME = os.environ.get("BOT_NAME", "Pinescript Bot")
BOT_VERSION = os.environ.get("BOT_VERSION", "1.2.0-live-gsheet")
PINE_PARITY_MODE = _b("PINE_PARITY_MODE", True)
LIVE_TICK_RISK_ENGINE = _b("LIVE_TICK_RISK_ENGINE", True)

# Execution mode
#   paper = use the configured Delta environment for market/account connectivity,
#           but NEVER send or cancel exchange orders. Orders/fills are simulated.
#   live  = send real orders. Production live trading additionally requires
#           LIVE_TRADING_ENABLED=true as an explicit second safety switch.
EXECUTION_MODE = os.environ.get("EXECUTION_MODE", "paper").strip().lower()
if EXECUTION_MODE not in {"paper", "live"}:
    raise ValueError("EXECUTION_MODE must be either paper or live")
LIVE_TRADING_ENABLED = _b("LIVE_TRADING_ENABLED", False)

# Exchange / product
DELTA_API_KEY = os.environ.get("DELTA_API_KEY", "YOUR_DELTA_API_KEY")
DELTA_API_SECRET = os.environ.get("DELTA_API_SECRET", "YOUR_DELTA_API_SECRET")
DELTA_TESTNET = _b("DELTA_TESTNET", True)  # safe-by-default
DELTA_LIVE_REST_URL = "https://api.india.delta.exchange"
DELTA_TESTNET_REST_URL = "https://cdn-ind.testnet.deltaex.org"
DELTA_REST_URL = DELTA_TESTNET_REST_URL if DELTA_TESTNET else DELTA_LIVE_REST_URL
SYMBOL = os.environ.get("SYMBOL", "BTC/USD:USD")          # ccxt unified symbol
DELTA_PRODUCT_SYMBOL = os.environ.get("DELTA_PRODUCT_SYMBOL", "BTCUSD")
ALERT_QTY = _i("ALERT_QTY", 30)
POSITION_BTC_SIZE = ALERT_QTY * 0.001  # display helper; live sizing is ALERT_QTY contracts

# Strategy execution model
CANDLE_TIMEFRAME = os.environ.get("CANDLE_TIMEFRAME", "30m")
PINE_MINTICK = _f("PINE_MINTICK", 0.5)
PINE_SLIPPAGE_TICKS = _i("PINE_SLIPPAGE_TICKS", 10)
PINE_POINT_VALUE = _f("PINE_POINT_VALUE", 0.001)
PINE_ORDER_QTY = _f("PINE_ORDER_QTY", 30.0)

# Current supplied Pine configuration: EMA 50 / 200
EMA_FAST_LEN = _i("EMA_FAST_LEN", 50)
EMA_TREND_LEN = _i("EMA_TREND_LEN", 200)
ATR_LEN = _i("ATR_LEN", 14)
DI_LEN = _i("DI_LEN", 14)
ADX_SMOOTH = _i("ADX_SMOOTH", 14)
ADX_EMA = _i("ADX_EMA", 5)
RSI_LEN = _i("RSI_LEN", 14)

# Exact Pine thresholds
ADX_TREND_TH = _f("ADX_TREND_TH", 20.0)
ADX_RANGE_TH = _f("ADX_RANGE_TH", 18.0)
ADX_TOLERANCE = _f("ADX_TOLERANCE", 0.0)
FILTER_ATR_MULT = _f("FILTER_ATR_MULT", 1.6)
FILTER_BODY_MULT = _f("FILTER_BODY_MULT", 0.4)
FILTER_BODY_TOLERANCE = _f("FILTER_BODY_TOLERANCE", 0.0)
FILTER_VOL_ENABLED = _b("FILTER_VOL_ENABLED", True)
FILTER_VOL_MULT = _f("FILTER_VOL_MULT", 1.0)
BREAKOUT_BUFFER_PTS = _f("BREAKOUT_BUFFER_PTS", 0.0)
RSI_OB = _i("RSI_OB", 70)
RSI_OS = _i("RSI_OS", 30)

# Exact Pine risk / reward
TREND_RR = _f("TREND_RR", 5.0)
RANGE_RR = _f("RANGE_RR", 3.0)
TREND_ATR_MULT = _f("TREND_ATR_MULT", 0.9)
RANGE_ATR_MULT = _f("RANGE_ATR_MULT", 0.7)
MAX_SL_MULT = _f("MAX_SL_MULT", 2.0)
MAX_SL_POINTS = _f("MAX_SL_POINTS", 1500.0)
BE_MULT = _f("BE_MULT", 1.0)

# (trigger ATR, legacy trail_points ATR multiplier, trail_offset ATR multiplier)
# BIG-MOVE-FIX:
# - Correct mode (default): triggerMult is the activation distance in ATR PRICE
#   units and offMult is the trailing gap in ATR PRICE units. This is the
#   intuitive meaning of the inputs and prevents the pre-Stage-1 micro trail.
# - Legacy mode: reproduces the old Pine mistake where ATR-price values were
#   passed directly to trail_points/trail_offset, which TradingView interprets
#   as TICKS (therefore multiplying by PINE_MINTICK again).
TRAIL_LEGACY_TV_TICK_SEMANTICS = _b("TRAIL_LEGACY_TV_TICK_SEMANTICS", False)
TRAIL_STAGE_UPDATE_MODE = os.environ.get("TRAIL_STAGE_UPDATE_MODE", "bar_close").strip().lower()
BREAKEVEN_UPDATE_MODE = os.environ.get("BREAKEVEN_UPDATE_MODE", "bar_close").strip().lower()
MAX_SL_EVAL_MODE = os.environ.get("MAX_SL_EVAL_MODE", "bar_close").strip().lower()
if TRAIL_STAGE_UPDATE_MODE not in {"bar_close", "tick"}:
    raise ValueError("TRAIL_STAGE_UPDATE_MODE must be bar_close or tick")
if BREAKEVEN_UPDATE_MODE not in {"bar_close", "tick"}:
    raise ValueError("BREAKEVEN_UPDATE_MODE must be bar_close or tick")
if MAX_SL_EVAL_MODE not in {"bar_close", "tick"}:
    raise ValueError("MAX_SL_EVAL_MODE must be bar_close or tick")

TRAIL_STAGES = [
    (_f("TRAIL1_TRIGGER", 1.0), _f("TRAIL1_PTS", 0.70), _f("TRAIL1_OFF", 0.55)),
    (_f("TRAIL2_TRIGGER", 2.0), _f("TRAIL2_PTS", 0.55), _f("TRAIL2_OFF", 0.45)),
    (_f("TRAIL3_TRIGGER", 3.0), _f("TRAIL3_PTS", 0.45), _f("TRAIL3_OFF", 0.35)),
    (_f("TRAIL4_TRIGGER", 5.0), _f("TRAIL4_PTS", 0.30), _f("TRAIL4_OFF", 0.25)),
    (_f("TRAIL5_TRIGGER", 8.0), _f("TRAIL5_PTS", 0.20), _f("TRAIL5_OFF", 0.15)),
]

# Pine strategy() commission_value=0.05 percent per fill.
COMMISSION_PCT = _f("COMMISSION_PCT", 0.05) / 100.0

# Signal market data. For exact parity this MUST match the TradingView chart.
# The supplied Pine alerts route to Delta BTCUSD.P, so Delta is the conservative
# default. Set BINANCE_SIGNAL_FEED=true only if your TradingView chart is
# BINANCE:BTCUSDT (and set PINE_MINTICK accordingly, commonly 0.1).
BINANCE_SIGNAL_FEED = _b("BINANCE_SIGNAL_FEED", False)
BINANCE_SYMBOL = os.environ.get("BINANCE_SYMBOL", "BTC/USDT")
WS_RECONNECT_SEC = _f("WS_RECONNECT_SEC", 5.0)
TRAIL_LOOP_SEC = _f("TRAIL_LOOP_SEC", 0.25)
TRAIL_EXIT_FROM_DELTA_WS = _b("TRAIL_EXIT_FROM_DELTA_WS", True)
TRAIL_FIRE_SL_ON_CANDLE_EXTREME = _b("TRAIL_FIRE_SL_ON_CANDLE_EXTREME", False)

# Live execution behavior. LIVE_TICK_RISK_ENGINE keeps protective price orders
# responsive to live ticks. Stage, breakeven, and Max-SL timing are independently
# selectable above; defaults are bar_close to match the supplied Pine script.
# Initial SL / TP / an already-armed trail still react to live prices for safety.
TP_HARD_EXIT = _b("TP_HARD_EXIT", True)  # master switch
TREND_HARD_TP_ENABLED = _b("TREND_HARD_TP_ENABLED", True)
RANGE_HARD_TP_ENABLED = _b("RANGE_HARD_TP_ENABLED", True)
BAR_CLOSE_SL_EVAL = _b("BAR_CLOSE_SL_EVAL", False)
TIME_EXIT_MINUTES = _i("TIME_EXIT_MINUTES", 0)
TRAIL_SL_PRE_FIRE_BUFFER = _f("TRAIL_SL_PRE_FIRE_BUFFER", 0.0)
TRAIL_OFFSET_FLOOR_MULT = _f("TRAIL_OFFSET_FLOOR_MULT", 0.0)
TRAIL_ARM_FLOOR_MULT = _f("TRAIL_ARM_FLOOR_MULT", 0.0)

# Optional real-world protections. Defaults are parity-friendly and therefore
# disabled/minimal. Turn them on only after parity has been proved and record the
# fact that production behavior will then differ from Pine.
SL_CONFIRM_MS = _i("SL_CONFIRM_MS", 0)
SL_CONFIRM_TICKS = _i("SL_CONFIRM_TICKS", 1)
TRAIL_SL_CONFIRM_TICKS = _i("TRAIL_SL_CONFIRM_TICKS", 1)
MAX_EXIT_SLIPPAGE_ATR_PCT = _f("MAX_EXIT_SLIPPAGE_ATR_PCT", 25.0)
EMERGENCY_BRACKET_ENABLED = _b("EMERGENCY_BRACKET_ENABLED", True)
BRACKET_SL_WIDEN_MULT = _f("BRACKET_SL_WIDEN_MULT", 3.0)
BRACKET_SL_MIN_PTS = _f("BRACKET_SL_MIN_PTS", 300.0)
BRACKET_SL_BUFFER = _f("BRACKET_SL_BUFFER", 10.0)
SL_FIRE_VIA_BRACKET = _b("SL_FIRE_VIA_BRACKET", False)

# Notifications
TELEGRAM_ENABLED = _b("TELEGRAM_ENABLED", False)
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "YOUR_TELEGRAM_BOT_TOKEN")
TELEGRAM_CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "YOUR_TELEGRAM_CHAT_ID")
WHATSAPP_ACCESS_TOKEN = os.environ.get("WHATSAPP_ACCESS_TOKEN", "")
WHATSAPP_PHONE_NUMBER_ID = os.environ.get("WHATSAPP_PHONE_NUMBER_ID", "")
WHATSAPP_TO_NUMBER = os.environ.get("WHATSAPP_TO_NUMBER", "")
WHATSAPP_VERIFY_TOKEN = os.environ.get("WHATSAPP_VERIFY_TOKEN", "")
WHATSAPP_TEMPLATE_NAME = os.environ.get("WHATSAPP_TEMPLATE_NAME", "")
WHATSAPP_TEMPLATE_LANG = os.environ.get("WHATSAPP_TEMPLATE_LANG", "en")

# Storage / logs
LOG_FILE = os.environ.get("LOG_FILE", "./data/pinescript_bot_journal.db")
GSHEET_ENABLED = _b("GSHEET_ENABLED", False)
GSHEET_SPREADSHEET_ID = os.environ.get("GSHEET_SPREADSHEET_ID", "")
GSHEET_CREDENTIALS_FILE = os.environ.get("GSHEET_CREDENTIALS_FILE", "")
GSHEET_CREDENTIALS_JSON = os.environ.get("GSHEET_CREDENTIALS_JSON", "")
GSHEET_AUTO_CREATE = _b("GSHEET_AUTO_CREATE", True)

# Flat aliases retained for old verification scripts.
ADX_EMA_LEN = ADX_EMA
TRAIL_T1_TRIG, TRAIL_T1_PTS, TRAIL_T1_OFF = TRAIL_STAGES[0]
TRAIL_T2_TRIG, TRAIL_T2_PTS, TRAIL_T2_OFF = TRAIL_STAGES[1]
TRAIL_T3_TRIG, TRAIL_T3_PTS, TRAIL_T3_OFF = TRAIL_STAGES[2]
TRAIL_T4_TRIG, TRAIL_T4_PTS, TRAIL_T4_OFF = TRAIL_STAGES[3]
TRAIL_T5_TRIG, TRAIL_T5_PTS, TRAIL_T5_OFF = TRAIL_STAGES[4]
