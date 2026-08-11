import os
import re
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Append current directory to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from gdrive_uploader import append_to_gsheet

REPORTS_DIR = "/home/briean/dev/health_stats/reports"

def parse_weather_aqi_file(file_path, date):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Fallback check
    if "No automated data was found in BigQuery" in content:
        logging.warning(f"Skipping fallback/empty weather report: {file_path}")
        return None

    # Extraction patterns
    conditions_match = re.search(r"\* \*\*Conditions:\*\* (.*)", content)
    temp_match = re.search(r"\* \*\*Temperature:\*\* ([\d\.-]+)°C", content)
    rain_match = re.search(r"\* \*\*Rain Probability:\*\* ([\d\.-]+)%", content)
    aqi_match = re.search(r"\* \*\*Air Quality Index \(AQI\):\*\* (\d+) \((.*?)\)", content)
    activity_match = re.search(r"\* \*\*Recommended Activity:\*\* \*\*(.*?)\*\*", content)
    reasoning_match = re.search(r"\* \*\*Reasoning:\*\* \*(.*?)\*", content)

    if not (conditions_match and temp_match and rain_match and aqi_match and activity_match and reasoning_match):
        logging.warning(f"Could not parse all fields in weather file: {file_path}")
        return None

    conditions = conditions_match.group(1).strip()
    temp_c = float(temp_match.group(1))
    rain_prob = float(rain_match.group(1))
    aqi_val = int(aqi_match.group(1))
    aqi_status = aqi_match.group(2).strip()
    activity = activity_match.group(1).strip()
    reasoning = reasoning_match.group(1).strip()

    headers = ["Date", "Conditions", "Temperature (C)", "Rain Probability (%)", "AQI", "AQI Status", "Recommended Activity", "Reasoning"]
    row_data = [date, conditions, temp_c, rain_prob, aqi_val, aqi_status, activity, reasoning]
    return headers, row_data


def parse_cardio_load_file(file_path, date):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    acute_match = re.search(r"\* \*\*Acute Load \(Miles Run Last 7 Days\):\*\* ([\d\.-]+) miles", content)
    chronic_match = re.search(r"\* \*\*Chronic Load \(Weekly Average Miles Last 28 Days\):\*\* ([\d\.-]+) miles/week", content)
    acwr_match = re.search(r"\* \*\*Acute-to-Chronic Workload Ratio \(ACWR\):\*\* \*\*([\d\.-]+)\*\*", content)
    zone_match = re.search(r"\* \*\*Workload Zone:\*\* \*\*(.*?)\*\*", content)
    safety_match = re.search(r"\* \*\*Safety Assessment:\*\* (.*)", content)
    recommendation_match = re.search(r"\* \*\*Today's Training Target:\*\* (.*)", content)

    if not (acute_match and chronic_match and acwr_match and zone_match and safety_match and recommendation_match):
        logging.warning(f"Could not parse all fields in cardio file: {file_path}")
        return None

    acute_miles = float(acute_match.group(1))
    chronic_weekly_avg = float(chronic_match.group(1))
    acwr = float(acwr_match.group(1))
    status_zone = zone_match.group(1).strip()
    safety_status = safety_match.group(1).strip()
    recommendation = recommendation_match.group(1).strip()

    headers = ["Date", "Acute Load (Last 7 Days Miles)", "Chronic Load (Weekly Avg 28 Days)", "ACWR (Acute-to-Chronic Ratio)", "Workload Zone", "Safety Assessment", "Training Recommendation"]
    row_data = [date, acute_miles, chronic_weekly_avg, acwr, status_zone, safety_status, recommendation]
    return headers, row_data



def parse_sleep_optimizer_file(file_path, date):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "No automated sleep stage logs were found" in content:
        logging.warning(f"Skipping fallback/empty sleep report: {file_path}")
        return None

    duration_match = re.search(r"\* \*\*Average Sleep Duration:\*\* (\d+)h (\d+)m per night", content)
    deep_match = re.search(r"\* \*\*Average Deep Sleep:\*\* ([\d\.-]+) mins/night \(([\d\.-]+)% of total sleep\) — \*\*(.*?)\*\*", content)
    rem_match = re.search(r"\* \*\*Average REM Sleep:\*\* ([\d\.-]+) mins/night \(([\d\.-]+)% of total sleep\) — \*\*(.*?)\*\*", content)
    light_match = re.search(r"\* \*\*Average Light Sleep:\*\* ([\d\.-]+) mins/night", content)
    awake_match = re.search(r"\* \*\*Average Awake Time:\*\* ([\d\.-]+) mins/night", content)

    if not (duration_match and deep_match and rem_match and light_match and awake_match):
        logging.warning(f"Could not parse all fields in sleep file: {file_path}")
        return None

    hours = int(duration_match.group(1))
    minutes = int(duration_match.group(2))
    total_mins = hours * 60 + minutes

    avg_deep = float(deep_match.group(1))
    deep_percentage = float(deep_match.group(2))
    deep_rating = deep_match.group(3).strip()

    avg_rem = float(rem_match.group(1))
    rem_percentage = float(rem_match.group(2))
    rem_rating = rem_match.group(3).strip()

    avg_light = float(light_match.group(1))
    avg_awake = float(awake_match.group(1))

    headers = ["Date", "Avg Sleep Duration (mins)", "Avg Deep Sleep (mins)", "Deep Sleep (%)", "Deep Sleep Rating", "Avg REM Sleep (mins)", "REM Sleep (%)", "REM Sleep Rating", "Avg Light Sleep (mins)", "Avg Awake Time (mins)"]
    row_data = [date, total_mins, avg_deep, deep_percentage, deep_rating, avg_rem, rem_percentage, rem_rating, avg_light, avg_awake]
    return headers, row_data


def parse_health_trend_file(file_path, date):
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()

    if "No health summary records were found" in content:
        logging.warning(f"Skipping fallback/empty trend report: {file_path}")
        return None

    try:
        # Extract sections
        steps_section = content.split("### 👣 1. Physical Movement")[1].split("### 🫀 2. Cardiovascular Efficiency")[0]
        hr_section = content.split("### 🫀 2. Cardiovascular Efficiency")[1].split("### 💤 3. Sleep Duration")[0]
        sleep_section = content.split("### 💤 3. Sleep Duration")[1].split("---")[0]

        # Parse Steps Section
        steps_curr = float(re.search(r"\* \*\*Current Week Average:\*\* ([\d\.-]+)", steps_section).group(1))
        steps_prev = float(re.search(r"\* \*\*Previous Week Average:\*\* ([\d\.-]+)", steps_section).group(1))
        steps_trend = re.search(r"\* \*\*Trend Assessment:\*\* (.*)", steps_section).group(1).strip()

        # Parse HR Section
        hr_curr = float(re.search(r"\* \*\*Current Week Average:\*\* ([\d\.-]+)", hr_section).group(1))
        hr_prev = float(re.search(r"\* \*\*Previous Week Average:\*\* ([\d\.-]+)", hr_section).group(1))
        hr_trend = re.search(r"\* \*\*Trend Assessment:\*\* (.*)", hr_section).group(1).strip()

        # Parse Sleep Section
        sleep_curr = float(re.search(r"\* \*\*Current Week Average:\*\* ([\d\.-]+)", sleep_section).group(1))
        sleep_prev = float(re.search(r"\* \*\*Previous Week Average:\*\* ([\d\.-]+)", sleep_section).group(1))
        sleep_trend = re.search(r"\* \*\*Trend Assessment:\*\* (.*)", sleep_section).group(1).strip()
    except Exception as e:
        logging.warning(f"Could not parse health trend sections in {file_path}: {e}")
        return None

    headers = ["Date", "Current Week Avg Steps", "Previous Week Avg Steps", "Steps Trend", "Current Week Avg HR", "Previous Week Avg HR", "HR Trend", "Current Week Avg Sleep (hrs)", "Previous Week Avg Sleep (hrs)", "Sleep Trend"]
    row_data = [date, steps_curr, steps_prev, steps_trend, hr_curr, hr_prev, hr_trend, sleep_curr, sleep_prev, sleep_trend]
    return headers, row_data



def backfill_all_sheets():
    logging.info("🚀 Starting Google Sheets backfill process from historical reports...")
    
    if not os.path.exists(REPORTS_DIR):
        logging.error(f"Reports directory {REPORTS_DIR} does not exist.")
        return

    files = sorted(os.listdir(REPORTS_DIR))
    
    # Track statistics
    backfilled_counts = {
        "weather": 0,
        "cardio": 0,
        "sleep": 0,
        "trend": 0,
        "synthesizer": 0
    }

    for f_name in files:
        if not f_name.endswith(".md"):
            continue

        file_path = os.path.join(REPORTS_DIR, f_name)
        
        # Extract date from filename: e.g. daily_weather_aqi_guard_2026-08-09.md -> 2026-08-09
        date_match = re.search(r"(\d{4}-\d{2}-\d{2})", f_name)
        if not date_match:
            continue
        date_str = date_match.group(1)

        # 1. Weather AQI Guard
        if f_name.startswith("daily_weather_aqi_guard_"):
            parsed = parse_weather_aqi_file(file_path, date_str)
            if parsed:
                headers, row = parsed
                success = append_to_gsheet("Daily Weather & AQI Risk Guard", headers, row)
                if success:
                    backfilled_counts["weather"] += 1

        # 2. Cardio Load Preventer
        elif f_name.startswith("daily_cardio_load_preventer_"):
            parsed = parse_cardio_load_file(file_path, date_str)
            if parsed:
                headers, row = parsed
                success = append_to_gsheet("Daily Cardio Load & Injury Preventer", headers, row)
                if success:
                    backfilled_counts["cardio"] += 1

        # 3. Sleep Recovery Optimizer
        elif f_name.startswith("weekly_sleep_optimizer_"):
            parsed = parse_sleep_optimizer_file(file_path, date_str)
            if parsed:
                headers, row = parsed
                success = append_to_gsheet("Weekly Sleep Stage & Deep Recovery Optimizer", headers, row)
                if success:
                    backfilled_counts["sleep"] += 1

        # 4. Health Trend Analyst
        elif f_name.startswith("weekly_health_trend_analyst_"):
            parsed = parse_health_trend_file(file_path, date_str)
            if parsed:
                headers, row = parsed
                success = append_to_gsheet("Weekly Health Trend & Data Integrity Analyst", headers, row)
                if success:
                    backfilled_counts["trend"] += 1

        # 5. Bio Synthesizer
        elif f_name.startswith("weekly_bio_synthesizer_"):
            with open(file_path, "r", encoding="utf-8") as bf:
                text = bf.read()
            headers = ["Date", "Holistic Wellness Report"]
            row = [date_str, text]
            success = append_to_gsheet("Weekly Holistic Wellness & Bio-Synthesizer", headers, row)
            if success:
                backfilled_counts["synthesizer"] += 1

    logging.info("🎉 Backfill process completed successfully!")
    for agent, count in backfilled_counts.items():
        logging.info(f"📊 Backfilled {count} records for {agent} agent.")

if __name__ == "__main__":
    backfill_all_sheets()