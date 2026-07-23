import os
import sys
from datetime import datetime, timedelta
import logging
from google.cloud import bigquery
from prefect import flow, task

# Append current directory to path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gdrive_uploader import upload_report_to_gdrive

# --- Configuration ---
PROJECT_ID = "my-data-479716"
KEY_PATH = "/home/briean/.gcp/bigquery-agent-key.json"
LOCAL_REPORTS_DIR = "/home/briean/dev/health_stats/reports"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

@task(name="generate_health_trend_report")
def generate_health_trend_report():
    client = get_bigquery_client()
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # Query summary logs for the last 14 days to do a week-over-week comparison!
    query = f"""
        SELECT
          date,
          total_steps,
          total_sleep,
          avg_heart_rate
        FROM
          `{PROJECT_ID}.health_stats.view_summary`
        WHERE
          PARSE_DATE('%Y/%m/%d', date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY)
        ORDER BY
          date DESC;
    """
    
    logging.info("Querying 14-day health summary from BigQuery...")
    try:
        query_job = client.query(query)
        rows = list(query_job.result())
    except Exception as e:
        logging.error(f"BigQuery query failed: {e}")
        return None

    if not rows:
        logging.warning("No health summary logs found in the past 14 days.")
        report_content = f"""# 📉 Weekly Health Trend & Data Integrity Analyst (Fallback)
Date: {today_str}

⚠️ **No health summary records were found in BigQuery for the past 14 days.**
Please ensure your ETL pipelines have run successfully.
"""
    else:
        # Separate rows into Week 1 (Days 1-7, most recent) and Week 2 (Days 8-14, baseline)
        today = datetime.now().date()
        week1_steps = []
        week1_sleep = []
        week1_hr = []
        
        week2_steps = []
        week2_sleep = []
        week2_hr = []
        
        # Track days with missing data for the Integrity Audit
        data_gaps = []
        
        # Initialize a set of last 7 dates to check for complete missing records
        expected_dates = [(today - timedelta(days=i)).strftime('%Y/%m/%d') for i in range(1, 8)]
        found_dates = set()

        for r in rows:
            date_str = r.date
            found_dates.add(date_str)
            try:
                activity_date = datetime.strptime(date_str, '%Y/%m/%d').date()
            except Exception:
                continue
                
            days_ago = (today - activity_date).days
            
            # --- Week 1: Days 1 to 7 (Acute) ---
            if 1 <= days_ago <= 7:
                # Steps Audit
                if r.total_steps is not None and r.total_steps > 0:
                    week1_steps.append(r.total_steps)
                else:
                    data_gaps.append(f"⚠️ **{date_str}:** Missing Step logs (0 or null steps recorded).")
                    
                # Sleep Audit
                if r.total_sleep is not None and r.total_sleep > 0:
                    week1_sleep.append(r.total_sleep / 3600.0) # Convert seconds to hours
                else:
                    data_gaps.append(f"⚠️ **{date_str}:** Missing Sleep logs (0 or null sleep hours recorded).")
                    
                # Heart Rate Audit
                if r.avg_heart_rate is not None and r.avg_heart_rate > 0:
                    week1_hr.append(r.avg_heart_rate)
                else:
                    data_gaps.append(f"⚠️ **{date_str}:** Missing Heart Rate log (null average recorded).")
                    
            # --- Week 2: Days 8 to 14 (Baseline) ---
            elif 8 <= days_ago <= 14:
                if r.total_steps is not None and r.total_steps > 0:
                    week2_steps.append(r.total_steps)
                if r.total_sleep is not None and r.total_sleep > 0:
                    week2_sleep.append(r.total_sleep / 3600.0)
                if r.avg_heart_rate is not None and r.avg_heart_rate > 0:
                    week2_hr.append(r.avg_heart_rate)

        # Flag days in the last 7 days that are completely missing from the table
        for exp_date in expected_dates:
            if exp_date not in found_dates:
                data_gaps.append(f"🚨 **{exp_date}:** CRITICAL DATA GAP - No record found in database for this day.")

        # Calculate averages for Week 1 (Current) vs Week 2 (Baseline)
        avg_steps_w1 = sum(week1_steps) / len(week1_steps) if week1_steps else 0.0
        avg_steps_w2 = sum(week2_steps) / len(week2_steps) if week2_steps else 0.0
        steps_diff = avg_steps_w1 - avg_steps_w2
        steps_trend = f"🟢 Improved by +{round(steps_diff, 1)} steps/day" if steps_diff >= 0 else f"🔴 Decreased by {round(steps_diff, 1)} steps/day"
        
        avg_sleep_w1 = sum(week1_sleep) / len(week1_sleep) if week1_sleep else 0.0
        avg_sleep_w2 = sum(week2_sleep) / len(week2_sleep) if week2_sleep else 0.0
        sleep_diff = avg_sleep_w1 - avg_sleep_w2
        sleep_trend = f"🟢 Improved by +{round(sleep_diff, 2)} hours/night" if sleep_diff >= 0 else f"🔴 Decreased by {round(abs(sleep_diff), 2)} hours/night"

        avg_hr_w1 = sum(week1_hr) / len(week1_hr) if week1_hr else 0.0
        avg_hr_w2 = sum(week2_hr) / len(week2_hr) if week2_hr else 0.0
        hr_diff = avg_hr_w1 - avg_hr_w2
        # A lowering resting heart rate is a sign of improved cardiovascular efficiency!
        if hr_diff <= 0:
            hr_trend = f"🟢 Cardiovascular efficiency improved! Resting heart rate lowered by {round(abs(hr_diff), 1)} bpm."
        else:
            hr_trend = f"🟡 Resting heart rate increased by +{round(hr_diff, 1)} bpm. Monitor stress, hydration, and fatigue levels."

        # Format Data Integrity Audit Section
        if not data_gaps:
            integrity_report = "🟢 **100% HEALTHY:** No data gaps or missing logs detected in the last 7 days. Your automated sync devices are performing perfectly!"
        else:
            integrity_report = "### ⚠️ Active Gaps & Missing Logs Detected:\n" + "\n".join(data_gaps)

        # Build the final report
        report_content = f"""# 📉 Weekly Health Trend & Data Integrity Analyst
**Date:** {today_str}
**Generated on:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}

---

## 🧭 Week-Over-Week Health Trend Analytics

This analysis compares your **Current Week** (last 7 days) against your **Previous Week** (days 8-14 baseline) to track cardiovascular and sleep changes.

### 👣 1. Physical Movement (Steps Volume)
* **Current Week Average:** {round(avg_steps_w1, 1)} steps/day
* **Previous Week Average:** {round(avg_steps_w2, 1)} steps/day
* **Trend Assessment:** {steps_trend}

### 🫀 2. Cardiovascular Efficiency (Resting Heart Rate Proxy)
* **Current Week Average:** {round(avg_hr_w1, 1)} bpm
* **Previous Week Average:** {round(avg_hr_w2, 1)} bpm
* **Trend Assessment:** {hr_trend}

### 💤 3. Sleep Duration
* **Current Week Average:** {round(avg_sleep_w1, 2)} hours/night
* **Previous Week Average:** {round(avg_sleep_w2, 2)} hours/night
* **Trend Assessment:** {sleep_trend}

---

## 🛠️ Data Integrity & Sync Audit

This audit cross-references your synced records from Samsung Health and wearable devices over the past 7 days to isolate data sync bugs.

{integrity_report}

---
*This report was automatically compiled and analyzed by your autonomous Cloud-to-Pi backups agent network.*
"""

    os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)
    report_file_path = os.path.join(LOCAL_REPORTS_DIR, f"weekly_health_trend_analyst_{today_str}.md")
    
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logging.info(f"Compiled local health trend report at: {report_file_path}")
    return report_file_path

@flow(name="health_trend_analyst_agent_flow")
def health_trend_analyst_flow():
    logging.info("Starting Weekly Health Trend & Data Integrity Analyst agent run...")
    local_path = generate_health_trend_report()
    if local_path:
        upload_report_to_gdrive(local_path)
    logging.info("Weekly Health Trend & Data Integrity Analyst agent run complete!")

if __name__ == "__main__":
    health_trend_analyst_flow()
