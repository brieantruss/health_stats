import requests
import pandas as pd
from datetime import datetime, timedelta
import mysql.connector
import os
import logging

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MySQL Connection Details ---
DB_HOST = 'localhost'
DB_USER = 'modulo'
DB_PASSWORD = 'modulo'
DB_NAME = 'health_stats'

# Define the output directory for the CSV file (portable, dynamically resolved)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "processed_files", "aqi")
OUTPUT_FILENAME = 'aqi.csv'
OUTPUT_PATH = os.path.join(OUTPUT_DIR, OUTPUT_FILENAME)

def get_mysql_connection():
    """Establishes and returns a MySQL database connection."""
    try:
        conn = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        logging.info("Successfully connected to MySQL.")
        return conn
    except mysql.connector.Error as err:
        logging.error(f"Error connecting to MySQL: {err}")
        import traceback
        traceback.print_exc()
        raise

def round_to_nearest_hour(dt_obj):
    """
    Rounds a datetime object to the nearest hour.
    """
    if dt_obj.minute >= 30:
        dt_obj = dt_obj.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        dt_obj = dt_obj.replace(minute=0, second=0, microsecond=0)
    return dt_obj

def process_aqi_data():
    """
    Fetches AQI data from Open-Meteo API for unique coordinate-timestamps
    from the 'locations' table that don't already exist in the 'weather_aqi' table.
    """
    all_locations_timestamps = []
    existing_set = set()

    # Step 1: Open connection, fetch locations & existing keys, then immediately close connection
    conn = None
    try:
        conn = get_mysql_connection()
        
        # Fetch unique location-timestamp pairs from 'locations'
        cursor_locations = conn.cursor()
        locations_query = """
            SELECT DISTINCT
                latitude,
                longitude,
                timestamp
            FROM locations
            ORDER BY timestamp DESC
            LIMIT 500; -- Limit to prevent quota/performance overhead
        """
        logging.info("Fetching unique location-timestamp pairs from 'locations'.")
        cursor_locations.execute(locations_query)
        all_locations_timestamps = cursor_locations.fetchall()
        cursor_locations.close()
        
        # Fetch existing AQI records
        cursor_aqi = conn.cursor()
        existing_aqi_query = """
            SELECT DISTINCT
                datetime, latitude, longitude
            FROM weather_aqi;
        """
        logging.info("Fetching existing AQI records.")
        cursor_aqi.execute(existing_aqi_query)
        existing_aqi_data = cursor_aqi.fetchall()
        cursor_aqi.close()
        
        for dt_str, lat, lon in existing_aqi_data:
            existing_set.add((dt_str, round(lat, 4), round(lon, 4)))
            
        logging.info(f"Loaded {len(all_locations_timestamps)} locations and {len(existing_set)} existing AQI keys.")
    except Exception as e:
        logging.error(f"Error reading initial database state: {e}")
        return f"Error: {e}", 500
    finally:
        if conn:
            conn.close()
            logging.info("Initial MySQL connection closed safely.")

    if not all_locations_timestamps:
        logging.info("No location-timestamp data found in 'locations' table. Exiting.")
        return "No data to process.", 200

    # Step 2: Parse and identify new records to query
    locations_to_query = []
    for lat, lon, full_timestamp_str in all_locations_timestamps:
        try:
            dt_obj_original = datetime.fromisoformat(full_timestamp_str.replace('Z', '+00:00'))
            dt_obj_rounded = round_to_nearest_hour(dt_obj_original)
            api_query_time_str = dt_obj_rounded.strftime('%Y-%m-%dT%H:%M:%S')

            key = (api_query_time_str, round(lat, 4), round(lon, 4))
            if key not in existing_set:
                locations_to_query.append((lat, lon, api_query_time_str, dt_obj_rounded))
        except ValueError as e:
            logging.warning(f"Skipping timestamp '{full_timestamp_str}' due to parsing error: {e}")
            continue

    logging.info(f"Identified {len(locations_to_query)} new location-time combinations to query.")

    if not locations_to_query:
        logging.info("All timestamps already exist in 'weather_aqi'. No new API calls needed.")
        return "No new data to process.", 200

    # Step 3: Run the API fetch loop (completely disconnected from MySQL to avoid wait_timeouts)
    df_responses = pd.DataFrame(columns=[
        'datetime', 'datetimeEpoch', 'latitude', 'longitude', 'aqi',
        'pm2_5', 'pm10', 'ozone', 'nitrogen_dioxide', 'carbon_monoxide', 'sulphur_dioxide'
    ])

    for lat, lon, query_time_str_rounded, dt_rounded in locations_to_query[:50]:
        date_str = dt_rounded.strftime('%Y-%m-%d')
        hour_val = dt_rounded.hour

        api_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=pm2_5,pm10,nitrogen_dioxide,sulphur_dioxide,ozone,carbon_monoxide,us_aqi"
            f"&start_date={date_str}&end_date={date_str}"
            f"&timezone=auto"
        )

        logging.info(f"Querying Open-Meteo AQI API for {lat},{lon} at {query_time_str_rounded}")
        try:
            response = requests.get(api_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            logging.error(f"API request failed for {lat},{lon} on {date_str}: {e}")
            continue

        if response.status_code == 200:
            data = response.json()
            hourly = data.get('hourly', {})
            times = hourly.get('time', [])
            api_target_time_str = dt_rounded.strftime('%Y-%m-%dT%H:00')
            
            if api_target_time_str in times:
                idx = times.index(api_target_time_str)
                
                aqi_val = hourly.get('us_aqi', [])[idx] if hourly.get('us_aqi') else None
                pm2_5_val = hourly.get('pm2_5', [])[idx] if hourly.get('pm2_5') else None
                pm10_val = hourly.get('pm10', [])[idx] if hourly.get('pm10') else None
                ozone_val = hourly.get('ozone', [])[idx] if hourly.get('ozone') else None
                no2_val = hourly.get('nitrogen_dioxide', [])[idx] if hourly.get('nitrogen_dioxide') else None
                co_val = hourly.get('carbon_monoxide', [])[idx] if hourly.get('carbon_monoxide') else None
                so2_val = hourly.get('sulphur_dioxide', [])[idx] if hourly.get('sulphur_dioxide') else None
                
                epoch = int(dt_rounded.timestamp())

                record = {
                    'datetime': query_time_str_rounded,
                    'datetimeEpoch': epoch,
                    'latitude': lat,
                    'longitude': lon,
                    'aqi': int(aqi_val) if aqi_val is not None else None,
                    'pm2_5': float(pm2_5_val) if pm2_5_val is not None else None,
                    'pm10': float(pm10_val) if pm10_val is not None else None,
                    'ozone': float(ozone_val) if ozone_val is not None else None,
                    'nitrogen_dioxide': float(no2_val) if no2_val is not None else None,
                    'carbon_monoxide': float(co_val) if co_val is not None else None,
                    'sulphur_dioxide': float(so2_val) if so2_val is not None else None
                }
                df_responses = pd.concat([df_responses, pd.DataFrame([record])], ignore_index=True)
                logging.info(f"Parsed AQI for {lat},{lon} at hour {hour_val}: AQI={aqi_val}")

    # Step 4: Open a fresh connection and batch insert data
    if not df_responses.empty:
        conn = None
        try:
            conn = get_mysql_connection()
            logging.info(f"Attempting to insert {len(df_responses)} rows into MySQL 'weather_aqi' table.")
            insert_sql = """
            INSERT IGNORE INTO weather_aqi (
                datetime, datetimeEpoch, latitude, longitude, aqi,
                pm2_5, pm10, ozone, nitrogen_dioxide, carbon_monoxide, sulphur_dioxide
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            """

            data_to_insert = []
            for idx, row in df_responses.iterrows():
                values = (
                    row['datetime'],
                    int(row['datetimeEpoch']) if pd.notna(row['datetimeEpoch']) else None,
                    float(row['latitude']),
                    float(row['longitude']),
                    int(row['aqi']) if pd.notna(row['aqi']) else None,
                    float(row['pm2_5']) if pd.notna(row['pm2_5']) else None,
                    float(row['pm10']) if pd.notna(row['pm10']) else None,
                    float(row['ozone']) if pd.notna(row['ozone']) else None,
                    float(row['nitrogen_dioxide']) if pd.notna(row['nitrogen_dioxide']) else None,
                    float(row['carbon_monoxide']) if pd.notna(row['carbon_monoxide']) else None,
                    float(row['sulphur_dioxide']) if pd.notna(row['sulphur_dioxide']) else None
                )
                data_to_insert.append(values)

            cursor_insert = conn.cursor()
            cursor_insert.executemany(insert_sql, data_to_insert)
            conn.commit()
            logging.info(f"Successfully loaded {cursor_insert.rowcount} rows into MySQL 'weather_aqi'.")
            cursor_insert.close()
        except mysql.connector.Error as err:
            logging.error(f"Error executing batch insert: {err}")
        finally:
            if conn:
                conn.close()
                logging.info("Database load connection closed successfully.")

        # --- Save DataFrame to CSV ---
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        if os.path.exists(OUTPUT_PATH):
            df_responses.to_csv(OUTPUT_PATH, mode='a', header=False, index=False)
        else:
            df_responses.to_csv(OUTPUT_PATH, index=False)
        logging.info(f"Successfully saved and appended AQI data to {OUTPUT_PATH}")

    return "AQI processing complete.", 200

if __name__ == '__main__':
    logging.info("Starting AQI processing ETL...")
    process_aqi_data()
