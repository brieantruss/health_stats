import os
import json
import logging
from googleapiclient.discovery import build
from google.oauth2 import service_account
from googleapiclient.http import MediaFileUpload

# --- Configuration paths ---
GDRIVE_CREDENTIALS_PATH = "/home/briean/dev/backups/config/gdrive_credentials.json"

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_gdrive_service():
    """Initializes and returns the Google Drive API service client."""
    if not os.path.exists(GDRIVE_CREDENTIALS_PATH):
        logging.error(f"❌ Google Drive credentials not found at {GDRIVE_CREDENTIALS_PATH}.")
        return None
    try:
        creds = service_account.Credentials.from_service_account_file(
            GDRIVE_CREDENTIALS_PATH, 
            scopes=["https://www.googleapis.com/auth/drive"]
        )
        return build("drive", "v3", credentials=creds)
    except Exception as e:
        logging.error(f"Failed to initialize Google Drive service: {e}")
        return None

def resolve_or_create_reports_folder(gdrive_service):
    """Finds or dynamically creates a folder named 'reports' in Google Drive."""
    try:
        # 1. Search for existing 'reports' folder shared with the Service Account
        query = "name = 'reports' and mimeType = 'application/vnd.google-apps.folder' and trashed = false"
        results = gdrive_service.files().list(q=query, fields="files(id)").execute()
        files = results.get("files", [])
        if files:
            return files[0].get("id")
        
        # 2. If not found, create a new root folder named 'reports'
        folder_metadata = {
            'name': 'reports',
            'mimeType': 'application/vnd.google-apps.folder'
        }
        folder = gdrive_service.files().create(body=folder_metadata, fields='id').execute()
        logging.info(f"📁 Created new Google Drive reports folder: {folder.get('id')}")
        return folder.get('id')
    except Exception as e:
        logging.error(f"Failed to resolve/create GDrive reports folder: {e}")
        return None

def upload_report_to_gdrive(file_path):
    """Uploads a local report file to the Google Drive 'reports' folder."""
    if not os.path.exists(file_path):
        logging.error(f"File {file_path} does not exist.")
        return False

    gdrive_service = get_gdrive_service()
    if not gdrive_service:
        return False

    folder_id = resolve_or_create_reports_folder(gdrive_service)
    if not folder_id:
        return False

    try:
        file_name = os.path.basename(file_path)
        
        # Check if file with the same name already exists in the reports folder to overwrite
        query = f"name = '{file_name}' and '{folder_id}' in parents and trashed = false"
        results = gdrive_service.files().list(q=query, fields="files(id)").execute()
        existing_files = results.get("files", [])

        file_metadata = {
            'name': file_name,
            'parents': [folder_id]
        }
        media = MediaFileUpload(file_path, mimetype='text/markdown')

        if existing_files:
            file_id = existing_files[0].get("id")
            # Overwrite existing file
            gdrive_service.files().update(fileId=file_id, media_body=media).execute()
            logging.info(f"✅ Successfully updated report in Google Drive: {file_name}")
        else:
            # Create new file
            gdrive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
            logging.info(f"✅ Successfully uploaded new report to Google Drive: {file_name}")
        return True
    except Exception as e:
        logging.error(f"Failed to upload report to Google Drive: {e}")
        return False
