import pandas as pd
import numpy as np
from typing import Dict, Any, List

def calculate_performance_metrics(
    daily_df: pd.DataFrame, 
    trade_log: List[Dict[str, Any]], 
    risk_free_rate: float
) -> Dict[str, Any]:
    """
    Calculate performance metrics for the backtested strategy and Buy & Hold benchmark.
    
    Parameters:
        daily_df (pd.DataFrame): Daily series containing PortfolioValue, BuyHoldValue, DailyReturn, BuyHoldReturn, Exposure.
        trade_log (List[Dict[str, Any]]): List of recorded trades.
        risk_free_rate (float): Annualized risk-free rate.
        
    Returns:
        Dict[str, Any]: Dictionary containing portfolio performance metrics.
    """
    metrics = {}
    daily_rf = risk_free_rate / 252.0
    
    # Calculate exact number of years in backtest
    days = (daily_df.index[-1] - daily_df.index[0]).days
    years = max(days / 365.25, 0.002) # prevent division by zero
    
    # ==========================================
    # STRATEGY METRICS
    # ==========================================
    initial_val = float(daily_df["PortfolioValue"].iloc[0])
    final_val = float(daily_df["PortfolioValue"].iloc[-1])
    
    total_return = (final_val - initial_val) / initial_val
    cagr = (final_val / initial_val) ** (1.0 / years) - 1.0 if final_val > 0 else -1.0
    
    # Standard deviation of daily returns
    daily_vol = daily_df["DailyReturn"].std()
    ann_vol = daily_vol * np.sqrt(252)
    
    # Sharpe Ratio
    # Excess return over daily risk free rate
    # Portfolio return includes risk-free interest earned on cash, so we subtract daily_rf from actual daily return.
    excess_returns = daily_df["DailyReturn"] - daily_rf
    mean_excess = excess_returns.mean()
    std_excess = excess_returns.std()
    sharpe = np.sqrt(252) * (mean_excess / std_excess) if std_excess > 0 else 0.0
    
    # Sortino Ratio
    # Standard deviation of negative excess returns
    downside_returns = excess_returns.copy()
    downside_returns[downside_returns > 0] = 0.0
    downside_std = downside_returns.std()
    sortino = np.sqrt(252) * (mean_excess / downside_std) if downside_std > 0 else 0.0
    
    # Drawdown
    peaks = daily_df["PortfolioValue"].cummax()
    drawdowns = (daily_df["PortfolioValue"] - peaks) / peaks
    max_dd = drawdowns.min()
    
    # Win Rate (percentage of days with positive return)
    pos_days = (daily_df["DailyReturn"] > 0.0).sum()
    total_days = len(daily_df["DailyReturn"])
    win_rate = (pos_days / total_days) * 100 if total_days > 0 else 0.0
    
    # Profit Factor
    gains = daily_df.loc[daily_df["DailyReturn"] > 0, "DailyReturn"].sum()
    losses = abs(daily_df.loc[daily_df["DailyReturn"] < 0, "DailyReturn"].sum())
    profit_factor = gains / losses if losses > 0 else float('inf') if gains > 0 else 0.0
    
    # Exposure (average daily exposure weight)
    mean_exposure = daily_df["Exposure"].mean() * 100
    
    metrics["strategy"] = {
        "initial_value": float(round(initial_val, 2)),
        "final_value": float(round(final_val, 2)),
        "total_return": float(round(total_return * 100, 2)),
        "cagr": float(round(cagr * 100, 2)),
        "annualized_volatility": float(round(ann_vol * 100, 2)),
        "sharpe_ratio": float(round(sharpe, 2)),
        "sortino_ratio": float(round(sortino, 2)),
        "max_drawdown": float(round(max_dd * 100, 2)),
        "win_rate_daily": float(round(win_rate, 2)),
        "profit_factor": float(round(profit_factor, 2)) if profit_factor != float('inf') else 999.0,
        "average_exposure": float(round(mean_exposure, 2)),
        "total_trades": int(len(trade_log))
    }
    
    # ==========================================
    # BUY & HOLD METRICS
    # ==========================================
    bh_initial = float(daily_df["BuyHoldValue"].iloc[0])
    bh_final = float(daily_df["BuyHoldValue"].iloc[-1])
    
    bh_total_return = (bh_final - bh_initial) / bh_initial
    bh_cagr = (bh_final / bh_initial) ** (1.0 / years) - 1.0 if bh_final > 0 else -1.0
    
    bh_daily_vol = daily_df["BuyHoldReturn"].std()
    bh_ann_vol = bh_daily_vol * np.sqrt(252)
    
    bh_excess = daily_df["BuyHoldReturn"] - daily_rf
    bh_mean_excess = bh_excess.mean()
    bh_std_excess = bh_excess.std()
    bh_sharpe = np.sqrt(252) * (bh_mean_excess / bh_std_excess) if bh_std_excess > 0 else 0.0
    
    bh_downside = bh_excess.copy()
    bh_downside[bh_downside > 0] = 0.0
    bh_downside_std = bh_downside.std()
    bh_sortino = np.sqrt(252) * (bh_mean_excess / bh_downside_std) if bh_downside_std > 0 else 0.0
    
    bh_peaks = daily_df["BuyHoldValue"].cummax()
    bh_drawdowns = (daily_df["BuyHoldValue"] - bh_peaks) / bh_peaks
    bh_max_dd = bh_drawdowns.min()
    
    bh_pos_days = (daily_df["BuyHoldReturn"] > 0.0).sum()
    bh_win_rate = (bh_pos_days / total_days) * 100 if total_days > 0 else 0.0
    
    bh_gains = daily_df.loc[daily_df["BuyHoldReturn"] > 0, "BuyHoldReturn"].sum()
    bh_losses = abs(daily_df.loc[daily_df["BuyHoldReturn"] < 0, "BuyHoldReturn"].sum())
    bh_profit_factor = bh_gains / bh_losses if bh_losses > 0 else float('inf') if bh_gains > 0 else 0.0
    
    metrics["buy_hold"] = {
        "initial_value": float(round(bh_initial, 2)),
        "final_value": float(round(bh_final, 2)),
        "total_return": float(round(bh_total_return * 100, 2)),
        "cagr": float(round(bh_cagr * 100, 2)),
        "annualized_volatility": float(round(bh_ann_vol * 100, 2)),
        "sharpe_ratio": float(round(bh_sharpe, 2)),
        "sortino_ratio": float(round(bh_sortino, 2)),
        "max_drawdown": float(round(bh_max_dd * 100, 2)),
        "win_rate_daily": float(round(bh_win_rate, 2)),
        "profit_factor": float(round(bh_profit_factor, 2)) if bh_profit_factor != float('inf') else 999.0
    }
    
    return metrics

def run_monte_carlo_simulation(
    daily_df: pd.DataFrame,
    initial_cash: float,
    num_sims: int = 1000
) -> Dict[str, Any]:
    """
    Run Monte Carlo simulation using bootstrapping on historical daily returns.
    
    Parameters:
        daily_df (pd.DataFrame): Daily series containing 'DailyReturn'.
        initial_cash (float): Starting portfolio value.
        num_sims (int): Number of simulated paths.
        
    Returns:
        Dict[str, Any]: Dictionary containing percentile series and summary stats.
    """
    returns = daily_df["DailyReturn"].values
    n_days = len(returns)
    
    if n_days < 5 or daily_df["DailyReturn"].std() == 0.0:
        # Fallback if no trade activity or not enough data: return flat lines
        dates_str = [d.strftime("%Y-%m-%d") for d in daily_df.index]
        flat_path = [initial_cash] * (n_days + 1)
        return {
            "dates": ["Start"] + dates_str,
            "p5": flat_path,
            "p25": flat_path,
            "p50": flat_path,
            "p75": flat_path,
            "p95": flat_path,
            "stats": {
                "prob_loss": 0.0,
                "var_95": 0.0,
                "cvar_95": 0.0,
                "median_terminal_value": initial_cash
            }
        }
        
    # Bootstrap returns: shape (num_sims, n_days)
    np.random.seed(42)  # For reproducibility
    sim_returns = np.random.choice(returns, size=(num_sims, n_days), replace=True)
    
    # Calculate wealth paths: shape (num_sims, n_days + 1)
    wealth_paths = np.zeros((num_sims, n_days + 1))
    wealth_paths[:, 0] = initial_cash
    
    # Calculate cumulative product for each path
    wealth_paths[:, 1:] = initial_cash * np.cumprod(1.0 + sim_returns, axis=1)
    
    # Calculate percentiles step-by-step
    p5 = np.percentile(wealth_paths, 5, axis=0).tolist()
    p25 = np.percentile(wealth_paths, 25, axis=0).tolist()
    p50 = np.percentile(wealth_paths, 50, axis=0).tolist()
    p75 = np.percentile(wealth_paths, 75, axis=0).tolist()
    p95 = np.percentile(wealth_paths, 95, axis=0).tolist()
    
    # Calculate terminal returns for VaR/CVaR
    terminal_values = wealth_paths[:, -1]
    terminal_returns = (terminal_values - initial_cash) / initial_cash
    
    # Probability of loss (terminal value < initial cash)
    prob_loss = float(np.mean(terminal_values < initial_cash) * 100)
    
    # 95% Value-at-Risk (VaR) of terminal returns (5th percentile of returns)
    var_95 = float(-np.percentile(terminal_returns, 5) * 100)
    
    # 95% Conditional Value-at-Risk (CVaR) / Expected Shortfall
    loss_returns = terminal_returns[terminal_returns <= np.percentile(terminal_returns, 5)]
    cvar_95 = float(-np.mean(loss_returns) * 100) if len(loss_returns) > 0 else 0.0
    
    median_terminal = float(np.percentile(terminal_values, 50))
    
    # Dates formatting (include a "Start" element for index 0)
    dates_str = [d.strftime("%Y-%m-%d") for d in daily_df.index]
    
    return {
        "dates": ["Start"] + dates_str,
        "p5": [float(round(x, 2)) for x in p5],
        "p25": [float(round(x, 2)) for x in p25],
        "p50": [float(round(x, 2)) for x in p50],
        "p75": [float(round(x, 2)) for x in p75],
        "p95": [float(round(x, 2)) for x in p95],
        "stats": {
            "prob_loss": float(round(prob_loss, 2)),
            "var_95": float(round(var_95, 2)),
            "cvar_95": float(round(cvar_95, 2)),
            "median_terminal_value": float(round(median_terminal, 2))
        }
    }

