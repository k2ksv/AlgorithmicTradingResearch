import pandas as pd
import numpy as np
from backend.strategies.base import BaseStrategy

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate the Average True Range (ATR) indicator."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    return atr

class BuyAndHoldStrategy(BaseStrategy):
    """Simple strategy that stays 100% invested in the asset."""
    
    def __init__(self, params: dict = None):
        super().__init__("Buy & Hold", params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        df_out["Signal"] = 1.0
        return df_out

class MACrossoverStrategy(BaseStrategy):
    """
    Moving Average Crossover Strategy.
    Long (1.0) when Fast MA > Slow MA, Neutral (0.0) otherwise.
    """
    
    def __init__(self, params: dict = None):
        default_params = {"fast_period": 50, "slow_period": 200}
        if params:
            default_params.update(params)
        super().__init__("MA Crossover", default_params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        
        df_out["Fast_MA"] = df_out["Close"].rolling(window=fast).mean()
        df_out["Slow_MA"] = df_out["Close"].rolling(window=slow).mean()
        
        df_out["Signal"] = 0.0
        # Fast MA > Slow MA
        df_out.loc[df_out["Fast_MA"] > df_out["Slow_MA"], "Signal"] = 1.0
        
        # Fill leading NaNs with 0
        df_out["Signal"] = df_out["Signal"].fillna(0.0)
        return df_out

class TrendFollowing50_200Strategy(BaseStrategy):
    """
    50-200 Trend Following Strategy.
    - Low Risk (0.0): Close <= MA200
    - Medium Risk (0.5): Close > MA200 and Close <= MA50
    - High Risk (1.0): Close > MA50 and Close > MA200
    """
    
    def __init__(self, params: dict = None):
        default_params = {"ma50_period": 50, "ma200_period": 200}
        if params:
            default_params.update(params)
        super().__init__("50-200 Trend Following", default_params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        ma50 = self.params["ma50_period"]
        ma200 = self.params["ma200_period"]
        
        df_out["MA50"] = df_out["Close"].rolling(window=ma50).mean()
        df_out["MA200"] = df_out["Close"].rolling(window=ma200).mean()
        
        df_out["Signal"] = 0.0
        
        # Medium Risk: Close > MA200 and Close <= MA50
        df_out.loc[
            (df_out["Close"] > df_out["MA200"]) & (df_out["Close"] <= df_out["MA50"]),
            "Signal"
        ] = 0.5
        
        # High Risk: Close > MA50 and Close > MA200
        df_out.loc[
            (df_out["Close"] > df_out["MA50"]) & (df_out["Close"] > df_out["MA200"]),
            "Signal"
        ] = 1.0
        
        df_out["Signal"] = df_out["Signal"].fillna(0.0)
        return df_out

class RSIStrategy(BaseStrategy):
    """
    RSI Strategy.
    - Buy (1.0) when RSI crosses below oversold threshold.
    - Sell (0.0) when RSI crosses above overbought threshold.
    - Hold previous position state otherwise.
    """
    
    def __init__(self, params: dict = None):
        default_params = {
            "rsi_period": 14,
            "oversold_threshold": 30,
            "overbought_threshold": 70
        }
        if params:
            default_params.update(params)
        super().__init__("RSI Strategy", default_params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        period = self.params["rsi_period"]
        oversold = self.params["oversold_threshold"]
        overbought = self.params["overbought_threshold"]
        
        # Calculate RSI
        delta = df_out["Close"].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        
        rs = gain / (loss + 1e-9)
        df_out["RSI"] = 100 - (100 / (1 + rs))
        
        # State machine for holding positions
        signals = []
        current_signal = 0.0
        
        for rsi_val in df_out["RSI"]:
            if pd.isna(rsi_val):
                signals.append(0.0)
            elif rsi_val < oversold:
                current_signal = 1.0
                signals.append(current_signal)
            elif rsi_val > overbought:
                current_signal = 0.0
                signals.append(current_signal)
            else:
                signals.append(current_signal)
                
        df_out["Signal"] = signals
        return df_out

class MACDStrategy(BaseStrategy):
    """
    MACD Crossover Strategy.
    - Long (1.0) when MACD Line > Signal Line.
    - Neutral (0.0) otherwise.
    """
    
    def __init__(self, params: dict = None):
        default_params = {
            "fast_period": 12,
            "slow_period": 26,
            "signal_period": 9
        }
        if params:
            default_params.update(params)
        super().__init__("MACD Strategy", default_params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        fast = self.params["fast_period"]
        slow = self.params["slow_period"]
        sig = self.params["signal_period"]
        
        # MACD Line & Signal Line
        ema_fast = df_out["Close"].ewm(span=fast, adjust=False).mean()
        ema_slow = df_out["Close"].ewm(span=slow, adjust=False).mean()
        df_out["MACD"] = ema_fast - ema_slow
        df_out["MACD_Signal"] = df_out["MACD"].ewm(span=sig, adjust=False).mean()
        
        df_out["Signal"] = 0.0
        df_out.loc[df_out["MACD"] > df_out["MACD_Signal"], "Signal"] = 1.0
        
        df_out["Signal"] = df_out["Signal"].fillna(0.0)
        return df_out

class BollingerBandsStrategy(BaseStrategy):
    """
    Bollinger Bands Strategy.
    - Buy (1.0) when Close price touches/drops below lower band.
    - Sell (0.0) when Close price touches/rises above upper band.
    - Hold previous state otherwise.
    """
    
    def __init__(self, params: dict = None):
        default_params = {"period": 20, "num_std": 2}
        if params:
            default_params.update(params)
        super().__init__("Bollinger Bands", default_params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        period = self.params["period"]
        num_std = self.params["num_std"]
        
        df_out["MA"] = df_out["Close"].rolling(window=period).mean()
        df_out["STD"] = df_out["Close"].rolling(window=period).std()
        df_out["Upper_Band"] = df_out["MA"] + (num_std * df_out["STD"])
        df_out["Lower_Band"] = df_out["MA"] - (num_std * df_out["STD"])
        
        # State machine for signals
        signals = []
        current_signal = 0.0
        
        for close_val, lower, upper in zip(df_out["Close"], df_out["Lower_Band"], df_out["Upper_Band"]):
            if pd.isna(lower) or pd.isna(upper):
                signals.append(0.0)
            elif close_val < lower:
                current_signal = 1.0
                signals.append(current_signal)
            elif close_val > upper:
                current_signal = 0.0
                signals.append(current_signal)
            else:
                signals.append(current_signal)
                
        df_out["Signal"] = signals
        return df_out

class VolatilityFilterStrategy(BaseStrategy):
    """
    Volatility Filter Strategy.
    - Base signal: 1.0 if Close > 50-day Moving Average, 0.0 otherwise.
    - If 20-day annualized volatility exceeds the threshold, target exposure is scaled down.
    - High volatility: Scale to 50% (0.5 signal).
    - Extreme volatility: Scale to 0% (0.0 signal).
    """
    
    def __init__(self, params: dict = None):
        default_params = {
            "ma_period": 50,
            "vol_period": 20,
            "vol_threshold": 0.25   # 25% annualized volatility
        }
        if params:
            default_params.update(params)
        super().__init__("Volatility Filter", default_params)
        
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        df_out = df.copy()
        ma_period = self.params["ma_period"]
        vol_period = self.params["vol_period"]
        vol_threshold = self.params["vol_threshold"]
        
        # Base trend indicator (Simple Moving Average)
        df_out["MA"] = df_out["Close"].rolling(window=ma_period).mean()
        base_signal = (df_out["Close"] > df_out["MA"]).astype(float)
        
        # Calculate rolling annualized volatility of daily returns
        daily_returns = df_out["Close"].pct_change()
        df_out["Vol"] = daily_returns.rolling(window=vol_period).std() * np.sqrt(252)
        
        # Adjust base signals based on volatility filters
        signals = []
        for base_sig, vol in zip(base_signal, df_out["Vol"]):
            if pd.isna(vol) or pd.isna(base_sig):
                signals.append(0.0)
            elif vol > vol_threshold * 1.5:
                # Extreme volatility: Go completely to cash
                signals.append(0.0)
            elif vol > vol_threshold:
                # High volatility: Halve the exposure
                signals.append(base_sig * 0.5)
            else:
                # Normal volatility: Follow trend signal fully
                signals.append(base_sig)
                
        df_out["Signal"] = signals
        return df_out
