import unittest
import asyncio

import config
import pandas as pd
from indicators.engine import IndicatorSnapshot, evaluate, SignalType, _ema
from risk.calculator import calc_levels, calc_real_pl, TrailState
from monitor.trail_loop import TrailMonitor
from strategy_logic import get_trail_params, max_sl_threshold


class ParityCoreTests(unittest.TestCase):
    def test_requested_ema_defaults(self):
        self.assertEqual(config.EMA_FAST_LEN, 20)
        self.assertEqual(config.EMA_TREND_LEN, 50)

    def test_supplied_pine_parameters(self):
        self.assertEqual(config.ADX_TREND_TH, 20.0)
        self.assertEqual(config.ADX_RANGE_TH, 18.0)
        self.assertEqual(config.FILTER_ATR_MULT, 1.6)
        self.assertEqual(config.FILTER_BODY_MULT, 0.4)
        self.assertEqual(config.TREND_RR, 5.0)
        self.assertEqual(config.RANGE_RR, 3.0)
        self.assertEqual(config.TREND_ATR_MULT, 0.9)
        self.assertEqual(config.RANGE_ATR_MULT, 0.7)
        self.assertEqual(config.MAX_SL_MULT, 2.0)
        self.assertEqual(config.MAX_SL_POINTS, 1500.0)
        self.assertEqual(config.BE_MULT, 1.0)
        self.assertEqual(config.TRAIL_STAGES[0], (1.0, 0.70, 0.55))
        self.assertEqual(config.TRAIL_STAGES[-1], (8.0, 0.20, 0.15))

    def test_risk_anchors_to_fill(self):
        r = calc_levels(1000.0, 100.0, True, True, signal_close=970.0)
        self.assertAlmostEqual(r.sl, 910.0)
        self.assertAlmostEqual(r.tp, 1450.0)
        self.assertAlmostEqual(r.entry_price, 1000.0)

    def test_trail_uses_tick_conversion(self):
        activation, offset = get_trail_params(0, 100.0)
        self.assertAlmostEqual(activation, 100.0 * 0.70 * config.PINE_MINTICK)
        self.assertAlmostEqual(offset, 100.0 * 0.55 * config.PINE_MINTICK)

    def test_trend_long_signal(self):
        s = IndicatorSnapshot(
            ema_trend=100, ema_fast=110, atr=10, rsi=50, dip=30, dim=20,
            adx=25, adx_raw=25, vol_sma=100, atr_sma=10,
            trend_regime=True, range_regime=False, filters_ok=True,
            atr_ok=True, vol_ok=True, body_ok=True, open=105, high=120,
            low=100, close=121, volume=150, prev_high=120, prev_low=100,
            timestamp=1,
        )
        self.assertEqual(evaluate(s).signal_type, SignalType.TREND_LONG)

    def test_max_sl(self):
        self.assertAlmostEqual(max_sl_threshold(100.0), 200.0)
        self.assertAlmostEqual(max_sl_threshold(1000.0), 1500.0)

    def test_ema_uses_pine_recursive_seed(self):
        src = pd.Series([10.0, 20.0, 30.0, 40.0])
        out = _ema(src, 3)  # alpha = 0.5, seed = first source value
        self.assertAlmostEqual(out.iloc[0], 10.0)
        self.assertAlmostEqual(out.iloc[1], 15.0)
        self.assertAlmostEqual(out.iloc[2], 22.5)
        self.assertAlmostEqual(out.iloc[3], 31.25)


    def test_live_tick_risk_engine_enabled(self):
        self.assertTrue(config.LIVE_TICK_RISK_ENGINE)

    def test_live_tick_upgrades_stage_and_breakeven(self):
        risk = calc_levels(1000.0, 100.0, True, True)
        state = TrailState(current_sl=risk.sl)
        mon = TrailMonitor()
        mon._risk = risk
        mon._state = state
        mon._current_atr = 100.0
        mon._static_orders_active = True
        asyncio.run(mon._evaluate_tick(1101.0, source="delta"))
        self.assertEqual(state.stage, 1)
        self.assertTrue(state.be_done)
        self.assertTrue(state.trail_armed)

    def test_delta_contract_pnl_and_commission(self):
        # 30 BTCUSD contracts = 0.03 BTC exposure for point-PnL accounting.
        # 100 point favorable move -> $3 gross before commission.
        entry, exit_, qty = 80000.0, 80100.0, 30
        expected_gross = 100.0 * 30 * 0.001
        expected_comm = (entry + exit_) * 30 * 0.001 * config.COMMISSION_PCT
        self.assertAlmostEqual(calc_real_pl(entry, exit_, True, qty), expected_gross - expected_comm)


if __name__ == '__main__':
    unittest.main()
