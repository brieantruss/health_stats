import os
import csv
import mysql.connector
from datetime import datetime # Import datetime to potentially get current timestamp if not using NOW() in SQL

# MySQL connection details
db_config = {
    "host": "localhost", # Assuming MySQL is on the same RPi5 as Airflow
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

# Base directory where processed CSV files are located
# This will now be passed as a command-line argument

# Table name in your MySQL database
table_name = "sleep" # Table name remains 'sleep'

def load_single_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single CSV file into a MySQL table.
    """
    cnx = None
    cursor = None

    print(f"Attempting to load data from: {file_path}")

    try:
        cnx = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"]
        )
        cursor = cnx.cursor()

        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            header = next(csv_reader) # Skip the header row (assuming header is present)

            # Updated SQL INSERT statement for 'sleep' table with new column names and Last_updated
            # Assuming 'Last_updated' column is of type DATETIME/TIMESTAMP in MySQL and
            # we want to set it to the current time of insertion.
            sql = f"INSERT INTO {table_name} (Date, Time, Duration, Stage, Last_updated) VALUES (%s, %s, %s, %s, %s)"

            data_to_insert = []
            for row in csv_reader:
                if len(row) >= 4: # Still expecting at least 4 columns from the CSV
                    try:
                        date_str = row[0]
                        time_str = row[1]
                        duration_val = int(row[2]) # Renamed from duration_int, corresponds to 'Duration'
                        stage_str = row[3]         # Renamed from sleep_stage_str, corresponds to 'Stage'
                        
                        # Get current timestamp for 'Last_updated'
                        current_timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                        data_to_insert.append((date_str, time_str, duration_val, stage_str, current_timestamp))

                    except (ValueError, IndexError) as e:
                        print(f"Skipping row in {os.path.basename(file_path)} due to data conversion or format error: {row} - {e}")
                else:
                    print(f"Skipping malformed row in {os.path.basename(file_path)} (too few columns): {row}")

            if data_to_insert:
                cursor.executemany(sql, data_to_insert)
                cnx.commit()
                print(f"{cursor.rowcount} records inserted successfully from {os.path.basename(file_path)} into {table_name}")
            else:
                print(f"No valid data found in {os.path.basename(file_path)} to insert after processing.")

    except mysql.connector.Error as err:
        print(f"MySQL Connector Error for {os.path.basename(file_path)}: {err}")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {file_path}. Please check the path.")
    except Exception as e:
        print(f"An unexpected error occurred while processing {os.path.basename(file_path)}: {e}")
    finally:
        if cursor:
            cursor.close()
        if cnx and cnx.is_connected():
            cnx.close()
        elif cnx:
            print("MySQL connection was not successfully established or was already closed for this file.")


if __name__ == "__main__":
    import sys # Import sys module here

    # Expecting one argument: the base directory for processed files
    if len(sys.argv) != 2:
        print("Usage: python3 load_sleep.py <processed_files_base_directory>")
        sys.exit(1)

    processed_files_base_dir = sys.argv[1]

    # Ensure the base directory exists
    if not os.path.isdir(processed_files_base_dir):
        print(f"Error: Processed files directory not found: {processed_files_base_dir}")
        sys.exit(1) # Use sys.exit here

    files_found = False
    for filename in os.listdir(processed_files_base_dir):
        # The script assumes all CSVs in the directory are sleep files. 
        # If other CSVs (like steps) might be present, you might want to add a more specific filename check, e.g., 'sleep' in filename.lower()
        if filename.endswith(".csv"):
            full_file_path = os.path.join(processed_files_base_dir, filename)
            load_single_csv_to_mysql(db_config, full_file_path, table_name)
            files_found = True

    if not files_found:
        print(f"No CSV files found in {processed_files_base_dir} to load.")
