import streamlit as st
import pandas as pd
import numpy as np
import datetime
import time
from scipy.stats import norm
from upstox_engine import UpstoxEngine
import config

# --- PAGE CONFIG ---
st.set_page_config(page_title="Upstox Option Chain Matrix", layout="wide")

# --- MATH ENGINE: BLACK-SCHOLES IV SOLVER ---
def get_implied_volatility(price, spot, strike, t, r, flag):
    if price <= 0.05 or t <= 0.0001: return 0
    low, high = 0.01, 5.0
    for _ in range(15):
        mid = (low + high) / 2
        try:
            d1 = (np.log(spot / strike) + (r + 0.5 * mid ** 2) * t) / (mid * np.sqrt(t))
            d2 = d1 - mid * np.sqrt(t)
            if flag == 'CE':
                theo = spot * norm.cdf(d1) - strike * np.exp(-r * t) * norm.cdf(d2)
            else:
                theo = strike * np.exp(-r * t) * norm.cdf(-d2) - spot * norm.cdf(-d1)
            if abs(theo - price) < 0.1: return mid
            if theo > price: high = mid
            else: low = mid
        except: return 0
    return (low + high) / 2

# --- MATH ENGINE: GREEKS ---
def calculate_greeks(spot, strike, t, r, iv, opt_type):
    try:
        if iv <= 0.001 or t <= 0.0001 or spot <= 0: return {'delta': 0, 'theta': 0, 'gamma': 0, 'vega': 0}
        d1 = (np.log(spot / strike) + (r + 0.5 * iv ** 2) * t) / (iv * np.sqrt(t))
        d2 = d1 - iv * np.sqrt(t)
        if opt_type == 'CE':
            delta = norm.cdf(d1)
            theta = (-spot * norm.pdf(d1) * iv / (2 * np.sqrt(t)) - r * strike * np.exp(-r * t) * norm.cdf(d2)) / 365
        else:
            delta = norm.cdf(d1) - 1
            theta = (-spot * norm.pdf(d1) * iv / (2 * np.sqrt(t)) + r * strike * np.exp(-r * t) * norm.cdf(-d2)) / 365
        gamma = norm.pdf(d1) / (spot * iv * np.sqrt(t))
        vega = spot * np.sqrt(t) * norm.pdf(d1) / 100
        return {'delta': round(delta, 3), 'theta': round(theta, 2), 'gamma': round(gamma, 5), 'vega': round(vega, 2)}
    except: return {'delta': 0, 'theta': 0, 'gamma': 0, 'vega': 0}

def get_time_to_expiry(expiry_date_str):
    try:
        expiry = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
        today = datetime.datetime.now()
        expiry = expiry.replace(hour=15, minute=30, second=0)
        diff = expiry - today
        T = (diff.days + diff.seconds / 86400) / 365.0
        return max(T, 0.00001)
    except: return 0.00001

# --- ADVANCED TREND LOGIC ---
def get_smart_trend(price_chg, oi_chg):
    if price_chg > 0 and oi_chg > 0: return "Long Buildup"
    if price_chg < 0 and oi_chg > 0: return "Short Buildup"
    if price_chg < 0 and oi_chg < 0: return "Long Unwinding"
    if price_chg > 0 and oi_chg < 0: return "Short Covering"
    if price_chg > 0 and oi_chg == 0: return "Buying (Flat OI)"
    if price_chg < 0 and oi_chg == 0: return "Selling (Flat OI)"
    return "Neutral"

# --- UI APP ---
def main():
    st.title("🚀 Money Matrix: Upstox Option Chain Dashboard")

    # Sidebar for config
    st.sidebar.header("Configuration")
    symbol = st.sidebar.selectbox("Select Symbol", ["NSE_INDEX|Nifty 50", "NSE_INDEX|Nifty Bank", "NSE_INDEX|Nifty Fin Service"], index=0)

    engine = UpstoxEngine()

    # Fetch expiries for the selected symbol
    with st.spinner("Fetching available expiries..."):
        expiries = engine.get_expiry_dates(symbol)

    if not expiries:
        st.error("Failed to fetch expiries. Check your API token or Internet connection.")
        return

    selected_expiry = st.sidebar.selectbox("Select Expiry", expiries, index=0)
    refresh_rate = st.sidebar.slider("Refresh Rate (seconds)", 5, 60, 30)

    risk_free_rate = config.RISK_FREE_RATE

    placeholder = st.empty()

    while True:
        with placeholder.container():
            # Fetch Data
            spot_price = engine.get_spot_price(symbol)
            if spot_price == 0:
                st.warning("Waiting for spot price...")
                time.sleep(2)
                continue

            chain_data = engine.get_option_chain(symbol, selected_expiry)
            if not chain_data:
                st.warning("Waiting for option chain data...")
                time.sleep(2)
                continue

            T = get_time_to_expiry(selected_expiry)

            clean_data = []
            for item in chain_data:
                strike = item['strike_price']
                ce_data = item.get('call_options')
                pe_data = item.get('put_options')

                if not ce_data or not pe_data: continue

                ce_market = ce_data['market_data']
                pe_market = pe_data['market_data']

                # CE Details
                c_ltp = ce_market.get('ltp', 0)
                c_oi = ce_market.get('oi', 0)
                c_prev_oi = ce_market.get('prev_oi', 0)
                c_chng_oi = c_oi - c_prev_oi
                c_vol = ce_market.get('volume', 0)
                c_chng = c_ltp - ce_market.get('close_price', 0) # Using close_price as prev close

                # PE Details
                p_ltp = pe_market.get('ltp', 0)
                p_oi = pe_market.get('oi', 0)
                p_prev_oi = pe_market.get('prev_oi', 0)
                p_chng_oi = p_oi - p_prev_oi
                p_vol = pe_market.get('volume', 0)
                p_chng = p_ltp - pe_market.get('close_price', 0)

                # Math Engine
                c_iv = get_implied_volatility(c_ltp, spot_price, strike, T, risk_free_rate, 'CE') * 100
                p_iv = get_implied_volatility(p_ltp, spot_price, strike, T, risk_free_rate, 'PE') * 100
                c_greeks = calculate_greeks(spot_price, strike, T, risk_free_rate, c_iv/100, 'CE')
                p_greeks = calculate_greeks(spot_price, strike, T, risk_free_rate, p_iv/100, 'PE')

                # Trend
                c_trend = get_smart_trend(c_chng, c_chng_oi)
                p_trend = get_smart_trend(p_chng, p_chng_oi)

                # Signal Logic
                signal = ""
                min_oi = 100
                if c_oi > min_oi and p_oi > min_oi:
                    if c_chng_oi < 0 and p_chng_oi > 0 and p_oi > c_oi: signal = "STRONG BUY CE 🚀"
                    elif p_chng_oi < 0 and c_chng_oi > 0 and c_oi > p_oi: signal = "STRONG BUY PE 🩸"
                    elif p_chng_oi > 0 and p_oi > c_oi * 1.5: signal = "Bullish Bias 🟢"
                    elif c_chng_oi > 0 and c_oi > p_oi * 1.5: signal = "Bearish Bias 🔴"

                clean_data.append({
                    'Call OI': c_oi, 'Call Chng OI': c_chng_oi, 'Call Vol': c_vol, 'Call IV': round(c_iv, 2),
                    'Call Trend': c_trend, 'Call Delta': c_greeks['delta'], 'Call Theta': c_greeks['theta'],
                    'Call Gamma': c_greeks['gamma'], 'Call Vega': c_greeks['vega'], 'Call LTP': c_ltp,
                    'Call Chng': round(c_chng, 2), 'Strike Price': strike, '⚠️ SIGNAL ⚠️': signal,
                    'Put LTP': p_ltp, 'Put Chng': round(p_chng, 2), 'Put Delta': p_greeks['delta'],
                    'Put Theta': p_greeks['theta'], 'Put Gamma': p_greeks['gamma'], 'Put Vega': p_greeks['vega'],
                    'Put Trend': p_trend, 'Put IV': round(p_iv, 2), 'Put Vol': p_vol,
                    'Put Chng OI': p_chng_oi, 'Put OI': p_oi
                })

            df = pd.DataFrame(clean_data)

            # Summary Metrics
            pcr = round(df['Put OI'].sum() / df['Call OI'].sum(), 2) if df['Call OI'].sum() > 0 else 0
            sentiment = "BULLISH" if pcr > 1.2 else "BEARISH" if pcr < 0.6 else "NEUTRAL"
            max_ce_oi_idx = df['Call OI'].idxmax()
            max_pe_oi_idx = df['Put OI'].idxmax()
            resistance = df.iloc[max_ce_oi_idx]['Strike Price']
            support = df.iloc[max_pe_oi_idx]['Strike Price']

            col1, col2, col3, col4 = st.columns(4)
            col1.metric("Spot Price", f"{spot_price:.2f}")
            col2.metric("PCR", f"{pcr} ({sentiment})")
            col3.metric("Support", f"{support}")
            col4.metric("Resistance", f"{resistance}")

            st.write(f"Last Updated: {datetime.datetime.now().strftime('%H:%M:%S')}")

            # Styling the table
            def highlight_signal(s):
                if "BUY CE" in s: return 'background-color: #d4edda; color: #155724'
                if "BUY PE" in s: return 'background-color: #f8d7da; color: #721c24'
                return ''

            # Display Table
            # Filter rows near ATM for better view (e.g., +/- 10 strikes)
            atm_strike = round(spot_price / 50) * 50 if "Nifty 50" in symbol else round(spot_price / 100) * 100
            df_display = df[(df['Strike Price'] >= atm_strike - 500) & (df['Strike Price'] <= atm_strike + 500)]

            st.dataframe(df_display.style.applymap(highlight_signal, subset=['⚠️ SIGNAL ⚠️']), use_container_width=True, height=600)

            time.sleep(refresh_rate)
            st.rerun()

if __name__ == "__main__":
    main()
