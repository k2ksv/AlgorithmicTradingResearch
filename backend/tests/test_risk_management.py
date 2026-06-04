import unittest
import pandas as pd
import numpy as np
from backend.backtesting.engine import BacktestEngine

class TestRiskManagement(unittest.TestCase):
    
    def test_trailing_stop_loss(self):
        # Create a mock dataframe where asset price starts at 100, goes to 120, then drops to 100
        dates = pd.date_range(start="2024-01-01", periods=5, freq="D")
        df = pd.DataFrame({
            "Open": [100.0, 110.0, 120.0, 100.0, 95.0],
            "High": [105.0, 120.0, 125.0, 105.0, 98.0],
            "Low": [98.0, 108.0, 118.0, 99.0, 90.0],
            "Close": [100.0, 110.0, 120.0, 100.0, 95.0],
            "Volume": [1000] * 5,
            "Signal": [1.0, 1.0, 1.0, 1.0, 1.0], # raw signal stays long
            "ATR": [2.0, 2.0, 2.0, 2.0, 2.0]
        }, index=dates)
        
        # Test with 10% trailing stop
        engine = BacktestEngine(
            initial_cash=100000.0,
            commission_rate=0.0,
            slippage_rate=0.0,
            risk_free_rate=0.0,
            trailing_stop_pct=0.10 # 10% stop loss
        )
        
        res = engine.run(df)
        trade_log = res["trade_log"]
        
        # Check if STOP LOSS hit is logged
        stop_loss_trades = [t for t in trade_log if t["Action"] == "STOP LOSS"]
        self.assertGreater(len(stop_loss_trades), 0)
        self.assertEqual(stop_loss_trades[0]["Action"], "STOP LOSS")
        
    def test_atr_position_sizing(self):
        # High volatility asset vs low volatility asset
        dates = pd.date_range(start="2024-01-01", periods=2, freq="D")
        
        # Low volatility df
        df_low_vol = pd.DataFrame({
            "Open": [100.0, 100.0],
            "High": [101.0, 101.0],
            "Low": [99.0, 99.0],
            "Close": [100.0, 100.0],
            "Volume": [1000] * 2,
            "Signal": [1.0, 1.0],
            "ATR": [1.0, 1.0] # low ATR
        }, index=dates)
        
        # High volatility df
        df_high_vol = pd.DataFrame({
            "Open": [100.0, 100.0],
            "High": [110.0, 110.0],
            "Low": [90.0, 90.0],
            "Close": [100.0, 100.0],
            "Volume": [1000] * 2,
            "Signal": [1.0, 1.0],
            "ATR": [10.0, 10.0] # high ATR (10x larger)
        }, index=dates)
        
        # Sizing engine: 2% risk, 2.0 ATR multiplier
        engine = BacktestEngine(
            initial_cash=100000.0,
            commission_rate=0.0,
            slippage_rate=0.0,
            risk_free_rate=0.0,
            use_atr_sizing=True,
            risk_pct=0.02,
            atr_multiplier=2.0
        )
        
        res_low = engine.run(df_low_vol)
        res_high = engine.run(df_high_vol)
        
        trade_log_low = res_low["trade_log"]
        trade_log_high = res_high["trade_log"]
        
        # Extract initial buy shares
        buy_low = [t for t in trade_log_low if t["Action"] == "BUY"][0]
        buy_high = [t for t in trade_log_high if t["Action"] == "BUY"][0]
        
        # High vol position size should be smaller than low vol position size
        self.assertLess(buy_high["Shares"], buy_low["Shares"])

if __name__ == "__main__":
    unittest.main()
