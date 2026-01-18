# OPTION-CHAIN-ANALYSIS

CONVERT THIS CODE FROM FRYERS TO UPSTOX AND USE PYTHON UI/TABLES INSTEAD OF GOOGLE SHEETS


OVERALL LOGICAL EXPLAINATION OF EXISTING CODE 

# Money Matrix: The Universal Option

# Chain (User Manual)

## 1. Disclaimer

Trading in the stock market, especially in derivatives (Options & Futures), involves
substantial risk.

```
 This tool is a Decision Support System, not a "Magic Money Button."
 It provides mathematical data and calculated probabilities. It does not guarantee
profits.
 The signals ("STRONG BUY", "Bearish Bias") are algorithmic interpretations of
data, not financial advice.
 Always use Stop Losses. The creator (Money Matrix) assumes no responsibility for
financial losses incurred while using this system.
```
## 2. What is this System?

The Money Matrix is a professional-grade trading dashboard that bridges the gap between
institutional tools and retail traders.

Instead of looking at a static webpage that refreshes every 3 minutes, this system:

1. Connects Directly to the Fyers Broker API (Legal, Free, Millisecond Latency).
2. Calculates advanced metrics (Greeks, IV) using a custom "Math Engine" (Black-
    Scholes Model).
3. Detects hidden market movements (Smart Trend Logic).
4. Streams everything into a live Google Sheet, allowing you to analyze BankNifty,
    Nifty, or any Stock in real-time.

## 3. Killer Features

```
 The "Key Hunter": It is crash-proof. It automatically detects the correct data labels
from the API, so the script never breaks when the broker changes data formats.
 Math Engine: Even if the broker hides the Implied Volatility (IV) or Greeks, this
system calculates them from scratch using option pricing formulas.
 Smart Trends: It doesn't just look at "Price Up/Down." It analyzes the relationship
between Price Change and Open Interest (OI) Change to tell you if a move is a
"Long Buildup" (Real Buying) or just "Short Covering" (Temporary Bounce).
```

```
 Deep Market Vision: Unlike free websites that show only 10 strikes, this system
pulls upto 500 strikes, covering the entire market depth.
 The "Greeks" Edge:
o Theta (The Silent Killer): Shows how much money you lose per day just by
holding the trade.
o Gamma (The Explosion Index): Shows which strike price will explode
fastest if the market moves.
```
### 4. Key Trading Problems Solved

Problem The Money Matrix Solution

"Is the market Bullish or
Bearish?"

```
Look at PCR (Put-Call Ratio). If > 1.2, Big Players are Bullish. If < 0.6, they
are Bearish.
```
"Which Strike Price do I
pick?"

```
Check the Delta column.
```
- 0.50 (ATM): Best balance.
- 0.70+ (ITM): High speed, acts like a Future.
- < 0.20 (OTM): Garbage/Lottery ticket. Avoid.

"Should I Buy or Sell
(Write)?"

```
Check the Trend column.
```
- Long Buildup: BUY (Momentum is up).
- Short Buildup: SELL/WRITE (Big players are selling).
"Where will the market
stop?"

```
The Sheet calculates Ultimate Support & Resistance based on max OI
concentrations. Exit your trades there.
```
### 5. How to Setup (Installation Guide)

##### Phase A: One-Time PC Setup

1. Install Python: Download Python 3.10+ from python.org.
2. Install Libraries: Open Command Prompt (cmd) and run:

```
Bash
```
```
pip install pandas gspread oauth2client fyers-apiv3 scipy numpy
```
```
(Tip for Windows Users: Enable "File Name Extensions" in your File Explorer View
settings. This prevents you from accidentally naming files like main.py.txt .)
```

##### Phase B: Creating The Files

You need to create a folder named option_chain and create 4 specific files inside it.

1. **credentials.json**

```
 Go to Google Cloud Console.
 Enable "Google Sheets API" and "Google Drive API".
 Create Credentials > Service Account > Create Key (JSON).
 Download and rename this file to credentials.json.
 Crucial: Open this JSON file, find the client_email, copy it, and Share your
Google Sheet with that email (give Editor access).
```
2. **config.py**

```
 Create a new text file and rename it to config.py. Paste your settings code inside.
 Important: When entering EXPIRY_DATE, ALWAYS use the format YYYY-MM-
DD (e.g., 2026 - 01 - 29 ). Do not use DD-MM-YYYY.
 Important: For SPREADSHEET_ID, do not paste the name. Paste the long ID found in
your sheet's URL (between /d/ and /edit).
```
3. **get_token.py**

```
 Create a new text file, rename it to get_token.py, and paste the login script code.
```
4. **main.py**

```
 Create a new text file, rename it to main.py, and paste the final V2.1 script code.
```
##### Step-by-Step Fyers API Registration

(For users doing this for the first time)

Prerequisite: You must have an active trading account with Fyers.

1. Go to the Developer Portal: Open https://myapi.fyers.in/dashboard in your browser.
2. Login: Use your standard Fyers Client ID and Password/OTP.
3. Create a New App:
    o Click on the "Create App" button (usually top right).
    o App Name: Give it any name (e.g., MoneyMatrix).
    o Redirect URL: Enter https://google.com (This must match the URL in
       your config.py file exactly).
    o Description: Enter "Personal Trading Dashboard".
    o Permissions: Select all available permissions (Order, Data, etc.) or just "Data"
       if prompted.
    o Click "Create App".
4. Get Your Credentials:


```
o Once created, you will see your app in the list.
o App ID: This is your CLIENT_ID (It looks like XP00000- 100 ).
o Secret ID: Click the "eye" icon to reveal it. This is your SECRET_KEY.
o Copy these two codes and paste them into your config.py file.
```
##### Can people use other brokers (Zerodha, Dhan, Angel One)?

The Short Answer: No. This specific software (V2.1) will only work with Fyers.

The Explanation (to include in FAQ/Manual):

```
 Unique Language: Every broker speaks a different "coding language" (API). This
system is written specifically in the Fyers language (fyers_apiv3 library). It cannot
"talk" to Zerodha or Dhan.
 Why Fyers? We chose Fyers for this system because:
```
1. It is FREE: Zerodha charges ₹2,000/month for their API. Fyers gives it for
    free.
2. Option Chain Data: Fyers provides a pre-built "Option Chain" data packet
    (which we utilize). Other brokers like Dhan or Angel often require us to fetch
    100 different symbols individually, which is slower and more complex to
    code.
 Can it be converted? Yes, a developer could rewrite the "Engine" part of this script
to support Dhan or Angel One, but the current main.py file will strictly require a
Fyers account to function.

##### Phase D: Daily Routine

Every morning at 9:00 AM:

1. Open Terminal (cmd) inside your folder.
2. Run: python get_token.py
    o Login to Fyers in the browser window.
    o Paste the Result URL back into the terminal.
3. Run: python main.py
    o The system starts. Leave it running all day.


### 6. How to identify correct stock and index symbol?

The format NSE:NIFTYBANK-INDEX comes from the Fyers specific symbol naming
convention. Since Fyers is the data source, you must use their exact format, or the API will
say "Symbol Not Found."

##### The Universal Logic for Fyers Symbols

The format is always: EXCHANGE:SYMBOL-SUFFIX

**_1. For Indices (Nifty, BankNifty, FinNifty)_**

Indices always end with -INDEX.

```
 Bank Nifty: NSE:NIFTYBANK-INDEX
 Nifty 50: NSE:NIFTY50-INDEX
 Fin Nifty: NSE:FINNIFTY-INDEX
 Midcap Nifty: NSE:MIDCPNIFTY-INDEX
```
**_2. For Stocks (Reliance, HDFC, Tata Motors)_**

Stocks that have Future & Options (FnO) end with -EQ.

```
 Reliance: NSE:RELIANCE-EQ
 HDFC Bank: NSE:HDFCBANK-EQ
 Tata Motors: NSE:TATAMOTORS-EQ
 Infosys: NSE:INFY-EQ
 State Bank of India: NSE:SBIN-EQ
```
##### How to Find Any Symbol (If You Are Not Sure)

If you are confused (e.g., is it M&M or MNM?), follow this simple trick:

1. Go to the Fyers Web Platform: (https://trade.fyers.in/)
2. Search for the stock in the search bar (e.g., "Mahindra").
3. Add it to your Watchlist.
4. Look at the name:
    o If you see NSE:M&M-EQ, that is your symbol.
    o Copy that exact text into your config.py file.


### 7. How to Take Trade Decisions (The Strategy)

Do not trade on every tick. Wait for the data to align.

##### Scenario 1: The Bullish Breakout (Call Buy)

```
 PCR: Rising and above 1.0.
 Signal: Column M shows "STRONG BUY CE 🚀 " or "Bullish Bias 🚀 ".
 Trend: Call Side shows "Long Buildup" (Green).
 Volume Check: Ensure the "Call Vol" column is high (liquidity is present).
 Action: Buy an ATM Call (Delta ~0.5).
 Target: The "Resistance" strike price shown in Row 2.
```
##### Scenario 2: The Bearish Crash (Put Buy)

```
 PCR: Falling and below 0.
 Signal: Column M shows "STRONG BUY PE 🚀 " or "Bearish Bias 🚀 ".
 Trend: Put Side shows "Long Buildup".
 Action: Buy an ATM Put.
 Target: The "Support" strike price shown in Row 2.
```
##### Scenario 3: The Trap (Do Not Trade)

```
 PCR: Stuck between 0.8 and 1.1 (Neutral).
 Trend: Shows "Short Covering" or "Long Unwinding" (No real buying/selling, just
profit booking).
 Action: Sit on hands. Option Buyers lose money here due to Theta Decay.
```
**Trend Name Simple Explanation Sentiment**

**Long Buildup** "Big players are buying." Price is up, Interest is up. **Bullish**

**Short Covering "The Jackpot Move."** Sellers are trapped and exiting fast. This causes sudden spikes. **Super Bullish**

**Short Buildup** "Big players are selling." Price is down, Interest is up. **Bearish**

**Long Unwinding** "Buyers are tired." They are booking profits. **Weak / Paused**


### 8. Troubleshooting & Maintenance

```
 "Access Token Invalid": Fyers tokens expire every night. You must run
get_token.py once every morning.
 "Quota Exceeded": If Google Sheets stops updating, you might be refreshing too
fast. The script is set to 60 seconds, which is safe. Do not lower it to 5 seconds.
 "Expiry Not Found": Double-check your config.py. Ensure the date format is
YYYY-MM-DD.
 Empty Columns: If columns go blank, check the terminal window. The "Key
Hunter" feature will print a debug list of keys. You can verify if Fyers has changed
their data format.
```
 

