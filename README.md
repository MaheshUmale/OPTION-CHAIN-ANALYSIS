# Money Matrix: Upstox Option Chain Dashboard

This system provides real-time option chain analysis using data from the Upstox API. It calculates Greeks (Delta, Theta, Gamma, Vega), Implied Volatility (IV), and detects market trends.

## Features
- **Upstox API Integration**: Fetches real-time spot prices and option chain data.
- **Math Engine**: Calculates Greeks and IV using the Black-Scholes model.
- **Smart Trend Logic**: Analyzes Price and Open Interest changes to identify Long Buildup, Short Covering, etc.
- **Data Persistence**: Stores option chain snapshots in a local SQLite database for historical analysis.
- **Exposed API**: Provides a FastAPI server to access the processed data programmatically.
- **Streamlit UI**: A clean, tabular web interface replacing the old Google Sheets.

## Architecture
1. **`data_worker.py`**: A background worker that fetches data from Upstox and stores it in the database.
2. **`api_server.py`**: A FastAPI server that exposes endpoints to retrieve data from the database.
3. **`main.py`**: The Streamlit dashboard that reads from the database and displays the data.
4. **`database.py`**: Handles all SQLite database operations.
5. **`upstox_engine.py`**: The core API client for Upstox.

## Setup Instructions

### 1. Prerequisites
- Python 3.10+
- Upstox API Token (Update in `config.py`)

### 2. Install Dependencies
```bash
pip install pandas scipy numpy streamlit requests fastapi uvicorn upstox-python-sdk
```

### 3. Configuration
Open `config.py` and ensure the `UPSTOX_TOKEN` is correct. You can also adjust the `RISK_FREE_RATE`.

### 4. Running the System

You need to run three components (can be in different terminals):

#### A. Start the Data Worker (Background process)
This will start fetching data every 60 seconds and storing it in `option_chain.db`.
```bash
python data_worker.py
```

#### B. Start the API Server
This exposes the data at `http://localhost:8000`.
```bash
python api_server.py
```

#### C. Start the Streamlit UI
This opens the dashboard in your browser.
```bash
streamlit run main.py
```

## API Usage
You can fetch the latest data for Nifty or BankNifty via API:
- **Nifty 50**: `http://localhost:8000/latest-chain/NSE_INDEX|Nifty 50/2026-01-20`
- **Bank Nifty**: `http://localhost:8000/latest-chain/NSE_INDEX|Nifty Bank/2026-01-27`

*(Note: Use URL encoding for symbols, e.g., replace `|` with `%7C` if using browser directly)*

## Preferred Expiries
The system is configured to track:
- **NIFTY**: 20 JAN 2026
- **BANKNIFTY**: 27 JAN 2026
