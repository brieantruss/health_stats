#!/usr/bin/env python3
import os
import sys
import json
import time
import sqlite3
from datetime import datetime

# Place health_events.db in the repository root directory
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(REPO_ROOT, "health_events.db")

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA journal_mode=WAL;")
    return conn

def update_snapshot(key: str, value_dict: dict):
    """Updates a single key-value entry in the latest state snapshot."""
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        value_json = json.dumps(value_dict)
        cursor.execute("""
            INSERT INTO latest_health_snapshot (key, value, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT(key) DO UPDATE SET
                value = excluded.value,
                updated_at = excluded.updated_at
        """, (key, value_json, now_str))
        conn.commit()
    except Exception as e:
        print(f"❌ [Consumer] Error updating snapshot for key '{key}': {e}")
    finally:
        conn.close()

def process_single_event(event_id: int, event_type: str, payload_str: str) -> bool:
    """Processes a single event, updates states, and generates alerts."""
    try:
        payload = json.loads(payload_str)
        print(f"⏳ [Consumer] Processing event ID {event_id}: '{event_type}'")
        
        if event_type == "workout_logged":
            update_snapshot("latest_workout", payload)
            exercise = payload.get("exercise", "workout")
            reps = payload.get("reps")
            alert_msg = f"🏋️‍♂️ Workout: '{exercise}' ({reps or 'N/A'} reps) logged!"
            suggestion = "💡 Recovery suggestion: Try completing an adductor_stretch or chest_stretch today."
            update_snapshot("latest_coaching_alert", {
                "message": alert_msg, "suggestion": suggestion, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        elif event_type == "sleep_summary_ready":
            update_snapshot("latest_sleep", payload)
            hours = payload.get("total_hours", 8.0)
            alert_msg = f"😴 Sleep summary loaded: {hours:.1f} hours sleep."
            suggestion = "💡 Alert: Total sleep is below target. Do a relaxing bridge_stretch tonight!" if hours < 7.0 else "🌟 Great sleep duration! Perfect day for a high-intensity session!"
            update_snapshot("latest_coaching_alert", {
                "message": alert_msg, "suggestion": suggestion, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        elif event_type == "diet_logged":
            update_snapshot("latest_diet", payload)
            item = payload.get("item", "food")
            alert_msg = f"🥗 Diet Logged: '{item}'."
            suggestion = "💡 Tip: Make sure to pair this meal with 300ml of water!"
            update_snapshot("latest_coaching_alert", {
                "message": alert_msg, "suggestion": suggestion, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        elif event_type == "anomaly_detected":
            alert_msg = f"🚨 Alert: {payload.get('message', 'Anomaly detected!')}"
            suggestion = payload.get("suggestion", "Rest and recover.")
            update_snapshot("latest_coaching_alert", {
                "message": alert_msg, "suggestion": suggestion, "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            })
            
        return True
    except Exception as e:
        print(f"❌ [Consumer] Error processing event ID {event_id}: {e}")
        return False

def run_consumer_loop():
    print("==========================================================")
    print("🚀 STARTING HEALTH STATS REAL-TIME EVENT STREAM CONSUMER")
    print(f"Database Path: {DB_PATH}")
    print("==========================================================")
    
    # Initialize DB (conn-close checks file existence)
    conn = get_db_connection()
    conn.close()
    
    while True:
        conn = get_db_connection()
        cursor = conn.cursor()
        try:
            cursor.execute(
                "SELECT id, event_type, payload FROM event_queue WHERE status = 'pending' ORDER BY id ASC LIMIT 1"
            )
            row = cursor.fetchone()
            if row:
                event_id, event_type, payload_str = row
                success = process_single_event(event_id, event_type, payload_str)
                now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                new_status = "processed" if success else "failed"
                cursor.execute(
                    "UPDATE event_queue SET status = ?, processed_at = ? WHERE id = ?",
                    (new_status, now_str, event_id)
                )
                conn.commit()
                print(f"✅ [Consumer] Event ID {event_id} marked as '{new_status}'.\n")
        except Exception as e:
            print(f"❌ [Consumer] Loop error: {e}")
        finally:
            conn.close()
        time.sleep(2)

if __name__ == "__main__":
    try:
        run_consumer_loop()
    except KeyboardInterrupt:
        print("\n👋 Consumer stopped. Goodbye!")
        sys.exit(0)
