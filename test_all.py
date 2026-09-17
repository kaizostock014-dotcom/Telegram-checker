import requests
import json

BASE_URL = "http://localhost:8080"
ENDPOINTS = [
    "/",
    "/api/v1/summary",
    "/api/v1/market-status",
    "/api/v1/indices",
    "/api/v1/sub-indices",
    "/api/v1/top-gainers",
    "/api/v1/top-losers",
    "/api/v1/top-traded",
    "/api/v1/top-turnover",
    "/api/v1/top-transactions",
    "/api/v1/live-market",
    "/api/v1/price-volume",
    "/api/v1/companies",
    "/api/v1/securities",
    "/api/v1/supply-demand",
    "/api/v1/statistics",
    "/health"
]

def test_endpoints():
    print(f"{'Endpoint':<30} | {'Status':<10} | {'Data Check'}")
    print("-" * 60)
    for ep in ENDPOINTS:
        try:
            response = requests.get(BASE_URL + ep)
            status_code = response.status_code
            data = response.json()
            
            # Check for developer info in response
            has_dev = "developer" in data
            is_success = data.get("status") == "success"
            
            check = "✅ OK" if status_code == 200 and has_dev and is_success else "❌ FAIL"
            print(f"{ep:<30} | {status_code:<10} | {check}")
        except Exception as e:
            print(f"{ep:<30} | ERROR      | {str(e)[:20]}...")

if __name__ == "__main__":
    test_endpoints()
