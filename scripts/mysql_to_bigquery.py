#!/usr/bin/env python3
import os
import sys
import datetime
import logging
import csv
import mysql.connector
from google.cloud import bigquery
from google.oauth2 import service_account

# Configure logging
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mysql_to_bigquery.log"))
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(sys.stdout)
    ]
)

# MySQL configuration
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

# BigQuery configuration
PROJECT_ID = "my-data-479716"
DATASET_ID = "health_stats"

# List of MySQL tables to sync to BigQuery as 'mysql_<table_name>'
TABLES_TO_SYNC = [
    "blood_pressure",
    "cycling",
    "cycling_summary",
    "diet",
    "exercises",
    "food_descriptions",
    "food_ingredients",
    "heart_rate",
    "locations",
    "oxygen",
    "running",
    "shootaround",
    "sleep",
    "steps",
    "swimming",
    "vo2max",
    "walking",
    "weather"
]

def get_bigquery_client():
    """
    Initializes and returns a BigQuery client.
    Attempts to use the local BigQuery agent service account key,
    falling back to Application Default Credentials (ADC).
    """
    key_path = "/home/briean/.gcp/bigquery-agent-key.json"
    if os.path.exists(key_path):
        logging.info(f"Authenticating BigQuery with service account key: {key_path}")
        return bigquery.Client.from_service_account_json(key_path, project=PROJECT_ID)
    else:
        logging.info("Service account key not found. Authenticating BigQuery with default credentials...")
        return bigquery.Client(project=PROJECT_ID)

def sync_mysql_to_bigquery():
    logging.info("Starting MySQL to BigQuery synchronization...")
    
    # 1. Initialize clients
    try:
        bq_client = get_bigquery_client()
    except Exception as e:
        logging.error(f"Failed to initialize BigQuery client: {e}")
        sys.exit(1)
        
    try:
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
    except Exception as e:
        logging.error(f"Failed to connect to MySQL database: {e}")
        sys.exit(1)
        
    # 2. Sync each table
    try:
        for table_name in TABLES_TO_SYNC:
            logging.info(f"--- Syncing table '{table_name}' ---")
            
            temp_csv_path = f"/tmp/mysql_{table_name}.csv"
            cursor = mysql_conn.cursor()
            
            try:
                # Get column headers
                cursor.execute(f"SELECT * FROM {table_name} LIMIT 0")
                columns = [col[0] for col in cursor.description]
                cursor.fetchall()  # Cleanly read the empty result set to clear the cursor
                
                # Fetch and stream rows directly to a local CSV in chunks to keep memory usage < 5MB
                logging.info(f"Fetching rows and streaming to local temporary file: {temp_csv_path}")
                with open(temp_csv_path, 'w', newline='', encoding='utf-8') as csv_file:
                    writer = csv.writer(csv_file)
                    writer.writerow(columns)  # Write header
                    
                    cursor.execute(f"SELECT * FROM {table_name}")
                    row_count = 0
                    while True:
                        rows = cursor.fetchmany(10000)
                        if not rows:
                            break
                        
                        # Process and format rows for BigQuery compatibility on-the-fly
                        formatted_rows = []
                        for row in rows:
                            formatted_row = []
                            for item in row:
                                if isinstance(item, (datetime.datetime, datetime.date)):
                                    formatted_row.append(item.isoformat())
                                elif isinstance(item, datetime.timedelta):
                                    formatted_row.append(str(item).split()[-1])  # Format cleanly as HH:MM:SS
                                else:
                                    formatted_row.append(item)
                            formatted_rows.append(formatted_row)
                            
                        writer.writerows(formatted_rows)
                        row_count += len(rows)
                        logging.info(f"Buffered and wrote {row_count} rows...")
                        
                logging.info(f"Streaming write complete. Total rows exported: {row_count}")
                
                # Define BigQuery target table
                bq_table_id = f"mysql_{table_name}"
                table_ref = bq_client.dataset(DATASET_ID).table(bq_table_id)
                
                # Configure load job
                # WRITE_TRUNCATE ensures the table is cleanly overwritten with the latest state
                # autodetect=True allows BigQuery to automatically discover and map types
                job_config = bigquery.LoadJobConfig(
                    source_format=bigquery.SourceFormat.CSV,
                    skip_leading_rows=1,
                    write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
                    autodetect=True
                )
                
                # Upload directly from file (highly memory efficient!)
                logging.info(f"Uploading file stream to BigQuery: {PROJECT_ID}.{DATASET_ID}.{bq_table_id}")
                with open(temp_csv_path, "rb") as source_file:
                    job = bq_client.load_table_from_file(source_file, table_ref, job_config=job_config)
                    job.result()  # Wait for the load job to complete
                    
                logging.info(f"Successfully synced table '{table_name}' to BigQuery!")
                
            except Exception as e:
                logging.error(f"Failed to sync table '{table_name}': {e}")
                
            finally:
                cursor.close()
                # Clean up temporary CSV file from disk
                if os.path.exists(temp_csv_path):
                    os.remove(temp_csv_path)
                    
    finally:
        mysql_conn.close()
        logging.info("MySQL connection closed.")
        
    logging.info("MySQL to BigQuery synchronization complete!")

if __name__ == "__main__":
    sync_mysql_to_bigquery()
