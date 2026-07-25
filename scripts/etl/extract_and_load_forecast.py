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

# Visual Crossing Key
VC_KEY = '9R2RM7GGXUTX9FK3R6TCL5E92'

# Define the output directory for the CSV file (portable, dynamically resolved)
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
OUTPUT_DIR = os.path.join(BASE_DIR, "processed_files", "forecast")
OUTPUT_FILENAME = 'forecast.csv'
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

def process_forecast_data():
    conn = None
    try:
        conn = get_mysql_connection()
        
        # 1. Get the latest logged coordinates
        cursor = conn.cursor()
        cursor.execute("SELECT latitude, longitude FROM locations ORDER BY timestamp DESC LIMIT 1;")
        latest_loc = cursor.fetchone()
        cursor.close()
        
        if not latest_loc:
            # Fallback to Chicago / Sears Tower if no GPS coordinates found
            lat, lon = 41.878876, -87.635915
            logging.warning("No GPS locations found. Falling back to default coordinates.")
        else:
            lat, lon = latest_loc
            logging.info(f"Using latest GPS coordinate: {lat},{lon}")

        # 2. Query Visual Crossing Timeline API for a 7-day weather forecast (current day + 7 days)
        today_str = datetime.today().strftime('%Y-%m-%d')
        end_date_str = (datetime.today() + timedelta(days=7)).strftime('%Y-%m-%d')
        
        vc_url = (
            f"https://weather.visualcrossing.com/VisualCrossingWebServices/rest/services/timeline/"
            f"{lat},{lon}/{today_str}/{end_date_str}"
            f"?key={VC_KEY}"
            f"&include=days&elements=datetime,temp,tempmax,tempmin,precipprob,conditions,windspeed"
            f"&unitGroup=metric"
        )
        
        logging.info("Querying Visual Crossing Weather Forecast API...")
        vc_response = requests.get(vc_url, timeout=15)
        vc_response.raise_for_status()
        vc_data = vc_response.json()
        
        # 3. Query Open-Meteo Air Quality Forecast API (PM2.5 / US AQI) using forecast_days=7
        om_url = (
            f"https://air-quality-api.open-meteo.com/v1/air-quality"
            f"?latitude={lat}&longitude={lon}"
            f"&hourly=us_aqi"
            f"&forecast_days=7"
            f"&timezone=auto"
        )
        
        logging.info("Querying Open-Meteo AQI Forecast API...")
        om_response = requests.get(om_url, timeout=15)
        om_response.raise_for_status()
        om_data = om_response.json()
        
        # Map Open-Meteo hourly AQI to daily maximums or averages
        hourly_times = om_data.get('hourly', {}).get('time', [])
        hourly_aqis = om_data.get('hourly', {}).get('us_aqi', [])
        
        daily_aqi_map = {}
        for t_str, aqi in zip(hourly_times, hourly_aqis):
            if aqi is not None:
                d_str = t_str.split('T')[0]
                if d_str not in daily_aqi_map:
                    daily_aqi_map[d_str] = []
                daily_aqi_map[d_str].append(aqi)
                
        # Calculate daily maximum AQI for each date
        daily_max_aqi = {d: int(max(vals)) for d, vals in daily_aqi_map.items()}

        # 4. Parse combined forecast data
        df_forecast = pd.DataFrame(columns=[
            'date', 'temp', 'temp_max', 'temp_min', 'precip_prob', 'conditions', 'wind_speed', 'aqi'
        ])
        
        for day in vc_data.get('days', []):
            d_str = day.get('datetime')
            aqi_forecast = daily_max_aqi.get(d_str, None)
            
            record = {
                'date': d_str,
                'temp': day.get('temp'),
                'temp_max': day.get('tempmax'),
                'temp_min': day.get('tempmin'),
                'precip_prob': day.get('precipprob'),
                'conditions': day.get('conditions'),
                'wind_speed': day.get('windspeed'),
                'aqi': aqi_forecast
            }
            df_forecast = pd.concat([df_forecast, pd.DataFrame([record])], ignore_index=True)

        # 5. Load/Upsert into MySQL 'weather_forecast'
        if not df_forecast.empty:
            logging.info(f"Upserting {len(df_forecast)} rows into MySQL 'weather_forecast'.")
            insert_sql = """
            INSERT INTO weather_forecast (
                date, temp, temp_max, temp_min, precip_prob, conditions, wind_speed, aqi
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON DUPLICATE KEY UPDATE
                temp = VALUES(temp),
                temp_max = VALUES(temp_max),
                temp_min = VALUES(temp_min),
                precip_prob = VALUES(precip_prob),
                conditions = VALUES(conditions),
                wind_speed = VALUES(wind_speed),
                aqi = VALUES(aqi);
            """
            
            data_to_insert = []
            for _, row in df_forecast.iterrows():
                values = (
                    row['date'],
                    float(row['temp']) if pd.notna(row['temp']) else None,
                    float(row['temp_max']) if pd.notna(row['temp_max']) else None,
                    float(row['temp_min']) if pd.notna(row['temp_min']) else None,
                    float(row['precip_prob']) if pd.notna(row['precip_prob']) else None,
                    str(row['conditions']) if pd.notna(row['conditions']) else None,
                    float(row['wind_speed']) if pd.notna(row['wind_speed']) else None,
                    int(row['aqi']) if pd.notna(row['aqi']) else None
                )
                data_to_insert.append(values)
                
            cursor = conn.cursor()
            cursor.executemany(insert_sql, data_to_insert)
            conn.commit()
            logging.info(f"Successfully upserted {cursor.rowcount} rows into MySQL 'weather_forecast'.")
            cursor.close()
            
            # --- Save to CSV ---
            os.makedirs(OUTPUT_DIR, exist_ok=True)
            df_forecast.to_csv(OUTPUT_PATH, index=False)
            logging.info(f"Successfully saved weather forecast to {OUTPUT_PATH}")
            
    except Exception as e:
        logging.critical(f"Forecast ETL failed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        if conn:
            conn.close()
            logging.info("MySQL connection closed.")

if __name__ == '__main__':
    logging.info("Starting Weather & AQI Forecast ETL...")
    process_forecast_data()
