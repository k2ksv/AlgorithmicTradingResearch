from abc import ABC, abstractmethod
import pandas as pd

class BaseStrategy(ABC):
    """
    Abstract Base Class for all trading strategies.
    
    Every strategy must implement `generate_signals` which accepts a historical
    DataFrame and returns the DataFrame with a 'Signal' column.
    The 'Signal' column represents the target portfolio weight/exposure (from 0.0 to 1.0).
    """
    
    def __init__(self, name: str, params: dict = None):
        self.name = name
        self.params = params or {}
        
    @abstractmethod
    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Calculates trading signals/weights based on historical price data.
        
        Parameters:
            df (pd.DataFrame): DataFrame containing Date index and columns: Open, High, Low, Close, Volume.
            
        Returns:
            pd.DataFrame: A copy of the DataFrame with an added 'Signal' column (values 0.0 to 1.0).
        """
        pass
