import os
import sys
import json
import requests

CREDENTIALS_PATH = "/home/briean/dev/backups/config/dropbox_credentials.json"

def authenticate_dropbox():
    print("====================================================")
    print("🛡️  Dropbox Long-Lived OAuth 2.0 Auth Helper  🛡️")
    print("====================================================")
    print("This helper will guide you to set up a permanent refresh token.")
    print("First, obtain your App Key and App Secret from the Dropbox Console:")
    print("👉 https://www.dropbox.com/developers/apps\n")

    app_key = input("Enter your Dropbox App Key: ").strip()
    app_secret = input("Enter your Dropbox App Secret: ").strip()

    if not app_key or not app_secret:
        print("❌ App Key and App Secret are required!")
        sys.exit(1)

    # 1. Print the authorization URL with token_access_type=offline (triggers refresh token)
    auth_url = f"https://www.dropbox.com/oauth2/authorize?client_id={app_key}&token_access_type=offline&response_type=code"
    
    print("\n----------------------------------------------------")
    print("Step 1: Open the following URL in your web browser:")
    print(auth_url)
    print("----------------------------------------------------")
    print("Log in, click 'Allow', and copy the authorization code given.")

    auth_code = input("\nStep 2: Enter the authorization code here: ").strip()

    if not auth_code:
        print("❌ Authorization code is required!")
        sys.exit(1)

    # 2. Exchange authorization code for access and refresh tokens
    print("\nExchanging code for permanent refresh token...")
    try:
        response = requests.post(
            "https://api.dropboxapi.com/oauth2/token",
            data={
                "code": auth_code,
                "grant_type": "authorization_code",
                "client_id": app_key,
                "client_secret": app_secret
            }
        )
        
        token_data = response.json()
        
        if "error" in token_data:
            print(f"❌ Exchange failed: {token_data.get('error_description', token_data['error'])}")
            sys.exit(1)

        refresh_token = token_data.get("refresh_token")
        access_token = token_data.get("access_token")

        if not refresh_token:
            print("❌ Did not receive a refresh token! Make sure you didn't skip any authorization prompts.")
            sys.exit(1)

        # 3. Save to credentials file
        credentials = {
            "app_key": app_key,
            "app_secret": app_secret,
            "refresh_token": refresh_token,
            "access_token": access_token
        }

        os.makedirs(os.path.dirname(CREDENTIALS_PATH), exist_ok=True)
        with open(CREDENTIALS_PATH, "w", encoding="utf-8") as f:
            json.dump(credentials, f, indent=2)

        print("\n----------------------------------------------------")
        print(f"🎉 SUCCESS! Permanent Dropbox credentials written to:")
        print(CREDENTIALS_PATH)
        print("Your automated backup scripts will now run forever on autopilot!")
        print("----------------------------------------------------")

    except Exception as e:
        print(f"❌ Network/Request error occurred: {e}")
        sys.exit(1)

if __name__ == "__main__":
    authenticate_dropbox()
