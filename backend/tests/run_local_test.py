import os
import sys
# Add workspace root to sys.path so Windows Python can find 'backend' module
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging
from backend.api.router import execute_single_backtest, BacktestRequest
from backend.visualization.charts import (
    generate_price_chart, 
    generate_equity_curve_chart, 
    generate_drawdown_chart, 
    generate_monthly_heatmap
)

logging.basicConfig(level=logging.INFO)

def run():
    req = BacktestRequest(
        ticker="AAPL",
        start_date="2024-01-01",
        end_date="2024-01-10",
        strategy_name="Buy & Hold",
        initial_cash=100000.0,
        risk_free_rate=0.06
    )
    
    print("Executing backtest...")
    res = execute_single_backtest(req)
    daily_df = res["daily_series"]
    trade_log = res["trade_log"]
    metrics = res["metrics"]
    
    print("Backtest finished. Metrics strategy CAGR:", metrics["strategy"]["cagr"])
    
    # Test chart generators
    print("Generating price chart...")
    generate_price_chart(daily_df, trade_log, req.ticker)
    
    print("Generating equity chart...")
    generate_equity_curve_chart(daily_df)
    
    print("Generating drawdown chart...")
    generate_drawdown_chart(daily_df)
    
    print("Generating heatmap...")
    generate_monthly_heatmap(daily_df)
    
    print("All charts generated successfully!")

if __name__ == "__main__":
    run()
