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
LOCAL_REPORTS_DIR = "/tmp"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

@task(name="generate_sleep_report")
def generate_sleep_report():
    client = get_bigquery_client()
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # Query the last 7 days of sleep entries from the view
    query = f"""
        SELECT
          Date,
          Stage,
          CAST(Duration AS INT64) as Duration
        FROM
          `{PROJECT_ID}.health_stats.view_sleep_time_by_stage`
        WHERE
          PARSE_DATE('%Y.%m.%d', SPLIT(Date, ' ')[OFFSET(0)]) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        ORDER BY
          Date DESC;
    """
    
    logging.info("Querying 7-day sleep stage logs from BigQuery...")
    try:
        query_job = client.query(query)
        rows = list(query_job.result())
    except Exception as e:
        logging.error(f"BigQuery query failed: {e}")
        return None

    # Process and aggregate durations per day per stage
    # Stages are typically: deep, light, rem, awake (or similar strings)
    daily_sleep = {}
    
    for r in rows:
        # Clean date string
        date_key = r.Date.split(' ')[0].replace('.', '-')
        stage = r.Stage.lower().strip()
        
        if date_key not in daily_sleep:
            daily_sleep[date_key] = {"deep": 0, "rem": 0, "light": 0, "awake": 0, "total": 0}
            
        duration_mins = r.Duration
        daily_sleep[date_key][stage] = daily_sleep[date_key].get(stage, 0) + duration_mins
        # Add to total sleep (excluding awake time)
        if stage != "awake":
            daily_sleep[date_key]["total"] += duration_mins

    # Calculate weekly averages
    total_days = len(daily_sleep)
    if total_days == 0:
        logging.warning("No sleep logs found in the past 7 days.")
        report_content = f"""# 💤 Weekly Sleep Stage & Deep Recovery Optimizer (Fallback)
Date: {today_str}

⚠️ **No automated sleep stage logs were found in BigQuery for the past week.** 
Please ensure your Samsung Health sleep sync jobs have completed successfully.
"""
    else:
        avg_total = sum(d["total"] for d in daily_sleep.values()) / total_days
        avg_deep = sum(d["deep"] for d in daily_sleep.values()) / total_days
        avg_rem = sum(d["rem"] for d in daily_sleep.values()) / total_days
        avg_light = sum(d["light"] for d in daily_sleep.values()) / total_days
        avg_awake = sum(d["awake"] for d in daily_sleep.values()) / total_days
        
        # Diagnostics
        deep_target_mins = 90
        rem_target_mins = 90
        
        deep_percentage = (avg_deep / avg_total) * 100 if avg_total > 0 else 0
        rem_percentage = (avg_rem / avg_total) * 100 if avg_total > 0 else 0
        
        # Deep Sleep Diagnostics & Action Steps
        if avg_deep < 60:
            deep_rating = "🚨 CRITICAL DEFICIT (Under 60 mins/night)"
            deep_advice = """* **Avoid Late-Night Blue Light:** Blue light blocks melatonin synthesis, keeping your brain in light sleep phases. Use blue light blockers or avoid screens for 1 hour before bed.
* **Optimize Room Temperature:** Deep sleep is triggered by a drop in core body temperature. Keep your bedroom cool, ideally between **65°F and 68°F (18-20°C)**.
* **Stop Eating 3 Hours Before Bed:** Late-night digestion forces active blood flow to your stomach instead of allowing your heart and brain to enter deep restorative recovery."""
        elif avg_deep < deep_target_mins:
            deep_rating = "⚠️ MODERATE (Needs Optimization)"
            deep_advice = """* **Increase Daytime Activity Volume:** Deep sleep is directly proportional to daytime physical expenditure. Recommending hitting at least **8,000 steps** or adding a cardio run during the day to build healthy physical sleep pressure.
* **Stick to a Rigid Sleep Schedule:** Going to bed and waking up at the exact same time stabilizes your circadian rhythm, optimizing your brain's deep sleep windows."""
        else:
            deep_rating = "🟢 EXCELLENT (Physically Restored)"
            deep_advice = """* **Keep Up Your Current Habits:** Your physical body, muscle tissue, and cells are recovering perfectly! Continue your daily walking, running, and balanced nutrition habits which directly stabilize deep sleep phases."""

        # REM Sleep Diagnostics & Action Steps
        if avg_rem < rem_target_mins:
            rem_rating = "⚠️ COGNITIVE RECOVERY DEFICIT (Under 90 mins/night)"
            rem_advice = """* **Reduce Caffeine Intake:** Caffeine has a 6-hour half-life and blocks adenosine receptors, truncating your late-night REM sleep windows. Avoid caffeine after **12:00 PM (Noon)**.
* **Prioritize Wind-Down Time:** Stress and high cortisol suppress REM sleep. Add 15 minutes of light reading, journaling, or breathing exercises before sleep."""
        else:
            rem_rating = "🟢 EXCELLENT (Cognitively Restored)"
            rem_advice = """* Your brain's cognitive synthesis, memory consolidation, and mental restoration are performing exceptionally well! Keep your stress management and morning sunlight habits consistent."""

        # Format the Weekly Report
        report_content = f"""# 💤 Weekly Sleep Stage & Deep Recovery Optimizer
**Date:** {today_str}
**Generated on:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}

---

## 📊 Weekly Sleep Architecture Summary
* **Average Sleep Duration:** {int(avg_total // 60)}h {int(avg_total % 60)}m per night
* **Average Deep Sleep:** {round(avg_deep, 1)} mins/night ({round(deep_percentage, 1)}% of total sleep) — **{deep_rating}**
* **Average REM Sleep:** {round(avg_rem, 1)} mins/night ({round(rem_percentage, 1)}% of total sleep) — **{rem_rating}**
* **Average Light Sleep:** {round(avg_light, 1)} mins/night
* **Average Awake Time:** {round(avg_awake, 1)} mins/night

---

## 🩺 Sleep Stage Diagnostics & Action Plans

### 🔋 1. Physical Recovery (Deep Sleep)
Deep sleep is the critical phase where growth hormone is released, cells regenerate, muscles repair, and physical fatigue is flushed.
{deep_advice}

### 🧠 2. Cognitive Recovery (REM Sleep)
REM sleep is the phase where your brain consolidates memories, processes emotions, synthesizes learning, and clears neural waste.
{rem_advice}

---

## 📉 Sleep stage history (Last 7 Days)
| Date | Total Sleep | Deep Sleep | REM Sleep | Awake |
| :--- | :--- | :--- | :--- | :--- |
"""
        for d_key, d_val in sorted(daily_sleep.items(), reverse=True):
            report_content += f"| {d_key} | {int(d_val['total'] // 60)}h {int(d_val['total'] % 60)}m | {d_val['deep']}m | {d_val['rem']}m | {d_val['awake']}m |\n"

        report_content += "\n\n---\n*This report was automatically compiled and analyzed by your autonomous Cloud-to-Pi backups agent network.*"

    os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)
    report_file_path = os.path.join(LOCAL_REPORTS_DIR, f"weekly_sleep_optimizer_{today_str}.md")
    
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logging.info(f"Compiled local sleep report at: {report_file_path}")

    # Append to Google Sheet if data was found
    if total_days > 0:
        try:
            sheet_name = "Weekly Sleep Stage & Deep Recovery Optimizer"
            headers = ["Date", "Avg Sleep Duration (mins)", "Avg Deep Sleep (mins)", "Deep Sleep (%)", "Deep Sleep Rating", "Avg REM Sleep (mins)", "REM Sleep (%)", "REM Sleep Rating", "Avg Light Sleep (mins)", "Avg Awake Time (mins)"]
            row_data = [today_str, round(avg_total, 1), round(avg_deep, 1), round(deep_percentage, 1), deep_rating, round(avg_rem, 1), round(rem_percentage, 1), rem_rating, round(avg_light, 1), round(avg_awake, 1)]
            append_to_gsheet(sheet_name, headers, row_data)
        except Exception as e:
            logging.error(f"Failed to append sleep data to Google Sheet: {e}")

    return report_file_path

@flow(name="sleep_recovery_optimizer_agent_flow")
def sleep_recovery_optimizer_flow():
    logging.info("Starting Weekly Sleep Stage & Deep Recovery Optimizer agent run...")
    local_path = generate_sleep_report()
    if local_path:
        upload_report_to_gdrive(local_path)
        try:
            os.remove(local_path)
            logging.info(f"Cleaned up temporary local report: {local_path}")
        except Exception as e:
            logging.error(f"Failed to delete temporary report {local_path}: {e}")
    logging.info("Weekly Sleep Stage & Deep Recovery Optimizer agent run complete!")

if __name__ == "__main__":
    sleep_recovery_optimizer_flow()
