import functions_framework
import requests
import pandas as pd
from datetime import datetime, timedelta
import mysql.connector
import os
import logging

# --- Configure Logging ---
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# --- MySQL Connection Details ---
DB_HOST = '192.168.0.110'
DB_USER = 'modulo'
DB_PASSWORD = 'modulo'
DB_NAME = 'health_stats'

# API Key
key = '9R2RM7GGXUTX9FK3R6TCL5E92'

# Define the output directory for the CSV file
OUTPUT_DIR = '/home/modulo/development/health_stats/processed_files/weather'
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

def round_to_nearest_hour(dt_obj):
    """
    Rounds a datetime object to the nearest hour.
    E.g., 10:08:10 -> 10:00:00, 10:35:00 -> 11:00:00
    """
    # Round to the nearest 30 minutes for simplicity, then truncate to hour
    # For a true "nearest hour" round:
    # If minutes >= 30, round up to next hour. Otherwise, round down.
    if dt_obj.minute >= 30:
        dt_obj = dt_obj.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1)
    else:
        dt_obj = dt_obj.replace(minute=0, second=0, microsecond=0)
    return dt_obj

def process_weather_data(request_mock=None):
    """
    Fetches weather data from Visual Crossing API for specific timestamps
    from the 'locations' table that don't already exist in the 'weather' table
    (based on timestamp only).
    """
    conn = None
    cursor_locations = None
    cursor_weather = None
    cursor_insert = None

    try:
        conn = get_mysql_connection()

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

        # --- Fetch unique location-timestamp pairs from 'locations' ---
        cursor_locations = conn.cursor()
        locations_query = """
            SELECT DISTINCT
                latitude,
                longitude,
                timestamp
            FROM locations
            ORDER BY timestamp ASC;
        """
        logging.info("Executing MySQL query to fetch unique location-timestamp pairs from 'locations'.")
        cursor_locations.execute(locations_query)
        all_locations_timestamps = cursor_locations.fetchall()
        cursor_locations.close()
        logging.info(f"Fetched {len(all_locations_timestamps)} unique location-timestamp pairs from 'locations'.")

        if not all_locations_timestamps:
            logging.info("No location-timestamp data found in the 'locations' table. Exiting.")
            return "No data to process.", 200

        # --- Fetch existing weather data entries (timestamp only, rounded to the hour) ---
        cursor_weather = conn.cursor()
        # IMPORTANT: When fetching existing timestamps from 'weather', ensure no date formatting
        # as the column is now VARCHAR and stores the ISO 8601 string directly.
        existing_weather_query = """
            SELECT DISTINCT
                datetime
            FROM weather;
        """
        logging.info("Executing MySQL query to fetch existing weather data timestamps (raw VARCHAR).")
        cursor_weather.execute(existing_weather_query)
        existing_weather_data = cursor_weather.fetchall()
        cursor_weather.close()
        logging.info(f"Fetched {len(existing_weather_data)} existing weather data timestamps (raw VARCHAR).")

        # Convert existing_weather_data to a set for efficient lookup
        # Each element in the set will be the ISO 8601 string as stored.
        existing_timestamps_set = set()
        for (dt_str,) in existing_weather_data:
            existing_timestamps_set.add(dt_str)
        logging.info(f"Existing timestamps in 'weather' table: {len(existing_timestamps_set)} entries.")
        # logging.debug(f"Existing timestamps details: {existing_timestamps_set}")

        locations_to_query = []
        for lat, lon, full_timestamp_str in all_locations_timestamps:
            try:
                dt_obj_original = datetime.fromisoformat(full_timestamp_str.replace('Z', '+00:00'))
                dt_obj_rounded = round_to_nearest_hour(dt_obj_original)
                api_query_time_str = dt_obj_rounded.strftime('%Y-%m-%dT%H:%M:%S') # Will now be HH:00:00

                logging.debug(f"Processing location timestamp: {full_timestamp_str} -> Rounded to: {api_query_time_str}")

                # We need to check if the *rounded* timestamp string exists in our set of existing timestamps.
                # The 'datetime' field in the DB should now store the precise API timestamp, which
                # for hourly data, will be on the hour.
                if api_query_time_str not in existing_timestamps_set:
                    # Store the original timestamp from 'locations' to query if needed,
                    # but the API call will use the rounded time.
                    locations_to_query.append((lat, lon, api_query_time_str, dt_obj_original)) # Pass original dt_obj
                    logging.info(f"Identified new timestamp to query (rounded): {api_query_time_str} (original: {full_timestamp_str}) for {lat},{lon}")
                else:
                    logging.info(f"Skipping {lat},{lon} at original {full_timestamp_str} (rounded to {api_query_time_str}) as this timestamp already exists in 'weather' table.")
            except ValueError as e:
                logging.warning(f"Skipping timestamp '{full_timestamp_str}' from locations due to parsing error: {e}")
                continue

        logging.info(f"Identified {len(locations_to_query)} new location-time combinations to query from API.")
        logging.debug(f"Locations to query details: {locations_to_query}")

        if not locations_to_query:
            logging.info("All relevant timestamps from 'locations' already exist in 'weather'. No new API calls needed.")
            return "No new data to process from API.", 200

        # Process each unique location-time that needs a new API call
        for lat, lon, query_time_str_rounded, original_dt_obj in locations_to_query: # Unpack original_dt_obj
            api_url = (
                'https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/'
                + str(lat) + ',' + str(lon) + '/' + query_time_str_rounded + '/' + query_time_str_rounded
                + '?key=' + key
                + '&include=hours&elements=conditions,datetime,datetimeEpoch,tzoffset,dew,precip,'
                + 'preciptype,pressure,snow,snowdepth,source,moonphase,feelslike,tempmax,tempmin,'
                + 'temp,winddir,windgust,windspeed,humidity,uvindex,temp,precipprob'
                + '&unitGroup=metric'
            )
            logging.info(f"Making API request for {lat},{lon} at rounded time {query_time_str_rounded} (original: {original_dt_obj.strftime('%Y-%m-%dT%H:%M:%S')})")
            logging.debug(f"API URL: {api_url}")

            response = requests.get(api_url)
            logging.info(f"Response status code: {response.status_code} for {lat},{lon} at {query_time_str_rounded}")
            
            try:
                response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
            except requests.exceptions.HTTPError as http_err:
                logging.error(f"HTTP error for {lat},{lon} at {query_time_str_rounded}: {http_err} - Response: {response.text}")
                continue # Skip to the next location if API call failed

            if response.status_code == 200:
                data = response.json()
                
                if 'days' not in data or not data['days']:
                    logging.warning(f"API response for {lat},{lon} on {query_time_str_rounded} had no 'days' data.")
                    continue

                if 'hours' not in data['days'][0] or not data['days'][0]['hours']:
                    logging.warning(f"API response for {lat},{lon} on {query_time_str_rounded} had no 'hours' data in the first day entry.")
                    continue
                
                found_matching_hour_in_api = False
                for day_data in data['days']:
                    for hour_data in day_data.get('hours', []):
                        # Construct the full datetime string from API response (day_data datetime + hour_data datetime)
                        full_hourly_dt_str_api = f"{day_data['datetime']}T{hour_data['datetime']}"
                        
                        try:
                            hourly_dt_obj_api = datetime.fromisoformat(full_hourly_dt_str_api)
                            # Format to second precision for comparison, which will match the '00' minutes/seconds
                            hourly_dt_at_second_precision_api = hourly_dt_obj_api.strftime('%Y-%m-%dT%H:%M:%S')

                            # We're looking for the hour that matches our *rounded* query time.
                            # The 'datetime' field in the DB should still store the original, precise timestamp
                            # from the 'locations' table if possible, or the API's precise timestamp.
                            # For now, let's keep it as the API's precise timestamp.
                            
                            # The check here is if the API-returned hour matches the rounded query time
                            if hourly_dt_at_second_precision_api == query_time_str_rounded:
                                record = {
                                    # Store the API's exact hourly timestamp as a string
                                    'datetime': hourly_dt_obj_api.isoformat(), # Convert to ISO 8601 string
                                    'datetimeEpoch': hour_data.get('datetimeEpoch'),
                                    'tempmax': day_data.get('tempmax'),
                                    'tempmin': day_data.get('tempmin'),
                                    'temp': hour_data.get('temp'),
                                    'feelslike': hour_data.get('feelslike'),
                                    'dew': hour_data.get('dew'),
                                    'precip': hour_data.get('precip'),
                                    'preciptype': str(hour_data.get('preciptype')[0]) if isinstance(hour_data.get('preciptype'), list) and hour_data.get('preciptype') else (str(hour_data.get('preciptype')) if pd.notna(hour_data.get('preciptype')) else None), # Handle list or string
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
                                    'latitude': lat,
                                    'longitude': lon,
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
                                logging.info(f"Added 1 hourly record for {lat},{lon} at API time {hourly_dt_at_second_precision_api} (queried for {query_time_str_rounded}) to DataFrame.")
                                found_matching_hour_in_api = True
                                break # Exit inner loop (hours)
                        except ValueError as e:
                            logging.error(f"Error parsing hourly datetime from API for {lat},{lon} at {full_hourly_dt_str_api}: {e}")
                            continue
                    if found_matching_hour_in_api:
                        break # Exit outer loop (days) since we found the specific hour we were looking for

                if not found_matching_hour_in_api:
                    # This warning might still fire if the API doesn't return the *exact* rounded hour.
                    # It's less likely now, but still possible due to API behavior.
                    logging.warning(f"Despite rounding, no matching hourly data found in API response for rounded query time {query_time_str_rounded} at {lat},{lon}.")
            # This `else` block is largely redundant due to `raise_for_status()`
            else:  
                logging.error(f"API request for {lat},{lon} at {query_time_str_rounded} finished with status code {response.status_code} but was not caught by raise_for_status(). This should not happen.")


        # --- Load processed data into MySQL ---
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
                    # Ensure the 'datetime' field is a string for VARCHAR column
                    row_exact_datetime_str = row['datetime'] 

                    values = (
                        row_exact_datetime_str, # This is now a string
                        int(row['datetimeEpoch']),
                        float(row['tempmax']),
                        float(row['tempmin']),
                        float(row['temp']),
                        float(row['feelslike']),
                        float(row['dew']),
                        float(row['precip']),
                        str(row['preciptype']) if pd.notna(row['preciptype']) else None,
                        float(row['snow']),
                        float(row['snowdepth']),
                        float(row['windgust']),
                        float(row['windspeed']),
                        float(row['winddir']),
                        float(row['pressure']),
                        float(row['moonphase']),
                        str(row['conditions']) if pd.notna(row['conditions']) else None,
                        str(row['source']) if pd.notna(row['source']) else None,
                        int(row['queryCost']),
                        float(row['latitude']),
                        float(row['longitude']),
                        str(row['resolvedAddress']) if pd.notna(row['resolvedAddress']) else None,
                        str(row['address']) if pd.notna(row['address']) else None,
                        str(row['timezone']) if pd.notna(row['timezone']) else None,
                        float(row['tzoffset']),
                        float(row['hourly_temp']),
                        float(row['hourly_humidity']),
                        float(row['hourly_precip']),
                        float(row['hourly_uvindex']),
                        str(row['hourly_conditions']) if pd.notna(row['hourly_conditions']) else None,
                        float(row['hourly_windspeed'])
                    )
                    data_to_insert.append(values)
                except Exception as row_e:
                    logging.error(f"Error preparing row {index} for insertion: {row_e}")
                    logging.error(f"Row data: {row.to_dict()}")
                    continue

            if data_to_insert:
                cursor_insert = conn.cursor()
                try:
                    cursor_insert.executemany(insert_sql, data_to_insert)
                    conn.commit()
                    logging.info(f"Successfully inserted {cursor_insert.rowcount} new rows into MySQL 'weather' table.")

                    for record in data_to_insert:
                        timestamp_added = record[0]
                        logging.info(f"Attempted to add record for timestamp: {timestamp_added}")

                except mysql.connector.Error as err:
                    logging.error(f"Error during batch insert into MySQL: {err}")
                    conn.rollback()
                finally:
                    cursor_insert.close()
            else:
                logging.info("No valid weather data prepared for insertion into MySQL (after filtering/API calls).")

            # --- Save DataFrame to CSV ---
            logging.info(f"Checking if output directory exists: {OUTPUT_DIR}")
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            logging.info(f"Saving weather data to {OUTPUT_PATH}")
            df_responses.to_csv(OUTPUT_PATH, index=False)
            logging.info(f"Successfully saved weather data to {OUTPUT_PATH}")

        else:
            logging.info("No new weather data to insert or save (df_responses was empty after API calls).")

        return "Weather data processed, loaded to MySQL, and saved to CSV successfully", 200

    except requests.exceptions.RequestException as req_err:
        logging.error(f"API request error: {req_err}")
        if conn:
            conn.rollback()
        return f"API request error: {req_err}", 500
    except mysql.connector.Error as sql_err:
        logging.error(f"MySQL error: {sql_err}")
        if conn:
            conn.rollback()
        return f"MySQL error: {sql_err}", 500
    except Exception as e:
        if conn:
            conn.rollback()
        logging.critical(f"An unexpected error occurred: {e}")
        import traceback
        traceback.print_exc()
        return f"An unexpected error occurred: {e}", 500
    finally:
        # Ensure all cursors are closed
        if cursor_locations:
            cursor_locations.close()
        if cursor_weather:
            cursor_weather.close()
        # The cursor_insert is now closed within its try/except/finally block
        if conn:
            conn.close()
            logging.info("MySQL connection closed.")

if __name__ == '__main__':
    logging.info("Starting weather data processing script...")
    status_message, status_code = process_weather_data(request_mock=None)
    logging.info(f"Script finished with status: {status_code} - {status_message}")
