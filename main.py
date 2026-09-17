from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from nepse import Nepse
import uvicorn
from typing import Optional, List, Dict, Any
from datetime import datetime
import asyncio
import random

app = FastAPI(
    title="NEPSE API Pro",
    description="""
    🚀 **NEPSE API Pro** - The Ultimate Unofficial Nepal Stock Exchange API.
    
    ### 🛠️ How to Run
    1. **Install**: `pip install api-nepse`
    2. **Run**: `api-nepse`
    
    ### 🌐 How to Host
    - **Local**: Run `api-nepse` on your machine.
    - **Cloud (Heroku/Render/Vercel)**: Deploy this repository and use `uvicorn api_nepse.main:app --host 0.0.0.0 --port $PORT`.
    - **Docker**: Use a Python image, install `api-nepse`, and expose port 8080.
    
    ### 👨‍💻 Developer
    - **Name**: Gunpark
    - **Instagram**: [@gunpark_xd](https://instagram.com/gunpark_xd)
    """,
    version="2.2.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Enhanced Nepse Client with Multiple Headers
class EnhancedNepse(Nepse):
    def __init__(self):
        super().__init__()
        self.user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/93.0.4577.63 Safari/537.36",
            "Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.0.3 Mobile/15E148 Safari/604.1"
        ]

    def get_random_headers(self):
        headers = self.headers.copy()
        headers["User-Agent"] = random.choice(self.user_agents)
        return headers

nepse = EnhancedNepse()
nepse.setTLSVerification(False)

DEVELOPER_INFO = {
    "name": "Gunpark",
    "instagram": "@gunpark_xd",
    "github": "BalochLeader",
    "version": "2.2.0",
    "status": "Official Tagda API"
}

def create_response(data: Any, endpoint: str, status: str = "success"):
    return {
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "developer": DEVELOPER_INFO,
        "data": data
    }

@app.get("/", tags=["General"])
async def read_root():
    return create_response({
        "message": "NEPSE API Pro is Running",
        "docs": "/docs",
        "example_usage": "import requests; r = requests.get('http://localhost:8080/api/v1/market/today-price'); print(r.json())"
    }, "/")

@app.get("/api/v1/market/status", tags=["Market"])
async def get_market_status():
    try:
        data = nepse.getMarketStatus()
        return create_response(data, "/api/v1/market/status")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/summary", tags=["Market"])
async def get_market_summary():
    try:
        data = nepse.getSummary()
        summary = {obj["detail"]: obj["value"] for obj in data}
        return create_response(summary, "/api/v1/market/summary")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/today-price", tags=["Market"])
async def get_today_price():
    try:
        data = nepse.getPriceVolume()
        return create_response(data, "/api/v1/market/today-price")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/indices", tags=["Indices"])
async def get_indices():
    try:
        data = nepse.getNepseIndex()
        return create_response(data, "/api/v1/indices")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/companies", tags=["Company"])
async def get_companies():
    try:
        data = nepse.getCompanyList()
        return create_response(data, "/api/v1/companies")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/live", tags=["Market"])
async def get_live_market():
    try:
        data = nepse.getLiveMarket()
        return create_response(data, "/api/v1/market/live")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/market/floorsheet", tags=["Advanced"])
async def get_floorsheet():
    try:
        data = await nepse.getFloorSheet()
        return create_response(data[:100], "/api/v1/market/floorsheet")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health", tags=["System"])
async def health():
    return {"status": "healthy"}

def main():
    uvicorn.run(app, host="0.0.0.0", port=8080)

if __name__ == "__main__":
    main()
