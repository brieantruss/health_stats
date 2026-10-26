import streamlit as st


pages = [
    st.Page("pages/1_Exercise.py", title="Exercise", default=True),
    st.Page("pages/2_Diet.py", title="Diet"),
]
st.navigation(pages).run()
