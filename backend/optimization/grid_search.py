import logging
import itertools
import pandas as pd
from typing import Dict, List, Any, Type
from backend.strategies.base import BaseStrategy
from backend.backtesting.engine import BacktestEngine
from backend.metrics.calculator import calculate_performance_metrics

logger = logging.getLogger(__name__)

def run_grid_search(
    df: pd.DataFrame,
    strategy_class: Type[BaseStrategy],
    param_ranges: Dict[str, List[Any]],
    metric_to_optimize: str = "sharpe_ratio",
    risk_free_rate: float = 0.06
) -> Dict[str, Any]:
    """
    Perform a grid search over specified parameter ranges for a strategy.
    
    Parameters:
        df: Historical price data.
        strategy_class: The strategy class to instantiate (e.g. MACrossoverStrategy).
        param_ranges: Dict mapping parameter names to lists of values, e.g. {'fast_period': [10, 20, 30], 'slow_period': [50, 100]}
        metric_to_optimize: The metric to rank configurations by (e.g. 'sharpe_ratio', 'cagr', 'total_return').
        risk_free_rate: Annualized risk free rate.
        
    Returns:
        Dict[str, Any]: Optimization results including best parameters, all results, and heatmap structure.
    """
    # Generate all combinations of parameter values
    keys = list(param_ranges.keys())
    values = list(param_ranges.values())
    combinations = [dict(zip(keys, prod)) for prod in itertools.product(*values)]
    
    results = []
    best_value = -float("inf")
    best_params = None
    
    # Instantiate backtest engine once
    engine = BacktestEngine(risk_free_rate=risk_free_rate)
    
    for params in combinations:
        # Business logic constraint check:
        # e.g., for MA Crossover, fast_period must be strictly less than slow_period.
        if "fast_period" in params and "slow_period" in params:
            if params["fast_period"] >= params["slow_period"]:
                continue
        if "ma50_period" in params and "ma200_period" in params:
            if params["ma50_period"] >= params["ma200_period"]:
                continue
        if "oversold_threshold" in params and "overbought_threshold" in params:
            if params["oversold_threshold"] >= params["overbought_threshold"]:
                continue
                
        try:
            # Instantiate strategy
            strat = strategy_class(params=params)
            df_signals = strat.generate_signals(df)
            
            # Backtest
            backtest_res = engine.run(df_signals)
            daily_df = backtest_res["daily_series"]
            trade_log = backtest_res["trade_log"]
            
            # Compute performance metrics
            perf = calculate_performance_metrics(daily_df, trade_log, risk_free_rate)
            strategy_perf = perf["strategy"]
            
            # Extract target metric value
            metric_val = strategy_perf.get(metric_to_optimize, 0.0)
            
            record = {
                "params": params,
                "metrics": strategy_perf
            }
            results.append(record)
            
            if metric_val > best_value:
                best_value = metric_val
                best_params = params
                
        except Exception as e:
            logger.error(f"Error evaluating strategy with parameters {params}: {str(e)}")
            continue
            
    # Generate heatmap dataset if we have exactly two parameters
    heatmap_data = []
    if len(keys) == 2:
        param_x = keys[0]
        param_y = keys[1]
        for res in results:
            heatmap_data.append({
                "x": res["params"][param_x],
                "y": res["params"][param_y],
                "z": res["metrics"].get(metric_to_optimize, 0.0)
            })
            
    return {
        "best_params": best_params,
        "best_value": round(best_value, 4) if best_value != -float("inf") else 0.0,
        "all_results": results,
        "heatmap_data": heatmap_data,
        "parameters_searched": keys
    }
