from datetime import date

import pandas as pd
import streamlit as st

from common import (
    add_new_diet_record,
    configure_page,
    delete_existing_diet_record,
    get_all_diet_records,
    get_food_descriptions,
)


configure_page("Diet")
st.markdown("<h1>diet</h1>", unsafe_allow_html=True)

with st.container(border=True):
    st.markdown("<h2>add new diet record</h2>", unsafe_allow_html=True)
    with st.form("add_diet_form"):
        food_descriptions = get_food_descriptions()
        col_diet1, col_diet2 = st.columns(2)
        with col_diet1:
            if food_descriptions:
                selected_item = st.selectbox(
                    "Item",
                    food_descriptions,
                    key="add_diet_item",
                    help="Type to search for a food item or select from the dropdown.",
                )
            else:
                st.warning(
                    "could not load food descriptions. please ensure your api is "
                    "running and the food_ingredients table has data."
                )
                selected_item = None

        with col_diet2:
            diet_record_date = st.date_input(
                "Date", value=date.today(), key="add_diet_date"
            )

        col_diet3, col_diet4 = st.columns(2)
        with col_diet3:
            grams_input = st.number_input(
                "Grams (optional)",
                min_value=0.0,
                step=0.1,
                value=None,
                format="%.3f",
                key="add_diet_grams",
            )
        with col_diet4:
            ml_input = st.number_input(
                "ML (optional)",
                min_value=0.0,
                step=0.1,
                value=None,
                format="%.3f",
                key="add_diet_ml",
            )

        diet_submitted = st.form_submit_button("add diet record")
        if diet_submitted:
            if selected_item:
                new_diet_record = {
                    "item": selected_item,
                    "record_date": diet_record_date.strftime("%Y-%m-%d"),
                    "grams": float(grams_input) if grams_input is not None else None,
                    "ml": float(ml_input) if ml_input is not None else None,
                }
                message, status = add_new_diet_record(new_diet_record)
                if status == 201:
                    st.success(
                        f"diet record added: {message.get('message')}. "
                        f"id: {message.get('id')}"
                    )
                    get_all_diet_records.clear()
                    st.rerun()
                else:
                    st.error(
                        f"failed to add diet record: "
                        f"{message.get('error', 'unknown error')}"
                    )
            else:
                st.error("cannot add diet record: no food item selected or loaded.")

with st.container(border=True):
    st.markdown(
        "<h2>view &amp; manage diet records</h2>", unsafe_allow_html=True
    )
    diet_filter_options = ["All"] + get_food_descriptions()
    filter_diet_item = st.selectbox(
        "Filter by Food Item",
        diet_filter_options,
        key="filter_diet_item",
        help="Type to search for a food item or select from the dropdown to filter records.",
    )
    diet_data = get_all_diet_records(filter_diet_item)

    if diet_data:
        diet_df = pd.DataFrame(diet_data)
        diet_df["record_date"] = pd.to_datetime(diet_df["record_date"])
        cols_order = ["id", "item", "record_date"] + [
            col for col in diet_df.columns if col not in ["id", "item", "record_date"]
        ]
        diet_df = diet_df[[col for col in cols_order if col in diet_df.columns]]
        st.dataframe(diet_df.set_index("id"), width="stretch")

        st.markdown("<h3>delete diet record by id</h3>", unsafe_allow_html=True)
        diet_del1, diet_del2 = st.columns([0.7, 0.3])
        with diet_del1:
            delete_diet_id = st.number_input(
                "Enter Diet ID to delete",
                min_value=1,
                step=1,
                value=None,
                key="delete_diet_id",
                placeholder="e.g., 5",
            )
        with diet_del2:
            st.markdown("<br>", unsafe_allow_html=True)
            if st.button("delete selected diet record"):
                if delete_diet_id:
                    message, status = delete_existing_diet_record(int(delete_diet_id))
                    if status == 200:
                        st.success(f"diet record deleted: {message.get('message')}")
                        get_all_diet_records.clear()
                        st.rerun()
                    elif status == 404:
                        st.warning(f"no diet record found with id: {delete_diet_id}")
                    else:
                        st.error(
                            f"failed to delete diet record: "
                            f"{message.get('error', 'unknown error')}"
                        )
                else:
                    st.warning("please enter an id to delete.")
    else:
        st.info("no diet records found or api is unreachable.")
