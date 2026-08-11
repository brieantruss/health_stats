import os
import json
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from google.oauth2.credentials import Credentials
from google.auth.transport.requests import Request
from googleapiclient.http import MediaFileUpload

# --- Configuration paths ---
GDRIVE_CREDENTIALS_PATHS = [
    "/home/briean/.gcp/gdrive_credentials.json",
    "/home/briean/dev/backups/config/gdrive_credentials.json"
]
REPORTS_FOLDER_ID = "1C5xjMCKFARv2gT0V-oLbaCNWEWkE4CMx" # Your personal backups reports GDrive folder!

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

USER_TOKEN_PATH = "/home/briean/.gcp/gdrive_user_token.json"
CLIENT_SECRETS_PATH = "/home/briean/.gcp/client_secrets.json"
SCOPES = [
    "https://www.googleapis.com/auth/drive",
    "https://www.googleapis.com/auth/spreadsheets"
]

def get_google_creds():
    """Retrieves and refreshes Google OAuth 2.0 User credentials, or falls back to Service Account."""
    # 1. Try to load personal OAuth 2.0 User credentials first
    if os.path.exists(USER_TOKEN_PATH):
        try:
            logging.info("🔑 Attempting to authenticate using Google Drive User Credentials (OAuth 2.0)...")
            creds = Credentials.from_authorized_user_file(USER_TOKEN_PATH, SCOPES)
            if creds and creds.expired and creds.refresh_token:
                logging.info("🔄 Google Drive User token expired, refreshing...")
                creds.refresh(Request())
                with open(USER_TOKEN_PATH, "w") as token_file:
                    token_file.write(creds.to_json())
            return creds
        except Exception as e:
            logging.error(f"⚠️ User OAuth authentication failed, falling back: {e}")

    # 2. Fall back to Google Service Account credentials
    logging.info("💼 User token not found or failed, falling back to Service Account...")
    creds_path = None
    for path in GDRIVE_CREDENTIALS_PATHS:
        if os.path.exists(path):
            creds_path = path
            break
            
    if not creds_path:
        logging.error(f"❌ Google Drive credentials not found at any expected paths: {GDRIVE_CREDENTIALS_PATHS}.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            creds_path, 
            scopes=SCOPES
        )
        return creds
    except Exception as e:
        logging.error(f"Failed to initialize Google Service Account credentials: {e}")
        return None

def get_gdrive_service():
    """Initializes and returns the Google Drive API service client."""
    creds = get_google_creds()
    if creds:
        return build("drive", "v3", credentials=creds)
    return None

def get_gsheets_service():
    """Initializes and returns the Google Sheets API service client."""
    creds = get_google_creds()
    if creds:
        return build("sheets", "v4", credentials=creds)
    return None

def upload_report_to_gdrive(file_path):
    """Uploads a local report file directly to your personal backups reports folder on Google Drive."""
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist.")
        return False

    gdrive_service = get_gdrive_service()
    if not gdrive_service:
        return False

    try:
        file_name = os.path.basename(file_path)
        
        # Check if file with the same name already exists in your reports folder to overwrite/update
        query = f"name = '{file_name}' and '{REPORTS_FOLDER_ID}' in parents and trashed = false"
        results = gdrive_service.files().list(q=query, fields="files(id)").execute()
        existing_files = results.get("files", [])

        file_metadata = {
            'name': file_name,
            'parents': [REPORTS_FOLDER_ID]
        }
        media = MediaFileUpload(file_path, mimetype='text/markdown')

        if existing_files:
            file_id = existing_files[0].get("id")
            # Overwrite existing file
            gdrive_service.files().update(fileId=file_id, media_body=media).execute()
            logging.info(f"✅ Successfully updated report in personal Google Drive: {file_name}")
        else:
            # Create new file
            gdrive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logging.info(f"✅ Successfully uploaded new report to personal Google Drive: {file_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to upload report to Google Drive: {e}")
        return False


def append_to_gsheet(sheet_name, headers, row_data):
    """
    Checks if a Google Sheet with sheet_name exists in REPORTS_FOLDER_ID.
    If not, creates it and writes the headers.
    Then, checks if a row with the same Date (first column of row_data) already exists in the sheet.
    If it exists, updates that row with the latest data.
    If not, appends the row to the bottom.
    """
    gdrive_service = get_gdrive_service()
    sheets_service = get_gsheets_service()
    if not gdrive_service or not sheets_service:
        logging.error("❌ Unable to initialize Google Drive or Sheets service.")
        return False

    try:
        # Normalize date format if it's the first element
        if row_data and isinstance(row_data[0], str):
            normalized_date = row_data[0].replace('/', '-').replace('.', '-')
            row_data[0] = normalized_date

        # 1. Search for the Google Sheet by name in the specified folder
        query = f"name = '{sheet_name}' and mimeType = 'application/vnd.google-apps.spreadsheet' and '{REPORTS_FOLDER_ID}' in parents and trashed = false"
        results = gdrive_service.files().list(q=query, fields="files(id)").execute()
        existing_files = results.get("files", [])

        if existing_files:
            spreadsheet_id = existing_files[0].get("id")
            logging.info(f"📂 Found existing Google Sheet: '{sheet_name}' (ID: {spreadsheet_id})")
        else:
            # Create a new Google Sheet
            file_metadata = {
                'name': sheet_name,
                'mimeType': 'application/vnd.google-apps.spreadsheet',
                'parents': [REPORTS_FOLDER_ID]
            }
            file = gdrive_service.files().create(body=file_metadata, fields='id').execute()
            spreadsheet_id = file.get('id')
            logging.info(f"🆕 Created new Google Sheet: '{sheet_name}' (ID: {spreadsheet_id})")
            
            # Write headers as the first row
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range="Sheet1!A1",
                valueInputOption="USER_ENTERED",
                body={"values": [headers]}
            ).execute()
            logging.info(f"📝 Wrote headers to new Google Sheet: {headers}")

        # 2. Check if the date already exists in the first column (Column A)
        target_date = row_data[0]
        result = sheets_service.spreadsheets().values().get(
            spreadsheetId=spreadsheet_id,
            range="Sheet1!A:A"
        ).execute()
        rows = result.get('values', [])

        row_index = -1
        for idx, row in enumerate(rows):
            if row and row[0] == target_date:
                row_index = idx
                break

        if row_index != -1:
            # Update existing row (remember Sheets are 1-indexed, and rows are 0-indexed)
            sheet_row_num = row_index + 1
            update_range = f"Sheet1!A{sheet_row_num}"
            sheets_service.spreadsheets().values().update(
                spreadsheetId=spreadsheet_id,
                range=update_range,
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
            logging.info(f"🔄 Updated existing row for date {target_date} in sheet '{sheet_name}' at row {sheet_row_num}")
        else:
            # Append new row
            append_range = "Sheet1!A1"
            sheets_service.spreadsheets().values().append(
                spreadsheetId=spreadsheet_id,
                range=append_range,
                valueInputOption="USER_ENTERED",
                body={"values": [row_data]}
            ).execute()
            logging.info(f"➕ Appended new row for date {target_date} to sheet '{sheet_name}'")

        return True
    except Exception as e:
        logging.error(f"❌ Failed to write to Google Sheet '{sheet_name}': {e}")
        return False
