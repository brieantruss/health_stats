import streamlit as st
import requests
import pandas as pd
from datetime import datetime, date

# --- Configuration ---
# Supports environment variables for secure/flexible deployment (e.g., Google Cloud Run)
import os
API_BASE_URL = os.environ.get("API_BASE_URL", "http://192.168.0.110:5001")
# Allowed exercises for input validation and display (existing)
ALLOWED_EXERCISES = [
    'adductor_stretch',
    'bridge_stretch',
    'butterfly_stretch',
    'calf_raises_one_leg',
    'calf_raises_two_leg',
    'calf_stretch',
    'chest_stretch',
    'chin_ups',
    'crunches',
    'dips',
    'dorsal_raise',
    'downward_dog_stretch',
    'glute_bridges',
    'hamstring_stretch',
    'heel_grab_stretch',
    'inverted_rows_underhanded',
    'inverted_rows',
    'kapotasana_stretch',
    'kneeling_hip_flexor_stretch',
    'leg_raises_hanging',
    'leg_raises',
    'lunges',
    'neck_raises',
    'neck_stretch',
    'prone_chest_opener',
    'pull_ups',
    'push_ups_decline',
    'push_ups_fingers_decline',
    'push_ups_fingers_handstand',
    'push_ups_fingers_incline',
    'push_ups_handstand',
    'push_ups_incline',
    'push_ups',
    'quad_stretch',
    'romanian_twists',
    'scissor_kicks',
    'shots',
    'shoulder_stretch',
    'side_stretch',
    'spinal_twist_stretch',
    'squats_pistol',
    'squats_single_leg',
    'squats',
    'toe touch',
    'triceps_stretch',
    'uttanasana_stretch',
    'weight'
]

# --- Streamlit Page Configuration ---
st.set_page_config(
    layout="wide",
    page_title="Health Stats Tracker",
    initial_sidebar_state="collapsed" # Collapses the sidebar by default
)

# Custom CSS for theme matching and general elements
st.markdown("""
<style>
    /* General body and text styles for a dark theme */
    body {
        color: #E0E0E0; /* Light gray text */
        background-color: #1A1A1A; /* Very dark background */
        font-family: 'Arial', sans-serif; /* Smoother font for body text */
    }
    .stApp {
        background-color: #1A1A1A; /* Apply to the whole app */
    }

    /* Header styles */
    h1, h2, h3, h4, h5, h6 {
        color: #FFFFFF; /* White for headings */
        font-family: 'Arial', sans-serif; /* Consistent font for headings */
        text-transform: lowercase; /* Make headings lowercase */
        padding-bottom: 10px; /* Space below headings */
        border-bottom: 1px solid #333333; /* Subtle line under headings */
        margin-bottom: 20px;
    }
    /* Specific adjustments for the main title h1 */
    h1.main-title { /* Added a class for precise targeting */
        font-size: 2.5em;
        text-align: center; /* Center the main title */
        margin-top: 0px; /* Adjust as needed */
        margin-bottom: 0px; /* Adjust as needed */
        padding-top: 0px;
        padding-bottom: 0px;
    }
    h2 {
        font-size: 1.8em;
        margin-top: 40px; /* More space above sub-headers */
    }

    /* Customizing Streamlit widgets for dark theme */
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stDateInput>div>div>input {
        background-color: #2B2B2B; /* Darker input background */
        color: #E0E0E0; /* Light text in inputs */
        border: 1px solid #444444; /* Subtle border */
        border-radius: 5px;
        font-family: 'Arial', sans-serif; /* Apply font to inputs */
    }
    .stSelectbox>div>div {
        background-color: #2B2B2B;
        color: #E0E0E0;
        border: 1px solid #444444;
        border-radius: 5px;
        font-family: 'Arial', sans-serif; /* Apply font to selectbox */
    }
    .stMultiSelect>div>div {
        background-color: #2B2B2B;
        color: #E0E0E0;
        border: 1px solid #444444;
        border-radius: 5px;
        font-family: 'Arial', sans-serif; /* Apply font to multiselect */
    }

    /* Buttons */
    .stButton>button {
        background-color: #007BFF; /* A distinct blue for buttons */
        color: white;
        border-radius: 5px;
        padding: 10px 20px;
        font-weight: bold;
        border: none;
        transition: background-color 0.3s ease;
        font-family: 'Arial', sans-serif; /* Apply font to buttons */
    }
    .stButton>button:hover {
        background-color: #0056b3; /* Darker blue on hover */
    }

    /* Dataframe styling to match dark theme tables */
    .stDataFrame {
        border: 1px solid #333333; /* Border around dataframe */
        border-radius: 5px;
        overflow-x: auto; /* Allow horizontal scrolling for wide tables */
        font-family: 'Arial', sans-serif; /* Apply font to dataframe */
    }
    /* Header row */
    .dataframe th {
        background-color: #333333; /* Darker header background */
        color: #FFFFFF; /* White header text */
        font-weight: bold;
        padding: 10px;
        border-right: 1px solid #444444; /* Separator between header cells */
    }
    /* Data rows */
    .dataframe td {
        background-color: #2B2B2B; /* Darker cell background */
        color: #E0E0E0; /* Light text in cells */
        padding: 8px 10px;
        border-right: 1px solid #333333; /* Separator between cells */
        border-top: 1px solid #333333; /* Separator between rows */
    }
    .dataframe tr:nth-child(even) td {
        background-color: #222222; /* Slightly different shade for even rows */
    }

    /* Info/Success/Error messages */
    .stAlert {
        background-color: #333333;
        color: #E0E0E0;
        border-radius: 5px;
        padding: 15px;
        margin-bottom: 20px;
        font-family: 'Arial', sans-serif; /* Apply font to alerts */
    }
    .stAlert.info { border-left: 5px solid #1E90FF; } /* Dodger Blue */
    .stAlert.success { border-left: 5px solid #28A745; } /* Green */
    .stAlert.error { border-left: 5px solid #DC3545; } /* Red */
    .stAlert.warning { border-left: 5px solid #FFC107; } /* Yellow */

    /* Separator lines */
    hr {
        border-top: 2px solid #444444; /* Thicker, more prominent separator */
        margin-top: 50px;
        margin-bottom: 50px;
    }

    /* Container styling for better spacing */
    .st-emotion-cache-nahz7x { /* Targeting a common container class for padding */
        padding-top: 2rem;
        padding-bottom: 2rem;
    }

    /* Ensure text within forms and labels also uses the chosen font */
    div[data-testid="stForm"] label,
    div[data-testid="stVerticalBlock"] label,
    div[data-testid="stHorizontalBlock"] label {
        font-family: 'Arial', sans-serif;
    }
    div[data-testid="stCaptionContainer"] { /* For help text */
        font-family: 'Arial', sans-serif;
    }

    /* Specific CSS for logo container - ensure it sits correctly within columns */
    .centered-logo-container {
        display: flex;
        justify-content: center; /* Center horizontally */
        align-items: center;   /* Center vertically */
        height: 100%; /* Take full height of its column */
    }

</style>
""", unsafe_allow_html=True)

# --- Add your logo and title ---
logo_path = "Optimize-with-MODULO-Logo2.png" # Assuming the logo is in the same directory

# Use st.columns to place the logo and title side-by-side with control
col1, col2, col3 = st.columns([1, 4, 1]) # Adjust ratios: small left, wide middle for title, small right

with col1:
    # Use a div to help center the logo vertically within its column if needed
    st.markdown('<div class="centered-logo-container">', unsafe_allow_html=True)
    st.image(logo_path, width=70) # Adjusted width for a smaller, unobtrusive look
    st.markdown('</div>', unsafe_allow_html=True)

with col2:
    # Use st.markdown for the title to apply custom CSS for centering
    st.markdown('<h1 class="main-title">Health Stats Tracker</h1>', unsafe_allow_html=True)

with col3:
    st.empty() # Empty column for spacing/alignment


# --- Functions to interact with the API ---

@st.cache_data(ttl=60) # Cache data for 60 seconds
def get_all_exercises(exercise_type=None):
    params = {}
    if exercise_type and exercise_type != "All":
        params['exercise'] = exercise_type
    last_exception = None
    for _ in range(2):
        try:
            response = requests.get(f"{API_BASE_URL}/exercises", params=params, timeout=15)
            response.raise_for_status() # Raise an exception for HTTP errors
            data = response.json()
            st.session_state["last_exercises_data"] = data
            return data
        except requests.exceptions.RequestException as e:
            last_exception = e

    st.warning("API temporarily unreachable. Retrying shortly. Showing last available records if present.")
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
        response = requests.delete(f"{API_BASE_URL}/exercises/{exercise_id}", timeout=15)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"error deleting exercise: {e}")
        return {"error": str(e)}, 500

@st.cache_data(ttl=3600) # Cache food descriptions for longer, as they don't change often
def get_food_descriptions():
    """
    Fetches all food descriptions from the API.
    """
    last_exception = None
    for _ in range(2):
        try:
            response = requests.get(f"{API_BASE_URL}/food_descriptions", timeout=15)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            last_exception = e

    st.warning("API temporarily unreachable while loading food descriptions. Please retry in a few seconds.")
    st.error(f"unable to fetch food descriptions from {API_BASE_URL}: {last_exception}")
    return []

def add_new_diet_record(data):
    """
    Adds a new diet record via the API.
    """
    try:
        response = requests.post(f"{API_BASE_URL}/diet", json=data, timeout=15)
        response.raise_for_status()
        return response.json(), response.status_code
    except requests.exceptions.RequestException as e:
        st.error(f"error adding diet record: {e}")
        return {"error": str(e)}, 500


# --- Streamlit Layout ---

## Add New Exercise Record
with st.container(border=True): # Use a container for better visual grouping and a border
    st.markdown("<h2>add new exercise record</h2>", unsafe_allow_html=True) # Changed to lowercase
    with st.form("add_exercise_form"):
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        with col_ex1:
            selected_exercise = st.selectbox(
                "Exercise Type",
                ALLOWED_EXERCISES,
                key="add_exercise_type",
                help="Type to search for an exercise or select from the dropdown."
            )
        with col_ex2:
            record_date = st.date_input("Date", value=date.today(), key="add_exercise_date")
        with col_ex3:
            reps_input = st.number_input("Reps (optional)", min_value=1, step=1, value=None, key="add_reps")

        col_ex4, col_ex5 = st.columns(2)
        with col_ex4:
            duration_input = st.number_input("Duration (minutes, optional)", min_value=0.0, step=0.1, value=None, format="%.2f", key="add_duration")
        with col_ex5:
            resistance_input = st.number_input("Resistance (kg, optional)", min_value=0.0, step=0.1, value=None, format="%.2f", key="add_resistance")

        submitted = st.form_submit_button("add exercise record") # Lowercase button text
        if submitted:
            new_record = {
                "exercise": selected_exercise,
                "record_date": record_date.strftime('%Y-%m-%d'),
                "reps": reps_input if reps_input is not None else None,
                "duration": float(duration_input) if duration_input is not None else None,
                "resistance_kg": float(resistance_input) if resistance_input is not None else None
            }
            message, status = add_new_exercise(new_record)
            if status == 201:
                st.success(f"exercise record added: {message.get('message')}. id: {message.get('id')}") # Lowercase messages
                st.cache_data.clear() # Clear cache to refresh data display
                st.rerun() # Rerun to refresh the page
            else:
                st.error(f"failed to add exercise record: {message.get('error', 'unknown error')}") # Lowercase messages

st.markdown("---") # Visual separator

## Add New Diet Record
with st.container(border=True): # Use a container for better visual grouping and a border
    st.markdown("<h2>add new diet record</h2>", unsafe_allow_html=True) # Changed to lowercase
    with st.form("add_diet_form"):
        food_descriptions = get_food_descriptions()
        
        col_diet1, col_diet2 = st.columns(2)
        with col_diet1:
            if food_descriptions:
                selected_item = st.selectbox(
                    "Item",
                    food_descriptions,
                    key="add_diet_item",
                    help="Type to search for a food item or select from the dropdown."
                )
            else:
                st.warning("could not load food descriptions. please ensure your api is running and the food_ingredients table has data.") # Lowercase messages
                selected_item = None
                
        with col_diet2:
            diet_record_date = st.date_input("Date", value=date.today(), key="add_diet_date")

        col_diet3, col_diet4 = st.columns(2)
        with col_diet3:
            grams_input = st.number_input("Grams (optional)", min_value=0.0, step=0.1, value=None, format="%.3f", key="add_diet_grams")
        
        with col_diet4:
            ml_input = st.number_input("ML (optional)", min_value=0.0, step=0.1, value=None, format="%.3f", key="add_diet_ml")

        diet_submitted = st.form_submit_button("add diet record") # Lowercase button text
        if diet_submitted:
            if selected_item:
                new_diet_record = {
                    "item": selected_item,
                    "record_date": diet_record_date.strftime('%Y-%m-%d'),
                    "grams": float(grams_input) if grams_input is not None else None,
                    "ml": float(ml_input) if ml_input is not None else None
                }
                message, status = add_new_diet_record(new_diet_record)
                if status == 201:
                    st.success(f"diet record added: {message.get('message')}. id: {message.get('id')}") # Lowercase messages
                    st.cache_data.clear()
                    st.rerun()
                else:
                    st.error(f"failed to add diet record: {message.get('error', 'unknown error')}") # Lowercase messages
            else:
                st.error("cannot add diet record: no food item selected or loaded.") # Lowercase messages

st.markdown("---") # Visual separator


## View & Manage Exercise Records
with st.container(border=True): # Use a container for better visual grouping and a border
    st.markdown("<h2>view & manage exercise records</h2>", unsafe_allow_html=True) # Changed to lowercase

    filter_exercise_type = st.selectbox(
        "Filter by Exercise Type",
        ["All"] + ALLOWED_EXERCISES,
        key="filter_exercise_type",
        help="Type to search for an exercise or select from the dropdown to filter records."
    )

    exercises_data = get_all_exercises(filter_exercise_type)

    if exercises_data:
        df = pd.DataFrame(exercises_data)
        df['record_date'] = pd.to_datetime(df['record_date'])
        df = df.sort_values(by=['record_date', 'id'], ascending=[False, False])
        st.dataframe(df.set_index('id'), use_container_width=True) # use_container_width for better fit

        st.markdown("<h3>delete exercise record by id</h3>", unsafe_allow_html=True) # Changed to lowercase
        col_del1, col_del2 = st.columns([0.7, 0.3])
        with col_del1:
            delete_id = st.number_input("Enter ID to delete", min_value=1, step=1, value=None, key="delete_id", placeholder="e.g., 5")
        with col_del2:
            st.markdown("<br>", unsafe_allow_html=True) # Add a line break for vertical alignment
            if st.button("delete selected exercise record"): # Lowercase button text
                if delete_id:
                    message, status = delete_existing_exercise(int(delete_id))
                    if status == 200:
                        st.success(f"exercise record deleted: {message.get('message')}") # Lowercase messages
                        st.cache_data.clear()
                        st.rerun()
                    elif status == 404:
                        st.warning(f"no exercise record found with id: {delete_id}") # Lowercase messages
                    else:
                        st.error(f"failed to delete exercise record: {message.get('error', 'unknown error')}") # Lowercase messages
                else:
                    st.warning("please enter an id to delete.") # Lowercase messages
    else:
        st.info("no exercise records found or api is unreachable.") # Lowercase messages
