import os
import sys

# Configure Prefect API URL programmatically to use local systemd service
# This bypasses the heavy ephemeral server and prevents VM RAM/CPU freezing issues.
os.environ["PREFECT_API_URL"] = "http://127.0.0.1:4200/api"

import subprocess
import logging
from datetime import timedelta
from prefect import flow, task

# Base directory for the repository
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ETL_DIR = os.path.join(BASE_DIR, "scripts", "etl")
GCS_KEY_FILE = "/home/briean/.gcp/bigquery-agent-key.json"

# Configure logging for Google Drive to MySQL pipeline
LOG_FILE = os.path.join(BASE_DIR, "gdrive_to_mysql.log")

# MySQL configuration
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

_db_initialized = False

def init_db_tables():
    global _db_initialized
    if _db_initialized:
        return
    try:
        import mysql.connector
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Create pipeline_execution_logs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS pipeline_execution_logs (
                id INT AUTO_INCREMENT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                pipeline_name VARCHAR(100),
                level VARCHAR(20),
                message TEXT
            )
        """)
        
        # Create drive_file_sync_history table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS drive_file_sync_history (
                id INT AUTO_INCREMENT PRIMARY KEY,
                processed_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                data_type VARCHAR(100),
                file_name VARCHAR(255),
                drive_modified_time DATETIME NULL,
                status VARCHAR(50),
                details TEXT
            )
        """)
        
        conn.commit()
        cursor.close()
        conn.close()
        _db_initialized = True
    except Exception as e:
        print(f"Error initializing DB tables: {e}")

def log_to_file(level, message):
    from datetime import datetime
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_msg = f"{timestamp} - {level} - {message}\n"
    try:
        with open(LOG_FILE, "a", encoding="utf-8") as f:
            f.write(formatted_msg)
            f.flush()
    except Exception as e:
        print(f"Error writing to log file: {e}")

    try:
        init_db_tables()
        import mysql.connector
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        # Truncate to a compact "gist" (2,000 chars max) to keep logging fast and lightweight
        truncated_msg = message[:2000] if message else ""
        
        cursor.execute(
            "INSERT INTO pipeline_execution_logs (pipeline_name, level, message) VALUES (%s, %s, %s)",
            ("gdrive_to_mysql", level, truncated_msg)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error writing log to database: {e}")

def log_file_sync(data_type, file_name, drive_modified_time, status, details=None):
    try:
        init_db_tables()
        import mysql.connector
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        mtime_str = drive_modified_time.strftime("%Y-%m-%d %H:%M:%S") if drive_modified_time else None
        truncated_details = details[:2000] if details else None
        
        cursor.execute(
            """INSERT INTO drive_file_sync_history 
               (data_type, file_name, drive_modified_time, status, details) 
               VALUES (%s, %s, %s, %s, %s)""",
            (data_type, file_name, mtime_str, status, truncated_details)
        )
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"Error logging file sync to database: {e}")

@task(name="run_etl_step")
def run_etl_step(script_name, *args):
    """
    Executes an ETL script as a subprocess to preserve isolation and minimize RAM overhead.
    """
    script_path = os.path.join(ETL_DIR, script_name)
    if not os.path.exists(script_path):
        log_to_file("ERROR", f"ETL script not found: {script_path}")
        raise FileNotFoundError(f"ETL script not found: {script_path}")
    
    cmd = [sys.executable, script_path] + list(args)
    log_to_file("INFO", f"Executing: {' '.join(cmd)}")
    print(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log_to_file("ERROR", f"Script {script_name} failed with exit code {result.returncode}")
        log_to_file("ERROR", f"STDOUT from failed script:\n{result.stdout}")
        log_to_file("ERROR", f"STDERR from failed script:\n{result.stderr}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        raise RuntimeError(f"Script {script_name} failed with exit code {result.returncode}")
    
    # Check if there is stdout to log, format it nicely
    stdout_content = result.stdout.strip()
    if stdout_content:
        log_to_file("INFO", f"STDOUT from {script_name}:\n{stdout_content}")
        print(f"STDOUT from {script_name}:\n{stdout_content}")
    else:
        log_to_file("INFO", f"Script {script_name} completed with no output.")
        print(f"Script {script_name} completed with no output.")
        
    # Centralized stdout parsing to log Drive files and Load statuses to Database
    try:
        # Normalize and deduce data_type from script_name
        data_type = script_name.replace("extract_", "").replace("transform_", "").replace("load_", "").replace(".py", "").replace("extract_and_load_", "")
        lines = stdout_content.splitlines() if stdout_content else []
        
        for line in lines:
            line_str = line.strip()
            # 1. Parse Extract steps
            if "Downloading/Updating file:" in line_str:
                file_name = line_str.split("Downloading/Updating file:", 1)[1].strip()
                # Try to get local modification time of the raw file
                raw_file_path = os.path.join(BASE_DIR, "raw_files", data_type, file_name)
                modified_time = None
                if os.path.exists(raw_file_path):
                    from datetime import datetime
                    modified_time = datetime.fromtimestamp(os.path.getmtime(raw_file_path))
                log_file_sync(data_type, file_name, modified_time, "Downloaded", "Successfully downloaded/updated from Google Drive")
                
            elif "Skipping file " in line_str and "no changes detected" in line_str:
                # Format: Skipping file filename - no changes detected.
                parts = line_str.split("Skipping file ", 1)[1].split(" - ", 1)
                file_name = parts[0].strip()
                # Try to get local modification time of the raw file
                raw_file_path = os.path.join(BASE_DIR, "raw_files", data_type, file_name)
                modified_time = None
                if os.path.exists(raw_file_path):
                    from datetime import datetime
                    modified_time = datetime.fromtimestamp(os.path.getmtime(raw_file_path))
                log_file_sync(data_type, file_name, modified_time, "Skipped", "No changes detected on Google Drive")
                
            # 2. Parse Load steps
            elif "records inserted successfully from" in line_str:
                # Format: {rowcount} records inserted successfully from {filename} into {table_name}
                parts = line_str.split(" records inserted successfully from ", 1)
                row_count = parts[0].strip()
                file_name = parts[1].split(" into ", 1)[0].strip()
                log_file_sync(data_type, file_name, None, "Loaded", f"Successfully loaded {row_count} records into MySQL table")
                
            elif "No valid data found in" in line_str and "to insert" in line_str:
                # Format: No valid data found in {filename} to insert after processing.
                file_name = line_str.split("No valid data found in ", 1)[1].split(" to insert", 1)[0].strip()
                log_file_sync(data_type, file_name, None, "No Data", "No new/valid data found in processed file to load")
    except Exception as e:
        print(f"Error parsing script output for logging: {e}")
        
    return result.returncode

def create_standard_flow(name, raw_subdir, processed_subdir, extract_script, transform_script, load_script):
    """
    Helper to create a standard extract -> transform -> load Prefect flow.
    """
    @flow(name=f"hs_{name}")
    def standard_flow():
        raw_dir = os.path.join(BASE_DIR, "raw_files", raw_subdir)
        processed_dir = os.path.join(BASE_DIR, "processed_files", processed_subdir)
        
        # Ensure directories exist
        os.makedirs(raw_dir, exist_ok=True)
        os.makedirs(processed_dir, exist_ok=True)
        
        # 1. Extract
        run_etl_step(extract_script, GCS_KEY_FILE, raw_dir)
        # 2. Transform
        run_etl_step(transform_script, raw_dir, processed_dir)
        # 3. Load
        run_etl_step(load_script, processed_dir)
        
    return standard_flow

# Generate the standard 11 flows
blood_pressure_flow = create_standard_flow("blood_pressure", "blood_pressure", "blood_pressure", "extract_blood_pressure.py", "transform_blood_pressure.py", "load_blood_pressure.py")
cycling_flow = create_standard_flow("cycling", "cycling", "cycling", "extract_cycling.py", "transform_cycling.py", "load_cycling.py")
heart_rate_flow = create_standard_flow("heart_rate", "heart_rate", "heart_rate", "extract_heart_rate.py", "transform_heart_rate.py", "load_heart_rate.py")
oxygen_flow = create_standard_flow("oxygen", "oxygen", "oxygen", "extract_oxygen.py", "transform_oxygen.py", "load_oxygen.py")
running_flow = create_standard_flow("running", "running", "running", "extract_running.py", "transform_running.py", "load_running.py")
shootaround_flow = create_standard_flow("shootaround", "shootaround", "shootaround", "extract_shootaround.py", "transform_shootaround.py", "load_shootaround.py")
sleep_flow = create_standard_flow("sleep", "sleep", "sleep", "extract_sleep.py", "transform_sleep.py", "load_sleep.py")
steps_flow = create_standard_flow("steps", "steps", "steps", "extract_steps.py", "transform_steps.py", "load_steps.py")
swimming_flow = create_standard_flow("swimming", "swimming", "swimming", "extract_swimming.py", "transform_swimming.py", "load_swimming.py")
vo2max_flow = create_standard_flow("vo2max", "vo2max", "vo2max", "extract_vo2max.py", "transform_vo2max.py", "load_vo2max.py")
walking_flow = create_standard_flow("walking", "walking", "walking", "extract_walking.py", "transform_walking.py", "load_walking.py")

# Custom flow for location which includes weather data fetching
@flow(name="hs_location")
def location_flow():
    raw_dir = os.path.join(BASE_DIR, "raw_files", "locations")
    processed_dir = os.path.join(BASE_DIR, "processed_files", "locations")
    
    # Ensure directories exist
    os.makedirs(raw_dir, exist_ok=True)
    os.makedirs(processed_dir, exist_ok=True)
    os.makedirs(os.path.join(BASE_DIR, "processed_files", "weather"), exist_ok=True)
    
    # 1. Extract
    run_etl_step("extract_locations.py", GCS_KEY_FILE, raw_dir)
    # 2. Transform
    run_etl_step("transform_locations.py", raw_dir, processed_dir)
    # 3. Load
    run_etl_step("load_locations.py", processed_dir)
    # 4. Fetch Weather Data (dependent on locations table being loaded)
    run_etl_step("extract_and_load_weather.py")

# Unified hourly flow that runs all 11 standard flows sequentially (one-by-one)
@flow(name="hs_hourly_etl")
def hourly_etl_flow():
    """
    Sequentially runs all 11 standard ETL tasks to minimize memory footprint and CPU spikes on the e2-micro VM.
    """
    print("Starting sequential hourly ETL pipeline...")
    blood_pressure_flow()
    cycling_flow()
    heart_rate_flow()
    oxygen_flow()
    running_flow()
    shootaround_flow()
    sleep_flow()
    steps_flow()
    swimming_flow()
    vo2max_flow()
    walking_flow()
    print("Sequential hourly ETL pipeline completed successfully!")

if __name__ == "__main__":
    if "--run-now" in sys.argv:
        print("Running hourly ETL pipeline manually now...")
        hourly_etl_flow()
        print("Running location flow manually now...")
        location_flow()
        print("Manual execution completed successfully!")
    else:
        print("Starting Prefect Orchestration Daemon...")
        
        # Define deployments (consolidated down to just two clean, staggered deployments)
        deployments = [
            hourly_etl_flow.to_deployment(name="hourly-etl", interval=timedelta(hours=1)),
            location_flow.to_deployment(name="location", interval=timedelta(minutes=30)),
        ]
        
        # Serve all deployments concurrently in a single headless daemon process
        from prefect import serve
        serve(*deployments)
