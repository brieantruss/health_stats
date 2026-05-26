import os
import csv
import mysql.connector
from mysql.connector import Error

# MySQL connection details
db_config = {
    "host": "localhost", # Assuming MySQL is on the same RPi5 as Airflow
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

# Table name in your MySQL database
table_name = "heart_rate"

def load_single_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single CSV file into a MySQL table using INSERT IGNORE INTO.
    Date and Time strings are inserted as-is from the CSV.
    Duplicate records (based on PRIMARY KEY) are skipped, and other records are inserted.
    No rows are dropped due to data issues in Python.
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

        # --- CRITICAL CHANGE: Using INSERT IGNORE INTO ---
        # This statement tells MySQL to ignore rows that cause a duplicate key error
        # and continue inserting the rest of the batch.
        sql = f"INSERT IGNORE INTO {table_name} (Date, Time, Heart_Rate, Last_Updated) VALUES (%s, %s, %s, %s)"

        data_to_insert = []
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.reader(csv_file)
            header = next(csv_reader) # Skip the header row

            for row_num, row in enumerate(csv_reader, start=2):
                if len(row) >= 4:
                    try:
                        # Take the strings directly from the CSV row, no formatting or parsing
                        date_str = row[0]
                        time_str = row[1]
                        heart_rate_val = row[2]
                        last_updated_str = row[3]

                        data_to_insert.append((date_str, time_str, heart_rate_val, last_updated_str))

                    except IndexError:
                        print(f"Skipping malformed row {row_num} in {os.path.basename(file_path)} (missing data for expected columns): {row}")
                    except Exception as e:
                        print(f"An unexpected error occurred while processing row {row_num} in {os.path.basename(file_path)}: {row} - {e}")
                else:
                    print(f"Skipping malformed row {row_num} in {os.path.basename(file_path)} (too few columns): {row}")

        if data_to_insert:
            try:
                cursor.executemany(sql, data_to_insert)
                cnx.commit()
                # rowcount will only reflect newly inserted rows, not ignored ones
                print(f"{cursor.rowcount} new records inserted (duplicates ignored) from {os.path.basename(file_path)} into {table_name}")
            except Error as err:
                # This block will now only catch other types of MySQL errors, not duplicate key errors,
                # because INSERT IGNORE handles those silently.
                print(f"MySQL Connector Error during insertion for {os.path.basename(file_path)}: {err}")
                cnx.rollback() # Rollback if a non-duplicate-key error occurs for the batch
        else:
            print(f"No valid data found in {os.path.basename(file_path)} to insert from {os.path.basename(file_path)}.")

    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL for {os.path.basename(file_path)}: {err}")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {file_path}. Please check the path.")
    except Exception as e:
        print(f"An unexpected error occurred while processing {os.path.basename(file_path)}: {e}")
    finally:
        if cursor:
            cursor.close()
        if cnx and cnx.is_connected():
            cnx.close()
            print("MySQL connection closed for this file.")


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python3 load_heart_rate.py <processed_files_base_directory>")
        sys.exit(1)

    processed_files_base_dir = sys.argv[1]

    if not os.path.isdir(processed_files_base_dir):
        print(f"Error: Processed files directory not found: {processed_files_base_dir}")
        sys.exit(1)

    files_found = False
    for filename in os.listdir(processed_files_base_dir):
        if filename.endswith(".csv"):
            full_file_path = os.path.join(processed_files_base_dir, filename)
            load_single_csv_to_mysql(db_config, full_file_path, table_name)
            files_found = True

    if not files_found:
        print(f"No CSV files found in {processed_files_base_dir} to load.")
