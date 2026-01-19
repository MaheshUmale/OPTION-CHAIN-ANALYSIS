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
                if pcr >= 1.2:
                    sentiment = "BULLISH"
                elif pcr <= 0.7:
                    sentiment = "BEARISH"
                else:
                    sentiment = "NEUTRAL"

                max_ce_oi_idx = df['c_oi'].idxmax()
                max_pe_oi_idx = df['p_oi'].idxmax()
                resistance = df.iloc[max_ce_oi_idx]['strike']
                support = df.iloc[max_pe_oi_idx]['strike']

                col1, col2, col3, col4 = st.columns(4)
                col1.metric("Spot Price", f"{spot_price:.2f}")
                col2.metric("PCR", f"{pcr} ({sentiment})")
                col3.metric("Support", f"{support}")
                col4.metric("Resistance", f"{resistance}")

                ist_now = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(hours=5, minutes=30)
                st.write(f"Data Last Captured: {timestamp} | Current Time (IST): {ist_now.strftime('%H:%M:%S')}")

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
                diffStrike = 500 if "Nifty 50" in symbol else 1000
                df_filtered = df_display[(df_display['Strike Price'] >= atm_strike - diffStrike) & (df_display['Strike Price'] <= atm_strike + diffStrike)]

                st.dataframe(df_filtered, use_container_width=True, height=600)

                # --- Charts Section ---
                st.divider()
                st.subheader("Time-Based Analysis & OI Distribution")

                # Fetch historical data
                hist_df = get_historical_snapshots(symbol, expiry)

                if not hist_df.empty:
                    # Strike selection for trend tracking
                    available_strikes = sorted(df['strike'].unique())
                    default_strike_idx = 0
                    # Try to default to ATM
                    atm_strike = round(spot_price / 50) * 50 if "Nifty 50" in symbol else round(spot_price / 100) * 100
                    if atm_strike in available_strikes:
                        default_strike_idx = available_strikes.index(atm_strike)

                    selected_strike = st.selectbox("Select Strike for Trend Tracking", available_strikes, index=default_strike_idx)

                    processed_hist = []
                    strike_trend_hist = []
                    market_trend_hist = []

                    for _, row in hist_df.iterrows():
                        try:
                            data = pd.read_json(io.StringIO(row['data_json']))
                            c_oi_sum = data['c_oi'].sum()
                            p_oi_sum = data['p_oi'].sum()
                            c_chng_oi_sum = data['c_chng_oi'].sum()
                            p_chng_oi_sum = data['p_chng_oi'].sum()

                            ts = pd.to_datetime(row['timestamp'])

                            processed_hist.append({
                                'Time': ts,
                                'Spot Price': row['spot_price'],
                                'Call OI': c_oi_sum,
                                'Put OI': p_oi_sum,
                                'Total OI': c_oi_sum + p_oi_sum,
                                'Call Chng OI': c_chng_oi_sum,
                                'Put Chng OI': p_chng_oi_sum,
                                'Total Chng OI': c_chng_oi_sum + p_chng_oi_sum,
                                'PCR': round(p_oi_sum / c_oi_sum, 2) if c_oi_sum > 0 else 0
                            })

                            # Extract trend for selected strike
                            s_data = data[data['strike'] == selected_strike]
                            if not s_data.empty:
                                strike_trend_hist.append({
                                    'Time': ts.strftime('%H:%M:%S'),
                                    'Spot': row['spot_price'],
                                    'Call Trend': s_data['c_trend'].values[0],
                                    'Put Trend': s_data['p_trend'].values[0]
                                })

                            # Market-wide Trend Aggregation
                            c_counts = data['c_trend'].value_counts().to_dict()
                            p_counts = data['p_trend'].value_counts().to_dict()

                            market_trend_hist.append({
                                'Time': ts,
                                'C_Long_Buildup': c_counts.get('Long Buildup', 0),
                                'C_Short_Buildup': c_counts.get('Short Buildup', 0),
                                'P_Long_Buildup': p_counts.get('Long Buildup', 0),
                                'P_Short_Buildup': p_counts.get('Short Buildup', 0)
                            })
                        except:
                            continue

                    df_hist = pd.DataFrame(processed_hist)
                    df_hist.set_index('Time', inplace=True)

                    # Layout like the requested image
                    # Row 1: Change in OI
                    col_bar1, col_line1 = st.columns([1, 4])

                    with col_bar1:
                        st.write("**Change in OI**")
                        latest_chng = {
                            'Type': ['CALL', 'PUT'],
                            'Value': [df['c_chng_oi'].sum(), df['p_chng_oi'].sum()]
                        }
                        st.bar_chart(pd.DataFrame(latest_chng).set_index('Type'))

                    with col_line1:
                        st.write("**Change in OI Trend**")

                        fig1 = make_subplots(specs=[[{"secondary_y": True}]])
                        fig1.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Call Chng OI'], name="Call Chng OI", line=dict(color='cyan')), secondary_y=False)
                        fig1.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Put Chng OI'], name="Put Chng OI", line=dict(color='red')), secondary_y=False)
                        fig1.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Total Chng OI'], name="Total Chng OI", line=dict(color='orange', dash='dash')), secondary_y=False)
                        fig1.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Spot Price'], name="Spot Price", line=dict(color='#ffd700', dash='dot')), secondary_y=True)

                        fig1.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        fig1.update_yaxes(title_text="OI", secondary_y=False, autorange=True, zeroline=False, rangemode='normal')
                        fig1.update_yaxes(title_text="Spot Price", secondary_y=True, autorange=True, zeroline=False, rangemode='normal')

                        st.plotly_chart(fig1, use_container_width=True)

                    # Row 2: Total OI
                    col_bar2, col_line2 = st.columns([1, 4])

                    with col_bar2:
                        st.write("**Total OI**")
                        latest_total = {
                            'Type': ['CALL', 'PUT'],
                            'Value': [df['c_oi'].sum(), df['p_oi'].sum()]
                        }
                        st.bar_chart(pd.DataFrame(latest_total).set_index('Type'))

                    with col_line2:
                        st.write("**Total OI Trend**")

                        fig2 = make_subplots(specs=[[{"secondary_y": True}]])
                        fig2.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Call OI'], name="Call OI", line=dict(color='cyan')), secondary_y=False)
                        fig2.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Put OI'], name="Put OI", line=dict(color='red')), secondary_y=False)
                        fig2.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Total OI'], name="Total OI", line=dict(color='orange', dash='dash')), secondary_y=False)
                        fig2.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Spot Price'], name="Spot Price", line=dict(color='#ffd700', dash='dot')), secondary_y=True)

                        fig2.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                        fig2.update_yaxes(title_text="OI", secondary_y=False, autorange=True, zeroline=False, rangemode='normal')
                        fig2.update_yaxes(title_text="Spot Price", secondary_y=True, autorange=True, zeroline=False, rangemode='normal')

                        st.plotly_chart(fig2, use_container_width=True)

                    # Row 3: PCR Trend
                    st.write("**PCR & Price Trend**")
                    fig3 = make_subplots(specs=[[{"secondary_y": True}]])
                    fig3.add_trace(go.Scatter(x=df_hist.index, y=df_hist['PCR'], name="PCR", line=dict(color='green')), secondary_y=False)
                    fig3.add_trace(go.Scatter(x=df_hist.index, y=df_hist['Spot Price'], name="Spot Price", line=dict(color='#ffd700', dash='dot')), secondary_y=True)
                    fig3.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    fig3.update_yaxes(title_text="PCR", secondary_y=False, autorange=True, zeroline=False, rangemode='normal')
                    fig3.update_yaxes(title_text="Spot Price", secondary_y=True, autorange=True, zeroline=False, rangemode='normal')
                    st.plotly_chart(fig3, use_container_width=True)

                    # --- Market Trend Aggregation Chart ---
                    st.write("**Market Trend Aggregation (Count of Strikes)**")
                    df_market_trend = pd.DataFrame(market_trend_hist).set_index('Time')

                    fig4 = go.Figure()
                    # CE Trends
                    fig4.add_trace(go.Scatter(x=df_market_trend.index, y=df_market_trend['C_Long_Buildup'], name="CE Long Buildup (Bullish)", line=dict(color='#2ecc71')))
                    fig4.add_trace(go.Scatter(x=df_market_trend.index, y=df_market_trend['C_Short_Buildup'], name="CE Short Buildup (Bearish)", line=dict(color='#e74c3c')))
                    # PE Trends
                    fig4.add_trace(go.Scatter(x=df_market_trend.index, y=df_market_trend['P_Long_Buildup'], name="PE Long Buildup (Bearish)", line=dict(color='#c0392b', dash='dot')))
                    fig4.add_trace(go.Scatter(x=df_market_trend.index, y=df_market_trend['P_Short_Buildup'], name="PE Short Buildup (Bullish)", line=dict(color='#27ae60', dash='dot')))

                    fig4.update_layout(height=400, margin=dict(l=0, r=0, t=0, b=0), legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
                    fig4.update_yaxes(title_text="Strike Count", autorange=True, zeroline=False)
                    st.plotly_chart(fig4, use_container_width=True)

                    # --- Trend Evolution Table ---
                    st.divider()
                    st.subheader(f"Trend Evolution: Strike {selected_strike}")
                    if strike_trend_hist:
                        df_trend_hist = pd.DataFrame(strike_trend_hist).iloc[::-1] # Show latest first

                        def color_trend_ce(val):
                            color = 'white'
                            if val == 'Long Buildup': color = '#2ecc71' # Green (Bullish)
                            elif val == 'Short Buildup': color = '#e74c3c' # Red (Bearish)
                            elif val == 'Short Covering': color = '#3498db' # Blue (Bullish)
                            elif val == 'Long Unwinding': color = '#f1c40f' # Yellow (Bearish)
                            return f'background-color: {color}; color: black'

                        def color_trend_pe(val):
                            color = 'white'
                            if val == 'Long Buildup': color = '#e74c3c' # Red (Bearish)
                            elif val == 'Short Buildup': color = '#2ecc71' # Green (Bullish)
                            elif val == 'Short Covering': color = '#f1c40f' # Yellow (Bearish)
                            elif val == 'Long Unwinding': color = '#3498db' # Blue (Bullish)
                            return f'background-color: {color}; color: black'

                        styled_df = df_trend_hist.style.map(color_trend_ce, subset=['Call Trend']).map(color_trend_pe, subset=['Put Trend'])
                        st.table(styled_df)
                    else:
                        st.info("No trend history available yet for this strike.")

            time.sleep(refresh_rate)
            st.rerun()

if __name__ == "__main__":
    main()
