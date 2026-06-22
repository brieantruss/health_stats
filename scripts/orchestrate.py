import os
import sys
import subprocess
from datetime import timedelta
from prefect import flow, task

# Base directory for the repository
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ETL_DIR = os.path.join(BASE_DIR, "scripts", "etl")
GCS_KEY_FILE = os.path.join(BASE_DIR, "gcs_key", "healthhub-425207-3fe090d13b2d.json")

@task(name="run_etl_step")
def run_etl_step(script_name, *args):
    """
    Executes an ETL script as a subprocess to preserve isolation and minimize RAM overhead.
    """
    script_path = os.path.join(ETL_DIR, script_name)
    if not os.path.exists(script_path):
        raise FileNotFoundError(f"ETL script not found: {script_path}")
    
    cmd = [sys.executable, script_path] + list(args)
    print(f"Executing: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
        raise RuntimeError(f"Script {script_name} failed with exit code {result.returncode}")
    
    print(f"STDOUT:\n{result.stdout}")
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
    print("Starting Prefect Orchestration Daemon...")
    
    # Define deployments (consolidated down to just two clean, staggered deployments)
    deployments = [
        hourly_etl_flow.to_deployment(name="hourly-etl", interval=timedelta(hours=1)),
        location_flow.to_deployment(name="location", interval=timedelta(minutes=30)),
    ]
    
    # Serve all deployments concurrently in a single headless daemon process
    from prefect import serve
    serve(*deployments)
