import os
import pandas as pd
import sys
from datetime import datetime

def process_files_pandas(raw_dir, processed_dir):
    """
    Processes raw heart rate files to prepare them for loading into MySQL.
    It focuses on extracting 'Date', 'Time', 'Heart_Rate' (from 'Heart rate (bpm)'),
    and adding a 'Last_Updated' timestamp, ensuring all are treated as strings.
    No rows are dropped due to parsing errors.
    """

    os.makedirs(processed_dir, exist_ok=True)
    print(f"Starting processing of files from {raw_dir} to {processed_dir}")

    if not os.listdir(raw_dir):
        print(f"Raw directory {raw_dir} is empty. No files to process.")
        return

    for filename in os.listdir(raw_dir):
        raw_file_path = os.path.join(raw_dir, filename)
        processed_file_path = os.path.join(processed_dir, filename)

        if not os.path.isfile(raw_file_path):
            continue

        try:
            print(f"Processing file: {filename}")
            df = pd.read_csv(raw_file_path)

            if df.empty:
                print(f"File {filename} contains no data rows or only headers. Skipping.")
                continue

            # Create new columns by directly mapping from source columns and handling missingness
            # and ensuring string type from the start.

            # Handle 'Date' column
            if 'Date' in df.columns:
                df['Date_Processed'] = df['Date'].astype(str).fillna('')
            else:
                df['Date_Processed'] = '' # If source column doesn't exist, fill with empty string

            # Handle 'Time' column
            if 'Time' in df.columns:
                df['Time_Processed'] = df['Time'].astype(str).fillna('')
            else:
                df['Time_Processed'] = ''

            # Handle 'Heart rate' column
            if 'Heart rate' in df.columns: # Corrected column name
                df['Heart_Rate_Processed'] = df['Heart rate'].astype(str).fillna('')
            else:
                df['Heart_Rate_Processed'] = ''

            # Add 'Last_Updated' timestamp
            df['Last_Updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Select the final columns and rename them to the desired output names
            output_df = df[['Date_Processed', 'Time_Processed', 'Heart_Rate_Processed', 'Last_Updated']].copy()
            output_df.rename(columns={
                'Date_Processed': 'Date',
                'Time_Processed': 'Time',
                'Heart_Rate_Processed': 'Heart_Rate'
            }, inplace=True)

            # Save the processed DataFrame
            output_df.to_csv(processed_file_path, index=False, header=True)
            print(f"Successfully processed {filename} to {processed_file_path}.")

        except pd.errors.EmptyDataError:
            print(f"Skipping truly empty file (no headers, no data): {filename}")
        except FileNotFoundError:
            print(f"Error: File not found at {raw_file_path}")
        except Exception as e:
            # Catching general exceptions to ensure no file stops the whole process
            print(f"An unexpected error occurred while processing file {filename}: {e}")
            # print(traceback.format_exc()) # Uncomment for full traceback if needed for deeper debugging

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python transform_heart_rate.py <raw_directory_path> <processed_directory_path>")
        sys.exit(1)

    raw_directory = sys.argv[1]
    processed_directory = sys.argv[2]

    process_files_pandas(raw_directory, processed_directory)
