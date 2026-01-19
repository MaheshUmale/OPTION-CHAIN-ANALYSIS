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
from database import get_latest_snapshot

DB_NAME = "option_chain.db"

TRACKED_SYMBOLS = [
    {
        "symbol": "NSE_INDEX|Nifty 50",
        "expiry": "2026-01-20",
        "trendlyne_symbol": "NIFTY",
        "trendlyne_expiry": "20-jan-2026-near",
        "strikes": range(25000, 26050, 50),
        "spot_calc_strikes": [25550, 25500, 25600]
    },
    {
        "symbol": "NSE_INDEX|Nifty Bank",
        "expiry": "2026-01-27",
        "trendlyne_symbol": "BANKNIFTY",
        "trendlyne_expiry": "27-jan-2026-near",
        "strikes": range(59000, 61050, 100),
        "spot_calc_strikes": [60000, 59900, 60100]
    }
]

def fetch_trendlyne_data(trendlyne_expiry, trendlyne_symbol, strike, opt_type):
    url = f"https://smartoptions.trendlyne.com/phoenix/api/fno/buildup-5/{trendlyne_expiry}/{trendlyne_symbol}/?fno_mtype=options&strikePrice={strike}&option_type={opt_type}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
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

def process_symbol(config_item, conn):
    symbol = config_item['symbol']
    expiry = config_item['expiry']
    trendlyne_symbol = config_item['trendlyne_symbol']
    trendlyne_expiry = config_item['trendlyne_expiry']
    strikes = config_item['strikes']

    all_data = {} # (interval) -> {strike -> {ce_data, pe_data}}

    print(f"Fetching Trendlyne data for {symbol}...")
    for strike in strikes:
        print(f"  Strike {strike}...", end="", flush=True)
        ce_json = fetch_trendlyne_data(trendlyne_expiry, trendlyne_symbol, strike, "call")
        time.sleep(0.2)
        pe_json = fetch_trendlyne_data(trendlyne_expiry, trendlyne_symbol, strike, "put")
        time.sleep(0.2)

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

    intervals = sorted(all_data.keys())
    cursor = conn.cursor()

    print(f"Processing {len(intervals)} intervals for {symbol}...")
    for interval_str in intervals:
        # Snapshot time is the END of the interval
        end_time_str = interval_str.split(" TO ")[1]
        timestamp_str = f"2026-01-19 {end_time_str}:00"

        # Check if snapshot already exists
        cursor.execute("SELECT 1 FROM option_chain_snapshots WHERE timestamp=? AND symbol=? AND expiry=?", (timestamp_str, symbol, expiry))
        if cursor.fetchone():
            print(f"  Skipping {timestamp_str} (already exists)")
            continue

        current_time = datetime.datetime.strptime(timestamp_str, "%Y-%m-%d %H:%M:%S")
        T = get_time_to_expiry_at(expiry, current_time)

        # Fetch previous snapshot FROM DATABASE to calculate delta (handles 1m/5m gaps correctly)
        _, _, prev_df = get_latest_snapshot(symbol, expiry, same_day_only=True)
        prev_data_map = {}
        if prev_df is not None:
            for _, row in prev_df.iterrows():
                prev_data_map[row['strike']] = row

        strike_data_list = all_data[interval_str]

        # Estimate spot price from Trendlyne interval close prices
        spot_price = 0
        for test_strike in config_item['spot_calc_strikes']:
            if test_strike in strike_data_list and 'ce' in strike_data_list[test_strike] and 'pe' in strike_data_list[test_strike]:
                ce_p = strike_data_list[test_strike]['ce'].get('close_price')
                pe_p = strike_data_list[test_strike]['pe'].get('close_price')
                if ce_p and pe_p:
                    spot_price = ce_p - pe_p + test_strike
                    break

        if spot_price == 0: continue

        clean_data = []
        for strike, data in strike_data_list.items():
            ce = data.get('ce')
            pe = data.get('pe')
            if not ce or not pe: continue

            c_ltp = ce.get('close_price')
            c_oi = ce.get('oi', 0)

            p_ltp = pe.get('close_price')
            p_oi = pe.get('oi', 0)

            if c_ltp is None or p_ltp is None: continue

            # Dynamic delta calculation relative to whatever is in DB
            if strike in prev_data_map:
                prev_item = prev_data_map[strike]
                c_chng_oi = c_oi - prev_item.get('c_oi', c_oi)
                p_chng_oi = p_oi - prev_item.get('p_oi', p_oi)
                c_chng_price = c_ltp - prev_item.get('c_ltp', c_ltp)
                p_chng_price = p_ltp - prev_item.get('p_ltp', p_ltp)
            else:
                # If first snapshot or no prev data, use Trendlyne's gross change
                # (which is the change since previous 5-min interval)
                c_chng_oi = ce.get('oi_change_gross', 0)
                p_chng_oi = pe.get('oi_change_gross', 0)
                # Trendlyne JSON doesn't give price change easily for first, so Neutral
                c_chng_price = 0
                p_chng_price = 0

            c_iv = get_implied_volatility(c_ltp, spot_price, strike, T, 0.07, 'CE') * 100
            p_iv = get_implied_volatility(p_ltp, spot_price, strike, T, 0.07, 'PE') * 100
            c_greeks = calculate_greeks(spot_price, strike, T, 0.07, c_iv/100, 'CE')
            p_greeks = calculate_greeks(spot_price, strike, T, 0.07, p_iv/100, 'PE')

            # Trend calculation based on interval momentum
            c_trend = get_smart_trend(c_chng_price, c_chng_oi)
            p_trend = get_smart_trend(p_chng_price, p_chng_oi)

            clean_data.append({
                'strike': strike, 'c_ltp': c_ltp, 'c_oi': c_oi, 'c_chng_oi': c_chng_oi, 'c_iv': round(c_iv, 2),
                'c_delta': c_greeks['delta'], 'c_theta': c_greeks['theta'], 'c_trend': c_trend,
                'p_ltp': p_ltp, 'p_oi': p_oi, 'p_chng_oi': p_chng_oi, 'p_iv': round(p_iv, 2),
                'p_delta': p_greeks['delta'], 'p_theta': p_greeks['theta'], 'p_trend': p_trend
            })

        if clean_data:
            df = pd.DataFrame(clean_data)
            cursor.execute('''
                INSERT OR IGNORE INTO option_chain_snapshots (timestamp, symbol, expiry, spot_price, data_json)
                VALUES (?, ?, ?, ?, ?)
            ''', (timestamp_str, symbol, expiry, spot_price, df.to_json(orient='records')))
            conn.commit()
            print(f"  Saved snapshot for {timestamp_str}")

def main():
    conn = sqlite3.connect(DB_NAME)
    for config_item in TRACKED_SYMBOLS:
        process_symbol(config_item, conn)
    conn.close()
    print("Database filling complete.")

if __name__ == "__main__":
    main()
