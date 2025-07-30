from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import re
import sys
from datetime import datetime

# --- Google Drive Configuration ---
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
# This is the new Google Drive folder ID as per your request
DRIVE_FOLDER_ID = '15qiYQIdtWw8--XkwM8pRc9Svx5xUvymD'

# --- Move files ---

def move_files_local(service_account_file, local_save_path):
    """
    Downloads files from Google Drive to a local directory, checking for existing files and
    replacing them with the latest modified version if new data is available.
    Handles both binary files and Google Docs Editor files (like Sheets exported as CSV).
    """

    print(f"Using service account file: {service_account_file}")
    print(f"Saving files to local path: {local_save_path}")

    # Authenticate with Google Drive API
    try:
        credentials = service_account.Credentials.from_service_account_file(
            service_account_file, scopes=DRIVE_SCOPES)
        drive_service = build('drive', 'v3', credentials=credentials)
    except Exception as e:
        print(f"Authentication failed: {e}")
        return # Exit if authentication fails

    # Ensure the local save directory exists
    os.makedirs(local_save_path, exist_ok=True)

    # Get list of files in the Google Drive folder
    page_token = None
    all_items = []
    while True:
        try:
            results = drive_service.files().list(
                q=f"'{DRIVE_FOLDER_ID}' in parents",
                # Include mimeType in fields to differentiate between regular files and Docs Editor files
                fields="nextPageToken, files(id, name, modifiedTime, mimeType)",
                pageToken=page_token
            ).execute()
            items = results.get('files', [])
            all_items.extend(items) # Add the retrieved items to the list
            page_token = results.get('nextPageToken', None)
            if page_token is None:
                break # No more pages
        except Exception as e:
            print(f"Error listing files from Google Drive: {e}")
            break # Exit loop on error

    # Regex pattern to match filenames like YYYYMMDD.csv
    # The ^ and $ ensure the entire string must match the pattern.
    filename_pattern = re.compile(r"^\d{8}\.csv$")
    files_downloaded_or_updated = False

    if not all_items:
        print('No files found in the Google Drive folder.')
    else:
        for item in all_items:
            file_name = item['name']
            file_modified_time = item['modifiedTime'] # ISO 8601 format string
            file_mime_type = item.get('mimeType') # Get the MIME type of the file
            local_file_path = os.path.join(local_save_path, file_name)

            # Check if the file name matches the desired pattern
            if filename_pattern.match(file_name):
                file_id = item['id']

                try:
                    local_file_exists = os.path.exists(local_file_path)
                    
                    # Convert Google Drive modifiedTime (e.g., '2025-06-19T10:30:00.123Z')
                    # to a comparable timestamp (seconds since epoch)
                    drive_modified_dt = datetime.strptime(file_modified_time.split('.')[0], '%Y-%m-%dT%H:%M:%S')
                    drive_modified_timestamp = drive_modified_dt.timestamp()

                    local_modified_timestamp = 0.0
                    if local_file_exists:
                        local_modified_timestamp = os.path.getmtime(local_file_path)

                    # Compare modification times: download/update if local file doesn't exist
                    # or if the Google Drive file is newer.
                    if not local_file_exists or local_modified_timestamp < drive_modified_timestamp:
                        print(f'Attempting to download/update file: {file_name}')

                        # Determine download method based on MIME type
                        # Google Docs Editor files (like Sheets) need to be exported
                        if file_mime_type and file_mime_type.startswith('application/vnd.google-apps'):
                            # For Google Sheets, export as CSV
                            print(f"File {file_name} is a Google Docs Editor file, attempting to export as CSV.")
                            request = drive_service.files().export_media(
                                fileId=file_id,
                                mimeType='text/csv'
                            )
                        else:
                            # For regular binary files
                            print(f"File {file_name} is a standard binary file, attempting direct download.")
                            request = drive_service.files().get_media(fileId=file_id)
                        
                        response = request.execute()
                        with open(local_file_path, 'wb') as f:
                            f.write(response)

                        # Update the local file's modification time to match Google Drive
                        # This is crucial for future comparisons to work correctly.
                        os.utime(local_file_path, (drive_modified_timestamp, drive_modified_timestamp))
                        
                        print(f'Successfully downloaded/updated file {file_name} to {local_file_path}')
                        files_downloaded_or_updated = True
                    else:
                        print(f'Skipping file {file_name} - local file is already the latest version.')
                except Exception as e:
                    print(f"An error occurred processing {file_name}: {e}")
            else:
                print(f"Skipping file {file_name} - does not match the 'YYYYMMDD.csv' pattern.")

    if not files_downloaded_or_updated:
        print("No new files or updates were downloaded.")

if __name__ == '__main__':
    # Expecting two arguments: service_account_file and local_save_path
    if len(sys.argv) != 3:
        print("Usage: python3 <your_script_name>.py <service_account_file_path> <local_save_path>")
        sys.exit(1)

    service_account_file = sys.argv[1]
    local_save_path = sys.argv[2]

    move_files_local(service_account_file, local_save_path)
