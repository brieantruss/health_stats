from __future__ import annotations

from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os

# Define the absolute paths for the external scripts
# NOTE: These paths MUST be exactly as they are on your Ubuntu server.
MYSQL_BACKUP_SCRIPT = "/home/modulo/finances/database/finances_mysql_backup.py"
G_SHEETS_LOADER_SCRIPT = "/home/modulo/finances/loader_master.py"


with DAG(
    # --- UPDATED DAG PROPERTIES ---
    dag_id='finances_data_pipeline',  # New, relevant DAG ID
    start_date=datetime(2023, 1, 1),
    schedule_interval=timedelta(weeks=1),
    catchup=False,
    tags=['finances', 'mysql', 'gdrive', 'gcp'], # Updated tags
) as dag:

    # --- REMOVED OLD VARIABLES (PIPELINE_SCRIPTS_DIR, RAW_FILES_DIR, etc.) ---
    
    # 1. Task to create a MySQL backup and upload it to Google Drive
    backup_task = BashOperator(
        task_id='run_mysql_backup_to_gdrive',
        # Executes the script directly using the python3 interpreter
        bash_command=f'python3 {MYSQL_BACKUP_SCRIPT}',
        # Important: The Airflow user must have permissions to run this script
        # and access the files/directories it uses (e.g., /var/backups/mysql).
        # You may need to ensure python packages (like google-api-python-client)
        # are installed in the Airflow environment.
    )

    # 2. Task to download Google Sheets data and load it into MySQL
    # This task *must* run after the backup is complete to ensure the database
    # is backed up *before* any new data overwrites/deletes the tables.
    load_task = BashOperator(
        task_id='run_g_sheets_to_mysql_load',
        # Executes the script directly using the python3 interpreter
        bash_command=f'python3 {G_SHEETS_LOADER_SCRIPT}',
        # Important: This script uses the requests and mysql.connector libraries.
        # Ensure they are installed in the Airflow environment.
    )

    # --- Define the sequential task dependencies ---
    # Backup runs first, then the loader runs.
    backup_task >> load_task
