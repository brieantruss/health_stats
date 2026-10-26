import os
import re
from pathlib import Path

import requests
import streamlit as st


API_BASE_URL = os.environ.get("API_BASE_URL", "http://192.168.0.110:5001")
ALLOWED_EXERCISES = [
    "adductor_stretch",
    "bridge_stretch",
    "butterfly_stretch",
    "calf_raises_one_leg",
    "calf_raises_two_leg",
    "calf_stretch",
    "chest_stretch",
    "chin_ups",
    "crunches",
    "dips",
    "dorsal_raise",
    "downward_dog_stretch",
    "glute_bridges",
    "hamstring_stretch",
    "heel_grab_stretch",
    "inverted_rows_underhanded",
    "inverted_rows",
    "kapotasana_stretch",
    "kneeling_hip_flexor_stretch",
    "leg_raises_hanging",
    "leg_raises",
    "lunges",
    "neck_raises",
    "neck_stretch",
    "prone_chest_opener",
    "pull_downs",
    "pull_ups",
    "push_ups_decline",
    "push_ups_fingers_decline",
    "push_ups_fingers_handstand",
    "push_ups_fingers_incline",
    "push_ups_handstand",
    "push_ups_incline",
    "push_ups",
    "quad_stretch",
    "romanian_twists",
    "scissor_kicks",
    "shots",
    "shoulder_stretch",
    "side_stretch",
    "spinal_twist_stretch",
    "squats_pistol",
    "squats_single_leg",
    "squats",
    "toe touch",
    "triceps_stretch",
    "uttanasana_stretch",
    "weight",
    "bench press (upper body)",
    "squats (lower body)",
    "deadlift (lower body)",
    "overhead press (upper body)",
    "barbell curl (arms)",
    "hiking",
    "running",
    "cycling",
    "swimming",
    "shootaround (basketball)",
]


def configure_page(title):
    st.set_page_config(
        layout="wide",
        page_title=f"{title} | Health Stats Tracker",
        initial_sidebar_state="expanded",
    )
    st.markdown(
        """
<style>
    body {
        color: #E0E0E0;
        background-color: #1A1A1A;
        font-family: 'Arial', sans-serif;
    }
    .stApp {
        background-color: #1A1A1A;
    }
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF;
        font-family: 'Arial', sans-serif;
        text-transform: lowercase;
        padding-bottom: 10px;
        border-bottom: 1px solid #333333;
        margin-bottom: 20px;
    }
    h1.main-title {
        font-size: 2.5em;
        text-align: center;
        margin-top: 0px;
        margin-bottom: 0px;
        padding-top: 0px;
        padding-bottom: 0px;
    }
    h2 {
        font-size: 1.8em;
        margin-top: 40px;
    }
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stDateInput>div>div>input {
        background-color: #2B2B2B;
        color: #E0E0E0;
        border: 1px solid #444444;
        border-radius: 5px;
        font-family: 'Arial', sans-serif;
    }
    .stSelectbox>div>div {
        background-color: #2B2B2B;
        color: #E0E0E0;
        border: 1px solid #444444;
        border-radius: 5px;
        font-family: 'Arial', sans-serif;
    }
    .stMultiSelect>div>div {
        background-color: #2B2B2B;
        color: #E0E0E0;
        border: 1px solid #444444;
        border-radius: 5px;
        font-family: 'Arial', sans-serif;
    }
    .stButton>button {
        background-color: #007BFF;
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s ease;
        font-family: 'Arial', sans-serif;
    }
    .stButton>button:hover {
        background-color: #0056b3;
    }
    .stDataFrame {
        border: 1px solid #333333;
        border-radius: 5px;
        overflow-x: auto;
        font-family: 'Arial', sans-serif;
    }
    .dataframe th {
        background-color: #333333;
        color: #FFFFFF;
        font-weight: bold;
        padding: 10px;
        border-right: 1px solid #444444;
    }
    .dataframe td {
        background-color: #2B2B2B;
        color: #E0E0E0;
        padding: 8px 10px;
        border-right: 1px solid #333333;
        border-top: 1px solid #333333;
    }
    .dataframe tr:nth-child(even) td {
        background-color: #222222;
    }
    .stAlert {
        background-color: #333333;
        color: #E0E0E0;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
        font-family: 'Arial', sans-serif;
    }
    .stAlert.info { border-left: 5px solid #1E90FF; }
    .stAlert.success { border-left: 5px solid #28A745; }
    .stAlert.error { border-left: 5px solid #DC3545; }
    .stAlert.warning { border-left: 5px solid #FFC107; }
    hr {
        border-top: 2px solid #444444;
        margin-top: 50px;
        margin-bottom: 50px;
    }
    .st-emotion-cache-nahz7x {
        padding-top: 2rem;
        padding-bottom: 2rem;
    }
    div[data-testid="stForm"] label,
    div[data-testid="stVerticalBlock"] label,
    div[data-testid="stHorizontalBlock"] label,
    div[data-testid="stCaptionContainer"] {
        font-family: 'Arial', sans-serif;
    }
    .centered-logo-container {
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100%;
    }
</style>
""",
        unsafe_allow_html=True,
    )

    logo_path = Path(__file__).with_name("Optimize-with-MODULO-Logo2.png")
    col1, col2, col3 = st.columns([1, 4, 1])
    with col1:
        st.markdown('<div class="centered-logo-container">', unsafe_allow_html=True)
        st.image(str(logo_path), width=70)
        st.markdown("</div>", unsafe_allow_html=True)
    with col2:
        st.markdown(
            '<h1 class="main-title">Health Stats Tracker</h1>',
            unsafe_allow_html=True,
        )
    with col3:
        st.empty()


def normalize_exercise_type(value):
    return re.sub(r"[^a-z0-9]+", "_", value.strip().lower()).strip("_")


@st.cache_data(ttl=60)
def get_exercise_types():
    try:
        response = requests.get(f"{API_BASE_URL}/exercise-types", timeout=15)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        st.error(f"unable to fetch exercise types from {API_BASE_URL}: {e}")
        return []


def add_exercise_type(name):
    try:
        response = requests.post(
            f"{API_BASE_URL}/exercise-types",
            json={"name": name},
            timeout=15,
        )
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        try:
            error = e.response.json().get("error", str(e))
        except (AttributeError, ValueError):
            error = str(e)
        return {"error": error}, e.response.status_code if e.response is not None else 500


@st.cache_data(ttl=60)
def get_all_exercises(exercise_type=None):
    params = {}
    if exercise_type and exercise_type != "All":
        params["exercise"] = exercise_type
    last_exception = None
    for _ in range(2):
        try:
            response = requests.get(
                f"{API_BASE_URL}/exercises", params=params, timeout=15
            )
            response.raise_for_status()
            data = response.json()
            st.session_state["last_exercises_data"] = data
            return data
        except requests.exceptions.RequestException as e:
            last_exception = e

    st.warning(
        "API temporarily unreachable. Retrying shortly. "
        "Showing last available records if present."
    )
    if "last_exercises_data" in st.session_state:
        return st.session_state["last_exercises_data"]

    st.error(f"unable to fetch exercises from {API_BASE_URL}: {last_exception}")
    return []


def add_new_exercise(data):
    try:
        response = requests.post(f"{API_BASE_URL}/exercises", json=data, timeout=15)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"error adding exercise: {e}")
        return {"error": str(e)}, 500


def delete_existing_exercise(exercise_id):
    try:
        response = requests.delete(
            f"{API_BASE_URL}/exercises/{exercise_id}", timeout=15
        )
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"error deleting exercise: {e}")
        return {"error": str(e)}, 500


@st.cache_data(ttl=3600)
def get_food_descriptions():
    last_exception = None
    for _ in range(2):
        try:
            response = requests.get(f"{API_BASE_URL}/food_descriptions", timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            last_exception = e

    st.warning(
        "API temporarily unreachable while loading food descriptions. "
        "Please retry in a few seconds."
    )
    st.error(f"unable to fetch food descriptions from {API_BASE_URL}: {last_exception}")
    return []


def add_new_diet_record(data):
    try:
        response = requests.post(f"{API_BASE_URL}/diet", json=data, timeout=15)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"error adding diet record: {e}")
        return {"error": str(e)}, 500


@st.cache_data(ttl=60)
def get_all_diet_records(item=None):
    params = {}
    if item and item != "All":
        params["item"] = item
    last_exception = None
    for _ in range(2):
        try:
            response = requests.get(f"{API_BASE_URL}/diet", params=params, timeout=15)
            response.raise_for_status()
            data = response.json()
            st.session_state["last_diet_data"] = data
            return data
        except requests.exceptions.RequestException as e:
            last_exception = e

    st.warning(
        "API temporarily unreachable. Retrying shortly. "
        "Showing last available diet records if present."
    )
    if "last_diet_data" in st.session_state:
        return st.session_state["last_diet_data"]

    st.error(f"unable to fetch diet records from {API_BASE_URL}: {last_exception}")
    return []


def delete_existing_diet_record(diet_id):
    try:
        response = requests.delete(f"{API_BASE_URL}/diet/{diet_id}", timeout=15)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"error deleting diet record: {e}")
        return {"error": str(e)}, 500
