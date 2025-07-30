import requests
import mysql.connector
import time
import sys
import csv
import os # For checking/creating directory

# --- Configuration ---
# IMPORTANT: This should be your actual OpenCage API key.
# The previous "placeholder check" has been removed below.
OPENCAGE_API_KEY = "b42e47d569334a1ca2a1edf2963b0fac"
DB_CONFIG = {
    "host": "localhost",
    "user": "modulo",         # <--- Replace with your MySQL username
    "password": "modulo", # <--- Replace with your MySQL password
    "database": "health_stats"
}
# Path where the geocoded data CSV will be saved by this script
GEOCODED_CSV_OUTPUT_PATH = "/home/modulo/development/health_stats/processed_files/geocoding/geocoded_locations.csv"

# --- OpenCage API Function ---
def get_geocoded_data_from_coordinates(latitude, longitude, api_key):
    """
    Uses the OpenCage API to get detailed geocoded information for given coordinates.

    Args:
        latitude (float): The latitude of the location.
        longitude (float): The longitude of the location.
        api_key (str): Your OpenCage API key.

    Returns:
        dict: A dictionary containing extracted fields (city, normalized_city, country, DMS, url, flag, timezone)
              or None if an error occurs or no results are found.
    """
    base_url = "https://api.opencagedata.com/geocode/v1/json"
    params = {
        "q": f"{latitude},{longitude}",
        "key": api_key,
        "pretty": 0,  # No need for pretty print for programmatic use
        "no_annotations": 0, # Ensure annotations are included if not default
        "no_record": 1 # Optional: Don't log this request in your dashboard
    }

    result = {
        'city': None,
        'normalized_city': None,
        'country': None,
        'DMS': None,
        'url': None,
        'flag': None,
        'timezone': None
    }

    try:
        response = requests.get(base_url, params=params)
        response.raise_for_status()  # Raise an exception for HTTP errors (4xx or 5xx)
        data = response.json()

        if data and data['results']:
            first_result = data['results'][0]
            components = first_result.get('components', {})
            annotations = first_result.get('annotations', {})

            # 1. City (most specific)
            result['city'] = components.get('city') or \
                             components.get('town') or \
                             components.get('village') or \
                             components.get('hamlet')

            # 2. Normalized City (prioritizes 'city' component explicitly)
            result['normalized_city'] = components.get('city') or \
                                         components.get('town') or \
                                         components.get('village') or \
                                         components.get('hamlet')

            # 3. Country
            result['country'] = components.get('country')

            # 4. DMS (Degrees, Minutes, Seconds) - ROBUST HANDLING ADDED HERE
            dms_info = annotations.get('DMS')
            if isinstance(dms_info, dict):
                # If DMS is a dict, extract lat and lng parts and format them
                lat_dms = dms_info.get('lat', '')
                lng_dms = dms_info.get('lng', '')
                if lat_dms and lng_dms:
                    result['DMS'] = f"{lat_dms}, {lng_dms}"
                else:
                    result['DMS'] = None # Or an empty string if no valid parts
            elif isinstance(dms_info, str):
                result['DMS'] = dms_info
            else:
                result['DMS'] = None # Default to None if not dict or string

            # 5. URL (OpenStreetMap URL)
            result['url'] = annotations.get('OSM', {}).get('url')

            # 6. Flag (Country Flag Emoji)
            result['flag'] = annotations.get('flag')

            # 7. Timezone - Robust handling (already present from previous fix)
            timezone_info = annotations.get('timezone')
            if isinstance(timezone_info, dict):
                result['timezone'] = timezone_info.get('name')
            elif isinstance(timezone_info, str):
                result['timezone'] = timezone_info
            else:
                result['timezone'] = None

            return result
        else:
            # print(f"  No geocoding results found for ({latitude}, {longitude}).")
            return result # Return dict with Nones if no results

    except requests.exceptions.RequestException as e:
        print(f"  API request error for ({latitude}, {longitude}): {e}")
        return result
    except KeyError:
        print(f"  Unexpected API response format for ({latitude}, {longitude}).")
        return result
    except Exception as e:
        print(f"  An unexpected error occurred during geocoding for ({latitude}, {longitude}): {e}")
        return result

# --- Database Interaction Functions ---

def connect_to_db(config):
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**config)
        print("Successfully connected to the database.")
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def get_distinct_coordinates(cursor):
    """Fetches all distinct latitude and longitude pairs from the 'locations' table."""
    try:
        query = "SELECT DISTINCT latitude, longitude FROM locations;"
        cursor.execute(query)
        coordinates = cursor.fetchall()
        print(f"Found {len(coordinates)} distinct coordinates to process from the database.")
        return coordinates
    except mysql.connector.Error as err:
        print(f"Error fetching distinct coordinates: {err}")
        return []

def load_geocoded_data_to_db(data, db_connection):
    """
    Loads geocoded data into the 'geocoded_locations' table in the database.
    Uses INSERT IGNORE to prevent duplicates based on latitude and longitude.
    """
    if not data:
        print("No geocoded data to load into the database.")
        return

    cursor = db_connection.cursor()
    # IMPORTANT: Ensure this table is created in your database with the PRIMARY KEY.
    # SQL:
    # CREATE TABLE IF NOT EXISTS geocoded_locations (
    #    latitude DECIMAL(10, 8) NOT NULL,
    #    longitude DECIMAL(11, 8) NOT NULL,
    #    city VARCHAR(255),
    #    normalized_city VARCHAR(255),
    #    country VARCHAR(255),
    #    DMS VARCHAR(255),
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
        for row_index, row in enumerate(data): # Added row_index for easier debugging
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
                # Log the error but don't stop the process for other rows
                print(f"  Error inserting row ({row.get('latitude')}, {row.get('longitude')}): {err}")
                print(f"  Problematic values: {values}") # Print values on error for more context
        db_connection.commit()
        print(f"Successfully attempted to load/update geocoded records into 'geocoded_locations' table (using INSERT IGNORE).")
    except Exception as e:
        print(f"An unexpected error occurred during database load: {e}")
        db_connection.rollback() # Rollback on error
    finally:
        cursor.close()

# --- CSV Export Function ---

def export_to_csv(data, file_path):
    """
    Exports a list of dictionaries to a CSV file.

    Args:
        data (list): A list of dictionaries, where each dictionary represents a row.
                     Each dictionary must have all defined fieldnames as keys.
        file_path (str): The full path to the output CSV file.
    """
    if not data:
        print("No data to export to CSV.")
        return

    # Define CSV headers - ensure they match the keys in your result dictionaries
    fieldnames = ['latitude', 'longitude', 'city', 'normalized_city',
                  'country', 'DMS', 'url', 'flag', 'timezone']

    # Ensure the directory exists
    output_dir = os.path.dirname(file_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}")
            return

    try:
        with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            writer.writeheader() # Write the header row
            for row in data:
                writer.writerow(row)
        print(f"\nSuccessfully exported geocoded results to: {file_path}")
    except IOError as e:
        print(f"Error writing CSV file to {file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CSV export: {e}")

# --- Main Execution ---
if __name__ == "__main__":
    # The problematic API key check has been removed.
    # The OPENCAGE_API_KEY variable is set at the top of the file.

    db_connection = connect_to_db(DB_CONFIG)
    if not db_connection:
        sys.exit(1)

    cursor = db_connection.cursor()
    geocoded_results = []

    try:
        distinct_coords = get_distinct_coordinates(cursor)

        if not distinct_coords:
            print("No distinct coordinates found in 'locations' table to process.")
        else:
            print("\nStarting geocoding process...")
            for i, (lat, lon) in enumerate(distinct_coords):
                current_lat = float(lat)
                current_lon = float(lon)

                print(f"Processing {i+1}/{len(distinct_coords)}: ({current_lat}, {current_lon})")

                # Get all geocoded data in a dictionary
                geocoded_data = get_geocoded_data_from_coordinates(current_lat, current_lon, OPENCAGE_API_KEY)

                # Add original coordinates to the dictionary before appending
                geocoded_data['latitude'] = current_lat
                geocoded_data['longitude'] = current_lon

                geocoded_results.append(geocoded_data)

                # OpenCage free tier allows 2,500 requests/day.
                # A delay of 0.15 seconds means approx 6-7 requests/second.
                # Adjust this sleep time based on your OpenCage plan's rate limits.
                time.sleep(0.15) # Small delay to respect API rate limits

            print("\nGeocoding process complete.")
            export_to_csv(geocoded_results, GEOCODED_CSV_OUTPUT_PATH)
            # THIS IS THE KEY CHANGE: Load data directly into DB from this script
            load_geocoded_data_to_db(geocoded_results, db_connection)

    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
            print("Database connection closed.")
