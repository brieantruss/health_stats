# Fitness Tracker UI

Run the app with `streamlit run streamlit_app.py`. The app opens on the Exercise
page; use Streamlit's page navigation to switch between the separate Exercise
and Diet pages. Both pages share the same styling and header.

The Exercise page displays at most the 50 most recent exercise records. The API
orders and limits these records before returning them to the UI.
