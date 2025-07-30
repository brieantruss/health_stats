import os
import csv
import mysql.connector
from datetime import datetime

# MySQL connection details
db_config = {
    "host": "localhost", # Assuming MySQL is on the same RPi5 as Airflow
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

# Table name in your MySQL database
table_name = "blood_pressure"

def load_single_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single CSV file into a MySQL table.
    Assumes the CSV has columns: Date, Time, Diastolic, Systolic, Heart rate, Comment, Last_Updated
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

            # Updated SQL INSERT statement for blood_pressure table
            # It now includes Diastolic, Systolic, Heart rate, Comment, and Last_Updated
            sql = f"INSERT INTO {table_name} (Date, Time, Diastolic, Systolic, heart_rate, Comment, Last_Updated) VALUES (%s, %s, %s, %s, %s, %s, %s)"

            data_to_insert = []
            for row in csv_reader:
                # Expecting 7 columns: Date, Time, Diastolic, Systolic, Heart rate, Comment, Last_Updated
                if len(row) >= 7:
                    try:
                        date_str = row[0]
                        time_str = row[1]
                        diastolic_float = float(row[2])
                        systolic_float = float(row[3])
                        heart_rate_int = int(row[4])
                        comment_str = row[5] if row[5] else None # Handle empty string for Comment
                        last_updated_str = row[6]

                        data_to_insert.append((date_str, time_str, diastolic_float, systolic_float, heart_rate_int, comment_str, last_updated_str))

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
    import sys

    # Expecting one argument: the base directory for processed files
    if len(sys.argv) != 2:
        print("Usage: python3 load_blood_pressure.py <processed_files_base_directory>")
        sys.exit(1)

    processed_files_base_dir = sys.argv[1]

    # Ensure the base directory exists
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
