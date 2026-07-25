import os
from google_auth_oauthlib.flow import InstalledAppFlow
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request

CLIENT_SECRETS_FILE = "/home/briean/.gcp/client_secrets.json"
TOKEN_FILE = "/home/briean/.gcp/gdrive_user_token.json"
SCOPES = ["https://www.googleapis.com/auth/drive"]

def authenticate_user():
    creds = None
    # Load existing token if available
    if os.path.exists(TOKEN_FILE):
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("Starting new authentication flow...")
            if not os.path.exists(CLIENT_SECRETS_FILE):
                raise FileNotFoundError(f"Missing {CLIENT_SECRETS_FILE}")
                
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            # Use run_local_server with open_browser=False so it prints a clear link for copy-pasting
            creds = flow.run_local_server(port=8080, prompt="select_account", open_browser=False)
            
        # Save the credentials for the next run
        with open(TOKEN_FILE, "w") as token:
            token.write(creds.to_json())
            
        print(f"🎉 Success! Personal user token saved to {TOKEN_FILE}")
    else:
        print(f"✅ Credentials are already valid and saved at {TOKEN_FILE}")

if __name__ == "__main__":
    authenticate_user()
