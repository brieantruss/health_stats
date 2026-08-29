import os
import sys
from datetime import datetime
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

@task(name="generate_weather_aqi_report")
def generate_weather_aqi_report():
    client = get_bigquery_client()
    today_str = datetime.today().strftime('%Y-%m-%d')
    
    # Query today's forecast and air quality indices from the weather view
    query = f"""
        SELECT
          forecast_date,
          forecast_temp_c,
          forecast_rain_probability_percent,
          forecast_conditions,
          forecast_aqi,
          recommended_activity,
          reasoning
        FROM
          `{PROJECT_ID}.health_stats.view_activity_recommendations`
        WHERE
          forecast_date = '{today_str}'
          OR forecast_date = FORMAT_DATE('%Y-%m-%d', CURRENT_DATE())
        ORDER BY
          recommendation_score DESC
        LIMIT 1;
    """
    
    logging.info(f"Querying weather and AQI forecast for {today_str}...")
    try:
        query_job = client.query(query)
        rows = list(query_job.result())
    except Exception as e:
        logging.error(f"BigQuery query failed: {e}")
        return None

    if not rows:
        logging.warning("No forecast metrics found for today.")
        # Create a fallback/empty state report so we never crash
        report_content = f"""# 🌬️ Daily Weather & AQI Risk Guard (Fallback)
Date: {today_str}

⚠️ **No automated data was found in BigQuery for today's forecast yet.** 
Please ensure your daily weather/AQI extraction jobs have run successfully.
"""
    else:
        r = rows[0]
        aqi_val = int(r.forecast_aqi) if r.forecast_aqi else 50
        
        # Color & safety coding for AQI
        if aqi_val <= 50:
            aqi_status = "🟢 GOOD (Healthy)"
            aqi_desc = "Air quality is satisfactory, and air pollution poses little or no risk."
            cardio_warning = "Perfect window for high-intensity outdoor training! Push your running distance or speed today."
        elif aqi_val <= 100:
            aqi_status = "🟡 MODERATE (Acceptable)"
            aqi_desc = "Air quality is acceptable. However, there may be a risk for some people, particularly those who are unusually sensitive."
            cardio_warning = "Outdoor cardio is safe, but monitor your breathing if you have sensitive lungs."
        elif aqi_val <= 150:
            aqi_status = "🟠 UNHEALTHY FOR SENSITIVE GROUPS"
            aqi_desc = "Members of sensitive groups may experience health effects. The general public is less likely to be affected."
            cardio_warning = "⚠️ **Caution:** Swap any intense running for an indoor session. Keep outdoor workouts to moderate walking only."
        else:
            aqi_status = "🔴 UNHEALTHY (High Risk)"
            aqi_desc = "Some members of the general public may experience health effects; members of sensitive groups may experience more serious health effects."
            cardio_warning = "🛑 **Critical Warning:** Highly recommend moving all physical exercise indoors. Swap outdoor running/walking for indoor shootarounds or strength training."

        report_content = f"""# 🌬️ Daily Weather & AQI Risk Guard
**Date:** {r.forecast_date}
**Generated on:** {datetime.now().strftime('%Y-%m-%d %I:%M %p')}

---

## ⛅ Today's Environmental Status
* **Conditions:** {r.forecast_conditions}
* **Temperature:** {r.forecast_temp_c}°C ({round(r.forecast_temp_c * 9/5 + 32, 1)}°F)
* **Rain Probability:** {r.forecast_rain_probability_percent}%
* **Air Quality Index (AQI):** {aqi_val} ({aqi_status})

> 💡 *{aqi_desc}*

---

## 🎯 Recommender Agent Decisions
* **Recommended Activity:** **{r.recommended_activity}**
* **Reasoning:** *{r.reasoning}*

### 👟 Cardiovascular Training Guidance:
{cardio_warning}

---
*This report was automatically compiled and analyzed by your autonomous Cloud-to-Pi backups agent network.*
"""

    os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)
    report_file_path = os.path.join(LOCAL_REPORTS_DIR, f"daily_weather_aqi_guard_{today_str}.md")
    
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_content)
    
    logging.info(f"Compiled local report at: {report_file_path}")

    # Append to Google Sheet if data was found
    if rows:
        try:
            sheet_name = "Daily Weather & AQI Risk Guard"
            headers = ["Date", "Conditions", "Temperature (C)", "Rain Probability (%)", "AQI", "AQI Status", "Recommended Activity", "Reasoning"]
            row_data = [r.forecast_date, r.forecast_conditions, r.forecast_temp_c, r.forecast_rain_probability_percent, aqi_val, aqi_status, r.recommended_activity, r.reasoning]
            append_to_gsheet(sheet_name, headers, row_data)
        except Exception as e:
            logging.error(f"Failed to append weather data to Google Sheet: {e}")

    return report_file_path

@flow(name="weather_aqi_guard_agent_flow")
def weather_aqi_guard_flow():
    logging.info("Starting Daily Weather & AQI Risk Guard agent run...")
    local_path = generate_weather_aqi_report()
    if local_path:
        upload_report_to_gdrive(local_path)
        try:
            os.remove(local_path)
            logging.info(f"Cleaned up temporary local report: {local_path}")
        except Exception as e:
            logging.error(f"Failed to delete temporary report {local_path}: {e}")
    logging.info("Daily Weather & AQI Risk Guard agent run complete!")

if __name__ == "__main__":
    weather_aqi_guard_flow()
