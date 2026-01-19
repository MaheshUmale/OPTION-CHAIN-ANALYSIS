import time
import datetime
import pandas as pd
import numpy as np
from scipy.stats import norm
from upstox_engine import UpstoxEngine
from database import init_db, save_snapshot, get_latest_snapshot
import config

# --- MATH ENGINE ---
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

def get_smart_trend(price_chg, oi_chg):
    if price_chg > 0 and oi_chg > 0: return "Long Buildup"
    if price_chg < 0 and oi_chg > 0: return "Short Buildup"
    if price_chg < 0 and oi_chg < 0: return "Long Unwinding"
    if price_chg > 0 and oi_chg < 0: return "Short Covering"
    return "Neutral"

def process_and_save():
    engine = UpstoxEngine()
    init_db()

    # We can monitor multiple symbols
    symbols_to_track = [
        {"symbol": "NSE_INDEX|Nifty 50", "expiry": "2026-01-20"},
        {"symbol": "NSE_INDEX|Nifty Bank", "expiry": "2026-01-27"}
    ]

    print("--- Data Worker Started ---")

    while True:
        for item in symbols_to_track:
            symbol = item['symbol']
            expiry = item['expiry']

            print(f"[{datetime.datetime.now()}] Fetching {symbol} for {expiry}")

            try:
                spot_price = engine.get_spot_price(symbol)
                if spot_price == 0:
                    print(f"  -> Failed to get spot price for {symbol}")
                    continue

                chain_data = engine.get_option_chain(symbol, expiry)
                if not chain_data:
                    print(f"  -> Failed to get chain data for {symbol}")
                    continue

                # Fetch previous snapshot for interval change calculation (today only)
                _, prev_spot, prev_df = get_latest_snapshot(symbol, expiry, same_day_only=True)
                prev_data_map = {}
                if prev_df is not None:
                    for _, row in prev_df.iterrows():
                        prev_data_map[row['strike']] = row

                T = get_time_to_expiry(expiry)
                clean_data = []

                for entry in chain_data:
                    strike = entry['strike_price']
                    ce_data = entry.get('call_options')
                    pe_data = entry.get('put_options')

                    if not ce_data or not pe_data: continue

                    ce_market = ce_data['market_data']
                    pe_market = pe_data['market_data']

                    c_ltp = ce_market.get('ltp', 0)
                    c_oi = ce_market.get('oi', 0)

                    p_ltp = pe_market.get('ltp', 0)
                    p_oi = pe_market.get('oi', 0)

                    # Interval change calculation
                    if strike in prev_data_map:
                        prev_item = prev_data_map[strike]
                        c_chng_oi = c_oi - prev_item.get('c_oi', c_oi)
                        p_chng_oi = p_oi - prev_item.get('p_oi', p_oi)
                        c_chng_price = c_ltp - prev_item.get('c_ltp', c_ltp)
                        p_chng_price = p_ltp - prev_item.get('p_ltp', p_ltp)
                    else:
                        c_chng_oi = 0
                        p_chng_oi = 0
                        c_chng_price = 0
                        p_chng_price = 0

                    c_iv = get_implied_volatility(c_ltp, spot_price, strike, T, config.RISK_FREE_RATE, 'CE') * 100
                    p_iv = get_implied_volatility(p_ltp, spot_price, strike, T, config.RISK_FREE_RATE, 'PE') * 100

                    c_greeks = calculate_greeks(spot_price, strike, T, config.RISK_FREE_RATE, c_iv/100, 'CE')
                    p_greeks = calculate_greeks(spot_price, strike, T, config.RISK_FREE_RATE, p_iv/100, 'PE')

                    # Smart trend based on interval momentum
                    c_trend = get_smart_trend(c_chng_price, c_chng_oi)
                    p_trend = get_smart_trend(p_chng_price, p_chng_oi)

                    clean_data.append({
                        'strike': strike, 'c_ltp': c_ltp, 'c_oi': c_oi, 'c_chng_oi': c_chng_oi, 'c_iv': round(c_iv, 2),
                        'c_delta': c_greeks['delta'], 'c_theta': c_greeks['theta'], 'c_trend': c_trend,
                        'p_ltp': p_ltp, 'p_oi': p_oi, 'p_chng_oi': p_chng_oi, 'p_iv': round(p_iv, 2),
                        'p_delta': p_greeks['delta'], 'p_theta': p_greeks['theta'], 'p_trend': p_trend
                    })

                df = pd.DataFrame(clean_data)
                save_snapshot(symbol, expiry, spot_price, df)
                print(f"  -> Saved {len(df)} rows for {symbol}")
            except Exception as e:
                print(f"  -> Error processing {symbol}: {e}")

        time.sleep(60) # Refresh every minute

if __name__ == "__main__":
    process_and_save()
