import io
import csv
import json
import logging
import plotly.io as pio
from typing import Dict, List, Any, Optional
from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse, Response
from pydantic import BaseModel

# Backend Modules
from backend.data.data_loader import load_ticker_data
from backend.strategies.implementations import (
    BuyAndHoldStrategy,
    MACrossoverStrategy,
    TrendFollowing50_200Strategy,
    RSIStrategy,
    MACDStrategy,
    BollingerBandsStrategy,
    VolatilityFilterStrategy
)
from backend.backtesting.engine import BacktestEngine
from backend.metrics.calculator import calculate_performance_metrics
from backend.optimization.grid_search import run_grid_search
from backend.visualization.charts import (
    generate_price_chart,
    generate_equity_curve_chart,
    generate_drawdown_chart,
    generate_monthly_heatmap
)

# ReportLab imports for PDF export
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

logger = logging.getLogger(__name__)
router = APIRouter()

STRATEGY_MAP = {
    "Buy & Hold": BuyAndHoldStrategy,
    "MA Crossover": MACrossoverStrategy,
    "50-200 Trend Following": TrendFollowing50_200Strategy,
    "RSI Strategy": RSIStrategy,
    "MACD Strategy": MACDStrategy,
    "Bollinger Bands": BollingerBandsStrategy,
    "Volatility Filter": VolatilityFilterStrategy
}

def parse_weights_str(weights_str: Optional[str]) -> Optional[Dict[str, float]]:
    if not weights_str:
        return None
    try:
        return json.loads(weights_str)
    except Exception:
        try:
            d = {}
            for item in weights_str.split(","):
                k, v = item.split(":")
                d[k.strip()] = float(v.strip())
            return d
        except Exception:
            return None

# ==========================================
# Pydantic Request Models
# ==========================================
class BacktestRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    interval: str = "1d"
    strategy_name: str
    strategy_params: Optional[Dict[str, Any]] = None
    initial_cash: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    risk_free_rate: float = 0.06
    weights: Optional[Dict[str, float]] = None
    trailing_stop_pct: float = 0.0
    use_atr_sizing: bool = False
    risk_pct: float = 0.02
    atr_multiplier: float = 2.0

class OptimizeRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    interval: str = "1d"
    strategy_name: str
    param_ranges: Dict[str, List[Any]]
    metric_to_optimize: str = "sharpe_ratio"
    risk_free_rate: float = 0.06

class CompareStrategyConfig(BaseModel):
    name: str
    params: Optional[Dict[str, Any]] = None

class CompareRequest(BaseModel):
    ticker: str
    start_date: str
    end_date: str
    interval: str = "1d"
    strategies: List[CompareStrategyConfig]
    initial_cash: float = 100000.0
    commission_rate: float = 0.001
    slippage_rate: float = 0.0005
    risk_free_rate: float = 0.06

# ==========================================
# Core Helper Logic
# ==========================================
def execute_single_backtest(req: BacktestRequest) -> Dict[str, Any]:
    """Helper to run a single backtest and compute metrics/charts."""
    if req.strategy_name not in STRATEGY_MAP:
        raise ValueError(f"Strategy '{req.strategy_name}' is not supported.")
        
    # 1. Parse tickers and weights from the ticker string
    tickers = []
    weights_dict = {}
    has_colons = False
    
    for item in req.ticker.split(","):
        item = item.strip()
        if not item:
            continue
        if ":" in item:
            has_colons = True
            tk, wt = item.split(":")
            tk = tk.strip()
            tickers.append(tk)
            weights_dict[tk] = float(wt.strip())
        else:
            tickers.append(item)
            
    if not tickers:
        raise ValueError("No valid tickers provided.")
        
    # 2. Fetch Data for all tickers
    from backend.data.data_loader import load_multiple_tickers_data
    dfs = load_multiple_tickers_data(tickers, req.start_date, req.end_date, req.interval)
    
    # 3. Instantiate Strategy and Generate Signals for each asset
    strat_class = STRATEGY_MAP[req.strategy_name]
    strategy_inst = strat_class(params=req.strategy_params)
    
    dfs_signals = {}
    for tk, df in dfs.items():
        dfs_signals[tk] = strategy_inst.generate_signals(df)
        
    # 4. Parse weights if not specified inline
    if not has_colons:
        if req.weights:
            weights_dict = req.weights
        elif len(tickers) > 1:
            # Default equal weights
            weights_dict = {tk: 1.0 / len(tickers) for tk in tickers}
        
    # 5. Run Backtest
    engine = BacktestEngine(
        initial_cash=req.initial_cash,
        commission_rate=req.commission_rate,
        slippage_rate=req.slippage_rate,
        risk_free_rate=req.risk_free_rate,
        trailing_stop_pct=req.trailing_stop_pct,
        use_atr_sizing=req.use_atr_sizing,
        risk_pct=req.risk_pct,
        atr_multiplier=req.atr_multiplier
    )
    res = engine.run(dfs_signals, weights=weights_dict)
    daily_df = res["daily_series"]
    trade_log = res["trade_log"]
    
    # 6. Compute Metrics
    perf_metrics = calculate_performance_metrics(daily_df, trade_log, req.risk_free_rate)
    
    return {
        "daily_series": daily_df,
        "trade_log": trade_log,
        "metrics": perf_metrics,
        "dfs": dfs_signals
    }

# ==========================================
# API Route Endpoints
# ==========================================
@router.post("/backtest")
def run_backtest(req: BacktestRequest):
    try:
        res = execute_single_backtest(req)
        daily_df = res["daily_series"]
        trade_log = res["trade_log"]
        metrics = res["metrics"]
        
        # Generate Plotly Chart JSONs
        price_chart = generate_price_chart(daily_df, trade_log, req.ticker, dfs=res["dfs"])
        equity_chart = generate_equity_curve_chart(daily_df)
        drawdown_chart = generate_drawdown_chart(daily_df)
        heatmap_chart = generate_monthly_heatmap(daily_df)
        
        # Run Monte Carlo simulation & generate chart
        from backend.metrics.calculator import run_monte_carlo_simulation
        from backend.visualization.charts import generate_monte_carlo_chart
        mc_data = run_monte_carlo_simulation(daily_df, req.initial_cash)
        mc_chart = generate_monte_carlo_chart(mc_data)
        
        return {
            "status": "success",
            "ticker": req.ticker,
            "strategy": req.strategy_name,
            "metrics": metrics,
            "trade_log": trade_log,
            "monte_carlo_stats": mc_data["stats"],
            "charts": {
                "price": price_chart,
                "equity": equity_chart,
                "drawdown": drawdown_chart,
                "heatmap": heatmap_chart,
                "monte_carlo": mc_chart
            }
        }
    except Exception as e:
        logger.exception("Error running backtest endpoint")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/optimize")
def run_optimization(req: OptimizeRequest):
    try:
        if req.strategy_name not in STRATEGY_MAP:
            raise ValueError(f"Strategy '{req.strategy_name}' is not supported.")
            
        df = load_ticker_data(req.ticker, req.start_date, req.end_date, req.interval)
        strat_class = STRATEGY_MAP[req.strategy_name]
        
        results = run_grid_search(
            df=df,
            strategy_class=strat_class,
            param_ranges=req.param_ranges,
            metric_to_optimize=req.metric_to_optimize,
            risk_free_rate=req.risk_free_rate
        )
        return {
            "status": "success",
            "ticker": req.ticker,
            "strategy": req.strategy_name,
            "optimization": results
        }
    except Exception as e:
        logger.exception("Error running optimization endpoint")
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/compare")
def compare_strategies(req: CompareRequest):
    try:
        tickers = []
        weights_dict = {}
        has_colons = False
        for item in req.ticker.split(","):
            item = item.strip()
            if not item:
                continue
            if ":" in item:
                has_colons = True
                tk, wt = item.split(":")
                tk = tk.strip()
                tickers.append(tk)
                weights_dict[tk] = float(wt.strip())
            else:
                tickers.append(item)
                
        if not tickers:
            raise ValueError("No valid tickers provided.")
            
        from backend.data.data_loader import load_multiple_tickers_data
        dfs = load_multiple_tickers_data(tickers, req.start_date, req.end_date, req.interval)
        
        if not has_colons:
            weights_dict = {tk: 1.0 / len(tickers) for tk in tickers}
        
        import plotly.graph_objects as go
        from backend.visualization.charts import apply_dark_theme, STRATEGY_COLOR, BENCHMARK_COLOR
        
        fig = go.Figure()
        comparison_results = {}
        
        # Color palettes for multiple strategies
        color_palette = ["#00e676", "#ffb300", "#d500f9", "#ff1744", "#1de9b6", "#3d5afe"]
        
        engine = BacktestEngine(
            initial_cash=req.initial_cash,
            commission_rate=req.commission_rate,
            slippage_rate=req.slippage_rate,
            risk_free_rate=req.risk_free_rate
        )
        
        # Loop through each strategy config
        for idx, strat_cfg in enumerate(req.strategies):
            if strat_cfg.name not in STRATEGY_MAP:
                continue
                
            strat_class = STRATEGY_MAP[strat_cfg.name]
            strat_inst = strat_class(params=strat_cfg.params)
            
            dfs_signals = {}
            for tk, d in dfs.items():
                dfs_signals[tk] = strat_inst.generate_signals(d)
                
            res = engine.run(dfs_signals, weights=weights_dict)
            daily_df = res["daily_series"]
            trade_log = res["trade_log"]
            
            metrics = calculate_performance_metrics(daily_df, trade_log, req.risk_free_rate)
            comparison_results[strat_cfg.name] = metrics["strategy"]
            
            # Save Buy & Hold metrics once
            if "Buy & Hold Benchmark" not in comparison_results:
                comparison_results["Buy & Hold Benchmark"] = metrics["buy_hold"]
                
                # Add Buy & Hold curve to chart
                fig.add_trace(go.Scatter(
                    x=daily_df.index,
                    y=daily_df["BuyHoldValue"],
                    mode="lines",
                    name="Buy & Hold Benchmark",
                    line=dict(color=BENCHMARK_COLOR, width=1.5, dash="dot")
                ))
            
            # Add this strategy's equity curve to the chart
            color = color_palette[idx % len(color_palette)]
            fig.add_trace(go.Scatter(
                x=daily_df.index,
                y=daily_df["PortfolioValue"],
                mode="lines",
                name=strat_cfg.name,
                line=dict(color=color, width=2.0)
            ))
            
        apply_dark_theme(fig, "Strategy Comparison - Portfolio Values")
        fig.update_layout(yaxis=dict(title="Portfolio Value ($)"))
        
        return {
            "status": "success",
            "ticker": req.ticker,
            "metrics": comparison_results,
            "chart": json.loads(pio.to_json(fig))
        }
    except Exception as e:
        logger.exception("Error running compare endpoint")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/export/csv")
def export_csv(
    ticker: str,
    start_date: str,
    end_date: str,
    strategy_name: str,
    interval: str = "1d",
    risk_free_rate: float = 0.06,
    trailing_stop_pct: float = 0.0,
    use_atr_sizing: bool = False,
    risk_pct: float = 0.02,
    atr_multiplier: float = 2.0,
    weights: Optional[str] = None
):
    try:
        req = BacktestRequest(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            strategy_name=strategy_name,
            interval=interval,
            risk_free_rate=risk_free_rate,
            trailing_stop_pct=trailing_stop_pct,
            use_atr_sizing=use_atr_sizing,
            risk_pct=risk_pct,
            atr_multiplier=atr_multiplier,
            weights=parse_weights_str(weights)
        )
        res = execute_single_backtest(req)
        trade_log = res["trade_log"]
        
        # Build CSV stream
        output = io.StringIO()
        writer = csv.writer(output)
        
        # Determine if trade log has tickers
        has_tickers = any("Ticker" in t and t["Ticker"] for t in trade_log)
        
        if has_tickers:
            writer.writerow(["Date", "Ticker", "Action", "Price", "Shares", "Value", "TransactionCost", "CashAfter", "PortfolioValueAfter", "ExposureAfter"])
            for trade in trade_log:
                writer.writerow([
                    trade["Date"],
                    trade.get("Ticker", ""),
                    trade["Action"],
                    trade["Price"],
                    trade["Shares"],
                    trade["Value"],
                    trade["TransactionCost"],
                    trade["CashAfter"],
                    trade["PortfolioValueAfter"],
                    trade["ExposureAfter"]
                ])
        else:
            writer.writerow(["Date", "Action", "Price", "Shares", "Value", "TransactionCost", "CashAfter", "PortfolioValueAfter", "ExposureAfter"])
            for trade in trade_log:
                writer.writerow([
                    trade["Date"],
                    trade["Action"],
                    trade["Price"],
                    trade["Shares"],
                    trade["Value"],
                    trade["TransactionCost"],
                    trade["CashAfter"],
                    trade["PortfolioValueAfter"],
                    trade["ExposureAfter"]
                ])
            
        output.seek(0)
        filename = f"{ticker.replace(',', '_')}_{strategy_name.replace(' ', '_')}_trade_log.csv"
        
        return StreamingResponse(
            io.BytesIO(output.getvalue().encode("utf-8")),
            media_type="text/csv",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.exception("Error exporting CSV")
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/export/pdf")
def export_pdf(
    ticker: str,
    start_date: str,
    end_date: str,
    strategy_name: str,
    interval: str = "1d",
    risk_free_rate: float = 0.06,
    trailing_stop_pct: float = 0.0,
    use_atr_sizing: bool = False,
    risk_pct: float = 0.02,
    atr_multiplier: float = 2.0,
    weights: Optional[str] = None
):
    try:
        req = BacktestRequest(
            ticker=ticker,
            start_date=start_date,
            end_date=end_date,
            strategy_name=strategy_name,
            interval=interval,
            risk_free_rate=risk_free_rate,
            trailing_stop_pct=trailing_stop_pct,
            use_atr_sizing=use_atr_sizing,
            risk_pct=risk_pct,
            atr_multiplier=atr_multiplier,
            weights=parse_weights_str(weights)
        )
        res = execute_single_backtest(req)
        trade_log = res["trade_log"]
        metrics = res["metrics"]
        
        # Build PDF Document using ReportLab
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
        styles = getSampleStyleSheet()
        
        # Custom Typography Styles
        title_style = ParagraphStyle(
            name="TitleStyle",
            parent=styles["Title"],
            fontSize=22,
            leading=26,
            textColor=colors.HexColor("#1b1b1b")
        )
        header_style = ParagraphStyle(
            name="HeaderStyle",
            parent=styles["Heading2"],
            fontSize=14,
            leading=18,
            textColor=colors.HexColor("#2a3b4c"),
            spaceBefore=12,
            spaceAfter=6
        )
        body_style = ParagraphStyle(
            name="BodyStyle",
            parent=styles["BodyText"],
            fontSize=10,
            leading=14,
            textColor=colors.HexColor("#333333")
        )
        
        story = []
        
        story.append(Paragraph("Quantlab Research Platform - Performance Report", title_style))
        story.append(Spacer(1, 15))
        
        # Meta Info
        meta_text = (
            f"<b>Ticker</b>: {ticker}<br/>"
            f"<b>Strategy</b>: {strategy_name}<br/>"
            f"<b>Interval</b>: {interval}<br/>"
            f"<b>Date Range</b>: {start_date} to {end_date}<br/>"
            f"<b>Risk Free Rate</b>: {risk_free_rate * 100:.1f}% Annual<br/>"
            f"<b>Trailing Stop</b>: {trailing_stop_pct * 100:.1f}%<br/>"
            f"<b>ATR Sizing</b>: {'Enabled (Risk ' + str(risk_pct*100) + '%, Mult ' + str(atr_multiplier) + ')' if use_atr_sizing else 'Disabled'}"
        )
        story.append(Paragraph(meta_text, body_style))
        story.append(Spacer(1, 15))
        
        # Summary Metrics Table
        story.append(Paragraph("Performance Metrics Summary", header_style))
        
        strat_m = metrics["strategy"]
        bh_m = metrics["buy_hold"]
        
        metrics_data = [
            ["Metric", "Risk Overlay Strategy", "Buy & Hold Benchmark"],
            ["Total Return", f"{strat_m['total_return']}%", f"{bh_m['total_return']}%"],
            ["CAGR", f"{strat_m['cagr']}%", f"{bh_m['cagr']}%"],
            ["Volatility (Ann)", f"{strat_m['annualized_volatility']}%", f"{bh_m['annualized_volatility']}%"],
            ["Sharpe Ratio", f"{strat_m['sharpe_ratio']}", f"{bh_m['sharpe_ratio']}"],
            ["Sortino Ratio", f"{strat_m['sortino_ratio']}", f"{bh_m['sortino_ratio']}"],
            ["Max Drawdown", f"{strat_m['max_drawdown']}%", f"{bh_m['max_drawdown']}%"],
            ["Win Rate (Daily)", f"{strat_m['win_rate_daily']}%", f"{bh_m['win_rate_daily']}%"],
            ["Profit Factor", f"{strat_m['profit_factor']}", f"{bh_m['profit_factor']}"],
            ["Average Exposure", f"{strat_m['average_exposure']}%", "100.00%"],
            ["Total Executed Trades", f"{strat_m['total_trades']}", "N/A"]
        ]
        
        metrics_table = Table(metrics_data, colWidths=[200, 160, 160])
        metrics_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#2a3b4c")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 6),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('BACKGROUND', (0,1), (-1,-1), colors.HexColor("#f8f9fa")),
            ('FONTNAME', (0,1), (-1,-1), 'Helvetica'),
            ('FONTSIZE', (0,0), (-1,-1), 9),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f1f3f5")]),
        ]))
        story.append(metrics_table)
        story.append(Spacer(1, 20))
        
        # Recent Trades Table
        story.append(Paragraph("Trade Log (Recent Trades)", header_style))
        
        has_tickers = any("Ticker" in t and t["Ticker"] for t in trade_log)
        displayed_trades = trade_log[-20:]
        
        if has_tickers:
            trade_data = [["Date", "Ticker", "Action", "Price", "Shares", "Value ($)", "Tx Cost ($)"]]
            col_widths = [80, 50, 60, 80, 80, 90, 90]
            for trade in displayed_trades:
                trade_data.append([
                    trade["Date"],
                    trade.get("Ticker", ""),
                    trade["Action"],
                    f"${trade['Price']}",
                    f"{trade['Shares']}",
                    f"${trade['Value']}",
                    f"${trade['TransactionCost']}"
                ])
        else:
            trade_data = [["Date", "Action", "Price", "Shares", "Value ($)", "Tx Cost ($)"]]
            col_widths = [90, 70, 90, 90, 95, 95]
            for trade in displayed_trades:
                trade_data.append([
                    trade["Date"],
                    trade["Action"],
                    f"${trade['Price']}",
                    f"{trade['Shares']}",
                    f"${trade['Value']}",
                    f"${trade['TransactionCost']}"
                ])
                
        if len(trade_log) == 0:
            cols_count = 7 if has_tickers else 6
            trade_data.append(["No trades executed during this period."] + [""] * (cols_count - 1))
            
        trade_table = Table(trade_data, colWidths=col_widths)
        trade_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,0), colors.HexColor("#4a5a6a")),
            ('TEXTCOLOR', (0,0), (-1,0), colors.whitesmoke),
            ('ALIGN', (0,0), (-1,-1), 'LEFT'),
            ('FONTNAME', (0,0), (-1,0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0,0), (-1,0), 5),
            ('GRID', (0,0), (-1,-1), 0.5, colors.grey),
            ('FONTSIZE', (0,0), (-1,-1), 8),
            ('ROWBACKGROUNDS', (0,1), (-1,-1), [colors.white, colors.HexColor("#f8f9fa")]),
        ]))
        story.append(trade_table)
        
        if len(trade_log) > 20:
            story.append(Spacer(1, 5))
            story.append(Paragraph(f"<i>* Showing last 20 trades of {len(trade_log)} total trades. Download trade log CSV for full records.</i>", body_style))
            
        # Build document
        doc.build(story)
        buffer.seek(0)
        
        filename = f"{ticker.replace(',', '_')}_{strategy_name.replace(' ', '_')}_report.pdf"
        
        return Response(
            buffer.getvalue(),
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename={filename}"}
        )
    except Exception as e:
        logger.exception("Error exporting PDF")
        raise HTTPException(status_code=400, detail=str(e))
