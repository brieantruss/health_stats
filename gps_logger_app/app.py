# app.py
from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime

app = Flask(__name__)

# --- Configuration ---
# Supports environment variables for secure/flexible deployment
import os
DB_CONFIG = {
    'host': os.environ.get('MYSQL_HOST', 'localhost'),
    'user': os.environ.get('MYSQL_USER', 'modulo'),
    'password': os.environ.get('MYSQL_PASSWORD', 'modulo'),
    'database': os.environ.get('MYSQL_DB', 'health_stats')
}
# -------------------

def insert_location_data(latitude, longitude):
    conn = None
    cursor = None
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        cursor = conn.cursor()
        sql = "INSERT INTO location_log (latitude, longitude, timestamp) VALUES (%s, %s, %s)"
        data = (latitude, longitude, datetime.now())
        cursor.execute(sql, data)
        conn.commit()
        print(f"Inserted: Lat={latitude}, Lon={longitude} at {datetime.now()}")
        return True
    except mysql.connector.Error as err:
        print(f"Error inserting data: {err}")
        return False
    finally:
        if cursor:
            cursor.close()
        if conn and conn.is_connected():
            conn.close()

@app.route('/gps_data', methods=['POST'])
def receive_gps_data():
    if not request.is_json:
        return jsonify({"status": "error", "message": "Request must be JSON"}), 400

    data = request.get_json()
    latitude = data.get('latitude')
    longitude = data.get('longitude')

    if latitude is None or longitude is None:
        return jsonify({"status": "error", "message": "Missing latitude or longitude in JSON"}), 400

    try:
        # Attempt to convert to float to catch invalid values
        latitude = float(latitude)
        longitude = float(longitude)
    except ValueError:
        return jsonify({"status": "error", "message": "Latitude or longitude is not a valid number"}), 400

    if insert_location_data(latitude, longitude):
        return jsonify({"status": "success", "message": "Location data received and stored"}), 200
    else:
        return jsonify({"status": "error", "message": "Failed to store data in database"}), 500

if __name__ == '__main__':
    # For development/testing: run directly
    # In production, use Gunicorn or similar (see Part 3, Step 1)
    app.run(host='0.0.0.0', port=5000, debug=True)
