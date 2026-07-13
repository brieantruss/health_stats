print("=========== api_app.py LOADED - VERSION CHECK ===========")
print(f"Query defined: SELECT ingredient_description FROM food_ingredients ORDER BY ingredient_description ASC")

# ~/fitness_api/api_app.py

from flask import Flask, request, jsonify
import mysql.connector
from datetime import datetime
import logging # Import logging module
import os
import time

app = Flask(__name__)

# Configure logging to show more details
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

FOOD_DESCRIPTIONS_CACHE = {
    "items": None,
    "loaded_at": 0,
}
FOOD_DESCRIPTIONS_TTL_SECONDS = 3600

# Database connection helper
def get_db_connection():
    return mysql.connector.connect(
        host=os.environ.get('MYSQL_HOST', 'localhost'),
        user=os.environ.get('MYSQL_USER', 'modulo'),
        password=os.environ.get('MYSQL_PASSWORD', 'modulo'),
        database=os.environ.get('MYSQL_DB', 'health_stats')
    )

def load_food_descriptions(force_refresh=False):
    now = time.time()
    cached_items = FOOD_DESCRIPTIONS_CACHE["items"]
    if not force_refresh and cached_items is not None and (now - FOOD_DESCRIPTIONS_CACHE["loaded_at"] < FOOD_DESCRIPTIONS_TTL_SECONDS):
        return cached_items

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            SELECT DISTINCT main_food_description
            FROM food_descriptions
            WHERE main_food_description IS NOT NULL
              AND main_food_description <> ''
            ORDER BY main_food_description ASC
        """
        logging.info("Executing query: SELECT DISTINCT main_food_description FROM food_descriptions ORDER BY main_food_description ASC")
        cursor.execute(query)
        food_descriptions = [row[0] for row in cursor.fetchall()]
        FOOD_DESCRIPTIONS_CACHE["items"] = food_descriptions
        FOOD_DESCRIPTIONS_CACHE["loaded_at"] = now
        logging.info(f"Successfully fetched {len(food_descriptions)} food descriptions.")
        return food_descriptions
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

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
    conn = get_db_connection()
    cursor = conn.cursor()
    exercise_filter = request.args.get('exercise')

    if exercise_filter:
        if exercise_filter not in ALLOWED_EXERCISES:
            cursor.close()
            conn.close()
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
    conn.close()
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

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        query = """
            INSERT INTO exercises (exercise, record_date, reps, duration, resistance_kg)
            VALUES (%s, %s, %s, %s, %s)
        """
        cursor.execute(query, (exercise, record_date, reps, duration, resistance_kg))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({"message": "Exercise added successfully", "id": new_id}), 201
    except Exception as e:
        if conn:
            conn.rollback() # Rollback in case of error
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/exercises/<int:exercise_id>', methods=['DELETE'])
def delete_exercise(exercise_id):
    """
    Deletes an exercise record by ID.
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM exercises WHERE id = %s", (exercise_id,))
    conn.commit()
    rows_affected = cursor.rowcount
    cursor.close()
    conn.close()

    if rows_affected == 0:
        return jsonify({"message": "No exercise found with that ID"}), 404
    return jsonify({"message": "Exercise deleted successfully"}), 200

# --- New Diet Endpoints ---

@app.route('/food_descriptions', methods=['GET'])
def get_food_descriptions():
    """
    Retrieves all food descriptions from the cached food_descriptions table source.
    """
    try:
        food_descriptions = load_food_descriptions()
        return jsonify(food_descriptions)
    except Exception as e:
        logging.error(f"Error fetching food descriptions: {e}", exc_info=True) # Log full exception info
        return jsonify({"error": str(e)}), 500

@app.route('/diet', methods=['POST'])
def add_diet_record():
    """
    Adds a new diet record.
    Expected JSON:
    {
        "item": "Apple",
        "record_date": "2023-10-26",
        "grams": 150.0,
        "ml": null
    }
    """
    data = request.get_json()

    item = data.get('item')
    record_date_str = data.get('record_date')
    grams = data.get('grams')
    ml = data.get('ml')

    if not item or not record_date_str:
        return jsonify({"error": "Missing required fields: item and record_date"}), 400

    try:
        record_date = datetime.strptime(record_date_str, '%Y-%m-%d').date()
    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        valid_food_items = set(load_food_descriptions())
        if item not in valid_food_items:
            cursor.close()
            conn.close()
            return jsonify({"error": f"Invalid food item: '{item}'. Please select from available descriptions."}), 400

        query = """
            INSERT INTO diet (item, date, grams, ml)
            VALUES (%s, %s, %s, %s)
        """
        cursor.execute(query, (item, record_date, grams, ml))
        conn.commit()
        new_id = cursor.lastrowid
        return jsonify({"message": "Diet record added successfully", "id": new_id}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/diet', methods=['GET'])
def get_diet_records():
    """
    Retrieves diet records from the database.
    Can be filtered by item: /diet?item=Banana
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        item_filter = request.args.get('item')

        if item_filter and item_filter != 'All':
            query = "SELECT id, item, date, grams, ml FROM diet WHERE item = %s ORDER BY date DESC, id DESC"
            cursor.execute(query, (item_filter,))
        else:
            query = "SELECT id, item, date, grams, ml FROM diet ORDER BY date DESC, id DESC"
            cursor.execute(query)

        data = []
        for row in cursor.fetchall():
            data.append({
                'id': row[0],
                'item': row[1],
                'record_date': row[2].strftime('%Y-%m-%d') if row[2] else None,
                'grams': float(row[3]) if row[3] is not None else None,
                'ml': float(row[4]) if row[4] is not None else None,
            })
        return jsonify(data)
    except Exception as e:
        logging.error(f"Error fetching diet records: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

@app.route('/diet/<int:diet_id>', methods=['DELETE'])
def delete_diet_record(diet_id):
    """
    Deletes a diet record by ID.
    """
    conn = None
    cursor = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM diet WHERE id = %s", (diet_id,))
        conn.commit()
        rows_affected = cursor.rowcount

        if rows_affected == 0:
            return jsonify({"message": "No diet record found with that ID"}), 404
        return jsonify({"message": "Diet record deleted successfully"}), 200
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"Error deleting diet record: {e}", exc_info=True)
        return jsonify({"error": str(e)}), 500
    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()

if __name__ == '__main__':
    # Run on all available network interfaces on port 5000
    # THIS IS FOR DEVELOPMENT. For production, use a WSGI server like Gunicorn.
    app.run(host='0.0.0.0', port=5001) # Changed port to 5001
