// API Base URL config
const API_BASE_URL = "http://localhost:8000/api";

// Page Descriptions
const PAGE_INFO = {
    home: { title: "Quantitative Research Platform", subtitle: "Historical analysis & parameter optimization engine" },
    backtest: { title: "Strategy Tester", subtitle: "Test and optimize individual algorithms" },
    comparison: { title: "Strategy Comparison Mode", subtitle: "Compare multiple strategy performance profiles side-by-side" },
    sessions: { title: "Saved Sessions", subtitle: "Access your local historical research runs" },
    about: { title: "About QuantLab", subtitle: "Platform documentation & architectural notes" }
};

// Map of Strategy parameter templates for Dynamic Render
const STRATEGY_PARAMS_MAP = {
    "Buy & Hold": {},
    "MA Crossover": {
        "fast_period": { label: "Fast MA Period", type: "number", default: 50 },
        "slow_period": { label: "Slow MA Period", type: "number", default: 200 }
    },
    "50-200 Trend Following": {
        "ma50_period": { label: "MA 50 Period", type: "number", default: 50 },
        "ma200_period": { label: "MA 200 Period", type: "number", default: 200 }
    },
    "RSI Strategy": {
        "rsi_period": { label: "RSI Period", type: "number", default: 14 },
        "oversold_threshold": { label: "Oversold Threshold (Buy)", type: "number", default: 30 },
        "overbought_threshold": { label: "Overbought Threshold (Sell)", type: "number", default: 70 }
    },
    "MACD Strategy": {
        "fast_period": { label: "Fast EMA Period", type: "number", default: 12 },
        "slow_period": { label: "Slow EMA Period", type: "number", default: 26 },
        "signal_period": { label: "Signal EMA Period", type: "number", default: 9 }
    },
    "Bollinger Bands": {
        "period": { label: "SMA Period", type: "number", default: 20 },
        "num_std": { label: "Num Standard Dev.", type: "number", default: 2 }
    },
    "Volatility Filter": {
        "ma_period": { label: "Base MA Period", type: "number", default: 50 },
        "vol_period": { label: "Volatility Period (Days)", type: "number", default: 20 },
        "vol_threshold": { label: "Annual Vol Threshold", type: "number", default: 0.25 }
    }
};

// Global states
let lastRunResults = null;
let lastRunInputs = null;
let currentChartTab = "price";

// Initialize page
document.addEventListener("DOMContentLoaded", () => {
    setupNavigation();
    renderStrategyParams();
    loadSessionsList();
});

// ==========================================
// NAVIGATION & PAGE SWITCHING
// ==========================================
function setupNavigation() {
    const menuItems = document.querySelectorAll(".menu-item");
    menuItems.forEach(item => {
        item.addEventListener("click", (e) => {
            e.preventDefault();
            const targetPage = item.getAttribute("data-page");
            switchPage(targetPage);
            
            // Update active menu link
            menuItems.forEach(mi => mi.classList.remove("active"));
            item.classList.add("active");
        });
    });
}

function switchPage(pageId) {
    // Hide all sections
    const sections = document.querySelectorAll(".page-section");
    sections.forEach(sec => sec.classList.remove("active"));
    
    // Show target section
    const targetSection = document.getElementById(`page-${pageId}`);
    if (targetSection) {
        targetSection.classList.add("active");
    }
    
    // Update titles
    const info = PAGE_INFO[pageId];
    if (info) {
        document.getElementById("page-title").innerText = info.title;
        document.getElementById("page-subtitle").innerText = info.subtitle;
    }
    
    if (pageId === "sessions") {
        loadSessionsList();
    }
}

// ==========================================
// DYNAMIC STRATEGY PARAMETERS
// ==========================================
function renderStrategyParams() {
    const selectedStrat = document.getElementById("input-strategy").value;
    const container = document.getElementById("strategy-params-inputs");
    container.innerHTML = "";
    
    const params = STRATEGY_PARAMS_MAP[selectedStrat];
    if (Object.keys(params).length === 0) {
        container.innerHTML = '<p class="text-secondary" style="font-size: 12px; font-style: italic;">No parameters needed for this strategy.</p>';
        return;
    }
    
    let html = '<div class="form-row">';
    let counter = 0;
    
    for (const [key, config] of Object.entries(params)) {
        if (counter > 0 && counter % 2 === 0) {
            html += '</div><div class="form-row">';
        }
        
        html += `
            <div class="form-group">
                <label for="param-${key}">${config.label}</label>
                <input type="${config.type}" id="param-${key}" value="${config.default}" step="${config.default % 1 === 0 ? 1 : 0.01}">
            </div>
        `;
        counter++;
    }
    
    html += '</div>';
    container.innerHTML = html;
}

function toggleAtrInputs() {
    const atrParamsDiv = document.getElementById("atr-sizing-params");
    const useAtrCheckbox = document.getElementById("input-use-atr-sizing");
    if (useAtrCheckbox.checked) {
        atrParamsDiv.classList.remove("hide");
    } else {
        atrParamsDiv.classList.add("hide");
    }
}

function getSelectedStrategyParams() {
    const selectedStrat = document.getElementById("input-strategy").value;
    const schema = STRATEGY_PARAMS_MAP[selectedStrat];
    const params = {};
    
    for (const key in schema) {
        const inputEl = document.getElementById(`param-${key}`);
        if (inputEl) {
            const val = parseFloat(inputEl.value);
            params[key] = isNaN(val) ? inputEl.value : val;
        }
    }
    return params;
}

// ==========================================
// RUN BACKTEST
// ==========================================
async function runBacktest() {
    // UI Updates
    document.getElementById("backtest-loader").classList.remove("hide");
    document.getElementById("backtest-results").classList.add("hide");
    document.getElementById("optimization-results").classList.add("hide");
    
    // Gather inputs
    const inputs = {
        ticker: document.getElementById("input-ticker").value.toUpperCase().trim(),
        start_date: document.getElementById("input-start-date").value,
        end_date: document.getElementById("input-end-date").value,
        interval: document.getElementById("input-interval").value,
        strategy_name: document.getElementById("input-strategy").value,
        strategy_params: getSelectedStrategyParams(),
        initial_cash: parseFloat(document.getElementById("input-cash").value),
        commission_rate: parseFloat(document.getElementById("input-commission").value) / 100,
        slippage_rate: parseFloat(document.getElementById("input-slippage").value) / 100,
        risk_free_rate: parseFloat(document.getElementById("input-rf").value) / 100,
        trailing_stop_pct: parseFloat(document.getElementById("input-trailing-stop").value) / 100,
        use_atr_sizing: document.getElementById("input-use-atr-sizing").checked,
        risk_pct: parseFloat(document.getElementById("input-risk-pct").value) / 100,
        atr_multiplier: parseFloat(document.getElementById("input-atr-mult").value)
    };
    
    lastRunInputs = inputs;
    
    try {
        const response = await fetch(`${API_BASE_URL}/backtest`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(inputs)
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Failed to execute backtest");
        }
        
        const data = await response.json();
        lastRunResults = data;
        
        // Hide loader & show results panel
        document.getElementById("backtest-loader").classList.add("hide");
        document.getElementById("backtest-results").classList.remove("hide");
        
        // Populate stats cards
        populateStats(data.metrics);
        
        // Render Plotly charts
        Plotly.newPlot("chart-price", data.charts.price.data, data.charts.price.layout);
        Plotly.newPlot("chart-equity", data.charts.equity.data, data.charts.equity.layout);
        Plotly.newPlot("chart-drawdown", data.charts.drawdown.data, data.charts.drawdown.layout);
        Plotly.newPlot("chart-heatmap", data.charts.heatmap.data, data.charts.heatmap.layout);
        
        // Render Monte Carlo chart
        if (data.charts.monte_carlo) {
            Plotly.newPlot("plotly-mc-chart", data.charts.monte_carlo.data, data.charts.monte_carlo.layout);
        }
        
        // Populate Monte Carlo stats
        if (data.monte_carlo_stats) {
            const mc = data.monte_carlo_stats;
            document.getElementById("stat-mc-prob-loss").innerText = `${mc.prob_loss}%`;
            document.getElementById("stat-mc-var").innerText = `${mc.var_95}%`;
            document.getElementById("stat-mc-cvar").innerText = `${mc.cvar_95}%`;
            document.getElementById("stat-mc-median").innerText = `$${mc.median_terminal_value.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}`;
        }
        
        // Re-align layouts dynamically
        switchChartTab(currentChartTab);
        
        // Populate Trade Logs
        populateTradeLog(data.trade_log);
        
    } catch (error) {
        document.getElementById("backtest-loader").classList.add("hide");
        alert(`Backtest Error: ${error.message}`);
        console.error(error);
    }
}

function populateStats(metrics) {
    const strat = metrics.strategy;
    const bh = metrics.buy_hold;
    
    // Total Return
    const stratRetEl = document.getElementById("stat-strat-return");
    stratRetEl.innerText = `${strat.total_return}%`;
    stratRetEl.className = strat.total_return >= 0 ? "green-text" : "red-text";
    document.getElementById("stat-bh-return").innerText = `Buy & Hold: ${bh.total_return}%`;
    
    // CAGR
    const cagrEl = document.getElementById("stat-strat-cagr");
    cagrEl.innerText = `${strat.cagr}%`;
    cagrEl.className = strat.cagr >= 0 ? "green-text" : "red-text";
    document.getElementById("stat-bh-cagr").innerText = `Buy & Hold: ${bh.cagr}%`;
    
    // Max DD
    document.getElementById("stat-strat-dd").innerText = `${strat.max_drawdown}%`;
    document.getElementById("stat-bh-dd").innerText = `Buy & Hold: ${bh.max_drawdown}%`;
    
    // Sharpe Ratio
    const sharpeEl = document.getElementById("stat-strat-sharpe");
    sharpeEl.innerText = strat.sharpe_ratio.toFixed(2);
    sharpeEl.className = strat.sharpe_ratio >= 1.0 ? "green-text" : strat.sharpe_ratio < 0.0 ? "red-text" : "text-primary";
    document.getElementById("stat-bh-sharpe").innerText = `Buy & Hold: ${bh.sharpe_ratio.toFixed(2)}`;
}

function switchChartTab(tabName) {
    currentChartTab = tabName;
    
    // Toggle active tab buttons
    const tabs = document.querySelectorAll(".tab-header");
    tabs.forEach(tab => {
        // Adjust matching for 'monte_carlo' -> 'monte' or 'mc'
        const matchName = tabName === 'monte_carlo' ? 'monte' : tabName.substring(0, 3);
        if (tab.innerText.toLowerCase().includes(matchName)) {
            tab.classList.add("active");
        } else {
            tab.classList.remove("active");
        }
    });
    
    // Toggle active chart windows
    const windows = document.querySelectorAll(".chart-window");
    windows.forEach(win => {
        if (win.id === `chart-${tabName}`) {
            win.classList.add("active");
            // Trigger Plotly resize layout adjustment
            if (tabName === 'monte_carlo') {
                Plotly.Plots.resize(document.getElementById("plotly-mc-chart"));
            } else {
                Plotly.Plots.resize(win);
            }
        } else {
            win.classList.remove("active");
        }
    });
}

function populateTradeLog(tradeLog) {
    const tbody = document.getElementById("trade-log-body");
    tbody.innerHTML = "";
    
    if (tradeLog.length === 0) {
        tbody.innerHTML = '<tr><td colspan="8" style="text-align: center; color: var(--text-secondary);">No trades executed by this strategy during this timeframe.</td></tr>';
        return;
    }
    
    // Render last 100 trades to prevent DOM slowdown on large backtests
    const maxRender = Math.min(tradeLog.length, 100);
    for (let i = 0; i < maxRender; i++) {
        const trade = tradeLog[i];
        const row = document.createElement("tr");
        
        row.innerHTML = `
            <td>${trade.Date}</td>
            <td class="${trade.Action === 'BUY' ? 'green-text' : 'red-text'}" style="font-weight: 600;">${trade.Action}</td>
            <td>$${trade.Price.toFixed(2)}</td>
            <td>${trade.Shares}</td>
            <td>$${trade.Value.toLocaleString()}</td>
            <td>$${trade.TransactionCost.toFixed(2)}</td>
            <td>$${trade.CashAfter.toLocaleString()}</td>
            <td>${(trade.ExposureAfter * 100).toFixed(0)}%</td>
        `;
        tbody.appendChild(row);
    }
    
    if (tradeLog.length > 100) {
        const spacerRow = document.createElement("tr");
        spacerRow.innerHTML = `<td colspan="8" style="text-align: center; color: var(--text-secondary); font-style: italic;">Showing first 100 of ${tradeLog.length} trades total. Download CSV log to view all trades.</td>`;
        tbody.appendChild(spacerRow);
    }
}

// ==========================================
// EXPORTS & REPORTS
// ==========================================
function exportCSV() {
    if (!lastRunInputs) return;
    const p = lastRunInputs;
    const url = `${API_BASE_URL}/export/csv?ticker=${p.ticker}&start_date=${p.start_date}&end_date=${p.end_date}&strategy_name=${encodeURIComponent(p.strategy_name)}&interval=${p.interval}&risk_free_rate=${p.risk_free_rate}&trailing_stop_pct=${p.trailing_stop_pct}&use_atr_sizing=${p.use_atr_sizing}&risk_pct=${p.risk_pct}&atr_multiplier=${p.atr_multiplier}`;
    window.location.href = url;
}

function exportPDF() {
    if (!lastRunInputs) return;
    const p = lastRunInputs;
    const url = `${API_BASE_URL}/export/pdf?ticker=${p.ticker}&start_date=${p.start_date}&end_date=${p.end_date}&strategy_name=${encodeURIComponent(p.strategy_name)}&interval=${p.interval}&risk_free_rate=${p.risk_free_rate}&trailing_stop_pct=${p.trailing_stop_pct}&use_atr_sizing=${p.use_atr_sizing}&risk_pct=${p.risk_pct}&atr_multiplier=${p.atr_multiplier}`;
    window.location.href = url;
}

// ==========================================
// STRATEGY OPTIMIZATION
// ==========================================
async function runOptimization() {
    document.getElementById("backtest-loader").classList.remove("hide");
    document.getElementById("backtest-results").classList.add("hide");
    document.getElementById("optimization-results").classList.add("hide");
    
    const selectedStrat = document.getElementById("input-strategy").value;
    
    // Build default parameter ranges for grid search
    let paramRanges = {};
    if (selectedStrat === "MA Crossover") {
        paramRanges = {
            "fast_period": [10, 20, 30, 50],
            "slow_period": [100, 150, 200, 250]
        };
    } else if (selectedStrat === "50-200 Trend Following") {
        paramRanges = {
            "ma50_period": [20, 30, 50, 70],
            "ma200_period": [150, 200, 250]
        };
    } else if (selectedStrat === "RSI Strategy") {
        paramRanges = {
            "rsi_period": [10, 14, 20],
            "oversold_threshold": [25, 30, 35],
            "overbought_threshold": [65, 70, 75]
        };
    } else {
        document.getElementById("backtest-loader").classList.add("hide");
        alert("Parameter Optimization is only configured for: MA Crossover, 50-200 Trend Following, or RSI Strategy.");
        return;
    }
    
    const inputs = {
        ticker: document.getElementById("input-ticker").value.toUpperCase().trim(),
        start_date: document.getElementById("input-start-date").value,
        end_date: document.getElementById("input-end-date").value,
        interval: document.getElementById("input-interval").value,
        strategy_name: selectedStrat,
        param_ranges: paramRanges,
        metric_to_optimize: "sharpe_ratio",
        risk_free_rate: parseFloat(document.getElementById("input-rf").value) / 100
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/optimize`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(inputs)
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Optimization failed");
        }
        
        const data = await response.json();
        const opt = data.optimization;
        
        document.getElementById("backtest-loader").classList.add("hide");
        document.getElementById("optimization-results").classList.remove("hide");
        
        // Update stats
        document.getElementById("stat-opt-best-params").innerText = JSON.stringify(opt.best_params);
        document.getElementById("stat-opt-best-val").innerText = opt.best_value.toFixed(2);
        
        // Render Heatmap if two dimensions exist
        if (opt.heatmap_data && opt.heatmap_data.length > 0) {
            const xVal = opt.heatmap_data.map(h => h.x);
            const yVal = opt.heatmap_data.map(h => h.y);
            const zVal = opt.heatmap_data.map(h => h.z);
            
            const heatmapTrace = {
                type: "heatmap",
                x: xVal,
                y: yVal,
                z: zVal,
                colorscale: "Viridis",
                colorbar: { title: "Sharpe Ratio" },
                hovertemplate: `${opt.parameters_searched[0]}: %{x}<br>${opt.parameters_searched[1]}: %{y}<br>Metric: %{z:.2f}<extra></extra>`
            };
            
            const layout = {
                title: "Hyperparameter Sharpe Ratio Heatmap",
                paper_bgcolor: "rgba(0,0,0,0)",
                plot_bgcolor: "rgba(0,0,0,0)",
                font: { color: "#e0e0e0" },
                xaxis: { title: opt.parameters_searched[0], gridcolor: "#333" },
                yaxis: { title: opt.parameters_searched[1], gridcolor: "#333" }
            };
            
            Plotly.newPlot("chart-opt-heatmap", [heatmapTrace], layout);
        } else {
            document.getElementById("chart-opt-heatmap").innerHTML = '<p class="text-secondary" style="text-align: center; line-height: 100px;">Heatmap display requires exactly a 2-parameter optimization search space.</p>';
        }
        
        // Populate results table
        populateOptTable(opt.all_results, opt.parameters_searched);
        
    } catch (error) {
        document.getElementById("backtest-loader").classList.add("hide");
        alert(`Optimization Error: ${error.message}`);
        console.error(error);
    }
}

function populateOptTable(allResults, paramKeys) {
    const tbody = document.getElementById("opt-results-body");
    tbody.innerHTML = "";
    
    // Sort results by Sharpe ratio descending
    allResults.sort((a,b) => b.metrics.sharpe_ratio - a.metrics.sharpe_ratio);
    
    allResults.forEach(res => {
        const row = document.createElement("tr");
        
        const paramsLabel = Object.entries(res.params).map(([k,v]) => `${k}:${v}`).join(", ");
        
        row.innerHTML = `
            <td style="font-family: monospace;">${paramsLabel}</td>
            <td class="${res.metrics.sharpe_ratio >= 0 ? 'green-text' : 'red-text'}">${res.metrics.sharpe_ratio.toFixed(2)}</td>
            <td>${res.metrics.cagr}%</td>
            <td>${res.metrics.max_drawdown}%</td>
            <td>${res.metrics.profit_factor}</td>
            <td>${res.metrics.total_trades}</td>
        `;
        tbody.appendChild(row);
    });
}

// ==========================================
// STRATEGY COMPARISON MODE
// ==========================================
async function runComparison() {
    document.getElementById("compare-loader").classList.remove("hide");
    document.getElementById("compare-results").classList.add("hide");
    
    // Determine selected checkbox list
    const strategies = [];
    if (document.getElementById("compare-cfg-ma").checked) {
        strategies.push({ name: "MA Crossover", params: { fast_period: 50, slow_period: 200 } });
    }
    if (document.getElementById("compare-cfg-trend").checked) {
        strategies.push({ name: "50-200 Trend Following", params: { ma50_period: 50, ma200_period: 200 } });
    }
    if (document.getElementById("compare-cfg-rsi").checked) {
        strategies.push({ name: "RSI Strategy", params: { rsi_period: 14 } });
    }
    if (document.getElementById("compare-cfg-macd").checked) {
        strategies.push({ name: "MACD Strategy" });
    }
    if (document.getElementById("compare-cfg-bb").checked) {
        strategies.push({ name: "Bollinger Bands" });
    }
    if (document.getElementById("compare-cfg-vol").checked) {
        strategies.push({ name: "Volatility Filter" });
    }
    
    const inputs = {
        ticker: document.getElementById("compare-ticker").value.toUpperCase().trim(),
        start_date: document.getElementById("compare-start").value,
        end_date: document.getElementById("compare-end").value,
        interval: "1d",
        strategies: strategies,
        initial_cash: 100000.0,
        commission_rate: 0.001,
        slippage_rate: 0.0005,
        risk_free_rate: 0.06
    };
    
    try {
        const response = await fetch(`${API_BASE_URL}/compare`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(inputs)
        });
        
        if (!response.ok) {
            const err = await response.json();
            throw new Error(err.detail || "Comparison run failed");
        }
        
        const data = await response.json();
        
        document.getElementById("compare-loader").classList.add("hide");
        document.getElementById("compare-results").classList.remove("hide");
        
        // Render comparison equity curve chart
        Plotly.newPlot("chart-compare-equity", data.chart.data, data.chart.layout);
        
        // Populate comparison details table
        populateComparisonTable(data.metrics);
        
    } catch (error) {
        document.getElementById("compare-loader").classList.add("hide");
        alert(`Comparison Error: ${error.message}`);
        console.error(error);
    }
}

function populateComparisonTable(metrics) {
    const tbody = document.getElementById("compare-table-body");
    tbody.innerHTML = "";
    
    for (const [name, stats] of Object.entries(metrics)) {
        const row = document.createElement("tr");
        
        row.innerHTML = `
            <td style="font-weight: 600;">${name}</td>
            <td class="${stats.total_return >= 0 ? 'green-text' : 'red-text'}">${stats.total_return}%</td>
            <td class="${stats.cagr >= 0 ? 'green-text' : 'red-text'}">${stats.cagr}%</td>
            <td>${stats.annualized_volatility}%</td>
            <td style="font-weight: bold;">${stats.sharpe_ratio.toFixed(2)}</td>
            <td>${stats.sortino_ratio.toFixed(2)}</td>
            <td class="red-text">${stats.max_drawdown}%</td>
            <td>${stats.total_trades || "N/A"}</td>
        `;
        tbody.appendChild(row);
    }
}

// ==========================================
// LOCAL STORAGE SESSION SAVES
// ==========================================
function saveCurrentSession() {
    if (!lastRunResults || !lastRunInputs) {
        alert("Run a backtest strategy successfully first before saving the session.");
        return;
    }
    
    const sessionName = prompt("Enter a unique name for this research session:", `${lastRunInputs.ticker} - ${lastRunInputs.strategy_name}`);
    if (!sessionName) return;
    
    const sessionRecord = {
        id: Date.now(),
        name: sessionName,
        timestamp: new Date().toLocaleString(),
        inputs: lastRunInputs,
        metrics: lastRunResults.metrics
    };
    
    let saved = localStorage.getItem("quantlab_sessions");
    saved = saved ? JSON.parse(saved) : [];
    saved.push(sessionRecord);
    localStorage.setItem("quantlab_sessions", JSON.stringify(saved));
    
    alert("Research Session saved successfully to LocalStorage.");
}

function loadSessionsList() {
    const container = document.getElementById("sessions-list");
    const emptyMsg = document.getElementById("no-sessions-msg");
    container.innerHTML = "";
    
    let saved = localStorage.getItem("quantlab_sessions");
    saved = saved ? JSON.parse(saved) : [];
    
    if (saved.length === 0) {
        emptyMsg.classList.remove("hide");
        return;
    }
    
    emptyMsg.classList.add("hide");
    
    saved.forEach(session => {
        const card = document.createElement("div");
        card.className = "session-item-card";
        
        card.innerHTML = `
            <div class="session-item-header">
                <span>${session.name}</span>
                <small>${session.timestamp}</small>
            </div>
            <div class="session-item-body">
                <strong>Ticker</strong>: ${session.inputs.ticker} | <strong>Strategy</strong>: ${session.inputs.strategy_name}<br/>
                <strong>CAGR</strong>: ${session.metrics.strategy.cagr}% | <strong>Sharpe</strong>: ${session.metrics.strategy.sharpe_ratio.toFixed(2)} | <strong>Max DD</strong>: ${session.metrics.strategy.max_drawdown}%
            </div>
            <div class="session-item-actions">
                <button class="btn btn-secondary btn-block" style="padding: 6px;" onclick="loadSavedSessionInputs(${session.id})">
                    <i class="fa-solid fa-folder-open"></i> Load
                </button>
                <button class="btn btn-secondary btn-block" style="padding: 6px; color: var(--neon-red);" onclick="deleteSavedSession(${session.id})">
                    <i class="fa-solid fa-trash"></i> Delete
                </button>
            </div>
        `;
        container.appendChild(card);
    });
}

function loadSavedSessionInputs(sessionId) {
    let saved = localStorage.getItem("quantlab_sessions");
    saved = saved ? JSON.parse(saved) : [];
    const session = saved.find(s => s.id === sessionId);
    if (!session) return;
    
    // Populate controls on Strategy Tester page
    document.getElementById("input-ticker").value = session.inputs.ticker;
    document.getElementById("input-start-date").value = session.inputs.start_date;
    document.getElementById("input-end-date").value = session.inputs.end_date;
    document.getElementById("input-interval").value = session.inputs.interval;
    document.getElementById("input-strategy").value = session.inputs.strategy_name;
    document.getElementById("input-cash").value = session.inputs.initial_cash;
    document.getElementById("input-rf").value = (session.inputs.risk_free_rate * 100).toFixed(1);
    document.getElementById("input-commission").value = (session.inputs.commission_rate * 100).toFixed(2);
    document.getElementById("input-slippage").value = (session.inputs.slippage_rate * 100).toFixed(2);
    
    // Restore risk management parameters
    document.getElementById("input-trailing-stop").value = session.inputs.trailing_stop_pct ? (session.inputs.trailing_stop_pct * 100).toFixed(1) : "0";
    document.getElementById("input-use-atr-sizing").checked = session.inputs.use_atr_sizing || false;
    document.getElementById("input-risk-pct").value = session.inputs.risk_pct ? (session.inputs.risk_pct * 100).toFixed(1) : "2.0";
    document.getElementById("input-atr-mult").value = session.inputs.atr_multiplier || "2.0";
    toggleAtrInputs();
    
    // Re-render parameters input
    renderStrategyParams();
    
    // Fill dynamic params value
    for (const key in session.inputs.strategy_params) {
        const paramEl = document.getElementById(`param-${key}`);
        if (paramEl) {
            paramEl.value = session.inputs.strategy_params[key];
        }
    }
    
    // Switch Page
    switchPage("backtest");
    alert(`Loaded inputs for ${session.name}. Click 'Run Backtest' to execute strategy.`);
}

function deleteSavedSession(sessionId) {
    if (!confirm("Are you sure you want to delete this session?")) return;
    
    let saved = localStorage.getItem("quantlab_sessions");
    saved = saved ? JSON.parse(saved) : [];
    saved = saved.filter(s => s.id !== sessionId);
    localStorage.setItem("quantlab_sessions", JSON.stringify(saved));
    
    loadSessionsList();
}
