import os
import csv
import mysql.connector
from datetime import datetime # Needed for proper timestamp handling

# MySQL connection details
db_config = {
    "host": "localhost", # Assuming MySQL is on the same RPi5 as Airflow
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

# Table name in your MySQL database (updated to "locations")
table_name = "locations"

def load_single_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single CSV file into a MySQL table.
    Assumes CSV has 'lat', 'lon', 'time', 'last_updated' columns.
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

        # SQL INSERT statement for the 'locations' table
        # Ensure column names match your actual table schema
        sql = f"INSERT IGNORE INTO {table_name} (timestamp, latitude, longitude, last_updated) VALUES (%s, %s, %s, %s)"

        data_to_insert = []
        with open(file_path, 'r', newline='') as csv_file:
            csv_reader = csv.DictReader(csv_file) # Use DictReader to access columns by name

            # Validate header presence for the expected fields
            expected_headers = ['time', 'lat', 'lon', 'last_updated']
            if not all(header in csv_reader.fieldnames for header in expected_headers):
                print(f"Error: CSV file {os.path.basename(file_path)} is missing one or more expected headers: {expected_headers}")
                return # Exit if headers are not as expected

            for row in csv_reader:
                try:
                    
                    time_val = row['time']
                    # Convert data to appropriate types
                    

                    lat_val = float(row['lat'])
                    lon_val = float(row['lon'])

                    # 'last_updated' field from CSV is also a string, assumed to be in a format MySQL can handle directly,
                    # or parsed if a specific format is known.
                    last_updated_val = row['last_updated'] 
                    
                    
                    data_to_insert.append((time_val, lat_val, lon_val, last_updated_val))
                    # data_to_insert.append((lat_val, lon_val, time_val, last_updated_val))

                except (ValueError, KeyError, IndexError) as e:
                    print(f"Skipping row in {os.path.basename(file_path)} due to data conversion or missing column error: {row} - {e}")
                
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
        print("Usage: python3 load_locations.py <processed_files_base_directory>")
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
