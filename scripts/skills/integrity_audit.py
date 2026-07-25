#!/usr/bin/env python3
import os
import mysql.connector
from datetime import datetime, timedelta

# --- Configuration ---
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

def get_integrity_audit():
    print("================================================================================")
    print("🌟 SKILL 2: HISTORICAL LOG INTEGRITY & GAP AUDITOR (PAST 30 DAYS)")
    print("================================================================================")
    
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor(dictionary=True)
    except Exception as e:
        print(f"❌ Failed to connect to MySQL: {e}")
        return

    # 1. Generate past 30 days list
    today = datetime.now().date()
    past_30_days = [today - timedelta(days=i) for i in range(1, 31)]
    past_30_days.sort() # Oldest to newest
    
    # 2. Fetch logged dates for key categories
    # Sleep
    cursor.execute("SELECT DISTINCT date(date) as logged_date FROM sleep WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);")
    sleep_dates = set(row['logged_date'] for row in cursor.fetchall())

    # Steps
    cursor.execute("SELECT DISTINCT date(date) as logged_date FROM steps WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);")
    steps_dates = set(row['logged_date'] for row in cursor.fetchall())

    # Diet
    cursor.execute("SELECT DISTINCT date(date) as logged_date FROM diet WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);")
    diet_dates = set(row['logged_date'] for row in cursor.fetchall())

    # Locations
    cursor.execute("SELECT DISTINCT date(timestamp) as logged_date FROM locations WHERE timestamp >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);")
    location_dates = set(row['logged_date'] for row in cursor.fetchall())

    # Blood Pressure
    cursor.execute("SELECT DISTINCT date(date) as logged_date FROM blood_pressure WHERE date >= DATE_SUB(CURDATE(), INTERVAL 30 DAY);")
    bp_dates = set(row['logged_date'] for row in cursor.fetchall())

    cursor.close()
    conn.close()

    # 3. Print audit report
    print(f"\n{'-'*95}")
    print(f"{'DATE':<12} | {'DAY':<10} | {'SLEEP LOG':<12} | {'STEPS LOG':<12} | {'DIET LOG':<12} | {'GPS TRACK':<12} | {'BP LOG':<10}")
    print(f"{'-'*95}")

    missing_sleep = 0
    missing_steps = 0
    missing_diet = 0
    missing_location = 0
    missing_bp = 0

    for d in past_30_days:
        day_name = d.strftime('%A')
        
        has_sleep = d in sleep_dates
        has_steps = d in steps_dates
        has_diet = d in diet_dates
        has_location = d in location_dates
        has_bp = d in bp_dates

        # Color-coded output
        sleep_str = f"\033[92mPRESENT\033[0m" if has_sleep else f"\033[91mMISSING\033[0m"
        steps_str = f"\033[92mPRESENT\033[0m" if has_steps else f"\033[91mMISSING\033[0m"
        diet_str = f"\033[92mPRESENT\033[0m" if has_diet else f"\033[91mMISSING\033[0m"
        loc_str = f"\033[92mPRESENT\033[0m" if has_location else f"\033[91mMISSING\033[0m"
        bp_str = f"\033[92mPRESENT\033[0m" if has_bp else f"\033[91mMISSING\033[0m"

        if not has_sleep: missing_sleep += 1
        if not has_steps: missing_steps += 1
        if not has_diet: missing_diet += 1
        if not has_location: missing_location += 1
        if not has_bp: missing_bp += 1

        print(f"{str(d):<12} | {day_name:<10} | {sleep_str:<12} | {steps_str:<12} | {diet_str:<12} | {loc_str:<12} | {bp_str:<10}")

    print(f"{'-'*95}")
    print("\n📊 30-Day Data Integrity Audit Summary:")
    print(f"  • Missing Sleep Logs     : {f_color(missing_sleep)}")
    print(f"  • Missing Steps Logs     : {f_color(missing_steps)}")
    print(f"  • Missing Diet Logs      : {f_color(missing_diet)}")
    print(f"  • Missing Location Tracks: {f_color(missing_location)}")
    print(f"  • Missing Blood Pressure : {f_color(missing_bp)}")
    
    total_gaps = missing_sleep + missing_steps + missing_diet + missing_location + missing_bp
    if total_gaps == 0:
        print("\n🏆 \033[92mPERFECT INTEGRITY! Your log database has 0 historical gaps. Incredible discipline! 🎉\033[0m\n")
    else:
        print(f"\n⚠️ \033[93mFound {total_gaps} total gaps across the past 30 days. Use Streamlit or Quick-Log to backfill!\033[0m\n")

def f_color(val):
    if val == 0:
        return f"\033[92m{val}\033[0m"
    return f"\033[91m{val}\033[0m"

if __name__ == "__main__":
    get_integrity_audit()
