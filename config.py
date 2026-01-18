# --- CONFIGURATION FILE ---

# 1. FYERS API CREDENTIALS
# Go to https://myapi.fyers.in/dashboard to get these
CLIENT_ID = "XXXXXXXXXX-100"  # Format: XXXXXX-100
SECRET_KEY = "XXXXXXXXXX"
REDIRECT_URI = "http://127.0.0.1" # Must match what you set in Fyers App
User_Name = "XS0000"              # Your Fyers User ID
TOTP_KEY = ""                     # Leave empty for manual login

# 2. GOOGLE SHEET SETTINGS
SPREADSHEET_ID = "1FN6qKkCyWsw2SrlGKCJ09rDbtJX_S8G-rCAB0og55_8"
CREDENTIALS_FILE = "credentials.json"

# 3. TRADING CONFIG
# For Fyers, Symbols look like: "NSE:NIFTYBANK-INDEX" or "NSE:NIFTY50-INDEX"
SYMBOL = "NSE:RELIANCE-EQ" 
EXPIRY_DATE = "2026-02-24" # Format: YYYY-MM-DD. Ensure this matches the STOCK monthly expiry!
RISK_FREE_RATE = 0.07