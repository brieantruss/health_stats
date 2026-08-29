import os
import logging
from google.cloud import bigquery
from mcp.server.fastmcp import FastMCP

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger("mcp_bigquery_server")

PROJECT_ID = "my-data-479716"

# Dynamic path resolution to support both Docker and Local Host runs
RUNNING_IN_DOCKER = os.path.exists("/.dockerenv") or os.environ.get("RUNNING_IN_DOCKER", "false").lower() == "true"
if RUNNING_IN_DOCKER:
    KEY_PATH = "/app/credentials/bigquery-agent-key.json"
else:
    KEY_PATH = "/home/briean/.gcp/bigquery-agent-key.json"

def get_bigquery_client():
    if os.path.exists(KEY_PATH):
        logger.info(f"Using service account key: {KEY_PATH}")
        return bigquery.Client.from_service_account_json(KEY_PATH, project=PROJECT_ID)
    logger.warning("BigQuery key not found. Using ADC fallback.")
    return bigquery.Client(project=PROJECT_ID)

mcp = FastMCP("BigQuery Health Server")

@mcp.tool()
def get_schema_info() -> str:
    """Returns the names and schemas of key views in the health_stats dataset to help formulate SQL queries."""
    return """
1. `view_summary` (Daily vitals & sleep total)
   - Columns: `date` (STRING, 'YYYY/MM/DD'), `total_steps` (INT64), `awake_at_night` (INT64 secs), `light_sleep`/`deep_sleep`/`rem_sleep` (INT64 secs), `total_sleep` (INT64 secs), `total_hours_of_sleep` (STRING), `avg_heart_rate` (INT64)

2. `view_sleep_summary` (Sleep stages + weather context)
   - Columns: `date` (DATE), `Stage` (STRING: 'awake'/'light'/'rem'/'deep'), `conditions` (STRING, e.g. 'Rain'), `precip` (FLOAT64), `temp` (FLOAT64), `duration_seconds` (INT64), `duration_hours` (FLOAT64)

3. `view_activity_recommendations` (Weather & AQI suggestions)
   - Columns: `forecast_date` (DATE), `recommended_activity` (STRING), `rationale` (STRING)

4. `view_diet_recommendations` (Macro targets matching weight/exercise)
   - Columns: `date` (DATE), `weight_kg` (FLOAT64), `calorie_target`/`protein_g`/`carbs_g`/`fat_g` (FLOAT64), `rationale` (STRING)

5. `view_scorecard_summary` (Recent vitals overview)
   - Columns: `date` (STRING), `avg_resting_heart_rate` (INT64), `total_steps` (INT64), `total_sleep_hours` (STRING), `blood_pressure_systolic`/`blood_pressure_diastolic` (INT64)
"""

@mcp.tool()
def execute_readonly_query(sql_query: str) -> str:
    """Executes a read-only SELECT query against the health_stats views and returns tabular results."""
    forbidden = ["drop", "delete", "insert", "update", "alter", "truncate", "create", "grant", "revoke", "merge"]
    query_lower = sql_query.lower()
    for word in forbidden:
        if f" {word} " in f" {query_lower} " or query_lower.startswith(word):
            return f"Error: SQL query contains forbidden database modification keyword: '{word}'"
    if "select" not in query_lower:
        return "Error: SQL query must be a read-only SELECT statement."

    try:
        client = get_bigquery_client()
        logger.info(f"Executing Query: {sql_query}")
        job_config = bigquery.QueryJobConfig(maximum_bytes_billed=100 * 1024 * 1024)
        query_job = client.query(sql_query, job_config=job_config)
        results = query_job.result()
        
        rows = list(results)
        if not rows:
            return "Query returned 0 rows."
            
        fields = [f.name for f in results.schema]
        header = "| " + " | ".join(fields) + " |"
        sep = "| " + " | ".join(["---"] * len(fields)) + " |"
        
        markdown_rows = []
        for r in rows[:100]: # Cap at 100
            vals = []
            for f in fields:
                v = r[f]
                vals.append("NULL" if v is None else str(v).replace("\n", " ").replace("|", "\\|"))
            markdown_rows.append("| " + " | ".join(vals) + " |")
            
        return "\n".join([header, sep] + markdown_rows)
    except Exception as e:
        return f"Error executing BigQuery query: {e}"

if __name__ == "__main__":
    mcp.run(transport="sse")

