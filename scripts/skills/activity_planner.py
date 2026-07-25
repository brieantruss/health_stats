#!/usr/bin/env python3
import os
from google.cloud import bigquery

# --- Configuration ---
PROJECT_ID = "my-data-479716"
KEY_PATH = "/home/briean/.gcp/bigquery-agent-key.json"

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    return bigquery.Client(project=PROJECT_ID)

def get_upcoming_activities():
    print("================================================================================")
    print("🌟 SKILL 4: INTERACTIVE 7-DAY ACTIVITY RECOMMENDATION PLANNER")
    print("================================================================================")
    
    try:
        client = get_bigquery_client()
    except Exception as e:
        print(f"❌ Failed to connect to BigQuery: {e}")
        return

    # Query the Dataform view
    query = """
        SELECT
          forecast_date,
          forecast_temp_c,
          forecast_rain_probability_percent,
          forecast_conditions,
          forecast_aqi,
          recommended_activity,
          activity_category,
          recommendation_score,
          reasoning
        FROM
          `my-data-479716.health_stats.view_activity_recommendations`
        WHERE
          recommendation_rank = 1 -- Only show the Top 1 priority recommendation per day!
        ORDER BY
          forecast_date ASC;
    """

    print("📡 Fetching recommendation forecast from BigQuery...")
    try:
        query_job = client.query(query)
        rows = list(query_job.result())
    except Exception as e:
        print(f"❌ BigQuery query failed: {e}")
        return

    if not rows:
        print("⚠️ No forecast recommendations found. Run the weather forecast ETL first!")
        return

    print(f"\n{'-'*110}")
    print(f"{'DATE':<12} | {'TEMP':<5} | {'RAIN %':<6} | {'CONDITIONS':<18} | {'TOP RECOMMENDED ACTIVITY':<25} | {'SCORE':<5}")
    print(f"{'-'*110}")

    for r in rows:
        date_str = str(r.forecast_date)
        temp = f"{r.forecast_temp_c}°C"
        rain = f"{r.forecast_rain_probability_percent}%"
        cond = str(r.forecast_conditions)[:18]
        act = str(r.recommended_activity)[:25]
        score = f"{r.recommendation_score}"
        
        # Color coding score
        score_val = float(r.recommendation_score)
        if score_val >= 80:
            score_str = f"\033[92m{score_val:.1f}\033[0m"
        elif score_val >= 50:
            score_str = f"\033[93m{score_val:.1f}\033[0m"
        else:
            score_str = f"\033[91m{score_val:.1f}\033[0m"

        print(f"{date_str:<12} | {temp:<5} | {rain:<6} | {cond:<18} | {act:<25} | {score_str:<5}")
        print(f"  \033[90m↳ Reasoning: {r.reasoning}\033[0m")
        print()

    print(f"{'-'*110}")
    print("\n🎯 Weekly Planning Tips:")
    print("  • Indoor Strength: Ideal for rainy/dusty days. Keeps your muscles activated.")
    print("  • Outdoor Cardio: Recommended for pleasant, sunny, high-AQI windows.")
    print("  • Active Recovery: Helps flush lactic acid and keeps joints mobile.")
    print(f"{'-'*110}\n")

if __name__ == "__main__":
    get_upcoming_activities()
