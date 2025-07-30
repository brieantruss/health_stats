import os
import pandas as pd
import sys
from datetime import datetime # Import datetime for timestamp

def process_files_pandas(raw_dir, processed_dir):
    """
    Processes CSV files from a raw directory, adds a 'last_updated' timestamp,
    and saves the output to a processed directory using Pandas. This script
    focuses on adding a timestamp without performing date/time column
    conversions or sorting on existing date columns.

    Args:
        raw_dir (str): The path to the directory containing the raw files.
        processed_dir (str): The path to the directory to save the processed files.
    """

    # Ensure the processed directory exists
    os.makedirs(processed_dir, exist_ok=True)

    print(f"Starting processing of files from {raw_dir} to {processed_dir}")

    # Check if the raw directory is empty
    if not os.listdir(raw_dir):
        print(f"Raw directory {raw_dir} is empty. No files to process.")
        return

    for filename in os.listdir(raw_dir):
        raw_file_path = os.path.join(raw_dir, filename)
        processed_file_path = os.path.join(processed_dir, filename)

        # Skip directories, process only files
        if not os.path.isfile(raw_file_path):
            continue

        try:
            print(f"Attempting to process file: {filename}")
            # Read the raw file into a Pandas DataFrame
            df = pd.read_csv(raw_file_path)

            # Check if DataFrame is empty after reading (e.g., only headers or completely blank file)
            if df.empty:
                print(f"File {filename} contains no data rows or only headers. Skipping processing.")
                continue # Skip to the next file in the loop

            # Add 'last_updated' column with the current timestamp
            # This column will be a string in 'YYYY-MM-DD HH:MM:SS' format
            df['last_updated'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

            # Save the updated DataFrame to the processed directory
            # index=False prevents writing the DataFrame index as a column in the CSV
            # header=True ensures column names are written
            df.to_csv(processed_file_path, index=False, header=True)
            print(f"Successfully processed file: {filename} from {raw_dir} to {processed_dir} with 'last_updated' column.")

        except pd.errors.EmptyDataError:
            print(f"Skipping truly empty file (no headers, no data): {filename}")
        except FileNotFoundError:
            print(f"Error: File not found at {raw_file_path}")
        except Exception as e:
            print(f"An unexpected error occurred while processing file {filename}: {e}")

if __name__ == "__main__":
    # Check if correct number of arguments are provided
    if len(sys.argv) != 3:
        print("Usage: python transform_data.py <raw_directory_path> <processed_directory_path>")
        sys.exit(1)

    # Extract raw and processed directory paths from command-line arguments
    raw_directory = sys.argv[1]
    processed_directory = sys.argv[2]

    # Process the files
    process_files_pandas(raw_directory, processed_directory)
