from airflow import DAG
from airflow.operators.bash import BashOperator
from datetime import datetime, timedelta
import os # Import os for path joining

with DAG(
    dag_id='health_stats_location_and_weather',
    start_date=datetime(2023, 1, 1), # Keep your start date, or adjust if needed, ya know
    schedule_interval=timedelta(minutes=30),       # Keep your desired schedule
    catchup=False,
    tags=['pandas', 'health_stats'], # Updated tag from 'pyspark' to 'pandas'
) as dag:
    # Define base paths for the pipeline.
    # Assuming your DAG file is in /opt/airflow/dags/ and your pandas scripts are in /opt/airflow/dags/scripts/

    # IMPORTANT: Ensure 'scripts' subfolder exists in your DAGs folder
    PIPELINE_SCRIPTS_DIR = os.path.join(os.path.dirname(__file__), "scripts")

    # Data paths (adjust these to your actual absolute data locations on the RPi5)
    # These paths are now the DIRECTORIES where files are read from/written to.
    RAW_FILES_DIR = "/home/modulo/development/health_stats/raw_files/locations"
    PROCESSED_FILES_DIR = "/home/modulo/development/health_stats/processed_files/locations"
    
    # Define the output directory for the weather script's CSV
    # This should match the OUTPUT_DIR variable in your weather.py script
    WEATHER_OUTPUT_DIR = "/home/modulo/development/health_stats/processed_files/weather" # This is already defined in your weather.py

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
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/extract_locations.py "{GCS_KEY_FILE}" "{RAW_FILES_DIR}"',
        # No need to pass GCS_KEY_PATH via env as it's now an argument to the script
        # The script itself handles the GOOGLE_APPLICATION_CREDENTIALS environment variable internally.
    )

    # Task to run the transform script
    # It takes the raw data directory as input and the processed data directory as output.
    transform_task = BashOperator(
        task_id='run_transform_pandas',
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/transform_locations.py "{RAW_FILES_DIR}" "{PROCESSED_FILES_DIR}"',
    )

    # Task to run the load script
    # It takes the processed data directory (which contains all CSVs to load) as its argument.
    load_task = BashOperator(
        task_id='run_load_pandas',
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/load_locations.py "{PROCESSED_FILES_DIR}"',
    )

    # Task to run the weather data script
    # This script doesn't take command-line arguments as it directly uses
    # the MySQL database for its input (locations table) and output (weather table/CSV).
    # Ensure that DB_HOST, DB_USER, DB_PASSWORD, DB_NAME, and API key are correctly set
    # within the weather.py script itself.
    fetch_weather_data_task = BashOperator(
        task_id='fetch_weather_data',
        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/extract_and_load_weather.py',
    )
    
    # Task to run the extract reverse geocoding script
#    extract_geodata_task = BashOperator(
#        task_id='extract_geocoded_csv_from_opencage',
#        bash_command=f'python3 {PIPELINE_SCRIPTS_DIR}/extract_and_load_reverse_geocoding.py'
#    )

    # Define the task dependencies
    # The weather data fetching should run AFTER the locations have been loaded,
    # as it depends on the 'locations' table being up-to-date.
    check_python_env >> extract_task >> transform_task >> load_task >> fetch_weather_data_task # >> extract_geodata_task 
