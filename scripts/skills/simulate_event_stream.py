#!/usr/bin/env python3
import os
import sys

# Add repository root to python search path
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.append(REPO_ROOT)

from scripts.event_stream import publish_event

def print_menu():
    print("\n" + "="*50)
    print("🧠 HEALTH STATS: STREAMING EVENT SIMULATOR")
    print("="*50)
    print("1) Simulate Workout Logged (e.g., Bench Press)")
    print("2) Simulate Poor Sleep Logged (< 7 hours)")
    print("3) Simulate Great Sleep Logged (>= 8 hours)")
    print("4) Simulate Diet Logged (e.g., Apple)")
    print("5) Simulate Anomaly Detected (e.g., resting heart rate spike)")
    print("6) Exit")
    print("="*50)

def main():
    while True:
        print_menu()
        try:
            choice = input("Select an event to simulate [1-6]: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n👋 Exiting simulator. Goodbye!")
            break
            
        if choice == "1":
            print("\nPublishing simulated workout event...")
            payload = {
                "exercise": "bench press (upper body)",
                "record_date": "2026-08-30",
                "reps": 12,
                "resistance_kg": 45.0
            }
            publish_event("workout_logged", payload)
            
        elif choice == "2":
            print("\nPublishing simulated poor sleep event...")
            payload = {
                "date": "2026-08-30",
                "total_hours": 5.8,
                "deep_sleep_ratio": 0.11,
                "light_sleep_ratio": 0.65
            }
            publish_event("sleep_summary_ready", payload)
            
        elif choice == "3":
            print("\nPublishing simulated great sleep event...")
            payload = {
                "date": "2026-08-30",
                "total_hours": 8.4,
                "deep_sleep_ratio": 0.22,
                "light_sleep_ratio": 0.58
            }
            publish_event("sleep_summary_ready", payload)
            
        elif choice == "4":
            print("\nPublishing simulated diet event...")
            payload = {
                "item": "Apple, raw",
                "record_date": "2026-08-30",
                "grams": 150.0
            }
            publish_event("diet_logged", payload)
            
        elif choice == "5":
            print("\nPublishing simulated anomaly alert...")
            payload = {
                "message": "Resting Heart Rate spiked to 92 bpm during sleep (baseline: 58 bpm)",
                "suggestion": "⚠️ Cardio Recovery Trigger: Fatigue or dehydration suspected. Recommend rest day and complete a calf_stretch."
            }
            publish_event("anomaly_detected", payload)
            
        elif choice == "6":
            print("\n👋 Exiting simulator. Goodbye!")
            break
        else:
            print("\n❌ Invalid choice. Please enter a number between 1 and 6.")

if __name__ == "__main__":
    main()
