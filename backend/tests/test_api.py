import requests
import json

def test_api():
    base_url = "http://localhost:8000/api"
    
    # 1. Test Single Backtest
    backtest_payload = {
        "ticker": "AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",
        "strategy_name": "Buy & Hold",
        "initial_cash": 100000.0,
        "risk_free_rate": 0.06
    }
    
    print("Sending /api/backtest request...")
    res = requests.post(f"{base_url}/backtest", json=backtest_payload)
    print("Status code:", res.status_code)
    
    if res.status_code != 200:
        print("Failed with:", res.text)
        return False
        
    data = res.json()
    print("Response keys:", list(data.keys()))
    print("Metrics strategy return:", data["metrics"]["strategy"]["total_return"])
    print("Trades count:", len(data["trade_log"]))
    
    # 2. Test Compare Strategies
    compare_payload = {
        "ticker": "AAPL",
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",
        "strategies": [
            {"name": "Buy & Hold"},
            {"name": "MA Crossover", "params": {"fast_period": 5, "slow_period": 10}}
        ]
    }
    
    print("\nSending /api/compare request...")
    res_comp = requests.post(f"{base_url}/compare", json=compare_payload)
    print("Status code:", res_comp.status_code)
    if res_comp.status_code != 200:
        print("Failed with:", res_comp.text)
        return False
        
    comp_data = res_comp.json()
    print("Comparison metrics strategies:", list(comp_data["metrics"].keys()))
    
    # 3. Test Multi-Asset Backtest with Risk Controls
    multi_payload = {
        "ticker": "AAPL:0.5, MSFT:0.5",
        "start_date": "2024-01-01",
        "end_date": "2024-01-10",
        "strategy_name": "MA Crossover",
        "strategy_params": {"fast_period": 5, "slow_period": 10},
        "initial_cash": 100000.0,
        "commission_rate": 0.001,
        "slippage_rate": 0.0005,
        "risk_free_rate": 0.06,
        "trailing_stop_pct": 0.05,
        "use_atr_sizing": True,
        "risk_pct": 0.02,
        "atr_multiplier: ": 2.0
    }
    
    print("\nSending multi-asset backtest with risk controls...")
    res_multi = requests.post(f"{base_url}/backtest", json=multi_payload)
    print("Status code:", res_multi.status_code)
    if res_multi.status_code != 200:
        print("Failed with:", res_multi.text)
        return False
        
    multi_data = res_multi.json()
    print("Multi-asset backtest keys:", list(multi_data.keys()))
    print("Multi-asset metrics:", list(multi_data["metrics"].keys()))
    
    print("\nE2E verification succeeded!")
    return True

if __name__ == "__main__":
    test_api()
