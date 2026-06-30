# Health Stats: Personal Health & Fitness Data Pipeline & Cloud Orchestration

Health Stats is an automated data platform that ingests, cleans, and consolidates full historical personal fitness data from my [Samsung Galaxy Watch](https://www.samsung.com/us/watches/) (including daily steps, sleep, and vitals), location data from mobile phone GPS logging, and workout details from a custom-built exercise logging API into a single database and visualizes the results for tracking and analysis. 

Originally built manually and running on a local Raspberry Pi cluster, this system was agentically migrated and optimized to run on the GCP Always Free Tier (using an e2-micro VM and serverless Cloud Run) for $0/month. It was developed as a practical application project in preparation for successfully certifying as a [Google Cloud Platform Professional Data Engineer](https://cloud.google.com/learn/certification/data-engineer).

*   **Looker Studio Dashboard**: [Access Live Reporting](https://datastudio.google.com/reporting/4d204527-a6ef-4860-b02c-73bf58cd1377)
*   **Self-Hosted Prefect UI**: `http://146.148.87.26:4200`

---

## AI Collaboration Notice

I migrated, debugged, and optimized this cloud setup in collaboration with an AI coding partner (Cline running Claude 3.5 Sonnet). Together, we worked through several real-world engineering constraints: diagnosing kernel Out-Of-Memory (OOM) crashes via GCP serial logs, refactoring the Python API layer, resolving SQLite database locks, and designing a lightweight, sequential execution pipeline. 

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
5.  **Data Warehouse Sync**: An automated hourly cron job on the VM runs a custom Python script (`mysql_to_bigquery.py`) to sync all 18 tables from MySQL to BigQuery using the `WRITE_TRUNCATE` pattern.
6.  **Analytics**: Looker Studio connects directly to **BigQuery** (instead of hitting the transactional MySQL database) to populate interactive dashboards tracking my health and fitness trends over time with zero transactional overhead!

---

## BigQuery Table Schema Mapping

| MySQL Source Table | Target BigQuery Table | Sync Pattern | Data Domain / Description |
| :--- | :--- | :--- | :--- |
| `blood_pressure` | `health_stats.blood_pressure` | Overwrite | Daily blood pressure (systolic/diastolic) vitals |
| `cycling` | `health_stats.cycling` | Overwrite | High-frequency GPS & speed telemetry from cycling |
| `cycling_summary` | `health_stats.cycling_summary` | Overwrite | Aggregate metrics per cycling workout session |
| `diet` | `health_stats.diet` | Overwrite | Daily food intake logs synced from Streamlit/MyFitnessPal |
| `exercises` | `health_stats.exercises` | Overwrite | Custom strength and cardio exercise definitions |
| `food_descriptions` | `health_stats.food_descriptions` | Overwrite | Calorie & macronutrient density data per food item |
| `food_ingredients` | `health_stats.food_ingredients` | Overwrite | Recipe ingredient mappings and custom logged meals |
| `heart_rate` | `health_stats.heart_rate` | Overwrite | Continuous second-by-second heart rate tracking |
| `locations` | `health_stats.locations` | Overwrite | Spatial latitude/longitude coordinates from watch GPS |
| `oxygen` | `health_stats.oxygen` | Overwrite | Blood oxygen saturation (SpO2) vitals tracking |
| `running` | `health_stats.running` | Overwrite | Granular running metrics and interval pace telemetry |
| `shootaround` | `health_stats.shootaround` | Overwrite | Basketball session times, active minutes, and logs |
| `sleep` | `health_stats.sleep` | Overwrite | Granular sleep stages (deep, light, REM, awake) |
| `steps` | `health_stats.steps` | Overwrite | Daily and hourly steps accumulated |
| `swimming` | `health_stats.swimming` | Overwrite | Ingested lap counts, stroke rates, and swim telemetry |
| `vo2max` | `health_stats.vo2max` | Overwrite | Cardiovascular fitness (VO2 Max) trends |
| `walking` | `health_stats.walking` | Overwrite | Step length, symmetry, and speed telemetry |
| `weather` | `health_stats.weather` | Overwrite | Weather conditions correlated hourly with location data |

---

## VM Constraints & Optimizations

Running a full database, orchestration server, and two APIs on a GCP `e2-micro` instance with only 1 GB of physical RAM required several critical performance tuning steps:

*   **Virtual Memory Protection**: We configured a permanent 2.0 GB swap file (`/swapfile`) on the VM's SSD, bringing total virtual memory to 3 GB. This prevents system freezes and Out-Of-Memory (OOM) crashes during database imports.
*   **Sequential Pipeline Execution**: To prevent CPU and disk I/O bottlenecks, we consolidated the 11 separate hourly ingestion pipelines into a single unified flow (`hs_hourly_etl`) that executes each task sequentially (one-by-one) instead of concurrently.
*   **Lock-Free Database Concurrency**: Prefect's local SQLite database (`prefect.db`) is configured to run in Write-Ahead Logging (WAL) Mode (`PRAGMA journal_mode=WAL;`). This allows concurrent read/write operations, completely eliminating `database is locked` errors during scheduled runs.
*   **Tuned MySQL 8.0**: Capped the InnoDB buffer pool to `64MB` (`innodb_buffer_pool_size=67108864`) to ensure the database operates comfortably alongside the Prefect server.
*   **Stable API Connections**: Refactored the core Flask API from `flask-mysqldb` to native `mysql-connector-python` to resolve worker crashes and guarantee compatibility with Flask 3.0+.
*   **Zero-Overhead BigQuery Sync**: Wrote a highly memory-efficient Python sync script (`scripts/mysql_to_bigquery.py`) that queries MySQL in chunks of 10,000 rows, streams them directly to local CSV files on the VM's disk, and uploads them using BigQuery's `load_table_from_file` stream. This caps RAM usage under 10MB (compared to >1.5GB of Pandas/PyArrow RAM spikes), eliminating disk thrashing or VM lockups during multi-million-row transfers.

---

## Project Structure

```
/
├── fitness_api/                      # Flask API served via Gunicorn (Port 5001)
├── fitness_streamlit_app/            # Workout Entry Portal deployed on GCP Cloud Run
├── gps_logger_app/                   # GPS logging API served via Gunicorn (Port 5000)
├── scripts/
│   ├── mysql_to_bigquery.py          # Lightweight BigQuery synchronization script
│   ├── orchestrate.py                # Core Prefect sequential orchestration pipeline
│   └── etl/                          # Python Extract-Transform-Load scripts
├── vm_config/
│   ├── mysql/                        # Low-memory my.cnf limits
│   └── systemd/                      # Managed daemon systemd units (Prefect & APIs)
└── ARCHITECTURE_AND_MANAGEMENT.md    # Master sysadmin operations & troubleshooting playbook
```
