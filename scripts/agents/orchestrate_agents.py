import sys
import os
from prefect import flow, serve

# Append current directory to path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from weather_aqi_guard import weather_aqi_guard_flow
from cardio_load_preventer import cardio_load_preventer_flow
from sleep_recovery_optimizer import sleep_recovery_optimizer_flow
from health_trend_analyst import health_trend_analyst_flow
from bio_synthesizer import bio_synthesizer_flow

@flow(name="unified_health_agents_orchestrator")
def main_agents_orchestrator():
    """
    Unified manager flow to trigger and serve all five personal health agents.
    """
    print("🚀 Triggering all daily, weekly, and AI health agents on-demand...")
    weather_aqi_guard_flow()
    cardio_load_preventer_flow()
    sleep_recovery_optimizer_flow()
    health_trend_analyst_flow()
    bio_synthesizer_flow()

if __name__ == "__main__":
    if "--deploy" in sys.argv:
        print("Registering and serving all 5 personal health agents with Prefect Server...")
        
        # Define the deployments
        weather_deployment = weather_aqi_guard_flow.to_deployment(
            name="daily-730am-weather-guard",
            cron="30 7 * * *" # Daily at 7:30 AM
        )
        
        cardio_deployment = cardio_load_preventer_flow.to_deployment(
            name="daily-8am-cardio-load-preventer",
            cron="0 8 * * *" # Daily at 8:00 AM
        )
        
        sleep_deployment = sleep_recovery_optimizer_flow.to_deployment(
            name="weekly-830am-saturday-sleep-optimizer",
            cron="30 8 * * 6" # Saturdays at 8:30 AM
        )
        
        trend_deployment = health_trend_analyst_flow.to_deployment(
            name="weekly-8am-sunday-trend-analyst",
            cron="0 8 * * 0" # Sundays at 8:00 AM
        )
        
        # New Gemini AI Holistic Wellness & Bio-Synthesizer Deployment!
        gemini_deployment = bio_synthesizer_flow.to_deployment(
            name="weekly-930am-saturday-gemini-bio-synthesizer",
            cron="30 9 * * 6" # Saturdays at 9:30 AM (Runs today!)
        )
        
        # Serve all deployments concurrently using the Prefect serve API
        print("Starting Prefect serving worker...")
        serve(
            weather_deployment,
            cardio_deployment,
            sleep_deployment,
            trend_deployment,
            gemini_deployment
        )
    else:
        # Runs all flows sequentially on-demand right now
        main_agents_orchestrator()
