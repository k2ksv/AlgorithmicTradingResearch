import os
import hashlib
import logging
import pandas as pd
import yfinance as yf
from backend.config import CACHE_DIR, DATA_DIR

logger = logging.getLogger(__name__)

def get_cache_filepath(ticker: str, start_date: str, end_date: str, interval: str) -> str:
    """Generate a unique filename for caching yfinance data."""
    # Normalize inputs
    ticker_clean = ticker.replace("^", "INDEX_").replace("-", "_").replace(".", "_")
    filename = f"{ticker_clean}_{start_date}_{end_date}_{interval}.csv"
    return os.path.join(CACHE_DIR, filename)

def calculate_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    """Calculate Average True Range (ATR) indicator."""
    high = df["High"]
    low = df["Low"]
    close = df["Close"]
    
    prev_close = close.shift(1)
    
    tr1 = high - low
    tr2 = (high - prev_close).abs()
    tr3 = (low - prev_close).abs()
    
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period).mean()
    # Fallback to simple High-Low range for initial values
    fallback = (high - low).rolling(window=period).mean().fillna(0.0)
    return atr.fillna(fallback).fillna(0.0)

def load_ticker_data(ticker: str, start_date: str, end_date: str, interval: str = "1d") -> pd.DataFrame:
    """
    Fetch historical stock data from Yahoo Finance or from the local cache.
    
    Parameters:
        ticker: The stock ticker (e.g. 'AAPL', 'RELIANCE.NS').
        start_date: Start date string (YYYY-MM-DD).
        end_date: End date string (YYYY-MM-DD).
        interval: Data interval ('1d', '1wk', '1mo').
        
    Returns:
        pd.DataFrame: A cleaned DataFrame with DatetimeIndex and columns: Open, High, Low, Close, Volume, ATR.
    """
    cache_path = get_cache_filepath(ticker, start_date, end_date, interval)
    
    # Check if cache exists
    if os.path.exists(cache_path):
        logger.info(f"Loading cached data for {ticker} from {cache_path}")
        df = pd.read_csv(cache_path, parse_dates=["Date"])
        df.set_index("Date", inplace=True)
        if not df.empty:
            if "ATR" not in df.columns:
                df["ATR"] = calculate_atr(df)
            return df
            
    logger.info(f"Fetching fresh data for {ticker} from yfinance (start: {start_date}, end: {end_date}, interval: {interval})")
    
    try:
        df = yf.download(ticker, start=start_date, end=end_date, interval=interval)
        
        if df.empty:
            raise ValueError(f"No data returned for ticker '{ticker}' from yfinance.")
            
        # Clean MultiIndex columns if present
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
            
        # Standardize index name and ensure DatetimeIndex
        df.index.name = "Date"
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        
        # Ensure critical columns exist and are numeric
        required_cols = ["Open", "High", "Low", "Close", "Volume"]
        for col in required_cols:
            if col not in df.columns:
                raise ValueError(f"Required column '{col}' is missing in fetched data.")
            df[col] = pd.to_numeric(df[col], errors="coerce")
            
        # Drop rows where Close is missing
        df = df.dropna(subset=["Close"])
        
        # Precompute ATR
        df["ATR"] = calculate_atr(df)
        
        # Save to cache
        df.to_csv(cache_path, index=True)
        logger.info(f"Saved cached data for {ticker} to {cache_path}")
        
        return df
        
    except Exception as e:
        logger.error(f"Failed to fetch data for ticker {ticker}: {str(e)}")
        
        # Check if local fallback file exists
        fallback_path = os.path.join(DATA_DIR, "nifty50_fallback.csv")
        if os.path.exists(fallback_path):
            logger.warning(f"Using offline fallback NIFTY50 dataset: {fallback_path}")
            try:
                # Load raw nifty50.csv (skipping ticker name and empty date rows)
                df = pd.read_csv(fallback_path, skiprows=[1, 2])
                df = df.rename(columns={"Price": "Date"})
                df["Date"] = pd.to_datetime(df["Date"])
                df.set_index("Date", inplace=True)
                df = df.sort_index()
                
                # Standardize columns
                required_cols = ["Open", "High", "Low", "Close", "Volume"]
                for col in required_cols:
                    df[col] = pd.to_numeric(df[col], errors="coerce")
                df = df.dropna(subset=["Close"])
                
                # Precompute ATR on full history before slicing (for rolling window completeness)
                df["ATR"] = calculate_atr(df)
                
                # Filter by requested date range
                start_dt = pd.to_datetime(start_date)
                end_dt = pd.to_datetime(end_date)
                df = df.loc[(df.index >= start_dt) & (df.index <= end_dt)]
                
                if df.empty:
                    raise ValueError(f"Fallback dataset has no data for range {start_date} to {end_date}.")
                
                return df
            except Exception as fe:
                logger.error(f"Fallback parse failed: {str(fe)}")
                raise fe
        raise e

def load_multiple_tickers_data(tickers: list[str], start_date: str, end_date: str, interval: str = "1d") -> dict[str, pd.DataFrame]:
    """
    Fetch historical stock data for multiple tickers.
    
    Returns:
        dict[str, pd.DataFrame]: Mapping of ticker -> DataFrame.
    """
    data = {}
    for ticker in tickers:
        ticker = ticker.strip()
        if not ticker:
            continue
        try:
            df = load_ticker_data(ticker, start_date, end_date, interval)
            data[ticker] = df
        except Exception as e:
            logger.error(f"Failed to load data for ticker {ticker}: {str(e)}")
            raise e
    return data

