import json
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import plotly.express as px
import plotly.io as pio
from typing import Dict, Any, List

# Standard Styling Constants for Dark Theme
DARK_BG = "#1e1e1e"
GRID_COLOR = "#333333"
TEXT_COLOR = "#e0e0e0"
STRATEGY_COLOR = "#00e676"  # Bright Neon Green
BENCHMARK_COLOR = "#00b0ff" # Neon Blue
RED_COLOR = "#ff5252"       # Crimson Red

def apply_dark_theme(fig: go.Figure, title: str) -> go.Figure:
    """Helper to apply a standard, high-quality dark theme layout to Plotly figures."""
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(color=TEXT_COLOR, size=18)
        ),
        paper_bgcolor="rgba(0,0,0,0)", # transparent background to blend with CSS cards
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color=TEXT_COLOR, family="Inter, Roboto, sans-serif"),
        margin=dict(l=50, r=50, t=60, b=50),
        xaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            tickfont=dict(color=TEXT_COLOR),
            showgrid=True
        ),
        yaxis=dict(
            gridcolor=GRID_COLOR,
            linecolor=GRID_COLOR,
            tickfont=dict(color=TEXT_COLOR),
            showgrid=True
        ),
        legend=dict(
            font=dict(color=TEXT_COLOR),
            bgcolor="rgba(30, 30, 30, 0.8)",
            bordercolor=GRID_COLOR,
            borderwidth=1
        )
    )
    return fig

def generate_price_chart(
    daily_df: pd.DataFrame, 
    trade_log: List[Dict[str, Any]], 
    ticker: str,
    dfs: Optional[Dict[str, pd.DataFrame]] = None
) -> Dict[str, Any]:
    """Generate close price chart with indicators and buy/sell trade markers (normalized if multi-ticker)."""
    fig = go.Figure()
    
    if dfs and len(dfs) > 1:
        # Multi-ticker: Plot normalized close prices (start at 100)
        color_palette = ["#00e676", "#00b0ff", "#ffeb3b", "#ff9800", "#d500f9", "#ff1744", "#1de9b6", "#3d5afe"]
        for idx, (tk, df) in enumerate(dfs.items()):
            if df.empty:
                continue
            first_val = float(df["Close"].iloc[0])
            norm_close = df["Close"] / first_val * 100.0
            color = color_palette[idx % len(color_palette)]
            fig.add_trace(go.Scatter(
                x=df.index,
                y=norm_close,
                mode="lines",
                name=f"{tk} (Normalized)",
                line=dict(color=color, width=1.5)
            ))
        apply_dark_theme(fig, "Multi-Asset Normalized Price Comparison (Base 100)")
        fig.update_layout(yaxis=dict(title="Normalized Value", ticksuffix="%"))
    else:
        # Single-ticker: Plot raw Close price, indicators and trade markers
        fig.add_trace(go.Scatter(
            x=daily_df.index,
            y=daily_df["Close"],
            mode="lines",
            name=f"{ticker} Close",
            line=dict(color="#ffffff", width=1.5)
        ))
        
        # Add indicators
        for ma_col in ["MA50", "MA200", "Fast_MA", "Slow_MA", "Upper_Band", "Lower_Band"]:
            if ma_col in daily_df.columns:
                color = "#ffeb3b" if "50" in ma_col or "Fast" in ma_col else "#ff9800"
                if "Band" in ma_col:
                    color = "#9e9e9e"
                fig.add_trace(go.Scatter(
                    x=daily_df.index,
                    y=daily_df[ma_col],
                    mode="lines",
                    name=ma_col,
                    line=dict(color=color, width=1.0, dash="dash" if "Band" in ma_col else "solid")
                ))
                
        # Add Trade Markers
        buys = [t for t in trade_log if t["Action"] == "BUY"]
        sells = [t for t in trade_log if t["Action"] == "SELL"]
        stops = [t for t in trade_log if t["Action"] == "STOP LOSS"]
        
        if buys:
            fig.add_trace(go.Scatter(
                x=[pd.to_datetime(t["Date"]) for t in buys],
                y=[t["Price"] for t in buys],
                mode="markers",
                name="BUY Signals",
                marker=dict(symbol="triangle-up", color=STRATEGY_COLOR, size=10, line=dict(color="#ffffff", width=1)),
                text=[f"Shares: {t['Shares']}<br>Value: {t['Value']}" for t in buys],
                hoverinfo="x+y+text"
            ))
            
        if sells:
            fig.add_trace(go.Scatter(
                x=[pd.to_datetime(t["Date"]) for t in sells],
                y=[t["Price"] for t in sells],
                mode="markers",
                name="SELL Signals",
                marker=dict(symbol="triangle-down", color=RED_COLOR, size=10, line=dict(color="#ffffff", width=1)),
                text=[f"Shares: {t['Shares']}<br>Value: {t['Value']}" for t in sells],
                hoverinfo="x+y+text"
            ))
            
        if stops:
            fig.add_trace(go.Scatter(
                x=[pd.to_datetime(t["Date"]) for t in stops],
                y=[t["Price"] for t in stops],
                mode="markers",
                name="STOP LOSS Hits",
                marker=dict(symbol="x", color="#ff1744", size=10, line=dict(color="#ffffff", width=1)),
                text=[f"Shares: {t['Shares']}<br>Value: {t['Value']}" for t in stops],
                hoverinfo="x+y+text"
            ))
            
        apply_dark_theme(fig, f"{ticker} Price & Trade Log")
        fig.update_layout(yaxis=dict(title="Price ($)"))
        
    return json.loads(pio.to_json(fig))

def generate_monte_carlo_chart(sim_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Generate a Plotly fan chart representing Monte Carlo percentile bands.
    
    Parameters:
        sim_data (Dict[str, Any]): Dict from metrics.calculator.run_monte_carlo_simulation.
        
    Returns:
        Dict[str, Any]: Plotly chart JSON representation.
    """
    fig = go.Figure()
    dates = sim_data["dates"]
    
    # 5% - 95% Band
    fig.add_trace(go.Scatter(
        x=dates,
        y=sim_data["p95"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=dates,
        y=sim_data["p5"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(0, 176, 255, 0.08)",
        name="5% - 95% Band"
    ))
    
    # 25% - 75% Band
    fig.add_trace(go.Scatter(
        x=dates,
        y=sim_data["p75"],
        mode="lines",
        line=dict(width=0),
        showlegend=False,
        hoverinfo="skip"
    ))
    fig.add_trace(go.Scatter(
        x=dates,
        y=sim_data["p25"],
        mode="lines",
        line=dict(width=0),
        fill="tonexty",
        fillcolor="rgba(0, 230, 118, 0.15)",
        name="25% - 75% Band"
    ))
    
    # Median Path
    fig.add_trace(go.Scatter(
        x=dates,
        y=sim_data["p50"],
        mode="lines",
        line=dict(color=STRATEGY_COLOR, width=2.5),
        name="Median Simulation (50%)"
    ))
    
    apply_dark_theme(fig, "Monte Carlo Stress Test Simulations")
    fig.update_layout(
        yaxis=dict(title="Simulated Portfolio Value ($)"),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
    )
    return json.loads(pio.to_json(fig))


def generate_equity_curve_chart(daily_df: pd.DataFrame) -> Dict[str, Any]:
    """Generate strategy equity curve vs Buy & Hold benchmark."""
    fig = go.Figure()
    
    # Strategy Equity
    fig.add_trace(go.Scatter(
        x=daily_df.index,
        y=daily_df["PortfolioValue"],
        mode="lines",
        name="Risk Overlay Strategy",
        line=dict(color=STRATEGY_COLOR, width=2.0)
    ))
    
    # Buy & Hold Equity
    fig.add_trace(go.Scatter(
        x=daily_df.index,
        y=daily_df["BuyHoldValue"],
        mode="lines",
        name="Buy & Hold Benchmark",
        line=dict(color=BENCHMARK_COLOR, width=1.5, dash="dot")
    ))
    
    apply_dark_theme(fig, "Equity Curve Performance Comparison")
    fig.update_layout(yaxis=dict(title="Portfolio Value ($)"))
    return json.loads(pio.to_json(fig))

def generate_drawdown_chart(daily_df: pd.DataFrame) -> Dict[str, Any]:
    """Generate drawdown chart for both strategy and Buy & Hold."""
    fig = go.Figure()
    
    # Strategy Drawdown
    strat_peaks = daily_df["PortfolioValue"].cummax()
    strat_dd = (daily_df["PortfolioValue"] - strat_peaks) / strat_peaks * 100
    
    fig.add_trace(go.Scatter(
        x=daily_df.index,
        y=strat_dd,
        mode="lines",
        name="Strategy Drawdown",
        line=dict(color=STRATEGY_COLOR, width=1.5),
        fill="tozeroy",
        fillcolor="rgba(0, 230, 118, 0.1)"
    ))
    
    # Buy & Hold Drawdown
    bh_peaks = daily_df["BuyHoldValue"].cummax()
    bh_dd = (daily_df["BuyHoldValue"] - bh_peaks) / bh_peaks * 100
    
    fig.add_trace(go.Scatter(
        x=daily_df.index,
        y=bh_dd,
        mode="lines",
        name="Buy & Hold Drawdown",
        line=dict(color=BENCHMARK_COLOR, width=1.2, dash="dot"),
        fill="tozeroy",
        fillcolor="rgba(0, 176, 255, 0.05)"
    ))
    
    apply_dark_theme(fig, "Drawdown Exposure Profile (%)")
    fig.update_layout(yaxis=dict(title="Drawdown (%)", ticksuffix="%"))
    return json.loads(pio.to_json(fig))

def generate_monthly_heatmap(daily_df: pd.DataFrame) -> Dict[str, Any]:
    """Generate Monthly Return Heatmap figure."""
    # Resample daily returns to monthly return
    monthly_series = daily_df["PortfolioValue"].resample("ME").ffill()
    monthly_returns = monthly_series.pct_change().fillna(0.0)
    
    # Reconstruct as a DataFrame of Years vs Months
    heatmap_df = pd.DataFrame({
        "Year": monthly_returns.index.year,
        "Month": monthly_returns.index.month,
        "Return": monthly_returns.values * 100.0  # percentage
    })
    
    pivot_df = heatmap_df.pivot_table(index="Year", columns="Month", values="Return", aggfunc="sum")
    
    # Rename columns to standard abbreviated months
    months_names = {
        1: "Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun",
        7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"
    }
    pivot_df = pivot_df.rename(columns=months_names)
    
    # Ensure all months exist in headers
    for m in months_names.values():
        if m not in pivot_df.columns:
            pivot_df[m] = np.nan
            
    # Sort columns by month order
    pivot_df = pivot_df[list(months_names.values())]
    pivot_df = pivot_df.fillna(0.0)
    
    # Generate Heatmap
    fig = go.Figure(data=go.Heatmap(
        z=pivot_df.values,
        x=pivot_df.columns,
        y=pivot_df.index,
        colorscale="RdYlGn", # standard Red-Yellow-Green Diverging scale
        zmid=0, # color center at 0% return
        colorbar=dict(title="Return (%)", ticksuffix="%"),
        hovertemplate="Year: %{y}<br>Month: %{x}<br>Return: %{z:.2f}%<extra></extra>"
    ))
    
    apply_dark_theme(fig, "Monthly Strategy Returns Heatmap")
    
    # Specific adjustment for heatmap yaxis to be treated as categorical (discrete years)
    fig.update_layout(
        yaxis=dict(
            type="category",
            autorange="reversed" # show oldest year at bottom or top (reversed puts oldest at top or bottom depending on preference, standard is chronological from top to bottom)
        )
    )
    return json.loads(pio.to_json(fig))
