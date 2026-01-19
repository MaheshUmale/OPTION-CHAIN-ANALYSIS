import streamlit as st
import pandas as pd
import datetime
import time
import io
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from database import get_latest_snapshot, get_historical_snapshots, init_db
import config

# --- PAGE CONFIG ---
st.set_page_config(page_title="Money Matrix: Smart Option Chain", layout="wide")

def main():
    st.title("🚀 Money Matrix Dashboard")

    # Initialize DB
    init_db()

    # Sidebar for config
    st.sidebar.header("Settings")
    symbol = st.sidebar.selectbox("Symbol", [
        "NSE_INDEX|Nifty 50",
        "NSE_INDEX|Nifty Bank",
        "NSE_INDEX|Nifty Fin Service"
    ], index=0)

    # Default expiries for the current context
    default_expiry = "2026-01-20" if "Nifty 50" in symbol else "2026-01-27"
    expiry = st.sidebar.text_input("Expiry Date", value=default_expiry)
    refresh_rate = st.sidebar.slider("Auto Refresh (sec)", 10, 60, 30)

    # Main view tabs
    tab_dashboard, tab_chain, tab_trends = st.tabs(["📊 Dashboard", "⛓️ Option Chain", "📈 Trends"])

    while True:
        # Read from DB
        timestamp, spot_price, df = get_latest_snapshot(symbol, expiry)

        if df is None or df.empty:
            st.warning(f"Waiting for data for {symbol} ({expiry})...")
        else:
            # Metrics Calculation
            total_c_oi = df['c_oi'].sum()
            total_p_oi = df['p_oi'].sum()
            pcr = round(total_p_oi / total_c_oi, 2) if total_c_oi > 0 else 0
            sentiment = "BULLISH" if pcr >= 1.2 else "BEARISH" if pcr <= 0.7 else "NEUTRAL"

            res_strike = df.iloc[df['c_oi'].idxmax()]['strike']
            sup_strike = df.iloc[df['p_oi'].idxmax()]['strike']

            # --- TAB 1: DASHBOARD ---
            with tab_dashboard:
                m1, m2, m3, m4 = st.columns(4)
                m1.metric("Spot Price", f"{spot_price:,.2f}")
                m2.metric("PCR (Sentiment)", f"{pcr} ({sentiment})")
                m3.metric("Support", f"{sup_strike:,.0f}")
                m4.metric("Resistance", f"{res_strike:,.0f}")

                st.caption(f"Last update: {timestamp} IST")

                st.subheader("Market Flow Momentum")
                c_chng = df['c_chng_oi'].sum()
                p_chng = df['p_chng_oi'].sum()

                f1, f2 = st.columns(2)
                with f1:
                    st.write(f"**Call Momentum:** {'🔴 Bearish' if c_chng > 0 else '🟢 Bullish/Covering'} ({c_chng:,.0f} OI)")
                with f2:
                    st.write(f"**Put Momentum:** {'🟢 Bullish' if p_chng > 0 else '🔴 Bearish/Unwinding'} ({p_chng:,.0f} OI)")

            # --- TAB 2: OPTION CHAIN ---
            with tab_chain:
                # Grouped columns for "Money Matrix" style
                df_view = df[['c_ltp', 'c_oi', 'c_chng_oi', 'c_trend', 'strike', 'p_trend', 'p_chng_oi', 'p_oi', 'p_ltp']].copy()
                df_view.columns = ['C_LTP', 'C_OI', 'C_Chng', 'C_Flow', 'STRIKE', 'P_Flow', 'P_Chng', 'P_OI', 'P_LTP']

                # ATM Centering
                atm = round(spot_price / 50) * 50 if "Nifty 50" in symbol else round(spot_price / 100) * 100
                rng = 500 if "Nifty 50" in symbol else 1000
                df_atm = df_view[(df_view['STRIKE'] >= atm - rng) & (df_view['STRIKE'] <= atm + rng)]

                st.dataframe(df_atm.style.format(precision=0, subset=['C_OI', 'C_Chng', 'P_Chng', 'P_OI', 'STRIKE'])
                                    .format(precision=2, subset=['C_LTP', 'P_LTP']),
                             use_container_width=True, height=600)

            # --- TAB 3: HISTORICAL TRENDS ---
            with tab_trends:
                hist = get_historical_snapshots(symbol, expiry)
                if not hist.empty:
                    processed = []
                    for _, row in hist.iterrows():
                        try:
                            d = pd.read_json(io.StringIO(row['data_json']))
                            processed.append({
                                'Time': pd.to_datetime(row['timestamp']),
                                'Spot': row['spot_price'],
                                'C_Flow': d['c_chng_oi'].sum(),
                                'P_Flow': d['p_chng_oi'].sum(),
                                'PCR': round(d['p_oi'].sum() / d['c_oi'].sum(), 2) if d['c_oi'].sum() > 0 else 0
                            })
                        except: continue

                    df_hist = pd.DataFrame(processed).set_index('Time')
                    df_hist['C_Flow_Cum'] = df_hist['C_Flow'].cumsum()
                    df_hist['P_Flow_Cum'] = df_hist['P_Flow'].cumsum()

                    fig = make_subplots(specs=[[{"secondary_y": True}]])
                    fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['C_Flow_Cum'], name="Call Flow", line=dict(color='cyan')), secondary_y=False)
                    fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['P_Flow_Cum'], name="Put Flow", line=dict(color='red')), secondary_y=False)
                    fig.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Spot'], name="Spot Price", line=dict(color='gold', dash='dot')), secondary_y=True)

                    fig.update_layout(height=500, template="plotly_dark", legend=dict(orientation="h", y=1.1))
                    st.plotly_chart(fig, use_container_width=True)

                    st.subheader("Sentiment (PCR)")
                    st.line_chart(df_hist['PCR'])

        time.sleep(refresh_rate)
        st.rerun()

if __name__ == "__main__":
    main()
