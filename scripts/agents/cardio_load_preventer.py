import os
import sys
from datetime import datetime, timedelta
import logging
from google.cloud import bigquery
from prefect import flow, task

# Append current directory to path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gdrive_uploader import upload_report_to_gdrive, append_to_gsheet

# --- Configuration ---
PROJECT_ID = "my-data-479716"
KEY_PATH = "/home/briean/.gcp/bigquery-agent-key.json"
LOCAL_REPORTS_DIR = "/home/briean/dev/health_stats/reports"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

@task(name="generate_cardio_load_report")
def generate_cardio_load_report():
    client = get_bigquery_client()
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # Query running records over the last 30 days
    query = f"""
        SELECT
          activity_date,
          CAST(distance_miles AS FLOAT64) as distance_miles,
          CAST(active_time_minutes AS FLOAT64) as active_time_minutes,
          CAST(avg_heart_rate AS INT64) as avg_heart_rate
        FROM
          `{PROJECT_ID}.health_stats.view_running`
        WHERE
          PARSE_DATE('%Y.%m.%d', SPLIT(activity_date, ' ')[OFFSET(0)]) >= DATE_SUB(CURRENT_DATE(), INTERVAL 30 DAY)
        ORDER BY
          activity_date DESC;
    """
    
    logging.info("Querying 30-day running logs from BigQuery...")
    try:
        query_job = client.query(query)
        rows = list(query_job.result())
    except Exception as e:
        logging.error(f"BigQuery query failed: {e}")
        return None

    # Calculate Acute and Chronic Training Loads
    # Acute Load = Sum of miles over the last 7 days
    # Chronic Load = Average of weekly miles over the past 28 days (calculated as monthly sum / 4)
    
    today = datetime.now().date()
    acute_miles = 0.0
    chronic_miles_total = 0.0
    recent_runs = []
    
    for r in rows:
        # Parse the activity date string cleanly (handling potential timestamps)
        date_part = r.activity_date.split(' ')[0]
        try:
            run_date = datetime.strptime(date_part, '%Y.%m.%d').date()
        except Exception:
            continue
            
        days_ago = (today - run_date).days
        
        if days_ago <= 7:
            acute_miles += r.distance_miles
        if days_ago <= 28:
            chronic_miles_total += r.distance_miles
            
        if len(recent_runs) < 3:
            recent_runs.append({
                "date": date_part,
                "miles": r.distance_miles,
                "mins": r.active_time_minutes,
                "hr": r.avg_heart_rate
            })

    # Chronic Load = Average weekly mileage (total of 28 days divided by 4 weeks)
    chronic_weekly_avg = chronic_miles_total / 4.0
    
    # Avoid division by zero if there's no baseline chronic volume yet
    if chronic_weekly_avg < 1.0:
        chronic_weekly_avg = 5.0 # Set a healthy baseline average of 5 miles per week
        
    acwr = acute_miles / chronic_weekly_avg
    
    # Establish Sports-Science ACWR Zones & Recommendations
    if acwr < 0.8:
        status_zone = "🔵 UNDER-TRAINING (Low Workload)"
        zone_color = "blue"
        safety_status = "Safe to increase training volume."
        recommendation = "You have room to safely build your cardiorespiratory base today. We recommend a solid **3.5 mile run** at your target aerobic pace."
    elif acwr <= 1.3:
        status_zone = "🟢 THE SWEET SPOT (Optimal Training)"
        zone_color = "green"
        safety_status = "Optimal fitness gains with extremely low injury risk!"
        recommendation = "You are in perfect athletic balance! Keep your momentum going today with a target of **3.0 miles** at your comfortable steady-state pace."
    elif acwr <= 1.5:
        status_zone = "🟡 CAUTION ZONE (Overreaching)"
        zone_color = "orange"
        safety_status = "Elevated injury risk. Training volume is spiking slightly faster than baseline."
        recommendation = "Slight training load spike detected. Your agent recommends keeping today's run light to allow active recovery: **2.0 miles max** at a relaxed, conversational pace."
    else:
        status_zone = "🔴 DANGER ZONE (High Injury Risk)"
        zone_color = "red"
        safety_status = "Critical injury risk. Your acute training load is significantly higher than your baseline capacity."
        recommendation = "High training load warning! To prevent joint fatigue or shin splints, your agent strongly recommends a **Cardio Rest Day** today. Swap running for active recovery stretching, mobility work, or a light indoor shootaround."

    # Build the report content
    report_content = f"""# 🏃 Daily 30-Day Running/Cardio Load & Injury Preventer
**Date:** {today_str}
**Generated on:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}

---

## 📊 Training Load Analytics (Acute-to-Chronic Ratio)
* **Acute Load (Miles Run Last 7 Days):** {round(acute_miles, 2)} miles
* **Chronic Load (Weekly Average Miles Last 28 Days):** {round(chronic_weekly_avg, 2)} miles/week
* **Acute-to-Chronic Workload Ratio (ACWR):** **{round(acwr, 2)}**
* **Workload Zone:** **{status_zone}**

> 💡 *The Acute-to-Chronic Workload Ratio (ACWR) measures your short-term running workload (fitness stress) against your long-term cardiovascular foundation. Keeping your ACWR between 0.8 and 1.3 is the clinical sweet spot for maximizing cardiovascular capacity while minimizing joint/soft-tissue injury.*

---

## 👟 Training Prescription & Safety Status
* **Safety Assessment:** {safety_status}
* **Today's Training Target:** {recommendation}

---

## 📉 Your Recent Running History (Last 3 Sessions)
"""

    if not recent_runs:
        report_content += "\n*No running logs found in the past 30 days. Start logging your runs to activate historical trend analysis!*"
    else:
        report_content += "\n"
        for run in recent_runs:
            pace_str = f"{round(run['mins'] / run['miles'], 2)} min/mile" if run['miles'] else "N/A"
            hr_str = f"{run['hr']} bpm" if run['hr'] else "N/A"
            report_content += f"* **{run['date']}:** {run['miles']} miles in {run['mins']} mins (Pace: {pace_str} | Avg HR: {hr_str})\n"

    report_content += "\n\n---\n*This report was automatically compiled and analyzed by your autonomous Cloud-to-Pi backups agent network.*"

    os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)
    report_file_path = os.path.join(LOCAL_REPORTS_DIR, f"daily_cardio_load_preventer_{today_str}.md")
    
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logging.info(f"Compiled local report at: {report_file_path}")

    # Append to Google Sheet
    try:
        sheet_name = "Daily Cardio Load & Injury Preventer"
        headers = ["Date", "Acute Load (Last 7 Days Miles)", "Chronic Load (Weekly Avg 28 Days)", "ACWR (Acute-to-Chronic Ratio)", "Workload Zone", "Safety Assessment", "Training Recommendation"]
        row_data = [today_str, round(acute_miles, 2), round(chronic_weekly_avg, 2), round(acwr, 2), status_zone, safety_status, recommendation]
        append_to_gsheet(sheet_name, headers, row_data)
    except Exception as e:
        logging.error(f"Failed to append cardio data to Google Sheet: {e}")

    return report_file_path

@flow(name="cardio_load_preventer_agent_flow")
def cardio_load_preventer_flow():
    logging.info("Starting Daily Cardio Load & Injury Preventer agent run...")
    local_path = generate_cardio_load_report()
    if local_path:
        upload_report_to_gdrive(local_path)
    logging.info("Daily Cardio Load & Injury Preventer agent run complete!")

if __name__ == "__main__":
    cardio_load_preventer_flow()
