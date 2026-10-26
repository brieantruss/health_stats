from datetime import date

import pandas as pd
import streamlit as st

from common import (
    ALLOWED_EXERCISES,
    add_exercise_type,
    add_new_exercise,
    configure_page,
    delete_existing_exercise,
    get_all_exercises,
    get_exercise_types,
    normalize_exercise_type,
)


configure_page("Exercise")
st.markdown("<h1>exercise</h1>", unsafe_allow_html=True)

exercise_types = get_exercise_types()
exercise_options = exercise_types or ALLOWED_EXERCISES

with st.container(border=True):
    st.markdown("<h2>add exercise type</h2>", unsafe_allow_html=True)
    with st.form("add_exercise_type_form"):
        exercise_type_input = st.text_input(
            "Exercise name", placeholder="e.g. Incline Press"
        )
        exercise_type_key = normalize_exercise_type(exercise_type_input)
        if exercise_type_key:
            st.caption(f"Added as: {exercise_type_key}")
        add_type_submitted = st.form_submit_button("add exercise type")
        if add_type_submitted:
            if not exercise_type_key or len(exercise_type_key) > 100:
                st.error(
                    "Enter an exercise name containing up to 100 letters or numbers."
                )
            else:
                result, status = add_exercise_type(exercise_type_input)
                if status in (200, 201):
                    get_exercise_types.clear()
                    st.success(f"Exercise type ready: {result['name']}")
                    st.rerun()
                else:
                    st.error(
                        f"Could not add exercise type: "
                        f"{result.get('error', 'unknown error')}"
                    )

with st.container(border=True):
    st.markdown("<h2>add new exercise record</h2>", unsafe_allow_html=True)
    with st.form("add_exercise_form"):
        col_ex1, col_ex2, col_ex3 = st.columns(3)
        with col_ex1:
            selected_exercise = st.selectbox(
                "Exercise Type",
                exercise_options,
                key="add_exercise_type",
                help="Type to search for an exercise or select from the dropdown.",
            )
        with col_ex2:
            record_date = st.date_input(
                "Date", value=date.today(), key="add_exercise_date"
            )
        with col_ex3:
            reps_input = st.number_input(
                "Reps (optional)", min_value=1, step=1, value=None, key="add_reps"
            )

        col_ex4, col_ex5 = st.columns(2)
        with col_ex4:
            duration_input = st.number_input(
                "Duration (minutes, optional)",
                min_value=0.0,
                step=0.1,
                value=None,
                format="%.2f",
                key="add_duration",
            )
        with col_ex5:
            resistance_input = st.number_input(
                "Resistance (kg, optional)",
                min_value=0.0,
                step=0.1,
                value=None,
                format="%.2f",
                key="add_resistance",
            )

        submitted = st.form_submit_button("add exercise record")
        if submitted:
            new_record = {
                "exercise": selected_exercise,
                "record_date": record_date.strftime("%Y-%m-%d"),
                "reps": reps_input if reps_input is not None else None,
                "duration": (
                    float(duration_input) if duration_input is not None else None
                ),
                "resistance_kg": (
                    float(resistance_input) if resistance_input is not None else None
                ),
            }
            message, status = add_new_exercise(new_record)
            if status == 201:
                st.success(
                    f"exercise record added: {message.get('message')}. "
                    f"id: {message.get('id')}"
                )
                get_all_exercises.clear()
                st.rerun()
            else:
                st.error(
                    f"failed to add exercise record: "
                    f"{message.get('error', 'unknown error')}"
                )

with st.container(border=True):
    st.markdown(
        "<h2>view &amp; manage exercise records</h2>", unsafe_allow_html=True
    )
    st.caption("Showing up to the 50 most recent exercise records.")
    filter_exercise_type = st.selectbox(
        "Filter by Exercise Type",
        ["All"] + exercise_options,
        key="filter_exercise_type",
        help="Type to search for an exercise or select from the dropdown to filter records.",
    )
    exercises_data = get_all_exercises(filter_exercise_type)

    if exercises_data:
        df = pd.DataFrame(exercises_data)
        df["record_date"] = pd.to_datetime(df["record_date"])
        cols_order = ["id", "exercise", "record_date"] + [
            col
            for col in df.columns
            if col not in ["id", "exercise", "record_date"]
        ]
        df = df[[col for col in cols_order if col in df.columns]]
        st.dataframe(df.set_index("id"), width="stretch")

        st.markdown("<h3>delete exercise record by id</h3>", unsafe_allow_html=True)
        col_del1, col_del2 = st.columns([0.7, 0.3])
        with col_del1:
            delete_id = st.number_input(
                "Enter ID to delete",
                min_value=1,
                step=1,
                value=None,
                key="delete_id",
                placeholder="e.g., 5",
            )
        with col_del2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("delete selected exercise record"):
                if delete_id:
                    message, status = delete_existing_exercise(int(delete_id))
                    if status == 200:
                        st.success(
                            f"exercise record deleted: {message.get('message')}"
                        )
                        get_all_exercises.clear()
                        st.rerun()
                    elif status == 404:
                        st.warning(f"no exercise record found with id: {delete_id}")
                    else:
                        st.error(
                            f"failed to delete exercise record: "
                            f"{message.get('error', 'unknown error')}"
                        )
                else:
                    st.warning("please enter an id to delete.")
    else:
        st.info("no exercise records found or api is unreachable.")
