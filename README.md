# HealthHub: Personal Fitness Data Pipeline & Cloud Orchestration

HealthHub is an automated data pipeline that ingests, cleans, and consolidates personal fitness, sleep, vitals, and location data from multiple sources (like a Galaxy Smart Watch and phone GPS loggers) into a single database. 

Originally running on a local Raspberry Pi cluster, this system was migrated and optimized to run on the GCP Always Free Tier (using an e2-micro VM and serverless Cloud Run) for $0/month.

*   **Looker Studio Dashboard**: [Access Live Reporting](https://datastudio.google.com/reporting/4d204527-a6ef-4860-b02c-73bf58cd1377)
*   **Self-Hosted Prefect UI**: `http://146.148.87.26:4200`
*   **Serverless Streamlit UI**: [Log Workouts Live](https://fitness-streamlit-ui-94214537108.us-central1.run.app)

---

## AI Collaboration Notice

I migrated, debugged, and optimized this cloud setup in collaboration with an AI coding partner (Cline running Claude 3.5 Sonnet). Together, we worked through several real-world engineering constraints: diagnosing kernel Out-Of-Memory (OOM) crashes via GCP serial logs, refactoring the Python API layer, resolving SQLite database locks, and designing a lightweight, sequential execution pipeline. 

It's a great example of how a developer and an AI assistant can cooperatively build and harden a complete, low-cost cloud system.

---

## Architecture & Data Flow

```
                                      [ Google Cloud Platform ]
                                      
  +----------------------+             +-------------------------------------------------+
  |  Google Cloud Run    |             |                 GCP e2-micro VM                 |
  |                      |             |                                                 |
  |  +----------------+  |  API POST   |  +-------------------+   +-------------------+  |
  |  |   Streamlit    |  |------------>|  |    Gunicorn APIs   |   |   Local MySQL     |  |
  |  |  Workout Entry |  | (Port 5001) |  |   (Ports 5000/5001)  |   | (Optimized RAM)   |  |
  |  +----------------+  |             |  +-------------------+   +---------^---------+  |
  |                      |             |                                   |
  |  (Scales to Zero!)   |             |  (Protected by a 2GB swap file)   |
  +----------------------+             +-------------------------------------------------+
```

1.  **Log Workouts**: I log my weight and strength workouts on a Streamlit web app. It is hosted on Google Cloud Run and scales down to zero instances when inactive to keep compute costs at $0.
2.  **API Layer**: The Streamlit app sends workout logs to a Flask API on port 5001 (served via Gunicorn on the VM), which writes them to MySQL.
3.  **Automatic Ingestion**: A background Prefect daemon runs on the VM to fetch raw sleep, steps, heart rate, and GPS logs directly from Google Drive and Cloud Storage.
4.  **Weather Enrichment**: The pipeline reverse-geocodes my GPS coordinates to find my location, queries the Visual Crossing Weather API for the conditions at that hour, and saves the enriched data to MySQL.
5.  **Analytics**: Looker Studio connects directly to the MySQL database to populate interactive dashboards tracking my health and fitness trends over time.

---

## VM Constraints & Optimizations

Running a full database, orchestration server, and two APIs on a GCP `e2-micro` instance with only 1 GB of physical RAM required several critical performance tuning steps:

*   **Virtual Memory Protection**: We configured a permanent 2.0 GB swap file (`/swapfile`) on the VM's SSD, bringing total virtual memory to 3 GB. This prevents system freezes and Out-Of-Memory (OOM) crashes during database imports.
*   **Sequential Pipeline Execution**: To prevent CPU and disk I/O bottlenecks, we consolidated the 11 separate hourly ingestion pipelines into a single unified flow (`hs_hourly_etl`) that executes each task sequentially (one-by-one) instead of concurrently.
*   **Lock-Free Database Concurrency**: Prefect's local SQLite database (`prefect.db`) is configured to run in Write-Ahead Logging (WAL) Mode (`PRAGMA journal_mode=WAL;`). This allows concurrent read/write operations, completely eliminating `database is locked` errors during scheduled runs.
*   **Tuned MySQL 8.0**: Capped the InnoDB buffer pool to `64MB` (`innodb_buffer_pool_size=67108864`) to ensure the database operates comfortably alongside the Prefect server.
*   **Stable API Connections**: Refactored the core Flask API from `flask-mysqldb` to native `mysql-connector-python` to resolve worker crashes and guarantee compatibility with Flask 3.0+.

---

## Project Structure

```
/
├── fitness_api/                      # Flask API served via Gunicorn (Port 5001)
├── fitness_streamlit_app/            # Workout Entry Portal deployed on GCP Cloud Run
├── gps_logger_app/                   # GPS logging API served via Gunicorn (Port 5000)
├── scripts/
│   ├── orchestrate.py                # Core Prefect sequential orchestration pipeline
│   └── etl/                          # Python Extract-Transform-Load scripts
├── vm_config/
│   ├── mysql/                        # Low-memory my.cnf limits
│   └── systemd/                      # Managed daemon systemd units (Prefect & APIs)
└── ARCHITECTURE_AND_MANAGEMENT.md    # Master sysadmin operations & troubleshooting playbook
```
