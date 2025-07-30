import os
import csv
import mysql.connector
from datetime import datetime
import sys

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
table_name = "shootaround"

def load_shootaround_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single shootaround CSV file into a MySQL table.
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
            header = next(csv_reader) # Skip the header row

            # Prepare the SQL INSERT statement for the shootaround table
            # Column mapping from CSV to table:
            # Date -> date
            # Time -> time
            # Elapsed time -> elapsed_time
            # Distance (miles) -> distance_miles
            # Calories (kcal) -> calories_kcal
            # Average heart rate -> average_heart_rate
            # Max heart rate -> max_heart_rate
            # Average speed -> average_speed
            # Max speed -> max_speed
            # (Generated) -> last_updated
            sql = f"""
                INSERT INTO {table_name} (
                    activity_name, activity_date, activity_time, elapsed_time_seconds, distance_miles, calories_kcal, 
                    average_heart_rate, max_heart_rate, average_speed_mph, max_speed_mph, 
                    last_updated
                ) VALUES ('shootaround', %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            data_to_insert = []
            for row in csv_reader:
                # The attached CSV snippet has 13 columns.
                # The date is at index 2, time at 3.
                # The provided schema for "shootaround" seems to exclude 'Active time' and 'Steps'.
                if len(row) >= 13:
                    try:
                        date_str = row[2]
                        time_str = row[3]
                        elapsed_time_int = int(row[4])
                        distance_float = float(row[6])
                        calories_float = float(row[7])
                        avg_heart_rate_int = int(row[9])
                        max_heart_rate_int = int(row[10])
                        avg_speed_float = float(row[11])
                        max_speed_float = float(row[12])
                        last_updated_ts = datetime.now() # Generate current timestamp

                        data_to_insert.append((
                            date_str, time_str, elapsed_time_int, distance_float, 
                            calories_float, avg_heart_rate_int, max_heart_rate_int, 
                            avg_speed_float, max_speed_float, last_updated_ts
                        ))

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
    # Expecting one argument: the base directory for processed files
    if len(sys.argv) != 2:
        print("Usage: python3 load_shootaround.py <processed_files_base_directory>")
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
            load_shootaround_csv_to_mysql(db_config, full_file_path, table_name)
            files_found = True

    if not files_found:
        print(f"No CSV files found in {processed_files_base_dir} to load.")
