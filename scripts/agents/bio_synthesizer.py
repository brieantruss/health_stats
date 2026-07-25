import os
import sys
from datetime import datetime, timedelta
import logging
from google.cloud import bigquery
import google.generativeai as genai
from prefect import flow, task

# Append current directory to path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gdrive_uploader import upload_report_to_gdrive

# --- Configuration ---
PROJECT_ID = "my-data-479716"
KEY_PATH = "/home/briean/.gcp/bigquery-agent-key.json"
GEMINI_API_KEY_PATH = "/home/briean/.gcp/gemini_api_key.txt"
LOCAL_REPORTS_DIR = "/home/briean/dev/health_stats/reports"

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

def get_gemini_api_key():
    if os.path.exists(GEMINI_API_KEY_PATH):
        with open(GEMINI_API_KEY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("GEMINI_API_KEY")

@task(name="compile_weekly_gdrive_gcp_metrics")
def compile_weekly_gdrive_gcp_metrics():
    """Queries all raw datafrom views and compiles a structured payload of metrics."""
    client = get_bigquery_client()
    
    # 1. Query sleep and heart rate summaries
    summary_query = f"""
        SELECT date, total_steps, total_sleep, avg_heart_rate
        FROM `{PROJECT_ID}.health_stats.view_summary`
        WHERE PARSE_DATE('%Y/%m/%d', date) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        ORDER BY date DESC;
    """
    
    # 2. Query sleep stage details
    stages_query = f"""
        SELECT Date, Stage, CAST(Duration AS INT64) as Duration
        FROM `{PROJECT_ID}.health_stats.view_sleep_time_by_stage`
        WHERE PARSE_DATE('%Y.%m.%d', SPLIT(Date, ' ')[OFFSET(0)]) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
        ORDER BY Date DESC;
    """
    
    # 3. Query weather and AQI forecast for today
    today_str = datetime.today().strftime('%Y-%m-%d')
    weather_query = f"""
        SELECT forecast_date, forecast_temp_c, forecast_rain_probability_percent, forecast_conditions, forecast_aqi
        FROM `{PROJECT_ID}.health_stats.view_weather_aqi`
        WHERE forecast_date = '{today_str}' OR forecast_date = CURRENT_DATE()
        LIMIT 1;
    """

    try:
        summary_rows = list(client.query(summary_query).result())
        stage_rows = list(client.query(stages_query).result())
        weather_rows = list(client.query(weather_query).result())
    except Exception as e:
        logging.error(f"Failed to query BigQuery views: {e}")
        return None

    # Construct the data payload
    data_payload = "=== RECENT BIOLOGICAL METRICS (LAST 7 DAYS) ===\n"
    for r in summary_rows:
        data_payload += f"Date: {r.date} | Steps: {r.total_steps} | Heart Rate (avg): {r.avg_heart_rate} bpm\n"
        
    data_payload += "\n=== RECENT SLEEP STAGE LOGS (LAST 7 DAYS) ===\n"
    for r in stage_rows:
        data_payload += f"Date: {r.Date} | Sleep Stage: {r.Stage} | Duration: {r.Duration} mins\n"
        
    data_payload += "\n=== TODAY'S ENVIRONMENTAL FORECAST ===\n"
    if weather_rows:
        w = weather_rows[0]
        data_payload += f"Date: {w.forecast_date} | Temp: {w.forecast_temp_c}°C | Conditions: {w.forecast_conditions} | AQI: {w.forecast_aqi}\n"
    else:
        data_payload += "No weather/AQI forecast recorded for today.\n"

    return data_payload

@task(name="synthesize_with_gemini_llm")
def synthesize_with_gemini_llm(data_payload):
    api_key = get_gemini_api_key()
    if not api_key:
        logging.error("❌ Gemini API Key not found. Skipping synthesis.")
        return None

    try:
        logging.info("Initializing Google Gemini Pro client...")
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-2.0-flash')
        
        prompt = f"""
        You are Briean's elite, world-class personal health coach, sleep scientist, and cardiovascular expert.
        Analyze his past 7 days of biological and environmental metrics gathered from his wearable devices and sensors:
        
        {data_payload}
        
        Write a highly personalized, engaging, and motivational weekly health trend synthesis report in beautiful Markdown format.
        
        You must structure your response with these exact headers:
        
        # 🫁 The Holistic Wellness & Bio-Synthesizer
        *Compiling data, predicting recovery, and optimizing performance.*
        
        ## 📊 1. Weekly Biological Synthesis
        (In this section, analyze the data. Connect the dots between his physical movement, sleep stages, and sleeping heart rates. For example, explain how his heart rate efficiency improves on active days or following nights with high deep sleep percentages. Be highly specific and cite actual dates/values from the logs.)
        
        ## 💤 2. Sleep Stages & Brain/Body Balance
        (Analyze his Deep sleep vs. REM sleep distribution. Deep sleep handles tissue repair and physical recovery; REM sleep consolidates memory and cognitive restoration. Advise him if his brain or body needs more recovery focus based on the ratios.)
        
        ## 🏃 3. Personalized Mobility & Training Plan
        (Recommend 2-3 specific, actionable targets for next week based on today's weather conditions, air quality, and his acute running load.)
        
        Keep the tone sharp, supportive, professional, and encouraging. Cite actual numbers and dates to make it truly personal and accurate.
        """
        
        logging.info("Sending data payload to Gemini...")
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        logging.error(f"Gemini API call failed: {e}")
        return None

@task(name="save_and_upload_synthesizer_report")
def save_and_upload_synthesizer_report(report_text):
    if not report_text:
        return None
        
    today_str = datetime.today().strftime('%Y-%m-%d')
    os.makedirs(LOCAL_REPORTS_DIR, exist_ok=True)
    report_file_path = os.path.join(LOCAL_REPORTS_DIR, f"weekly_bio_synthesizer_{today_str}.md")
    
    with open(report_file_path, "w", encoding="utf-8") as f:
        f.write(report_text)
        
    logging.info(f"Compiled local Gemini report at: {report_file_path}")
    return report_file_path

# --- Main Flow ---
@flow(name="bio_synthesizer_agent_flow")
def bio_synthesizer_flow():
    logging.info("Starting Gemini Holistic Wellness & Bio-Synthesizer agent run...")
    data_payload = compile_weekly_gdrive_gcp_metrics()
    if data_payload:
        report_text = synthesize_with_gemini_llm(data_payload)
        if report_text:
            local_path = save_and_upload_synthesizer_report(report_text)
            if local_path:
                upload_report_to_gdrive(local_path)
    logging.info("Gemini Holistic Wellness & Bio-Synthesizer agent run complete!")

if __name__ == "__main__":
    bio_synthesizer_flow()
