import pandas as pd
import numpy as np

# =============================
# 1. Load data
# =============================
data = pd.read_csv("../data/processed/nifty50_clean.csv")

price_col = "Close"
data[price_col] = pd.to_numeric(data[price_col], errors="coerce")
data = data.dropna(subset=[price_col]).reset_index(drop=True)

# =============================
# 2. Indicators
# =============================
data["MA50"] = data[price_col].rolling(50).mean()
data["MA200"] = data[price_col].rolling(200).mean()

# =============================
# 3. Risk overlay exposure
# =============================
data["Exposure"] = 0.0

# Medium risk
data.loc[
    (data[price_col] > data["MA200"]) &
    (data[price_col] <= data["MA50"]),
    "Exposure"
] = 0.5

# High risk
data.loc[
    (data[price_col] > data["MA50"]) &
    (data[price_col] > data["MA200"]),
    "Exposure"
] = 1.0

# Lag exposure (no lookahead)
data["Exposure"] = data["Exposure"].shift(1).fillna(0)

# =============================
# 4. Buy & Hold with overlay
# =============================
initial_capital = 100000

data["DailyReturn"] = data[price_col].pct_change().fillna(0)

# Overlay-adjusted returns
data["OverlayReturn"] = data["DailyReturn"] * data["Exposure"]

# Equity curves
data["BuyHoldEquity"] = initial_capital * (1 + data["DailyReturn"]).cumprod()
data["OverlayEquity"] = initial_capital * (1 + data["OverlayReturn"]).cumprod()

# =============================
# 5. Drawdown
# =============================
data["OverlayPeak"] = data["OverlayEquity"].cummax()
data["OverlayDrawdown"] = (
    data["OverlayEquity"] - data["OverlayPeak"]
) / data["OverlayPeak"]

max_dd = data["OverlayDrawdown"].min() * 100

# =============================
# 6. Metrics
# =============================
years = len(data) / 252
final_overlay = data["OverlayEquity"].iloc[-1]
final_bh = data["BuyHoldEquity"].iloc[-1]

cagr_overlay = (final_overlay / initial_capital) ** (1 / years) - 1
cagr_bh = (final_bh / initial_capital) ** (1 / years) - 1

risk_free_rate = 0.06
daily_rf = risk_free_rate / 252

excess_overlay = data["OverlayReturn"] - daily_rf
sharpe_overlay = np.sqrt(252) * excess_overlay.mean() / excess_overlay.std()

time_in_market = (data["Exposure"] > 0).mean() * 100

# =============================
# 7. Output
# =============================
print("===== BUY & HOLD + RISK OVERLAY =====")
print(f"Final Overlay Value : {final_overlay:.2f}")
print(f"Final Buy & Hold    : {final_bh:.2f}")
print(f"Overlay CAGR (%)    : {cagr_overlay * 100:.2f}")
print(f"Buy & Hold CAGR (%) : {cagr_bh * 100:.2f}")
print(f"Time in Market (%)  : {time_in_market:.2f}")
print(f"Max Drawdown (%)    : {max_dd:.2f}")
print(f"Overlay Sharpe      : {sharpe_overlay:.2f}")
