import requests
import config

class UpstoxEngine:
    def __init__(self, token=None):
        self.token = token or config.UPSTOX_TOKEN
        self.base_url = "https://api.upstox.com/v2"
        self.headers = {
            'Accept': 'application/json',
            'Authorization': f'Bearer {self.token}'
        }

    def get_spot_price(self, instrument_key):
        """
        Fetches the last traded price for a given instrument.
        """
        # Upstox Quote API expects symbols to be comma separated if multiple
        # And it uses | or : depending on the context, but usually expects | in the request
        url = f"{self.base_url}/market-quote/quotes"
        params = {'symbol': instrument_key}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                # The response structure for quotes is a bit nested
                # Upstox might return key as "NSE_INDEX:Nifty 50" instead of "NSE_INDEX|Nifty 50" in data
                # Or "NSE_EQ|RELIANCE"
                # We normalize the keys by replacing : with | for matching
                search_key = instrument_key.replace(":", "|")
                for key, val in data['data'].items():
                    normalized_key = key.replace(":", "|")
                    if search_key == normalized_key:
                        return val.get('last_price', 0)
        return 0

    def get_option_chain(self, instrument_key, expiry_date):
        """
        Fetches the option chain for a given underlying and expiry date.
        """
        url = f"{self.base_url}/option/chain"
        params = {
            'instrument_key': instrument_key,
            'expiry_date': expiry_date
        }
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                return data['data']
        else:
            print(f"Error fetching option chain: {response.status_code} - {response.text}")
        return []

    def get_expiry_dates(self, instrument_key):
        """
        Fetches available expiry dates for a given underlying.
        """
        url = f"{self.base_url}/option/contract"
        params = {'instrument_key': instrument_key}
        response = requests.get(url, headers=self.headers, params=params)
        if response.status_code == 200:
            data = response.json()
            if data['status'] == 'success':
                # Extract unique expiry dates
                expiries = sorted(list(set(item['expiry'] for item in data['data'])))
                return expiries
        return []

if __name__ == "__main__":
    # Test
    engine = UpstoxEngine()
    spot = engine.get_spot_price("NSE_INDEX|Nifty 50")
    print(f"Spot Price: {spot}")
    # expiries = engine.get_expiry_dates("NSE_INDEX|Nifty 50")
    # print(f"Expiries: {expiries}")
