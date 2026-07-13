from googleapiclient.discovery import build
from google.oauth2 import service_account
import os
import re
import sys # Import sys module

# --- Google Drive Configuration ---
DRIVE_SCOPES = ['https://www.googleapis.com/auth/drive']
# SERVICE_ACCOUNT_FILE will be passed as a command-line argument

# Import the centralized folder configuration
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from drive_config import FOLDER_SLEEP_IDS as DRIVE_FOLDER_IDS

# --- Local Save Path Configuration ---
# LOCAL_SAVE_PATH will be passed as a command-line argument


# --- Move files ---

def move_files_local(service_account_file, local_save_path):
    """Downloads files from Google Drive to a local directory, checking for existing files and latest modified date."""

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

    filename_patterns = [
        re.compile(r"Sleep \d{4}\.\d{2}\.\d{2}( \d{2}\:\d{2}:\d{2})? Samsung Health\.csv"),
        re.compile(r"^Sleep \d{4}[\.\-_/\s]?\d{2}[\.\-_/\s]?\d{2}.*?Samsung Health\.csv$", re.IGNORECASE)
    ]
    files_downloaded = False

    # Iterate over all configured Google Drive folders to download sleep CSVs
    for folder_id in DRIVE_FOLDER_IDS:
        print(f"Checking Google Drive folder: {folder_id}")
        page_token = None
        all_items = []
        while True:
            try:
                results = drive_service.files().list(
                    q=f"'{folder_id}' in parents",
                    fields="nextPageToken, files(id, name, modifiedTime)",  # Include modifiedTime
                    pageToken=page_token
                ).execute()
                items = results.get('files', [])
                all_items.extend(items)  # Add the retrieved items to the list
                page_token = results.get('nextPageToken', None)
                if page_token is None:
                    break  # No more pages
            except Exception as e:
                print(f"Error listing files from Google Drive folder {folder_id}: {e}")
                break # Exit loop on error

        if not all_items:
            print(f'No files found in Google Drive folder {folder_id}.')
            continue

        for item in all_items:
            file_name = item['name']
            file_modified_time = item['modifiedTime']
            local_file_path = os.path.join(local_save_path, file_name)

            if any(pat.match(file_name) for pat in filename_patterns):
                file_id = item['id']

                try:
                    local_file_exists = os.path.exists(local_file_path)
                    # Convert Google Drive modifiedTime to a comparable format (seconds since epoch)
                    drive_modified_timestamp = int(datetime.strptime(file_modified_time, '%Y-%m-%dT%H:%M:%S.%fZ').timestamp())
                    local_modified_timestamp = os.path.getmtime(local_file_path) if local_file_exists else 0.0

                    if not local_file_exists or local_modified_timestamp < drive_modified_timestamp:
                        print(f'Downloading/Updating file: {file_name}')

                        # Download file from Google Drive
                        request = drive_service.files().get_media(fileId=file_id)
                        response = request.execute()
                        with open(local_file_path, 'wb') as f:
                            f.write(response)

                        # Update the local file's modification time to match Google Drive
                        os.utime(local_file_path, (drive_modified_timestamp, drive_modified_timestamp)) # Use drive_modified_timestamp for both atime and mtime

                        print(f'Successfully downloaded/updated file {file_name} to {local_file_path}')
                        files_downloaded = True
                    else:
                        print(f'Skipping file {file_name} - no changes detected.')
                except Exception as e:
                    print(f"An error occurred processing {file_name}: {e}")
            else:
                print(f"Skipping file {file_name} - does not match the pattern.")

    if not files_downloaded:
        print("No new updates.")

if __name__ == '__main__':
    from datetime import datetime # Still needed here for strptime

    # Expecting two arguments: service_account_file and local_save_path
    if len(sys.argv) != 3:
        print("Usage: python3 extract_steps.py <service_account_file_path> <local_save_path>")
        sys.exit(1)

    service_account_file = sys.argv[1]
    local_save_path = sys.argv[2]

    move_files_local(service_account_file, local_save_path)
