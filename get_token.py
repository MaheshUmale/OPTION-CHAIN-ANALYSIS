from fyers_apiv3 import fyersModel
import webbrowser
import config
import os

def get_access_token():
    print("--- Fyers Auto-Login ---")
    
    # 1. Create Session
    session = fyersModel.SessionModel(
        client_id=config.CLIENT_ID,
        secret_key=config.SECRET_KEY,
        redirect_uri=config.REDIRECT_URI,
        response_type="code",
        grant_type="authorization_code"
    )

    # 2. Generate and Open Login URL
    auth_link = session.generate_authcode()
    print("\n1. Opening Browser to Login...")
    webbrowser.open(auth_link)
    
    # 3. User Pastes the URL
    print("\n2. After login, you will be redirected to Google.")
    print("   COPY the entire URL from the address bar and paste it below.")
    new_url = input("   👉 Paste Redirect URL: ").strip()
    
    # 4. Extract Code & Generate Token
    try:
        if "auth_code=" not in new_url:
            print("\n❌ Error: URL does not contain 'auth_code'. Try again.")
            return

        auth_code = new_url.split("auth_code=")[1].split("&")[0]
        session.set_token(auth_code)
        response = session.generate_token()
        
        if "access_token" in response:
            access_token = response["access_token"]
            with open("access_token.txt", "w") as f:
                f.write(access_token)
            print("\n✅ SUCCESS! Token saved to 'access_token.txt'.")
            print("   You can now run 'main.py'.")
        else:
            print(f"\n❌ Login Failed: {response}")

    except Exception as e:
        print(f"\n❌ Exception: {e}")

if __name__ == "__main__":
    get_access_token()