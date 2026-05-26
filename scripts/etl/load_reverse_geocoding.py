import mysql.connector
import csv
import os
import sys

# --- Configuration ---
# IMPORTANT: Replace with your actual MySQL database credentials
DB_CONFIG = {
    "host": "localhost",
    "user": "modulo",       # <--- Replace with your MySQL username
    "password": "modulo", # <--- Replace with your MySQL password
    "database": "health_stats"
}

# Path to your CSV file
CSV_FILE_PATH = "/home/modulo/development/health_stats/processed_files/geocoding/geocoded_locations.csv"
TABLE_NAME = "geocoded_locations"

def load_data_to_mysql(csv_file_path, db_config, table_name):
    """
    Loads data from a CSV file into a specified MySQL table.

    Args:
        csv_file_path (str): The full path to the CSV file.
        db_config (dict): Dictionary containing database connection parameters.
        table_name (str): The name of the target table in the database.
    """
    if not os.path.exists(csv_file_path):
        print(f"Error: CSV file not found at {csv_file_path}")
        sys.exit(1)

    conn = None
    cursor = None
    try:
        # Establish database connection
        print("Attempting to connect to the database...")
        conn = mysql.connector.connect(**db_config)
        cursor = conn.cursor()
        print("Successfully connected to the database.")

        # Read CSV data
        data_to_insert = []
        with open(csv_file_path, 'r', newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Ensure fieldnames match the CSV headers and table columns
            # The order here must match the order in the INSERT statement
            fieldnames = [
                'latitude', 'longitude', 'city', 'normalized_city',
                'country', 'DMS', 'url', 'flag', 'timezone'
            ]

            for row in reader:
                # Prepare data for insertion, handle potential None for empty strings
                # Convert empty strings to None, as MySQL NULL is appropriate for missing data
                processed_row = {k: v if v != '' else None for k, v in row.items()}
                
                # Convert latitude and longitude to float, handling potential errors
                try:
                    processed_row['latitude'] = float(processed_row['latitude']) if processed_row['latitude'] is not None else None
                    processed_row['longitude'] = float(processed_row['longitude']) if processed_row['longitude'] is not None else None
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert latitude/longitude for row: {row}. Skipping this row.")
                    continue

                # Append values in the correct order for the INSERT statement
                data_to_insert.append(tuple(processed_row[field] for field in fieldnames))

        if not data_to_insert:
            print("No data found in the CSV file to load.")
            return

        # SQL INSERT statement
        # Note: We omit the 'id' column as it's AUTO_INCREMENT
        insert_query = f"""
        INSERT INTO {table_name} (
            latitude, longitude, city, normalized_city,
            country, DMS, url, flag, timezone
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s, %s
        )
        """

        # Execute bulk insert
        print(f"Loading {len(data_to_insert)} rows into {table_name}...")
        cursor.executemany(insert_query, data_to_insert)
        conn.commit()
        print(f"Successfully loaded {len(data_to_insert)} rows into {table_name}.")

    except mysql.connector.Error as err:
        print(f"Database error: {err}")
        if conn:
            conn.rollback() # Rollback changes on error
            print("Database transaction rolled back.")
        sys.exit(1)
    except FileNotFoundError:
        print(f"Error: The file {csv_file_path} was not found.")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        if conn:
            conn.rollback() # Rollback changes on error
            print("Database transaction rolled back due to unexpected error.")
        sys.exit(1)
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()
            print("Database connection closed.")

if __name__ == "__main__":
    load_data_to_mysql(CSV_FILE_PATH, DB_CONFIG, TABLE_NAME)
