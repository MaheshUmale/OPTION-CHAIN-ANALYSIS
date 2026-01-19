import requests
import pandas as pd
import numpy as np
from scipy.stats import norm
import datetime
import sqlite3
import json
import time
import io
import config
from data_worker import get_implied_volatility, calculate_greeks, get_smart_trend

DB_NAME = "option_chain.db"
SYMBOL = "NSE_INDEX|Nifty 50"
EXPIRY = "2026-01-20"
TRENDLYNE_SYMBOL = "NIFTY"
TRENDLYNE_EXPIRY = "20-jan-2026-near"

STRIKES = range(25000, 26050, 50)

def fetch_trendlyne_data(strike, opt_type):
    url = f"https://smartoptions.trendlyne.com/phoenix/api/fno/buildup-5/{TRENDLYNE_EXPIRY}/{TRENDLYNE_SYMBOL}/?fno_mtype=options&strikePrice={strike}&option_type={opt_type}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Failed {strike} {opt_type}: {response.status_code}")
    except Exception as e:
        print(f"Error fetching {strike} {opt_type}: {e}")
    return None

def get_time_to_expiry_at(expiry_date_str, current_time):
    try:
        expiry = datetime.datetime.strptime(expiry_date_str, "%Y-%m-%d")
        expiry = expiry.replace(hour=15, minute=30, second=0)
        diff = expiry - current_time
        T = (diff.days * 86400 + diff.seconds) / (365.0 * 86400)
        return max(T, 0.00001)
    except: return 0.00001

def main():
    all_data = {} # (interval) -> {strike -> {ce_data, pe_data}}

    print("Fetching data from Trendlyne...")
    for strike in STRIKES:
        print(f"  Strike {strike}...", end="", flush=True)
        ce_json = fetch_trendlyne_data(strike, "call")
        time.sleep(0.5) # Avoid hitting rate limits
        pe_json = fetch_trendlyne_data(strike, "put")
        time.sleep(0.5)

        if ce_json and pe_json:
            ce_intervals = ce_json.get('body', {}).get('data_v2', [])
            pe_intervals = pe_json.get('body', {}).get('data_v2', [])

            for item in ce_intervals:
                interval = item['interval']
                if interval not in all_data: all_data[interval] = {}
                if strike not in all_data[interval]: all_data[interval][strike] = {}
                all_data[interval][strike]['ce'] = item

            for item in pe_intervals:
                interval = item['interval']
                if interval not in all_data: all_data[interval] = {}
                if strike not in all_data[interval]: all_data[interval][strike] = {}
                all_data[interval][strike]['pe'] = item
            print(" Done")
        else:
            print(" Failed")

    # Now process each interval
    intervals = sorted(all_data.keys()) # Process in chronological order

    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    # Ensure DB is initialized
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS option_chain_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME,
            symbol TEXT,
            expiry TEXT,
            spot_price REAL,
            data_json TEXT
        )
    ''')
    conn.commit()

    print(f"Processing {len(intervals)} intervals...")

    for interval_str in intervals:
        # interval_str is like "12:05 TO 12:10"
        end_time_str = interval_str.split(" TO ")[1]
        timestamp_str = f"2026-01-19 {end_time_str}:00"
        current_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        T = get_time_to_expiry_at(EXPIRY, current_time)

        strike_data_list = all_data[interval_str]

        # Calculate spot price from ATM strikes if available
        spot_price = 0
        for test_strike in [25550, 25500, 25600, 25450]:
            if test_strike in strike_data_list and 'ce' in strike_data_list[test_strike] and 'pe' in strike_data_list[test_strike]:
                ce_p = strike_data_list[test_strike]['ce'].get('close_price')
                pe_p = strike_data_list[test_strike]['pe'].get('close_price')
                if ce_p is not None and pe_p is not None:
                    # S = C - P + K
                    spot_price = ce_p - pe_p + test_strike
                    break

        if spot_price == 0:
            print(f"Warning: Could not calculate spot for interval {interval_str}")
            continue

        clean_data = []
        for strike, data in strike_data_list.items():
            ce = data.get('ce')
            pe = data.get('pe')
            if not ce or not pe: continue

            c_ltp = ce.get('close_price')
            c_oi = ce.get('oi')
            c_chng_oi = ce.get('oi_change_gross')
            c_trend = ce.get('buildup') or "Neutral"

            p_ltp = pe.get('close_price')
            p_oi = pe.get('oi')
            p_chng_oi = pe.get('oi_change_gross')
            p_trend = pe.get('buildup') or "Neutral"

            if c_ltp is None or p_ltp is None: continue

            # Calculate IV and Greeks
            c_iv = get_implied_volatility(c_ltp, spot_price, strike, T, config.RISK_FREE_RATE, 'CE') * 100
            p_iv = get_implied_volatility(p_ltp, spot_price, strike, T, config.RISK_FREE_RATE, 'PE') * 100

            c_greeks = calculate_greeks(spot_price, strike, T, config.RISK_FREE_RATE, c_iv/100, 'CE')
            p_greeks = calculate_greeks(spot_price, strike, T, config.RISK_FREE_RATE, p_iv/100, 'PE')

            clean_data.append({
                'strike': strike, 'c_ltp': c_ltp, 'c_oi': c_oi, 'c_chng_oi': c_chng_oi, 'c_iv': round(c_iv, 2),
                'c_delta': c_greeks['delta'], 'c_theta': c_greeks['theta'], 'c_trend': c_trend,
                'p_ltp': p_ltp, 'p_oi': p_oi, 'p_chng_oi': p_chng_oi, 'p_iv': round(p_iv, 2),
                'p_delta': p_greeks['delta'], 'p_theta': p_greeks['theta'], 'p_trend': p_trend
            })

        if clean_data:
            df = pd.DataFrame(clean_data)
            data_json = df.to_json(orient='records')

            cursor.execute('''
                INSERT INTO option_chain_snapshots (timestamp, symbol, expiry, spot_price, data_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp_str, SYMBOL, EXPIRY, spot_price, data_json))
            print(f"  Saved snapshot for {timestamp_str} (Spot: {spot_price:.2f}, Strikes: {len(clean_data)})")

    conn.commit()
    conn.close()
    print("Data filling complete.")

if __name__ == "__main__":
    main()
