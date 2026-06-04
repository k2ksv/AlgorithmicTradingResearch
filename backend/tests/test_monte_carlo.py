import unittest
import pandas as pd
import numpy as np
from backend.metrics.calculator import run_monte_carlo_simulation

class TestMonteCarlo(unittest.TestCase):
    
    def setUp(self):
        # Create a mock daily series of returns
        dates = pd.date_range(start="2024-01-01", periods=100, freq="D")
        np.random.seed(42)
        # Random normal returns
        self.returns = np.random.normal(loc=0.0005, scale=0.01, size=100)
        self.daily_df = pd.DataFrame({
            "PortfolioValue": 100000.0 * np.cumprod(1.0 + self.returns),
            "DailyReturn": self.returns
        }, index=dates)
        self.initial_cash = 100000.0
        
    def test_monte_carlo_dimensions(self):
        res = run_monte_carlo_simulation(self.daily_df, self.initial_cash, num_sims=100)
        
        # Test series length matches n_days + 1
        self.assertEqual(len(res["dates"]), len(self.daily_df) + 1)
        self.assertEqual(len(res["p5"]), len(self.daily_df) + 1)
        self.assertEqual(len(res["p95"]), len(self.daily_df) + 1)
        
        # All paths should start at initial cash
        self.assertEqual(res["p5"][0], self.initial_cash)
        self.assertEqual(res["p50"][0], self.initial_cash)
        self.assertEqual(res["p95"][0], self.initial_cash)
        
    def test_monte_carlo_statistics(self):
        res = run_monte_carlo_simulation(self.daily_df, self.initial_cash, num_sims=500)
        stats = res["stats"]
        
        # Verify stats keys exist
        self.assertIn("prob_loss", stats)
        self.assertIn("var_95", stats)
        self.assertIn("cvar_95", stats)
        self.assertIn("median_terminal_value", stats)
        
        # Check values are reasonable numeric types
        self.assertTrue(0.0 <= stats["prob_loss"] <= 100.0)
        self.assertIsInstance(stats["var_95"], float)
        self.assertIsInstance(stats["cvar_95"], float)

if __name__ == "__main__":
    unittest.main()
