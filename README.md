# HealthHub: Enterprise Cloud-Native Fitness Ingestion & Orchestration Ecosystem

**HealthHub** is a highly optimized, fully automated data engineering and orchestration ecosystem that ingests, transforms, and analyzes multi-source fitness, sleep, vital, and spatial telemetry data. Originally hosted on a local Raspberry Pi cluster, the system has been migrated to a highly resource-efficient, production-grade cloud architecture under the **Google Cloud Platform (GCP) Always Free Tier ($0/month)**.

Integrated analytics, vital trends, and spatial fitness correlations are presented in real-time via interactive **Looker Studio (Data Studio) Dashboards**.

📊 **Looker Studio Dashboard Link**: [Access Live Reporting](https://datastudio.google.com/reporting/4d204527-a6ef-4860-b02c-73bf58cd1377)  
🎧 **Self-Hosted Prefect UI**: `http://146.148.87.26:4200`  
🎨 **Serverless Streamlit UI**: [Log Workouts Live](https://fitness-streamlit-ui-94214537108.us-central1.run.app)

---

## Technical Architecture Overview

The system is designed with a strict emphasis on cloud-native scalability, zero-cost budgeting, and high resource efficiency, enabling heavy data pipelines to run smoothly on a micro virtual machine with only 1 GB of physical RAM.

```
                                      [ Google Cloud Platform ]
                                      
  +----------------------+             +-------------------------------------------------+
  |  Google Cloud Run    |             |                 GCP e2-micro VM                 |
  |                      |             |                                                 |
  |  +----------------+  |  API POST   |  +-------------------+   +-------------------+  |
  |  |   Streamlit    |  |------------>|  |    Gunicorn APIs   |   |   Local MySQL     |  |
  |  |  Workout Entry |  | (Port 5001) |  |   (Ports 5000/5001)  |   | (Optimized RAM)   |  |
  |  +----------------+  |             |  +-------------------+   +---------^---------+  |
  |  (Scales to Zero!)   |             |                                    |            |
  +----------------------+             |  +-------------------+             |            |
                                       |  |  Prefect Daemon   |-------------+            |
  +----------------------+             |  | (Sequential ETL)  |   Load Ingested Data     |
  |   Cloud Storage &    |             |  +---------^---------+                          |
  |   Google Drive APIs  |             |            |                                    |
  |                      |  Ingest Raw |  +---------v---------+                          |
  |  +----------------+  |  CSVs/APIs  |  |  Prefect Server   |                          |
  |  |  Galaxy Watch  |  |------------>|  |  (SQLite WAL Mode)|                          |
  |  |  GPS Telemetry |  |             |  +-------------------+                          |
  |  +----------------+  |             |  (2GB Virtual SWAP)                             |
  +----------------------+             +-------------------------------------------------+
```

### 1. Compute & Resource Stabilization (GCP e2-micro VM)
*   **Virtual Memory Optimization**: Operating on a single-core instance with a hard limit of 1 GB physical RAM, the host is protected against Out-of-Memory (OOM) kernel panics and SSH connection freezes by a permanently configured **2.0 GB SSD swap file** (`/swapfile`). This extends total virtual memory to 3 GB, maintaining continuous system stability during heavy database writes.
*   **Micro-Tuned Relational Database (MySQL 8.0)**: Tuned specifically for low-memory micro instances. The global InnoDB buffer pool is restricted to `64MB` (`innodb_buffer_pool_size=67108864`), thread stack sizes are minimized, and maximum concurrent connections are capped to prevent memory leaks and thread exhaustion under peak pipeline loads.

### 2. Modern Workflow Orchestration (Self-Hosted Prefect Open Source)
*   **Decoupled Orchestration**: Migrated from a heavy, resource-intensive legacy Airflow instance to a lightweight, self-hosted **Prefect Open Source Core** server. 
*   **Lock-Free Database Concurrency (SQLite WAL Mode)**: Prefect's backing metadata store (`prefect.db`) is configured to run in **Write-Ahead Logging (WAL) Mode** (`PRAGMA journal_mode=WAL;`). This replaces traditional exclusive locking with concurrent readers and writers, resolving all SQLite database blockages and job scheduling latencies.
*   **Sequential Pipeline Ingestion (CPU/Disk Flattening)**: To prevent CPU and disk I/O bottlenecks, the 11 separate hourly ingestion pipelines (extracting sleep, steps, heart rate, oxygen, running, cycling, etc.) are consolidated into a single, unified orchestration flow (`hs_hourly_etl`). This flow executes each sub-pipeline sequentially (one-by-one), maintaining a flat, predictable resource profile on the VM.

### 3. Serverless Frontend UI (Google Cloud Run)
*   **Auto-Scaling Streamlit Interface**: The Streamlit-based workout entry portal is packaged as a Docker container and deployed serverless on **Google Cloud Run**. 
*   **Zero-Cost Scaling**: Configured to scale down to **zero active instances** (`--min-instances 0`) when inactive, ensuring $0/month GCR compute charges. When a user opens the interface, it instantly spins up, executes POST/GET payloads to the VM's custom Flask/Gunicorn API (port `5001`), and scales back down upon completion.

---

## Ingestion & ETL Pipeline Flow

The orchestrator manages roughly 20 ingestion steps, running on a dual-trigger schedule (every 30 minutes for spatial telemetry and hourly for vital/activity datasets):

1.  **Extract**: Python sub-tasks leverage service account OAuth2 keys to programmatically query **Google Cloud Storage (GCS) Buckets** and **Google Drive folders** containing raw Galaxy Watch exports (synced via Health Sync) and GPS loggers.
2.  **Transform**: Data is parsed into structured Pandas DataFrames, performing coordinate smoothing, date/time normalizations, and cleaning null values.
3.  **Enrichment (Weather API & Geocoding)**: Location coordinates are reverse-geocoded to map exact city and country boundaries. These coordinates are then used to query the **Visual Crossing Weather API** at the rounded hour of each tracking point, correlating weather conditions (temperature, precipitation, wind speed) with individual vital and athletic performance metrics.
4.  **Load**: Cleaned, enriched records are batch-inserted into MySQL tables using optimized bulk `executemany` database transactions.

---

## Project Repository Structure

```
/
├── fitness_api/                      # Custom Flask API served via Gunicorn (Port 5001)
├── fitness_streamlit_app/            # Workout Entry Portal deployed on GCP Cloud Run
├── gps_logger_app/                   # GPS logging API served via Gunicorn (Port 5000)
├── scripts/
│   ├── orchestrate.py                # Core Prefect sequential orchestration pipeline
│   └── etl/                          # Discrete Python Extract-Transform-Load scripts
├── vm_config/
│   ├── mysql/                        # Low-memory my.cnf limits
│   └── systemd/                      # Managed daemon systemd units (Prefect & APIs)
└── ARCHITECTURE_AND_MANAGEMENT.md    # Master sysadmin operations & troubleshooting playbook
```

---

## Clean Boot & Service Management

All backend APIs, database daemons, and orchestrators on the VM are managed as native `systemd` service units to ensure automatic recovery upon reboots.

```bash
# Check status of all system units
sudo systemctl status prefect-server prefect-daemon mysql fitness-api gps-logger-api --no-pager
```

*Developed as a demonstration of high-efficiency, zero-budget cloud migration architecture and enterprise-grade data engineering.*
