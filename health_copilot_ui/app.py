import os
import asyncio
import streamlit as st
import google.generativeai as genai
import pandas as pd
from mcp import ClientSession
from mcp.client.sse import sse_client

st.set_page_config(layout="wide", page_title="Health Copilot", page_icon="🧠")
st.markdown("<style>.stApp { background-color: #1A1A1A; color: #E0E0E0; }</style>", unsafe_allow_html=True)

# Dynamic Path & URL Resolution to support both Docker and Bare-Metal VM runs
RUNNING_IN_DOCKER = os.path.exists("/.dockerenv") or os.path.exists("/app/credentials")

if RUNNING_IN_DOCKER:
    URL = "http://mcp-bigquery-server:8000/sse"
    KEY_PATH = "/app/credentials/gemini_api_key.txt"
else:
    URL = "http://localhost:8000/sse"
    KEY_PATH = "/home/briean/.gcp/gemini_api_key.txt"


def get_gemini_key():
    if os.path.exists(KEY_PATH):
        with open(KEY_PATH, "r", encoding="utf-8") as f:
            return f.read().strip()
    return os.environ.get("GEMINI_API_KEY", "")

async def call_mcp(tool_name: str, args: dict):
    async with sse_client(URL) as (r, w):
        async with ClientSession(r, w) as session:
            await session.initialize()
            res = await session.call_tool(tool_name, args)
            return res.content[0].text if res.content else ""

def get_schema_info() -> str:
    """Returns the names and schemas of BigQuery views available for query."""
    return asyncio.run(call_mcp("get_schema_info", {}))

def execute_readonly_query(sql_query: str) -> str:
    """Executes a read-only SELECT query against the health_stats views and returns tabular markdown."""
    if "queries_run" not in st.session_state:
        st.session_state.queries_run = []
    st.session_state.queries_run.append(sql_query)
    return asyncio.run(call_mcp("execute_readonly_query", {"sql_query": sql_query}))

def parse_markdown_table(text):
    lines = [l.strip() for l in text.strip().split("\n") if l.strip().startswith("|")]
    if len(lines) < 3:
        return None
    try:
        header = [p.strip() for p in lines[0].split("|")[1:-1]]
        data = []
        for l in lines[2:]:
            vals = [p.strip() for p in l.split("|")[1:-1]]
            if len(vals) == len(header):
                data.append(vals)
        df = pd.DataFrame(data, columns=header)
        for col in df.columns:
            try:
                df[col] = pd.to_numeric(df[col])
            except ValueError:
                pass
        return df
    except Exception:
        return None

with st.sidebar:
    st.title("🧠 MCP Discovery")
    st.info("Discovers and queries BigQuery views via Model Context Protocol.")
    st.markdown("""
    - **`view_summary`**: Daily vitals, steps, sleep.
    - **`view_sleep_summary`**: Sleep stages + weather.
    - **`view_activity_recommendations`**: Training advice.
    - **`view_diet_recommendations`**: Target calories & macros.
    - **`view_scorecard_summary`**: Vitals dashboard metrics.
    """)

st.title("🧠 Personal Health Copilot")
st.caption("AI insights running securely over BigQuery via MCP.")

api_key = get_gemini_key()
if not api_key:
    st.error("❌ Gemini API Key not found at `/home/briean/.gcp/gemini_api_key.txt` on the host.")
    st.stop()

genai.configure(api_key=api_key)
if "chat_session" not in st.session_state:
    model = genai.GenerativeModel(
        model_name="gemini-2.0-flash",
        tools=[get_schema_info, execute_readonly_query],
        system_instruction=(
            "You are Briean's elite health copilot. "
            "You have tools to query his BigQuery views using SQL. "
            "Always fetch schema info using `get_schema_info` if you are unsure of columns. "
            "Answer questions using actual query results, cite dates/metrics, and write clear SQL. "
            "Whenever you query data, present the results as a Markdown table so the UI can graph it. "
            "Keep insights concise, encouraging, and analytical."
        )
    )
    st.session_state.chat_session = model.start_chat(enable_automatic_function_calling=True)
    st.session_state.messages = []

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])
        if msg.get("queries"):
            for q in msg["queries"]:
                with st.expander("🔍 SQL Query", expanded=False):
                    st.code(q, language="sql")
        if msg.get("df") is not None:
            st.dataframe(msg["df"], use_container_width=True)
            num_cols = msg["df"].select_dtypes(include="number").columns.tolist()
            if len(num_cols) >= 1 and len(msg["df"]) > 1:
                st.line_chart(msg["df"], y=num_cols[0], use_container_width=True)

if prompt := st.chat_input("Ask about sleep, resting heart rate, workouts..."):
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})
    st.session_state.queries_run = []

    with st.chat_message("assistant"):
        with st.spinner("Analyzing and querying BigQuery warehouse..."):
            try:
                response = st.session_state.chat_session.send_message(prompt)
                ans_text = response.text
                st.markdown(ans_text)
                
                queries = list(st.session_state.get("queries_run", []))
                for q in queries:
                    with st.expander("🔍 SQL Query Executed", expanded=False):
                        st.code(q, language="sql")
                
                df = parse_markdown_table(ans_text)
                if df is not None:
                    st.dataframe(df, use_container_width=True)
                    num_cols = df.select_dtypes(include="number").columns.tolist()
                    if len(num_cols) >= 1 and len(df) > 1:
                        st.line_chart(df, y=num_cols[0], use_container_width=True)
                
                st.session_state.messages.append({
                    "role": "assistant",
                    "content": ans_text,
                    "queries": queries,
                    "df": df
                })
            except Exception as e:
                st.error(f"Failed to generate response: {e}")
