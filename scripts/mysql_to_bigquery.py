#!/usr/bin/env python3
import os
import sys
import datetime
import logging
import mysql.connector
import pandas as pd
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
            logging.info(f"Syncing table '{table_name}'...")
            
            # Fetch data from MySQL
            cursor = mysql_conn.cursor()
            try:
                cursor.execute(f"SELECT * FROM {table_name}")
                columns = [col[0] for col in cursor.description]
                rows = cursor.fetchall()
            except Exception as e:
                logging.error(f"Failed to query MySQL table '{table_name}': {e}")
                continue
            finally:
                cursor.close()
                
            # Load into Pandas DataFrame
            df = pd.DataFrame(rows, columns=columns)
            logging.info(f"Table '{table_name}' loaded from MySQL: {len(df)} rows.")
            
            # Convert datetime columns to strings or native Pandas datetimes if needed
            # to prevent formatting issues during BigQuery load
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]) or isinstance(df[col].iloc[0], (datetime.datetime, datetime.date)) if len(df) > 0 else False:
                    # Convert date/datetime objects to ISO string representation
                    df[col] = df[col].apply(lambda x: x.isoformat() if pd.notna(x) else None)
            
            # Define BigQuery target table
            bq_table_id = f"mysql_{table_name}"
            table_ref = bq_client.dataset(DATASET_ID).table(bq_table_id)
            
            # Configure load job (WRITE_TRUNCATE ensures the table is cleanly overwritten)
            job_config = bigquery.LoadJobConfig(
                write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
            )
            
            # Upload to BigQuery
            try:
                logging.info(f"Uploading '{table_name}' to BigQuery dataset '{DATASET_ID}' as '{bq_table_id}'...")
                job = bq_client.load_table_from_dataframe(df, table_ref, job_config=job_config)
                job.result()  # Wait for the load job to complete
                logging.info(f"Successfully synced table '{table_name}' to BigQuery!")
            except Exception as e:
                logging.error(f"Failed to load table '{table_name}' to BigQuery: {e}")
                
    finally:
        mysql_conn.close()
        logging.info("MySQL connection closed.")
        
    logging.info("MySQL to BigQuery synchronization complete!")

if __name__ == "__main__":
    sync_mysql_to_bigquery()
