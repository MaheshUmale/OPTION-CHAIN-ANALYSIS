import streamlit as st
import pandas as pd
import datetime
import time
from database import get_latest_snapshot, init_db
import config

# --- PAGE CONFIG ---
st.set_page_config(page_title="Upstox Option Chain Matrix", layout="wide")

def main():
    st.title("🚀 Money Matrix: Upstox Option Chain Dashboard")

    # Initialize DB
    init_db()

    # Sidebar for config
    st.sidebar.header("Configuration")
    symbol = st.sidebar.selectbox("Select Symbol", [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|Nifty Bank",
        "NSE_INDEX|Nifty Fin Service"
    ], index=0)

    # User requested specific expiries
    default_expiry = "2026-01-20" if "Nifty 50" in symbol else "2026-01-27"

    expiry = st.sidebar.text_input("Expiry Date (YYYY-MM-DD)", value=default_expiry)
    refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 5, 60, 10)

    placeholder = st.empty()

    while True:
        with placeholder.container():
            # Read from DB instead of API
            timestamp, spot_price, df = get_latest_snapshot(symbol, expiry)

            if df is None or df.empty:
                st.warning(f"No data found in database for {symbol} / {expiry}. Make sure 'data_worker.py' is running.")
                st.info("The worker fetches data every 60 seconds.")
            else:
                # Summary Metrics
                # Re-calculate PCR and Support/Resistance from the retrieved data
                pcr = round(df['p_oi'].sum() / df['c_oi'].sum(), 2) if df['c_oi'].sum() > 0 else 0
                sentiment = "BULLISH" if pcr > 1.2 else "BEARISH" if pcr < 0.6 else "NEUTRAL"

                max_ce_oi_idx = df['c_oi'].idxmax()
                max_pe_oi_idx = df['p_oi'].idxmax()
                resistance = df.iloc[max_ce_oi_idx]['strike']
                support = df.iloc[max_pe_oi_idx]['strike']

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Spot Price", f"{spot_price:.2f}")
                col2.metric("PCR", f"{pcr} ({sentiment})")
                col3.metric("Support", f"{support}")
                col4.metric("Resistance", f"{resistance}")

                st.write(f"Data Last Captured: {timestamp} | Current Time: {datetime.datetime.now().strftime('%H:%M:%S')}")

                # Rename columns for display
                display_cols = {
                    'c_oi': 'Call OI', 'c_chng_oi': 'Call Chng OI', 'c_iv': 'Call IV',
                    'c_trend': 'Call Trend', 'c_delta': 'Call Delta', 'c_theta': 'Call Theta',
                    'c_ltp': 'Call LTP', 'strike': 'Strike Price',
                    'p_ltp': 'Put LTP', 'p_delta': 'Put Delta', 'p_theta': 'Put Theta',
                    'p_trend': 'Put Trend', 'p_iv': 'Put IV', 'p_chng_oi': 'Put Chng OI', 'p_oi': 'Put OI'
                }

                df_display = df.rename(columns=display_cols)

                # Filter rows near ATM
                atm_strike = round(spot_price / 50) * 50 if "Nifty 50" in symbol else round(spot_price / 100) * 100
                df_filtered = df_display[(df_display['Strike Price'] >= atm_strike - 500) & (df_display['Strike Price'] <= atm_strike + 500)]

                st.dataframe(df_filtered, use_container_width=True, height=600)

            time.sleep(refresh_rate)
            st.rerun()

if __name__ == "__main__":
    main()
