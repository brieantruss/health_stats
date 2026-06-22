print("=========== api_app.py LOADED - VERSION CHECK ===========")
print(f"Query defined: SELECT ingredient_description FROM food_ingredients ORDER BY ingredient_description ASC")

# ~/fitness_api/api_app.py

from flask import Flask, request, jsonify
from flask_mysqldb import MySQL
from datetime import datetime
import logging # Import logging module
import os

app = Flask(__name__)

# Configure logging to show more details
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# MySQL Configurations (supports environment variables for secure/flexible deployment)
app.config['MYSQL_HOST'] = os.environ.get('MYSQL_HOST', 'localhost')
app.config['MYSQL_USER'] = os.environ.get('MYSQL_USER', 'modulo')
app.config['MYSQL_PASSWORD'] = os.environ.get('MYSQL_PASSWORD', 'modulo')
app.config['MYSQL_DB'] = os.environ.get('MYSQL_DB', 'health_stats')

mysql = MySQL(app)

# Allowed exercises for input validation (existing)
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

@app.route('/')
def home():
    return "Fitness API is running! Use /exercises or /diet endpoints."

# --- Existing Exercise Endpoints ---

@app.route('/exercises', methods=['GET'])
def get_exercises():
    """
    Retrieves all exercises from the database.
    Can be filtered by exercise type: /exercises?exercise=push_ups
    """
    cursor = mysql.connection.cursor()
    exercise_filter = request.args.get('exercise')

    if exercise_filter:
        if exercise_filter not in ALLOWED_EXERCISES:
            return jsonify({"error": f"Invalid exercise type. Allowed are: {', '.join(ALLOWED_EXERCISES)}"}), 400
        query = "SELECT id, exercise, record_date, reps, duration, resistance_kg FROM exercises WHERE exercise = %s ORDER BY record_date DESC, id DESC"
        cursor.execute(query, (exercise_filter,))
    else:
        query = "SELECT id, exercise, record_date, reps, duration, resistance_kg FROM exercises ORDER BY record_date DESC, id DESC"
        cursor.execute(query)

    data = []
    for row in cursor.fetchall():
        data.append({
            'id': row[0],
            'exercise': row[1],
            'record_date': row[2].strftime('%Y-%m-%d'), # Format date for JSON
            'reps': row[3],
            'duration': float(row[4]) if row[4] is not None else None,
            'resistance_kg': float(row[5]) if row[5] is not None else None
        })
    cursor.close()
    return jsonify(data)

@app.route('/exercises', methods=['POST'])
def add_exercise():
    """
    Adds a new exercise record.
    Expected JSON:
    {
        "exercise": "push_ups",
        "record_date": "2023-10-26",
        "reps": 20,
        "duration": 60.5,
        "resistance_kg": 0.0
    }
    'reps', 'duration', 'resistance_kg' are optional but must be valid types if provided.
    """
    data = request.get_json()

    # Basic validation
    exercise = data.get('exercise')
    record_date_str = data.get('record_date')
    reps = data.get('reps')
    duration = data.get('duration')
    resistance_kg = data.get('resistance_kg')

    if not exercise or not record_date_str:
        return jsonify({"error": "Missing required fields: exercise and record_date"}), 400

    if exercise not in ALLOWED_EXERCISES:
        return jsonify({"error": f"Invalid exercise type. Allowed are: {', '.join(ALLOWED_EXERCISES)}"}), 400

    try:
        # Validate date format
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    # Type validation for optional fields
    if reps is not None and not isinstance(reps, int):
        return jsonify({"error": "Reps must be an integer"}), 400
    if duration is not None and not (isinstance(duration, (float, int)) and duration >= 0):
        return jsonify({"error": "Duration must be a non-negative decimal"}), 400
    if resistance_kg is not None and not (isinstance(resistance_kg, (float, int)) and resistance_kg >= 0):
        return jsonify({"error": "Resistance_kg must be a non-negative decimal"}), 400

    try:
        cursor = mysql.connection.cursor()
        query = """
            INSERT INTO exercises (exercise, record_date, reps, duration, resistance_kg)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (exercise, record_date, reps, duration, resistance_kg))
        mysql.connection.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return jsonify({"message": "Exercise added successfully", "id": new_id}), 201
    except Exception as e:
        mysql.connection.rollback() # Rollback in case of error
        return jsonify({"error": str(e)}), 500

@app.route('/exercises/<int:exercise_id>', methods=['DELETE'])
def delete_exercise(exercise_id):
    """
    Deletes an exercise record by ID.
    """
    cursor = mysql.connection.cursor()
    cursor.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))
    mysql.connection.commit()
    rows_affected = cursor.rowcount
    cursor.close()

    if rows_affected == 0:
        return jsonify({"message": "No exercise found with that ID"}), 404
    return jsonify({"message": "Exercise deleted successfully"}), 200

# --- New Diet Endpoints ---

@app.route('/food_descriptions', methods=['GET'])
def get_food_descriptions():
    """
    Retrieves all food descriptions from the food_ingredients table.
    """
    cursor = None # Initialize cursor to None
    try:
        cursor = mysql.connection.cursor()
        # Corrected column name to 'main_food_description'
        query = "SELECT distinct ingredient_description FROM food_ingredients ORDER BY ingredient_description ASC"
        logging.info(f"Executing query: {query}") # Log the query
        cursor.execute(query)
        food_descriptions = [row[0] for row in cursor.fetchall()]
        logging.info(f"Successfully fetched {len(food_descriptions)} food descriptions.")
        return jsonify(food_descriptions)
    except Exception as e:
        logging.error(f"Error fetching food descriptions: {e}", exc_info=True) # Log full exception info
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor: # Ensure cursor is closed even if an error occurs
            cursor.close()

@app.route('/diet', methods=['POST'])
def add_diet_record():
    """
    Adds a new diet record.
    Expected JSON:
    {
        "item": "Apple",
        "record_date": "2023-10-26"
    }
    """
    data = request.get_json()

    item = data.get('item')
    record_date_str = data.get('record_date')

    if not item or not record_date_str:
        return jsonify({"error": "Missing required fields: item and record_date"}), 400

    try:
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    try:
        cursor = mysql.connection.cursor()
        # Optional: Validate if the item exists in food_ingredients
        cursor.execute("SELECT COUNT(*) FROM food_ingredients WHERE ingredient_description = %s", (item,))
        if cursor.fetchone()[0] == 0:
            return jsonify({"error": f"Invalid food item: '{item}'. Please select from available descriptions."}), 400

        query = """
            INSERT INTO diet (item, date)
            VALUES (%s, %s)
        """
        cursor.execute(query, (item, record_date))
        mysql.connection.commit()
        new_id = cursor.lastrowid
        cursor.close()
        return jsonify({"message": "Diet record added successfully", "id": new_id}), 201
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Run on all available network interfaces on port 5000
    # THIS IS FOR DEVELOPMENT. For production, use a WSGI server like Gunicorn.
    app.run(host='0.0.0.0', port=5001) # Changed port to 5001
