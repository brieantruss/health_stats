import os
import json
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

# --- Configuration paths ---
GDRIVE_CREDENTIALS_PATHS = [
    "/home/briean/.gcp/gdrive_credentials.json",
    "/home/briean/dev/backups/config/gdrive_credentials.json"
]
REPORTS_FOLDER_ID = "1C5xjMCKFARv2gT0V-oLbaCNWEWkE4CMx" # Your personal backups reports GDrive folder!

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_gdrive_service():
    """Initializes and returns the Google Drive API service client."""
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
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logging.error(f"Failed to initialize Google Drive service: {e}")
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
