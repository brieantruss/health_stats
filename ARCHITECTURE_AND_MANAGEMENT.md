# Health Stats Architecture & Management

This document describes the architecture currently configured in this repository and the commands used to operate it. It is a deployment and troubleshooting reference, not proof of the state of a remote VM or GCP service. Confirm live state with the checks in [Operations](#operations).

Repository baseline: `2026-09-22`.

## 1. Current Architecture

```text
 Samsung Health / Health Sync                         GPS Logger phone
          | Google Drive exports                              |
          v                                                   v
   +------------------+                              +------------------+
   | Prefect ETL      |                              | GPS Logger API   |
   | VM: 4200         |                              | VM: 5000         |
   +--------+---------+                              +--------+---------+
            |                                                 |
            | extract, transform, load                         |
            v                                                 |
   +----------------------------------------------------------------+
   | GCP e2-micro VM                                               |
   | MySQL: health_stats | Fitness API: 5001 | Event SQLite queue  |
   +-------------------+----------------------+-------------------+
                       |                      |
                       | manual/scripted sync |
                       v                      v
                +-------------+       +------------------+
                | BigQuery    |       | SSE/REST         |
                | health_stats|       | telemetry API    |
                +------+------+       +--------+---------+
                       |                         |
                       v                         v
                +-------------+       +------------------+
                | Dataform    |       | Ops dashboard    |
                | SQLX views  |       | React/Vite       |
                +------+------+       | port 5173       |
                       |              +------------------+
                       v
                Looker Studio / Health Copilot

 Separate Compose services:
   mcp-bigquery-server :8000 (localhost-only host binding)
   health-copilot-ui   :8502
   ops-dashboard       :5173
```

### Runtime boundaries

| Component | Current role | Configured runtime |
| :--- | :--- | :--- |
| MySQL `health_stats` | Transactional store for imported health data and workout/diet entries | VM, local port `3306` |
| Prefect server | Local orchestration API and UI | systemd, port `4200` |
| Prefect ETL daemon | Runs the hourly health ETL and 30-minute location enrichment deployment | systemd |
| Prefect agents daemon | Runs scheduled coaching/analysis agents | systemd |
| Fitness API | Workout, diet, telemetry, REST, and SSE endpoints | Gunicorn, port `5001` |
| GPS Logger API | Receives mobile GPS posts at `POST /gps_data` | Gunicorn, port `5000` |
| Event stream | WAL-enabled SQLite queue and latest health snapshots | `health_events.db` |
| Event consumer | Processes queued operational events | systemd |
| BigQuery MCP server | Read-only query gateway for the `health_stats` dataset | Docker Compose, port `8000`, host-local only |
| Health Copilot UI | Streamlit conversational BigQuery client | Docker Compose, port `8502` |
| Ops dashboard | React/TypeScript telemetry and event dashboard | systemd preview or Compose, port `5173` |
| Workout Streamlit UI | Workout and diet entry frontend | Cloud Run deployment target; API URL is configurable |
| BigQuery | Analytical warehouse for synchronized MySQL tables | Project `my-data-479716`, dataset `health_stats`, location `US` |
| Dataform | SQLX analytical view definitions | `definitions/*.sqlx`; deployment is external to this repository |

The Compose file does not start MySQL, Prefect, either Flask API, or the event consumer. Those components are VM/systemd services. The Compose stack is the MCP, Copilot, and local operations-dashboard layer.

## 2. Data Flows

1. Health Sync exports Samsung Health data to Google Drive. Prefect ETL scripts download, transform, and load supported categories into MySQL.
2. The hourly deployment runs the 11 standard categories sequentially to limit memory and CPU pressure on the e2-micro VM.
3. The location deployment runs every 30 minutes: GPS extraction, location loading, reverse geocoding, weather, AQI, and forecast enrichment.
4. The workout UI sends entries to the Fitness API. The GPS Logger app sends coordinates to the GPS Logger API.
5. The Fitness API publishes operational events to the local SQLite queue. The event consumer updates the operational snapshot used by REST/SSE telemetry consumers.
6. `scripts/mysql_to_bigquery.py` copies configured MySQL tables to BigQuery with overwrite loads. The repository contains the sync script, but does not contain a cron or systemd timer; the schedule must be verified on the VM.
7. Dataform definitions in `definitions/` build analytical views in BigQuery when the Dataform workflow is run.
8. Looker Studio reads BigQuery views. The Health Copilot uses the read-only MCP gateway to query selected BigQuery views and render conversational answers/charts.

## 3. Schedules and Workloads

### Prefect ETL

`scripts/orchestrate.py` serves two deployments:

- `hourly-etl`: every hour; sequentially runs blood pressure, cycling, heart rate, oxygen, running, shootaround, sleep, steps, swimming, VO2 max, and walking ETL.
- `location`: every 30 minutes; loads locations and performs reverse geocoding, weather, AQI, and forecast enrichment.

Run both flows immediately for a controlled manual test:

```bash
python3 scripts/orchestrate.py --run-now
```

### Health agents

The agent deployment is configured in `scripts/agents/orchestrate_agents.py`:

| Agent | Schedule |
| :--- | :--- |
| Weather AQI Guard | Daily at 07:30 |
| Cardio Load Preventer | Daily at 08:00 |
| Sleep Recovery Optimizer | Saturdays at 08:30 |
| Health Trend Analyst | Sundays at 08:00 |

Reports are written to the repository's `reports/` directory when the agent runtime is configured to run successfully. They are intended to be uploaded to Google Drive by the uploader integration.

## 4. Management Links

| Service | Link or command | Purpose |
| :--- | :--- | :--- |
| GCP Console | [console.cloud.google.com](https://console.cloud.google.com) | Billing, IAM, APIs, and monitoring |
| Compute Engine | [console.cloud.google.com/compute/instances](https://console.cloud.google.com/compute/instances) | VM power, serial logs, SSH, and resource usage |
| Cloud Run | [console.cloud.google.com/run](https://console.cloud.google.com/run) | Workout UI deployment and logs |
| Firewall rules | [console.cloud.google.com/networking/firewalls/list](https://console.cloud.google.com/networking/firewalls/list) | Review externally reachable VM ports |
| Prefect UI | `http://<VM_EXTERNAL_IP>:4200` | Flow runs, deployments, and logs |
| Looker Studio | [lookerstudio.google.com](https://lookerstudio.google.com) | Analytical dashboards |
| Public dashboard | [Health Stats - Public](https://datastudio.google.com/reporting/4d204527-a6ef-4860-b02c-73bf58cd1377) | Current published visualization |

Do not expose port `8000` publicly. Compose binds the MCP server to `127.0.0.1:8000`; the Copilot container reaches it over the private `health-network` bridge.

## 5. Deployment and Operations

### VM service installation

The unit files in `vm_config/systemd/` are the source of truth for the configured VM services. They currently define:

```text
prefect-server.service
prefect-daemon.service
prefect-agents.service
fitness-api.service
gps-logger-api.service
health-event-stream.service
health-ops-dashboard.service
```

The units reference `/home/briean/health_stats` for most VM services. The operations dashboard unit references `/home/briean/dev/health_stats`. Keep these paths aligned with the actual checkout before enabling services.

Typical installation on the VM:

```bash
sudo apt update
sudo apt install -y mysql-server python3-pip python3-venv gunicorn nodejs npm
sudo cp vm_config/mysql/low-memory.cnf /etc/mysql/conf.d/low-memory.cnf
sudo systemctl restart mysql
sudo cp vm_config/systemd/*.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable --now prefect-server prefect-daemon prefect-agents \
  fitness-api gps-logger-api health-event-stream health-ops-dashboard
```

Install Python dependencies in the project environment rather than relying on a global interpreter:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
pip install -r fitness_api/requirements.txt -r gps_logger_app/requirements.txt
pip install -r mcp_bigquery_server/requirements.txt
```

### Compose services

From the repository root:

```bash
docker compose up -d --build
docker compose ps
docker compose logs -f mcp-bigquery-server health-copilot-ui ops-dashboard
```

The Compose services require the host credentials directory `/home/briean/.gcp` and the BigQuery service-account file expected by the containers. Treat those credentials as host-managed secrets; do not commit them.

### Workout UI on Cloud Run

The deployment target is `fitness-streamlit-ui` in `us-central1`, with scale-to-zero, one maximum instance, `256Mi` memory, and the Fitness API URL supplied through `API_BASE_URL`:

```bash
gcloud run deploy fitness-streamlit-ui \
  --source fitness_streamlit_app \
  --region us-central1 \
  --platform managed \
  --allow-unauthenticated \
  --min-instances 0 --max-instances 1 --memory 256Mi --cpu 1 \
  --set-env-vars API_BASE_URL="http://<VM_EXTERNAL_IP>:5001"
```

The public Cloud Run service must be able to reach the VM API. Review firewall exposure and authentication before using `--allow-unauthenticated` in a production setting.

## 6. Health Checks and Troubleshooting

Check service state and recent failures:

```bash
sudo systemctl --failed
sudo systemctl status prefect-server prefect-daemon prefect-agents
sudo systemctl status fitness-api gps-logger-api health-event-stream health-ops-dashboard
sudo journalctl -u <service-name> -n 100 --no-pager
```

Check listeners and VM memory:

```bash
sudo ss -ltnp | grep -E ':4200|:5000|:5001|:8502|:8000|:5173'
free -h
ps aux --sort=-%mem | head -n 10
```

Check the application surfaces locally:

```bash
curl http://127.0.0.1:5001/
curl http://127.0.0.1:5001/api/pipeline/status
curl http://127.0.0.1:5000/
curl http://127.0.0.1:4200/api/health
```

Run a manual warehouse sync when appropriate:

```bash
python3 scripts/mysql_to_bigquery.py
```

The sync currently includes operational and nutrition tables in addition to the activity tables. It uses `WRITE_TRUNCATE` semantics and should be treated as a full refresh of each selected destination table. Pass valid table names to limit a run, for example:

```bash
python3 scripts/mysql_to_bigquery.py sleep weather
```

## 7. Data, Credentials, and Resource Constraints

- MySQL defaults to `health_stats` / user `modulo`; override API connection values with `MYSQL_HOST`, `MYSQL_USER`, `MYSQL_PASSWORD`, and `MYSQL_DB`.
- BigQuery defaults are project `my-data-479716`, dataset `health_stats`, and location `US`, as defined in `workflow_settings.yaml`.
- BigQuery credentials are expected outside the repository, normally at `/home/briean/.gcp/bigquery-agent-key.json` or through Application Default Credentials.
- Prefect metadata uses SQLite. The event queue uses repository-root `health_events.db` with WAL mode for concurrent producer/consumer access.
- `vm_config/mysql/low-memory.cnf` caps MySQL memory for the e2-micro target. A swap file may be present on the VM, but its existence is an operational fact to verify rather than something created by this repository.
- Do not publish service-account keys, Gemini keys, OAuth tokens, database passwords, SQLite databases, generated reports, or raw health exports.

## 8. Known Gaps and Verification Notes

The repository cannot prove that a remote VM, Cloud Run revision, Prefect deployment, cron entry, BigQuery sync, or Dataform workflow is currently running. Before calling the system live, verify:

1. The systemd unit paths match the active checkout and all expected units are active.
2. The BigQuery sync is scheduled externally if hourly refresh is required; no scheduler for `mysql_to_bigquery.py` is committed here.
3. Dataform workflows are deployed and compiling the SQLX definitions; no Dataform deployment command or CI workflow is included here.
4. Cloud Run `API_BASE_URL` points to the current VM address and the required firewall route works.
5. The dashboard's production proxy can resolve `fitness-api`; the Compose file does not define a service with that name, so the systemd/VM deployment and Compose deployment are separate modes.
6. Firewall rules expose only the endpoints that must be public. In particular, keep MCP port `8000` private.
