from fastapi import FastAPI, HTTPException
from database import get_latest_snapshot
import pandas as pd

app = FastAPI(title="Option Chain API")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Option Chain API. Use /latest-chain/{symbol}/{expiry} to get data."}

@app.get("/latest-chain/{symbol}/{expiry}")
def get_latest_chain(symbol: str, expiry: str):
    """
    Returns the latest option chain data for a given symbol and expiry.
    Symbol format: NSE_INDEX|Nifty 50 (URL encode | as %7C)
    Expiry format: YYYY-MM-DD
    """
    timestamp, spot_price, data = get_latest_snapshot(symbol, expiry)
    if data is None:
        raise HTTPException(status_code=404, detail="Data not found for the given symbol and expiry.")

    return {
        "symbol": symbol,
        "expiry": expiry,
        "timestamp": timestamp,
        "spot_price": spot_price,
        "data": data.to_dict(orient='records')
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
