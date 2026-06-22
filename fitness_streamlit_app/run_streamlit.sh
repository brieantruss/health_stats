#!/bin/bash
cd /home/modulo/fitness_streamlit_app # Replace with your app's actual directory
source fitness_streamlit_app/bin/activate  # Replace 'venv' if your virtual environment has a different name
streamlit run streamlit_app.py --server.port 8501 --server.enableCORS true --server.enableXsrfProtection false # Adjust app.py and port as needed

