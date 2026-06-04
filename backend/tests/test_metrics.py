import unittest
import pandas as pd
import numpy as np
from backend.metrics.calculator import calculate_performance_metrics

class TestMetricsCalculator(unittest.TestCase):
    
    def setUp(self):
        # Create a mock daily series with 252 days (1 year)
        dates = pd.date_range(start="2024-01-01", periods=252, freq="D")
        
        # 10% flat daily compounding return mock
        # Day 0: 100000. For 252 days, daily return such that final value is 110000
        returns = np.zeros(252)
        returns[0] = 0.0
        
        self.daily_df = pd.DataFrame({
            "PortfolioValue": 100000 * (1 + 0.000397)**np.arange(252), # ~10% annualized
            "BuyHoldValue": 100000 * (1 + 0.000397)**np.arange(252),
            "DailyReturn": np.full(252, 0.000397),
            "BuyHoldReturn": np.full(252, 0.000397),
            "Exposure": np.ones(252)
        }, index=dates)
        
        # Set first return to 0
        self.daily_df.loc[dates[0], "DailyReturn"] = 0.0
        self.daily_df.loc[dates[0], "BuyHoldReturn"] = 0.0
        
        self.trade_log = []
        self.risk_free_rate = 0.06 # 6%
        
    def test_cagr_calculation(self):
        metrics = calculate_performance_metrics(self.daily_df, self.trade_log, self.risk_free_rate)
        # CAGR should be around 10%
        strategy_cagr = metrics["strategy"]["cagr"]
        self.assertTrue(14.0 <= strategy_cagr <= 17.0)
        
    def test_sharpe_ratio_non_negative(self):
        metrics = calculate_performance_metrics(self.daily_df, self.trade_log, self.risk_free_rate)
        # With 10% return and 6% risk free rate, Sharpe should be positive
        self.assertGreater(metrics["strategy"]["sharpe_ratio"], 0.0)
        
    def test_max_drawdown_is_zero_for_flat_growth(self):
        metrics = calculate_performance_metrics(self.daily_df, self.trade_log, self.risk_free_rate)
        # No drops, max drawdown should be 0.0%
        self.assertEqual(metrics["strategy"]["max_drawdown"], 0.0)

if __name__ == "__main__":
    unittest.main()
