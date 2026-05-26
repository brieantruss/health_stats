from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os # Import os for path joining

with DAG(
    dag_id='health_stats_oxygen',
    start_date=datetime(2023, 1, 1), # Keep your start date, or adjust if needed, ya know
    schedule_interval=timedelta(hours=1),         # Keep your desired schedule
    catchup=False,
    tags=['pandas', 'health_stats'], # Updated tag from 'pyspark' to 'pandas'
) as dag:
    # Define base paths for the pipeline.
    # Assuming your DAG file is in /opt/airflow/dags/ and your pandas scripts are in /opt/airflow/dags/scripts/

    # IMPORTANT: Ensure 'scripts' subfolder exists in your DAGs folder
    PIPELINE_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

    # Data paths (adjust these to your actual absolute data locations on the RPi5)
    # These paths are now the DIRECTORIES where files are read from/written to.
    RAW_FILES_DIR = "/home/modulo/development/health_stats/raw_files/oxygen"
    PROCESSED_FILES_DIR = "/home/modulo/development/health_stats/processed_files/oxygen"

    # GCS key path (adjust to its actual absolute location on the RPi5)
    GCS_KEY_FILE = "/home/modulo/development/health_stats/gcs_key/healthhub-425207-3fe090d13b2d.json" # NOTE: Corrected path from 'gcs_key' to 'development/health_stats/gcs_key'

    # --- TASKS ---
    
    # Add this diagnostic task
    check_python_env = BashOperator(
        task_id='check_python_environment',
        bash_command='python3 -c "import sys; print(f\'Task Python Executable: {sys.executable}\'); print(f\'Task sys.path: {sys.path}\')"',
    )
    # Task to run the extract script
    # It now takes the GCS key file path and the local raw data directory as arguments.
    extract_task = BashOperator(
        task_id='run_extract_pandas',
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/extract_oxygen.py "{GCS_KEY_FILE}" "{RAW_FILES_DIR}"',
        # No need to pass GCS_KEY_PATH via env as it's now an argument to the script
        # The script itself handles the GOOGLE_APPLICATION_CREDENTIALS environment variable internally.
    )

    # Task to run the transform script
    # It takes the raw data directory as input and the processed data directory as output.
    transform_task = BashOperator(
        task_id='run_transform_pandas',
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/transform_oxygen.py "{RAW_FILES_DIR}" "{PROCESSED_FILES_DIR}"',
    )

    # Task to run the load script
    # It takes the processed data directory (which contains all CSVs to load) as its argument.
    load_task = BashOperator(
        task_id='run_load_pandas',
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/load_oxygen.py "{PROCESSED_FILES_DIR}"',
    )

    # Define the task dependencies
    extract_task >> transform_task >> load_task
