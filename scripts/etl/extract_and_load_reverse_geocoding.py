import requests
import mysql.connector
import time
import sys
import csv
import os

# --- Configuration ---
DB_CONFIG = {
    "host": "localhost",
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}
# Path where the geocoded data CSV will be saved by this script
GEOCODED_CSV_OUTPUT_PATH = "/home/modulo/development/health_stats/processed_files/geocoding/geocoded_locations.csv"

def get_flag_emoji(country_code):
    """
    Converts a two-letter country code (e.g., 'US', 'ES') into its flag emoji.
    """
    if not country_code or len(country_code) != 2:
        return ""
    try:
        return "".join(chr(127397 + ord(c)) for c in country_code.upper())
    except Exception:
        return ""

# --- Nominatim API Function ---
def get_geocoded_data_from_coordinates(latitude, longitude):
    """
    Uses the free Nominatim OpenStreetMap API to get detailed geocoded information.
    """
    base_url = "https://nominatim.openstreetmap.org/reverse"
    params = {
        "lat": latitude,
        "lon": longitude,
        "format": "json",
        "zoom": 10,
        "addressdetails": 1
    }
    # Custom User-Agent to prevent getting 403 Forbidden
    headers = {
        "User-Agent": "HealthStatsTracker/1.0 (briean.j.truss@gmail.com)"
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
        response = requests.get(base_url, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        data = response.json()

        if data and 'address' in data:
            address = data['address']

            # 1. City (most specific)
            result['city'] = address.get('city') or \
                             address.get('town') or \
                             address.get('village') or \
                             address.get('hamlet') or \
                             address.get('municipality') or \
                             address.get('suburb')

            # 2. Normalized City (larger area: state, province, county)
            result['normalized_city'] = address.get('state') or \
                                         address.get('province') or \
                                         address.get('county') or \
                                         address.get('region')

            # 3. Country
            result['country'] = address.get('country')

            # 4. DMS
            result['DMS'] = f"{latitude}, {longitude}"

            # 5. URL
            osm_type = data.get('osm_type', 'node')
            osm_id = data.get('osm_id', '')
            if osm_id:
                result['url'] = f"https://www.openstreetmap.org/{osm_type}/{osm_id}"

            # 6. Flag (Country Flag Emoji)
            country_code = address.get('country_code', '')
            result['flag'] = get_flag_emoji(country_code)

            # 7. Timezone (leaves NULL or derived elsewhere)
            result['timezone'] = None

            return result
        else:
            return result

    except Exception as e:
        print(f"  An error occurred during geocoding for ({latitude}, {longitude}): {e}")
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
    """Fetches distinct latitude and longitude pairs from the 'locations' table that aren't already geocoded."""
    try:
        # Fetch already geocoded locations to avoid duplicate queries
        cursor.execute("SELECT DISTINCT latitude, longitude FROM geocoded_locations;")
        existing_coords = set((float(row[0]), float(row[1])) for row in cursor.fetchall())

        query = "SELECT DISTINCT latitude, longitude FROM locations;"
        cursor.execute(query)
        all_coords = cursor.fetchall()

        coordinates = []
        for row in all_coords:
            lat_val = float(row[0])
            lon_val = float(row[1])
            # Check for a match with small tolerance (4 decimal places ~ 11 meters) to avoid floating point mismatch
            is_existing = False
            for exist_lat, exist_lon in existing_coords:
                if abs(exist_lat - lat_val) < 1e-4 and abs(exist_lon - lon_val) < 1e-4:
                    is_existing = True
                    break
            if not is_existing:
                coordinates.append((lat_val, lon_val))

        print(f"Found {len(coordinates)} new distinct coordinates to process out of {len(all_coords)} total coordinates.")
        return coordinates
    except mysql.connector.Error as err:
        print(f"Error fetching coordinates: {err}")
        return []

def load_geocoded_data_to_db(data, db_connection):
    """
    Loads geocoded data into the 'geocoded_locations' table in the database.
    """
    if not data:
        print("No geocoded data to load into the database.")
        return

    cursor = db_connection.cursor()
    insert_query = """
    INSERT IGNORE INTO geocoded_locations (
        latitude, longitude, city, normalized_city, country, DMS, url, flag, timezone
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
    """
    try:
        print("Starting to load geocoded data into the database...")
        for row in data:
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
            cursor.execute(insert_query, values)
        db_connection.commit()
        print(f"Successfully loaded/updated geocoded records into 'geocoded_locations' table.")
    except Exception as e:
        print(f"An unexpected error occurred during database load: {e}")
        db_connection.rollback()
    finally:
        cursor.close()

# --- CSV Export Function ---

def export_to_csv(data, file_path):
    """
    Exports a list of dictionaries to a CSV file.
    """
    if not data:
        print("No data to export to CSV.")
        return

    fieldnames = ['latitude', 'longitude', 'city', 'normalized_city',
                  'country', 'DMS', 'url', 'flag', 'timezone']

    output_dir = os.path.dirname(file_path)
    if output_dir and not os.path.exists(output_dir):
        try:
            os.makedirs(output_dir)
            print(f"Created directory: {output_dir}")
        except OSError as e:
            print(f"Error creating directory {output_dir}: {e}")
            return

    try:
        # Append mode to keep existing CSV records intact
        file_exists = os.path.exists(file_path)
        with open(file_path, 'a', newline='', encoding='utf-8') as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            for row in data:
                writer.writerow(row)
        print(f"\nSuccessfully exported and appended geocoded results to: {file_path}")
    except IOError as e:
        print(f"Error writing CSV file to {file_path}: {e}")
    except Exception as e:
        print(f"An unexpected error occurred during CSV export: {e}")

# --- Main Execution ---
if __name__ == "__main__":
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
            print("\nStarting keyless Nominatim geocoding process...")
            # Query up to 100 new coordinates per run to stay well within limits
            target_coords = distinct_coords[:100]
            for i, (lat, lon) in enumerate(target_coords):
                current_lat = float(lat)
                current_lon = float(lon)

                print(f"Processing {i+1}/{len(target_coords)}: ({current_lat}, {current_lon})")

                # Get geocoded data in a dictionary
                geocoded_data = get_geocoded_data_from_coordinates(current_lat, current_lon)

                # Add original coordinates to the dictionary before appending
                geocoded_data['latitude'] = current_lat
                geocoded_data['longitude'] = current_lon

                geocoded_results.append(geocoded_data)

                # Sleep 1.0 second between requests to strictly respect Nominatim's Usage Policy (1 request/second)
                time.sleep(1.0)

            print("\nGeocoding process complete.")
            export_to_csv(geocoded_results, GEOCODED_CSV_OUTPUT_PATH)
            load_geocoded_data_to_db(geocoded_results, db_connection)

    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")

    finally:
        if cursor:
            cursor.close()
        if db_connection:
            db_connection.close()
            print("Database connection closed.")
