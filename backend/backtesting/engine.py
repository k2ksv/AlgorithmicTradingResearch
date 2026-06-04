import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Any, Optional

from backend.config import DEFAULT_INITIAL_CASH, DEFAULT_RISK_FREE_RATE, DEFAULT_COMMISSION, DEFAULT_SLIPPAGE

logger = logging.getLogger(__name__)

class BacktestEngine:
    """
    Chronological Backtesting Engine.
    Simulates trading day-by-day, tracking cash, positions, transaction costs,
    and generating detailed trade logs. Supports single or multi-asset portfolios,
    trailing stop-losses, and ATR position sizing.
    """
    
    def __init__(
        self,
        initial_cash: float = DEFAULT_INITIAL_CASH,
        commission_rate: float = DEFAULT_COMMISSION,
        slippage_rate: float = DEFAULT_SLIPPAGE,
        risk_free_rate: float = DEFAULT_RISK_FREE_RATE,
        trailing_stop_pct: float = 0.0,
        use_atr_sizing: bool = False,
        risk_pct: float = 0.02,
        atr_multiplier: float = 2.0
    ):
        self.initial_cash = initial_cash
        self.commission_rate = commission_rate
        self.slippage_rate = slippage_rate
        self.risk_free_rate = risk_free_rate
        self.daily_rf = risk_free_rate / 252.0
        self.trailing_stop_pct = trailing_stop_pct
        self.use_atr_sizing = use_atr_sizing
        self.risk_pct = risk_pct
        self.atr_multiplier = atr_multiplier
        
    def run(self, data: Any, weights: Optional[Dict[str, float]] = None) -> Dict[str, Any]:
        """
        Run the chronological backtest.
        
        Parameters:
            data (pd.DataFrame or Dict[str, pd.DataFrame]): 
                DataFrame with columns: Date (index), Open, High, Low, Close, Volume, Signal, ATR (optional).
                Or Dict of such DataFrames mapping ticker -> DataFrame.
            weights (Dict[str, float], optional):
                Base allocation weight per ticker. If None and multi-asset, weights are equally divided.
                
        Returns:
            Dict[str, Any]: Dictionary containing daily time series DataFrame and list of trade logs.
        """
        # Convert single asset to dict
        if isinstance(data, pd.DataFrame):
            dfs = {"PORTFOLIO_ASSET": data}
            weights = {"PORTFOLIO_ASSET": 1.0}
            is_multi = False
        else:
            dfs = data
            is_multi = True
            if not weights:
                weights = {ticker: 1.0 / len(dfs) for ticker in dfs.keys()}
            else:
                # Normalize weights to sum to <= 1.0
                total_w = sum(weights.values())
                if total_w > 1.0:
                    weights = {k: v / total_w for k, v in weights.items()}
        
        # Shift signals by 1 day to prevent look-ahead bias (signals generated on day t-1 are applied to day t)
        dfs_clean = {}
        for ticker, df in dfs.items():
            df_copy = df.copy()
            df_copy["Exposure"] = df_copy["Signal"].shift(1).fillna(0.0)
            dfs_clean[ticker] = df_copy
            
        # Get all unique dates sorted chronologically
        all_dates = sorted(list(set().union(*(df.index for df in dfs_clean.values()))))
        
        if not all_dates:
            raise ValueError("No overlapping dates found in backtest data.")
            
        # Initialize variables
        cash = self.initial_cash
        positions = {ticker: 0.0 for ticker in dfs_clean.keys()}
        
        # Track initial closes for Buy & Hold
        first_closes = {}
        for ticker, df in dfs_clean.items():
            first_closes[ticker] = float(df["Close"].iloc[0])
            
        last_prices = {ticker: first_closes[ticker] for ticker in dfs_clean.keys()}
        
        # Risk management tracking
        peak_prices = {ticker: 0.0 for ticker in dfs_clean.keys()}
        stopped_out = {ticker: False for ticker in dfs_clean.keys()}
        
        daily_records = []
        trade_log = []
        
        for date in all_dates:
            # 1. Earn risk-free interest on overnight cash
            interest = cash * self.daily_rf
            cash += interest
            
            # 2. Get today's prices (Close, High, Low) for all assets
            today_closes = {}
            today_highs = {}
            today_lows = {}
            
            for ticker, df in dfs_clean.items():
                if date in df.index:
                    row = df.loc[date]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    close_p = float(row["Close"])
                    high_p = float(row["High"]) if "High" in row else close_p
                    low_p = float(row["Low"]) if "Low" in row else close_p
                    
                    last_prices[ticker] = close_p
                    today_closes[ticker] = close_p
                    today_highs[ticker] = high_p
                    today_lows[ticker] = low_p
                else:
                    # Asset not traded today, use last seen price
                    today_closes[ticker] = last_prices[ticker]
                    today_highs[ticker] = last_prices[ticker]
                    today_lows[ticker] = last_prices[ticker]
            
            # 3. Calculate portfolio value before trading
            equity_val = sum(positions[tk] * today_closes[tk] for tk in dfs_clean.keys())
            portfolio_value = cash + equity_val
            
            # 4. Check Trailing Stop-Loss for held assets
            for ticker in dfs_clean.keys():
                shares = positions[ticker]
                
                # Retrieve raw signal to reset stop-out flag
                df = dfs_clean[ticker]
                if date in df.index:
                    row = df.loc[date]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    raw_signal = float(row["Signal"])
                else:
                    prior_df = df.loc[df.index < date]
                    raw_signal = float(prior_df["Signal"].iloc[-1]) if not prior_df.empty else 0.0
                    
                if stopped_out[ticker] and raw_signal == 0.0:
                    stopped_out[ticker] = False
                    
                if shares > 0.0:
                    peak_prices[ticker] = max(peak_prices[ticker], today_highs[ticker])
                    
                    # Trailing Stop Loss check
                    if self.trailing_stop_pct > 0.0:
                        stop_level = peak_prices[ticker] * (1.0 - self.trailing_stop_pct)
                        if today_lows[ticker] < stop_level:
                            # Trigger stop: Liquidate at daily Close price (conservative)
                            exit_price = today_closes[ticker]
                            trade_val = shares * exit_price
                            commission = trade_val * self.commission_rate
                            slippage = trade_val * self.slippage_rate
                            tx_cost = commission + slippage
                            
                            cash += (trade_val - tx_cost)
                            positions[ticker] = 0.0
                            peak_prices[ticker] = 0.0
                            stopped_out[ticker] = True
                            
                            trade_log.append({
                                "Date": date.strftime("%Y-%m-%d"),
                                "Ticker": ticker if is_multi else "",
                                "Action": "STOP LOSS",
                                "Price": float(round(exit_price, 2)),
                                "Shares": float(round(shares, 4)),
                                "Value": float(round(trade_val, 2)),
                                "TransactionCost": float(round(tx_cost, 2)),
                                "CashAfter": float(round(cash, 2)),
                                "PortfolioValueAfter": float(round(cash, 2)),
                                "ExposureAfter": 0.0
                            })
                            logger.info(f"[{date.strftime('%Y-%m-%d')}] Trailing stop hit for {ticker} at {exit_price:.2f}. Liquidated.")
                            
            # 5. Rebalance assets based on today's exposure
            # Recompute total equity and portfolio value post stop-loss liquidations
            equity_val = sum(positions[tk] * today_closes[tk] for tk in dfs_clean.keys())
            portfolio_value = cash + equity_val
            
            for ticker in dfs_clean.keys():
                if stopped_out[ticker]:
                    continue
                    
                df = dfs_clean[ticker]
                if date in df.index:
                    row = df.loc[date]
                    if isinstance(row, pd.DataFrame):
                        row = row.iloc[0]
                    exposure = float(row["Exposure"])
                    atr_val = float(row["ATR"]) if "ATR" in row else 0.0
                else:
                    prior_df = df.loc[df.index < date]
                    if not prior_df.empty:
                        last_row = prior_df.iloc[-1]
                        exposure = float(last_row["Exposure"])
                        atr_val = float(last_row["ATR"]) if "ATR" in last_row else 0.0
                    else:
                        exposure = 0.0
                        atr_val = 0.0
                        
                close_price = today_closes[ticker]
                base_w = weights[ticker]
                
                # Check ATR Position Sizing
                if self.use_atr_sizing and exposure > 0.0 and atr_val > 0.0:
                    # Size based on volatility: weight = risk_pct * price / (atr * multiplier)
                    atr_w = (self.risk_pct * close_price) / (atr_val * self.atr_multiplier)
                    # Target weight is scaled by exposure and capped at base weight budget
                    target_w = exposure * min(base_w, atr_w)
                else:
                    target_w = exposure * base_w
                    
                target_equity_value = target_w * portfolio_value
                current_equity_value = positions[ticker] * close_price
                trade_value = target_equity_value - current_equity_value
                
                if abs(trade_value) > 10.0 and close_price > 0.0:
                    shares_to_trade = trade_value / close_price
                    commission = abs(trade_value) * self.commission_rate
                    slippage = abs(trade_value) * self.slippage_rate
                    tx_cost = commission + slippage
                    
                    # Execute Trade
                    positions[ticker] += shares_to_trade
                    cash -= (trade_value + tx_cost)
                    
                    # Set peak price on initial position entry
                    if current_equity_value == 0.0 and positions[ticker] > 0.0:
                        peak_prices[ticker] = today_highs[ticker]
                        
                    # Recompute portfolio value
                    current_equity = sum(positions[tk] * today_closes[tk] for tk in dfs_clean.keys())
                    temp_port_val = cash + current_equity
                    
                    trade_log.append({
                        "Date": date.strftime("%Y-%m-%d"),
                        "Ticker": ticker if is_multi else "",
                        "Action": "BUY" if trade_value > 0 else "SELL",
                        "Price": float(round(close_price, 2)),
                        "Shares": float(round(abs(shares_to_trade), 4)),
                        "Value": float(round(abs(trade_value), 2)),
                        "TransactionCost": float(round(tx_cost, 2)),
                        "CashAfter": float(round(cash, 2)),
                        "PortfolioValueAfter": float(round(temp_port_val, 2)),
                        "ExposureAfter": float(round(target_w, 4))
                    })
                    
            # 6. Record daily state
            # Benchmark Portfolio: Buy and Hold from first date
            buy_hold_value = 0.0
            for ticker, df in dfs_clean.items():
                first_c = first_closes[ticker]
                close_p = today_closes[ticker]
                buy_hold_value += self.initial_cash * weights[ticker] * (close_p / first_c)
                
            # Recompute portfolio value after rebalancing
            final_equity = sum(positions[tk] * today_closes[tk] for tk in dfs_clean.keys())
            portfolio_value = cash + final_equity
            
            # Average daily exposure across portfolio
            total_exposure = 0.0
            for ticker in dfs_clean.keys():
                df = dfs_clean[ticker]
                if date in df.index:
                    exp = float(df.loc[date, "Exposure"])
                else:
                    prior_df = df.loc[df.index < date]
                    exp = float(prior_df["Exposure"].iloc[-1]) if not prior_df.empty else 0.0
                total_exposure += exp * weights[ticker]
                
            daily_records.append({
                "Date": date,
                "Close": today_closes[list(dfs_clean.keys())[0]], # Representative price
                "Exposure": total_exposure,
                "Cash": cash,
                "PortfolioValue": portfolio_value,
                "BuyHoldValue": buy_hold_value
            })
            
        # Create daily series DataFrame
        daily_df = pd.DataFrame(daily_records)
        daily_df.set_index("Date", inplace=True)
        
        # Calculate daily returns
        daily_df["DailyReturn"] = daily_df["PortfolioValue"].pct_change().fillna(0.0)
        daily_df["BuyHoldReturn"] = daily_df["BuyHoldValue"].pct_change().fillna(0.0)
        
        return {
            "daily_series": daily_df,
            "trade_log": trade_log
        }
