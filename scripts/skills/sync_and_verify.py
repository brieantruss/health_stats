#!/usr/bin/env python3
import os
import sys
import subprocess
import mysql.connector
from google.cloud import bigquery

# --- Configuration ---
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}
PROJECT_ID = "my-data-479716"
DATASET_ID = "health_stats"
KEY_PATH = "/home/briean/.gcp/bigquery-agent-key.json"

TABLES_TO_CHECK = [
    ("blood_pressure", "blood_pressure"),
    ("cycling", "cycling"),
    ("cycling_summary", "cycling_summary"),
    ("diet", "diet_logs"),
    ("exercises", "exercises"),
    ("food_descriptions", "diet_food_descriptions_usda"),
    ("food_ingredients", "diet_food_ingredients_usda"),
    ("heart_rate", "heart_rate"),
    ("locations", "locations"),
    ("oxygen", "oxygen"),
    ("running", "running"),
    ("shootaround", "shootaround"),
    ("sleep", "sleep"),
    ("steps", "steps"),
    ("swimming", "swimming"),
    ("vo2max", "vo2max"),
    ("walking", "walking"),
    ("weather", "weather"),
    ("weather_aqi", "weather_aqi"),
    ("weather_forecast", "weather_forecast"),
    ("geocoded_locations", "geocoded_locations")
]

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

def run_sync():
    print("🔄 [1/3] Triggering MySQL-to-BigQuery Sync Pipeline...")
    sync_script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "mysql_to_bigquery.py"))
    
    try:
        result = subprocess.run([sys.executable, sync_script_path], capture_output=True, text=True, check=True)
        print("✅ Sync execution completed successfully.")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Error during sync execution: {e}")
        print(f"STDOUT:\n{e.stdout}")
        print(f"STDERR:\n{e.stderr}")
        return False

def verify_counts():
    print("\n🔍 [2/3] Fetching Row Counts & Verifying Synchronization...")
    
    # 1. Connect to MySQL
    try:
        mysql_conn = mysql.connector.connect(**MYSQL_CONFIG)
        mysql_cursor = mysql_conn.cursor()
    except Exception as e:
        print(f"❌ Failed to connect to MySQL: {e}")
        return
        
    # 2. Connect to BigQuery
    try:
        bq_client = get_bigquery_client()
    except Exception as e:
        print(f"❌ Failed to connect to BigQuery: {e}")
        mysql_conn.close()
        return

    print(f"\n{'-'*80}")
    print(f"{'MYSQL TABLE':<25} | {'BIGQUERY TABLE_ID':<30} | {'MYSQL ROWS':<10} | {'BQ ROWS':<10} | {'STATUS':<8}")
    print(f"{'-'*80}")

    in_sync_count = 0
    mismatch_count = 0

    for mysql_table, bq_table in TABLES_TO_CHECK:
        # Get MySQL count
        try:
            mysql_cursor.execute(f"SELECT COUNT(*) FROM {mysql_table}")
            mysql_count = mysql_cursor.fetchone()[0]
        except Exception as e:
            mysql_count = "ERROR"
            
        # Get BigQuery count
        try:
            query = f"SELECT COUNT(*) as cnt FROM `{PROJECT_ID}.{DATASET_ID}.{bq_table}`"
            query_job = bq_client.query(query)
            bq_count = list(query_job.result())[0].cnt
        except Exception as e:
            bq_count = "ERROR"

        status = "MATCH"
        if mysql_count == "ERROR" or bq_count == "ERROR":
            status = "ERROR"
            mismatch_count += 1
        elif mysql_count != bq_count:
            status = "MISMATCH"
            mismatch_count += 1
        else:
            in_sync_count += 1

        color_status = f"\033[92m{status}\033[0m" if status == "MATCH" else f"\033[91m{status}\033[0m"
        print(f"{mysql_table:<25} | {bq_table:<30} | {mysql_count:<10} | {bq_count:<10} | {color_status:<8}")

    mysql_cursor.close()
    mysql_conn.close()

    print(f"{'-'*80}")
    print("\n📊 [3/3] Final Synchronization Audit Summary:")
    print(f"  • Total Tables Audited : {len(TABLES_TO_CHECK)}")
    print(f"  • In Sync (Match)      : \033[92m{in_sync_count}\033[0m")
    if mismatch_count > 0:
        print(f"  • Mismatches/Errors    : \033[91m{mismatch_count}\033[0m ⚠️")
    else:
        print("  • Mismatches/Errors    : \033[92m0\033[0m (Perfect Sync! 🎉)")
    print(f"{'-'*80}\n")

if __name__ == "__main__":
    print("================================================================================")
    print("🌟 SKILL 1: DATA WAREHOUSE SYNCHRONIZATION & DIAGNOSTIC VERIFIER")
    print("================================================================================")
    if run_sync():
        verify_counts()
