# Product Requirements Document (PRD): Minute-by-Minute Option Chain Analysis Engine

## 1. Overview
The "Money Matrix" Option Chain Analysis Engine is designed to provide high-frequency, actionable insights into the derivatives market. By shifting from a static sheet-based model to an automated, database-backed processing pipeline, the system ensures that traders have access to real-time Greeks, Implied Volatility (IV), and trend signals without the latency or limitations of traditional brokers' interfaces.

## 2. Business Logic & Data Flow
The system operates on a continuous loop, performing a full analysis cycle every 60 seconds (configurable).

### 2.1. The Analysis Cycle
Each minute, the `data_worker.py` performs the following steps for each tracked symbol (e.g., NIFTY, BANKNIFTY):

1.  **Data Acquisition**:
    - Fetches the current **Spot Price** for the underlying index.
    - Retrieves the full **Option Chain** data packet for the target expiry from Upstox.
2.  **Normalization**:
    - Pairs Call (CE) and Put (PE) data for every strike price into a unified record.
    - Extracts Last Traded Price (LTP), Open Interest (OI), Volume, and Previous Close.
3.  **Mathematical Processing (The Math Engine)**:
    - **Time to Expiry (T)**: Calculated in years down to the second.
    - **Implied Volatility (IV)**: Derived using a Newton-Raphson solver on the Black-Scholes pricing model.
    - **Greeks**: Delta and Theta are calculated for every strike to help traders understand risk and time decay.
4.  **Signal Generation (Smart Trend Logic)**:
    - The engine compares the change in Price vs. the change in Open Interest to determine market sentiment.
5.  **Persistence**:
    - The entire processed matrix is serialized into JSON and stored in the SQLite database (`option_chain.db`) along with a high-resolution timestamp.

### 2.2. Smart Trend Sentiment Analysis
The core of the "Money Matrix" logic is identifying what big players are doing by analyzing the relationship between Price and OI:

| Price Change | OI Change | Trend Name | Business Interpretation |
| :--- | :--- | :--- | :--- |
| **UP** | **UP** | **Long Buildup** | Strong buying. Bulls are entering new positions. |
| **DOWN** | **UP** | **Short Buildup** | Strong selling. Bears are creating new shorts. |
| **DOWN** | **DOWN** | **Long Unwinding** | Bulls are exiting/booking profits. Weakening trend. |
| **UP** | **DOWN** | **Short Covering** | Bears are trapped and exiting. Often leads to sharp spikes. |

## 3. Key Metrics & Indicators
- **PCR (Put-Call Ratio)**: Total Put OI / Total Call OI.
    - `> 1.2`: Extremely Bullish (Possible Overbought).
    - `< 0.6`: Extremely Bearish (Possible Oversold).
- **Support & Resistance**: Identified by the strike prices with the maximum OI concentration for Puts and Calls, respectively.
- **ATM Filtering**: The UI focuses on the strikes nearest to the current Spot Price (the "In-the-Money" and "Near-the-Money" strikes) where the most significant volatility and volume occur.

## 4. System Architecture
- **Worker Tier**: `data_worker.py` (The "Brain") - Responsible for heavy lifting, math, and API communication.
- **Data Tier**: `database.py` (The "Memory") - SQLite storage ensuring data is not lost between refreshes.
- **Service Tier**: `api_server.py` (The "Bridge") - REST API for programmatic access or external integrations.
- **Presentation Tier**: `main.py` (The "Eyes") - Streamlit dashboard providing the visual interface for the trader.

## 5. Deployment & Execution
To maintain the integrity of the analysis, the Worker must run continuously during market hours (09:15 - 15:30 IST). The UI and API can be accessed anytime to review the latest captured snapshot.
