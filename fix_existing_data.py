import sqlite3
import json
import pandas as pd
import io

DB_NAME = "option_chain.db"

def fix_data():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Get symbols and expiries
    cursor.execute("SELECT DISTINCT symbol, expiry FROM option_chain_snapshots")
    groups = cursor.fetchall()

    for symbol, expiry in groups:
        print(f"Processing {symbol} | {expiry}...")
        cursor.execute("SELECT id, timestamp, data_json FROM option_chain_snapshots WHERE symbol=? AND expiry=? ORDER BY timestamp ASC", (symbol, expiry))
        rows = cursor.fetchall()

        prev_oi_map = {} # strike -> (c_oi, p_oi)

        for i, (row_id, ts, data_json) in enumerate(rows):
            data = json.loads(data_json)
            new_data = []

            for item in data:
                strike = item['strike']
                c_oi = item.get('c_oi', 0)
                p_oi = item.get('p_oi', 0)

                if strike in prev_oi_map:
                    prev_c_oi, prev_p_oi = prev_oi_map[strike]
                    item['c_chng_oi'] = c_oi - prev_c_oi
                    item['p_chng_oi'] = p_oi - prev_p_oi
                else:
                    # For the first row, we keep it as is or set to 0.
                    # Setting to 0 is safer for cumulative sums.
                    item['c_chng_oi'] = 0
                    item['p_chng_oi'] = 0

                prev_oi_map[strike] = (c_oi, p_oi)
                new_data.append(item)

            # Update the DB
            new_json = json.dumps(new_data)
            cursor.execute("UPDATE option_chain_snapshots SET data_json=? WHERE id=?", (new_json, row_id))

        print(f"  Fixed {len(rows)} snapshots.")

    conn.commit()
    conn.close()
    print("Migration complete.")

if __name__ == "__main__":
    fix_data()
