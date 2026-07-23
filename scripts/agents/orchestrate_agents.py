import sys
import os
from prefect import flow, serve

# Append current directory to path for relative imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from weather_aqi_guard import weather_aqi_guard_flow
from cardio_load_preventer import cardio_load_preventer_flow
from sleep_recovery_optimizer import sleep_recovery_optimizer_flow
from health_trend_analyst import health_trend_analyst_flow

@flow(name="unified_health_agents_orchestrator")
def main_agents_orchestrator():
    """
    Unified manager flow to trigger and serve all four personal health agents.
    """
    print("🚀 Triggering all daily and weekly health agents on-demand...")
    weather_aqi_guard_flow()
    cardio_load_preventer_flow()
    sleep_recovery_optimizer_flow()
    health_trend_analyst_flow()

if __name__ == "__main__":
    if "--deploy" in sys.argv:
        print("Registering and serving all 4 personal health agents with Prefect Server...")
        
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
        
        # Serve all deployments concurrently using the Prefect serve API
        print("Starting Prefect serving worker...")
        serve(
            weather_deployment,
            cardio_deployment,
            sleep_deployment,
            trend_deployment
        )
    else:
        # Runs all flows sequentially on-demand right now
        main_agents_orchestrator()
