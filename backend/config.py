import os

# Base Directories
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
CACHE_DIR = os.path.join(DATA_DIR, ".cache")
REPORTS_DIR = os.path.join(BASE_DIR, "reports")

# Create directories if they don't exist
os.makedirs(CACHE_DIR, exist_ok=True)
os.makedirs(REPORTS_DIR, exist_ok=True)

# Application Settings
HOST = os.getenv("QUANT_PLATFORM_HOST", "0.0.0.0")
PORT = int(os.getenv("QUANT_PLATFORM_PORT", "8000"))

# Default Backtesting Settings
DEFAULT_RISK_FREE_RATE = float(os.getenv("DEFAULT_RISK_FREE_RATE", "0.06"))
DEFAULT_INITIAL_CASH = float(os.getenv("DEFAULT_INITIAL_CASH", "100000.0"))
DEFAULT_COMMISSION = 0.001   # 0.1% flat commission fee
DEFAULT_SLIPPAGE = 0.0005     # 0.05% slippage price impact
