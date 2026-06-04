import unittest
import pandas as pd
import numpy as np
from backend.strategies.implementations import BuyAndHoldStrategy, MACrossoverStrategy

class TestStrategies(unittest.TestCase):
    
    def setUp(self):
        # Create a dummy pricing DataFrame
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        self.df = pd.DataFrame({
            "Open": np.linspace(100, 150, 100),
            "High": np.linspace(102, 152, 100),
            "Low": np.linspace(98, 148, 100),
            "Close": np.linspace(100, 150, 100),
            "Volume": np.full(100, 10000)
        }, index=dates)
        
    def test_buy_and_hold_signals(self):
        strategy = BuyAndHoldStrategy()
        res = strategy.generate_signals(self.df)
        
        self.assertIn("Signal", res.columns)
        self.assertTrue((res["Signal"] == 1.0).all())
        
    def test_ma_crossover_signals(self):
        # Fast MA = 5, Slow MA = 20
        # Since price is strictly rising (np.linspace(100,150)), Fast MA (last 5 days)
        # will always be greater than Slow MA (last 20 days) after the warm-up period.
        strategy = MACrossoverStrategy(params={"fast_period": 5, "slow_period": 20})
        res = strategy.generate_signals(self.df)
        
        self.assertIn("Signal", res.columns)
        # Check that post slow period, signal is 1.0
        active_signals = res["Signal"].iloc[25:]
        self.assertTrue((active_signals == 1.0).all())
        
if __name__ == "__main__":
    unittest.main()
