import mysql.connector
import csv
import os
import sys

# --- Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "modulo",         # <--- Replace with your MySQL username
    "password": "modulo", # <--- Replace with your MySQL password
    "database": "health_stats"
}
# --- IMPORTANT: Path to your EXISTING geocoded CSV file ---
EXISTING_GEOCODED_CSV_PATH = "/home/modulo/development/health_stats/processed_files/geocoding/geocoded_locations.csv"

# --- Database Connection ---
def connect_to_db(config):
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**config)
        print("Successfully connected to the database.")
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

# --- CSV Loading Function ---
def load_data_from_csv(file_path):
    """
    Loads geocoded data from an existing CSV file into a list of dictionaries.
    Ensures latitude/longitude are floats and handles empty strings as None.
    """
    if not os.path.exists(file_path):
        print(f"Error: CSV file not found at {file_path}")
        return []

    data = []
    try:
        with open(file_path, 'r', newline='', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                processed_row = {}
                # Convert latitude and longitude to float, handling potential errors and None
                try:
                    processed_row['latitude'] = float(row['latitude']) if row.get('latitude') else None
                    processed_row['longitude'] = float(row['longitude']) if row.get('longitude') else None
                except (ValueError, TypeError):
                    print(f"Warning: Could not convert lat/lon to float for row: {row}. Skipping row.")
                    continue

                # Process other fields: ensure they are strings or None for empty strings
                for key in ['city', 'normalized_city', 'country', 'DMS', 'url', 'flag', 'timezone']:
                    value = row.get(key)
                    if value == '': # Treat empty strings from CSV as None
                        processed_row[key] = None
                    else:
                        processed_row[key] = value # Keep as string (csv.DictReader already makes them strings)
                data.append(processed_row)
        print(f"Successfully loaded {len(data)} records from {file_path}")
        return data
    except IOError as e:
        print(f"Error reading CSV file from {file_path}: {e}")
        return []
    except Exception as e:
        print(f"An unexpected error occurred during CSV loading: {e}")
        return []

# --- Database Loading Function ---
def load_geocoded_data_to_db(data, db_connection):
    """
    Loads geocoded data into the 'geocoded_locations' table in the database.
    Uses INSERT IGNORE to prevent duplicates based on latitude and longitude.
    """
    if not data:
        print("No geocoded data to load into the database.")
        return

    cursor = db_connection.cursor()
    # Ensure your MySQL table 'geocoded_locations' has this schema:
    # CREATE TABLE IF NOT EXISTS geocoded_locations (
    #    latitude DECIMAL(10, 8) NOT NULL,
    #    longitude DECIMAL(11, 8) NOT NULL,
    #    city VARCHAR(255),
    #    normalized_city VARCHAR(255),
    #    country VARCHAR(255),
    #    DMS VARCHAR(255), -- Or TEXT if DMS string can be very long
    #    url TEXT,
    #    flag VARCHAR(100),
    #    timezone VARCHAR(255),
    #    PRIMARY KEY (latitude, longitude) -- Composite primary key to prevent duplicates
    # );
    insert_query = """
    INSERT IGNORE INTO geocoded_locations (
        latitude, longitude, city, normalized_city, country, DMS, url, flag, timezone
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        print("Starting to load geocoded data into the database...")
        for row_index, row in enumerate(data):
            values = (
                row.get('latitude'),
                row.get('longitude'),
                row.get('city'),
                row.get('normalized_city'),
                row.get('country'),
                row.get('DMS'),
                row.get('url'),
                row.get('flag'),
                row.get('timezone')
            )

            # --- DEBUGGING: Check types before execution ---
            print(f"--- Debugging Row {row_index} ---")
            print(f"  Latitude ({type(values[0])}): {values[0]}")
            print(f"  Longitude ({type(values[1])}): {values[1]}")
            print(f"  City ({type(values[2])}): {values[2]}")
            print(f"  Normalized City ({type(values[3])}): {values[3]}")
            print(f"  Country ({type(values[4])}): {values[4]}")
            print(f"  DMS ({type(values[5])}): {values[5]}")
            print(f"  URL ({type(values[6])}): {values[6]}")
            print(f"  Flag ({type(values[7])}): {values[7]}")
            print(f"  Timezone ({type(values[8])}): {values[8]}")
            print("-------------------------")
            # --- END DEBUGGING ---

            try:
                cursor.execute(insert_query, values)
            except mysql.connector.Error as err:
                print(f"  Error inserting row ({row.get('latitude')}, {row.get('longitude')}): {err}")
                print(f"  Problematic values: {values}")
        db_connection.commit()
        print(f"Successfully attempted to load/update geocoded records into 'geocoded_locations' table (using INSERT IGNORE).")
    except Exception as e:
        print(f"An unexpected error occurred during database load: {e}")
        db_connection.rollback()
    finally:
        cursor.close()

# --- Main Execution ---
if __name__ == "__main__":
    db_connection = connect_to_db(DB_CONFIG)
    if not db_connection:
        sys.exit(1)

    try:
        print(f"\n--- Loading data from existing CSV: {EXISTING_GEOCODED_CSV_PATH} ---")
        geocoded_data_to_load = load_data_from_csv(EXISTING_GEOCODED_CSV_PATH)

        if not geocoded_data_to_load:
            print("No data loaded from CSV. Exiting.")
            sys.exit(1)

        load_geocoded_data_to_db(geocoded_data_to_load, db_connection)

        print("\nCSV data loading process complete.")

    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

    finally:
        if db_connection:
            db_connection.close()
            print("Database connection closed.")
