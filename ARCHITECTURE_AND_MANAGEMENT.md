# Cloud Fitness Architecture & Data Flow Documentation

This document describes the end-to-end target architecture, data flows, and links required to manage your personal health and fitness analytics system on the GCP Always Free Tier.

---

## 1. End-to-End Personal Data Flows

The data flows from Google APIs, Google Drive, your mobile device (GPS Logger), and the Streamlit App, landing into your centralized Looker Studio dashboard:

```
+------------------+     (1) Extracts raw CSVs hourly
|   Google Drive   |==============================================+
+------------------+                                              |
                                                                  v
+------------------+     (2) Scrapes location data (30m)    +-----------+
|  Google Maps API |=======================================>|  Prefect  |
+------------------+                                        |  Flows    |
                                                            | (VM-side) |
+------------------+     (3) Fetches matching weather       +-----+-----+
| OpenWeather API  |==============================================+     |
+------------------+                                              |     |
                                                                  |     | (4) Transforms and
                                                                  |     |     loads clean CSVs
                                                                  v     v
+------------------+     (5) POSTs GPS coordinates          +-----------+
| GPS Logger App   |=======================================>|  GCP VM   |
+------------------+                                        |  Local    |
                                                            |  MySQL    |
+------------------+     (6) Adds workouts / diet logs      |  Database |
|  Streamlit UI    |=======================================>+-----+-----+
|   (Cloud Run)    |                                              |
+------------------+                                              | (7) Direct Database
                                                                  |     Connector
                                                                  v
                                                            +-----------+
                                                            |  Looker   |
                                                            |  Studio   |
                                                            | Dashboard |
                                                            +-----------+
```

---

## 2. Key Management Links

Use these direct console links to monitor, configure, and visualize your fitness tracking system.

| Dashboard / Service | URL | Purpose |
| :--- | :--- | :--- |
| **GCP Cloud Console** | [console.cloud.google.com](https://console.cloud.google.com) | Central dashboard for billing, projects, and monitoring. |
| **Compute Engine Instances** | [console.cloud.google.com/compute/instances](https://console.cloud.google.com/compute/instances) | Power on/off your e2-micro VM, view CPU/RAM usage, and SSH in. |
| **Cloud Run Console** | [console.cloud.google.com/run](https://console.cloud.google.com/run) | Monitor Streamlit container instances, access limits, and view weblogs. |
| **VPC Firewall Rules** | [console.cloud.google.com/networking/firewalls/list](https://console.cloud.google.com/networking/firewalls/list) | Manage security rules for Port `5001` (Fitness API), `5000` (GPS), and `4200` (Prefect). |
| **Prefect Dashboard** | `http://<YOUR_VM_EXTERNAL_IP>:4200` | Access the headless Prefect Web UI to inspect flow runs, logs, and schedules. |
| **Looker Studio Creator** | [lookerstudio.google.com](https://lookerstudio.google.com) | Build, view, and customize your fitness charts and dashboards. |

---

## 3. Step-by-Step Initial VM Deployment Guide

Since cloud orchestrators and local service accounts don't have SSH keys or direct network admin permissions to manipulate your live GCP account, use this guide to apply the changes in 2 minutes:

### Step 3A: Open Ports 4200, 5000, 5001 in your GCP Firewall
If you cannot use the link, navigate manually using the sidebar inside the Google Cloud Console:
1. Open the [GCP Cloud Console](https://console.cloud.google.com).
2. Click the **Navigation Menu** (three horizontal bars in the top left corner).
3. Scroll down and hover over **VPC network**, then select **Firewall** (or click [this direct link](https://console.cloud.google.com/networking/firewalls/list)).
4. Click the **CREATE FIREWALL RULE** button at the top.
5. Enter the following properties:
   *   **Name**: `allow-fitness-system`
   *   **Network**: `default`
   *   **Priority**: `1000`
   *   **Direction of traffic**: `Ingress`
   *   **Action on match**: `Allow`
   *   **Targets**: `All instances in the network`
   *   **Source filter**: `IP ranges`
   *   **Source IP ranges**: `0.0.0.0/0`
   *   **Protocols and ports**: Check **TCP** and enter `4200, 5000, 5001`
6. Click **Create** at the bottom.

---

### Step 3B: Connect to your VM, Install Packages, and Clone Code
1. Open your computer's terminal and SSH into your VM:
   ```bash
   gcloud compute ssh health-stats-vm --zone=us-central1-a
   ```
2. Run system package updates and install necessary system-level dependencies (including MySQL Server, Python3, Pip, and Gunicorn):
   ```bash
   sudo apt update && sudo apt install -y mysql-server python3-pip python3-venv gunicorn
   ```
3. Clone your GitHub repository onto the VM and move into it:
   ```bash
   git clone <YOUR_GITHUB_REPO_URL> health_stats
   cd health_stats
   ```

---

### Step 3C: Apply low-memory MySQL configuration
Run these commands to apply the customized low-memory configuration to fit under the 1GB RAM ceiling:
```bash
# Copy low-memory mysql configuration to MySQL's config directory
sudo cp vm_config/mysql/low-memory.cnf /etc/mysql/conf.d/low-memory.cnf

# Restart MySQL to apply RAM limitations
sudo systemctl restart mysql
```

---

### Step 3D: Install Python Packages, and Activate Gunicorn and Prefect systemd Services
Install Python-level package requirements first, then copy the service files, reload systemd, and turn on the active services so they run automatically:
```bash
# Install Python dependencies globally on the VM
sudo pip3 install -r requirements.txt prefect gunicorn flask flask-mysqldb mysql-connector-python

# Copy systemd service files to systemd directory
```bash
# Copy systemd service files to systemd directory
sudo cp vm_config/systemd/*.service /etc/systemd/system/

# Reload systemd manager configuration
sudo systemctl daemon-reload

# Enable services to run at boot, and start them immediately
sudo systemctl enable --now prefect-daemon fitness-api gps-logger-api
```

---

## 4. Operations & Maintenance Playbook

### A. Monitoring RAM Footprint (1GB Limit)
Since you are on a tight 1GB RAM budget, SSH into your VM and check RAM allocation using:
```bash
free -h
```
Or view sorted process memory utilization:
```bash
ps aux --sort=-%mem | head -n 10
```

### B. Troubleshooting VM systemd Services
To check the running logs and status of your active pipelines and APIs:

*   **Prefect Flows Daemon**:
    ```bash
    sudo journalctl -u prefect-daemon.service -f -n 50
    ```
*   **Fitness API**:
    ```bash
    sudo journalctl -u fitness-api.service -f -n 50
    ```
*   **GPS Logger App**:
    ```bash
    sudo journalctl -u gps-logger-api.service -f -n 50
    ```

### C. Manually Triggering a Flow Run
You can run any flow immediately by running its Python trigger (e.g. `python3 scripts/orchestrate.py` will spin up the local scheduler).
