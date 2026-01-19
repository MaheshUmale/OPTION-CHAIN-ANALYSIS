import sqlite3
import pandas as pd
import json
import datetime

DB_NAME = "option_chain.db"

def init_db():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()

    # Table for storing snapshots
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS option_chain_snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            symbol TEXT,
            expiry TEXT,
            spot_price REAL,
            data_json TEXT
        )
    ''')

    conn.commit()
    conn.close()

def save_snapshot(symbol, expiry, spot_price, df_data):
    """
    Saves a snapshot of the option chain to the database.
    df_data should be a pandas DataFrame.
    """
    conn = sqlite3.connect(DB_NAME)
    # Convert DataFrame to JSON for storage
    data_json = df_data.to_json(orient='records')

    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO option_chain_snapshots (symbol, expiry, spot_price, data_json)
        VALUES (?, ?, ?, ?)
    ''', (symbol, expiry, spot_price, data_json))

    conn.commit()
    conn.close()

def get_latest_snapshot(symbol, expiry):
    """
    Retrieves the latest snapshot for a given symbol and expiry.
    """
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT timestamp, spot_price, data_json
        FROM option_chain_snapshots
        WHERE symbol = ? AND expiry = ?
        ORDER BY timestamp DESC LIMIT 1
    '''
    df = pd.read_sql_query(query, conn, params=(symbol, expiry))
    conn.close()

    if not df.empty:
        import io
        snapshot_time = df.iloc[0]['timestamp']
        spot_price = df.iloc[0]['spot_price']
        data = pd.read_json(io.StringIO(df.iloc[0]['data_json']))
        return snapshot_time, spot_price, data
    return None, None, None

def get_historical_snapshots(symbol, expiry):
    """
    Retrieves historical snapshots for a given symbol and expiry.
    """
    conn = sqlite3.connect(DB_NAME)
    query = '''
        SELECT timestamp, spot_price, data_json
        FROM option_chain_snapshots
        WHERE symbol = ? AND expiry = ?
        ORDER BY timestamp ASC
    '''
    df = pd.read_sql_query(query, conn, params=(symbol, expiry))
    conn.close()
    return df

if __name__ == "__main__":
    init_db()
    print("Database initialized.")
