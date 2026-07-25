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

# API Key
key = '9R2RM7GGXUTX9FK3R6TCL5E92'

# Sears Tower Coordinates
LATITUDE = 41.878876
LONGITUDE = -87.635915

# Define the output directory for the CSV file (portable, dynamically resolved)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "processed_files", "weather")
OUTPUT_FILENAME = 'weather.csv'
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

def run_backfill():
    start_date = datetime(2025, 12, 12)
    end_date = datetime(2026, 6, 22)
    
    conn = None
    cursor_weather = None
    cursor_insert = None

    try:
        conn = get_mysql_connection()

        # Fetch existing weather data entries to avoid duplicates
        cursor_weather = conn.cursor()
        existing_weather_query = "SELECT DISTINCT datetime FROM weather;"
        logging.info("Fetching existing weather data timestamps.")
        cursor_weather.execute(existing_weather_query)
        existing_weather_data = cursor_weather.fetchall()
        cursor_weather.close()
        
        existing_timestamps_set = {dt_str for (dt_str,) in existing_weather_data}
        logging.info(f"Fetched {len(existing_timestamps_set)} existing timestamps.")

        # Initialize DataFrame to accumulate API responses
        df_responses = pd.DataFrame(columns=[
            'datetime', 'datetimeEpoch', 'tempmax', 'tempmin', 'temp',
            'feelslike', 'dew', 'precip', 'preciptype', 'snow', 'snowdepth',
            'windgust', 'windspeed', 'winddir', 'pressure', 'moonphase',
            'conditions', 'source', 'queryCost', 'latitude', 'longitude',
            'resolvedAddress', 'address', 'timezone', 'tzoffset',
            'hourly_temp', 'hourly_humidity', 'hourly_precip', 'hourly_uvindex',
            'hourly_conditions', 'hourly_windspeed'
        ])

        # Generate 30-day chunks to be safe with payload size and reliable execution
        current_chunk_start = start_date
        chunks = []
        while current_chunk_start <= end_date:
            current_chunk_end = min(current_chunk_start + timedelta(days=29), end_date)
            chunks.append((current_chunk_start, current_chunk_end))
            current_chunk_start = current_chunk_end + timedelta(days=1)

        logging.info(f"Split backfill range into {len(chunks)} chunks.")

        for chunk_start, chunk_end in chunks:
            start_str = chunk_start.strftime('%Y-%m-%d')
            end_str = chunk_end.strftime('%Y-%m-%d')
            
            # API Timeline Request URL for the date range
            api_url = (
                f'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/'
                f'{LATITUDE},{LONGITUDE}/{start_str}/{end_str}'
                f'?key={key}'
                f'&include=hours&elements=conditions,datetime,datetimeEpoch,tzoffset,dew,precip,'
                f'preciptype,pressure,snow,snowdepth,source,moonphase,feelslike,tempmax,tempmin,'
                f'temp,winddir,windgust,windspeed,humidity,uvindex,temp,precipprob'
                f'&unitGroup=metric'
            )

            logging.info(f"Requesting weather range: {start_str} to {end_str} for Sears Tower ({LATITUDE},{LONGITUDE})")
            response = requests.get(api_url)
            
            try:
                response.raise_for_status()
            except requests.exceptions.HTTPError as http_err:
                logging.error(f"HTTP error for range {start_str} to {end_str}: {http_err} - Response: {response.text}")
                continue

            if response.status_code == 200:
                data = response.json()
                if 'days' not in data or not data['days']:
                    logging.warning(f"No 'days' in API response for range {start_str} to {end_str}.")
                    continue

                for day_data in data['days']:
                    for hour_data in day_data.get('hours', []):
                        # Filter to only midnight (00:00:00)
                        if hour_data.get('datetime') == '00:00:00':
                            full_hourly_dt_str_api = f"{day_data['datetime']}T{hour_data['datetime']}"
                            
                            # Skip if this timestamp already exists in the database
                            if full_hourly_dt_str_api in existing_timestamps_set:
                                logging.info(f"Timestamp {full_hourly_dt_str_api} already exists. Skipping.")
                                continue

                            record = {
                                'datetime': full_hourly_dt_str_api,
                                'datetimeEpoch': hour_data.get('datetimeEpoch'),
                                'tempmax': day_data.get('tempmax'),
                                'tempmin': day_data.get('tempmin'),
                                'temp': hour_data.get('temp'),
                                'feelslike': hour_data.get('feelslike'),
                                'dew': hour_data.get('dew'),
                                'precip': hour_data.get('precip'),
                                'preciptype': str(hour_data.get('preciptype')[0]) if isinstance(hour_data.get('preciptype'), list) and hour_data.get('preciptype') else (str(hour_data.get('preciptype')) if pd.notna(hour_data.get('preciptype')) else None),
                                'snow': hour_data.get('snow'),
                                'snowdepth': hour_data.get('snowdepth'),
                                'windgust': hour_data.get('windgust'),
                                'windspeed': hour_data.get('windspeed'),
                                'winddir': hour_data.get('winddir'),
                                'pressure': hour_data.get('pressure'),
                                'moonphase': day_data.get('moonphase'),
                                'conditions': hour_data.get('conditions'),
                                'source': day_data.get('source'),
                                'queryCost': data.get('queryCost'),
                                'latitude': LATITUDE,
                                'longitude': LONGITUDE,
                                'resolvedAddress': data.get('resolvedAddress'),
                                'address': data.get('address'),
                                'timezone': data.get('timezone'),
                                'tzoffset': data.get('tzoffset'),
                                'hourly_temp': hour_data.get('temp'),
                                'hourly_humidity': hour_data.get('humidity'),
                                'hourly_precip': hour_data.get('precip'),
                                'hourly_uvindex': hour_data.get('uvindex'),
                                'hourly_conditions': hour_data.get('conditions'),
                                'hourly_windspeed': hour_data.get('windspeed')
                            }
                            df_responses = pd.concat([df_responses, pd.DataFrame([record])], ignore_index=True)
                            logging.info(f"Added midnight record for {day_data['datetime']} to DataFrame.")

        # Load processed data into MySQL
        if not df_responses.empty:
            logging.info(f"Attempting to insert {len(df_responses)} rows into MySQL 'weather' table.")
            insert_sql = """
            INSERT IGNORE INTO weather (
                datetime, datetimeEpoch, tempmax, tempmin, temp, feelslike, dew, precip,
                preciptype, snow, snowdepth, windgust, windspeed, winddir, pressure,
                moonphase, conditions, source, queryCost, latitude, longitude,
                resolvedAddress, address, timezone, tzoffset,
                hourly_temp, hourly_humidity, hourly_precip, hourly_uvindex,
                hourly_conditions, hourly_windspeed
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s
            )
            """

            data_to_insert = []
            for index, row in df_responses.iterrows():
                try:
                    values = (
                        row['datetime'],
                        int(row['datetimeEpoch']),
                        float(row['tempmax']) if pd.notna(row['tempmax']) else None,
                        float(row['tempmin']) if pd.notna(row['tempmin']) else None,
                        float(row['temp']) if pd.notna(row['temp']) else None,
                        float(row['feelslike']) if pd.notna(row['feelslike']) else None,
                        float(row['dew']) if pd.notna(row['dew']) else None,
                        float(row['precip']) if pd.notna(row['precip']) else None,
                        str(row['preciptype']) if pd.notna(row['preciptype']) else None,
                        float(row['snow']) if pd.notna(row['snow']) else None,
                        float(row['snowdepth']) if pd.notna(row['snowdepth']) else None,
                        float(row['windgust']) if pd.notna(row['windgust']) else None,
                        float(row['windspeed']) if pd.notna(row['windspeed']) else None,
                        float(row['winddir']) if pd.notna(row['winddir']) else None,
                        float(row['pressure']) if pd.notna(row['pressure']) else None,
                        float(row['moonphase']) if pd.notna(row['moonphase']) else None,
                        str(row['conditions']) if pd.notna(row['conditions']) else None,
                        str(row['source']) if pd.notna(row['source']) else None,
                        int(row['queryCost']),
                        float(row['latitude']),
                        float(row['longitude']),
                        str(row['resolvedAddress']) if pd.notna(row['resolvedAddress']) else None,
                        str(row['address']) if pd.notna(row['address']) else None,
                        str(row['timezone']) if pd.notna(row['timezone']) else None,
                        float(row['tzoffset']),
                        float(row['hourly_temp']) if pd.notna(row['hourly_temp']) else None,
                        float(row['hourly_humidity']) if pd.notna(row['hourly_humidity']) else None,
                        float(row['hourly_precip']) if pd.notna(row['hourly_precip']) else None,
                        float(row['hourly_uvindex']) if pd.notna(row['hourly_uvindex']) else None,
                        str(row['hourly_conditions']) if pd.notna(row['hourly_conditions']) else None,
                        float(row['hourly_windspeed']) if pd.notna(row['hourly_windspeed']) else None
                    )
                    data_to_insert.append(values)
                except Exception as row_e:
                    logging.error(f"Error preparing row {index} for insertion: {row_e}")
                    continue

            if data_to_insert:
                cursor_insert = conn.cursor()
                try:
                    cursor_insert.executemany(insert_sql, data_to_insert)
                    conn.commit()
                    logging.info(f"Successfully inserted {cursor_insert.rowcount} rows into MySQL 'weather' table.")
                except mysql.connector.Error as err:
                    logging.error(f"Error during batch insert: {err}")
                    conn.rollback()
                finally:
                    cursor_insert.close()

            # Append to weather.csv to keep it in sync
            logging.info(f"Ensuring output directory exists: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            
            if os.path.exists(OUTPUT_PATH):
                logging.info(f"Appending new records to existing CSV: {OUTPUT_PATH}")
                df_responses.to_csv(OUTPUT_PATH, mode='a', header=False, index=False)
            else:
                logging.info(f"Saving new CSV file: {OUTPUT_PATH}")
                df_responses.to_csv(OUTPUT_PATH, index=False)
            logging.info("CSV updated successfully.")
            
        else:
            logging.info("No new weather data to backfill.")

        return "Weather backfill completed successfully.", 200

    except Exception as e:
        logging.critical(f"An unexpected error occurred during backfill: {e}")
        import traceback
        traceback.print_exc()
        return f"Error: {e}", 500
    finally:
        if conn:
            conn.close()
            logging.info("MySQL connection closed.")

if __name__ == '__main__':
    logging.info("Starting weather backfill script...")
    run_backfill()
