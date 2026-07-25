#!/usr/bin/env python3
import sys
import mysql.connector
from datetime import datetime

# --- Configuration ---
MYSQL_CONFIG = {
    "host": "localhost",
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

def print_usage():
    print("================================================================================")
    print("🌟 SKILL 3: QUICK-LOG TERMINAL LOGGER")
    print("================================================================================")
    print("Usage:")
    print("  • Log water:  python3 quick_log.py water <amount_in_ml>")
    print("  • Log food:   python3 quick_log.py food \"<food_query>\" <amount_in_grams>")
    print("\nExamples:")
    print("  • python3 quick_log.py water 500")
    print("  • python3 quick_log.py food \"Banana, raw\" 120")
    print("================================================================================")

def log_water(amount_ml):
    try:
        amount = float(amount_ml)
    except ValueError:
        print("❌ Error: Water amount must be a number (in ml).")
        sys.exit(1)

    today_str = datetime.now().strftime('%Y-%m-%d')
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()
        
        insert_query = "INSERT INTO diet (item, date, grams, ml) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, ("Water", today_str, None, amount))
        conn.commit()
        
        print(f"✅ Success! Logged \033[94m{amount} ml of Water\033[0m for today ({today_str}).")
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"❌ Database error: {e}")

def log_food(food_query, amount_g):
    try:
        amount = float(amount_g)
    except ValueError:
        print("❌ Error: Food amount must be a number (in grams).")
        sys.exit(1)

    today_str = datetime.now().strftime('%Y-%m-%d')
    try:
        conn = mysql.connector.connect(**MYSQL_CONFIG)
        cursor = conn.cursor()

        # Try to find matching food in main_food_descriptions
        search_query = "SELECT main_food_description FROM main_food_descriptions WHERE main_food_description LIKE %s"
        cursor.execute(search_query, (f"%{food_query}%",))
        matches = [row[0] for row in cursor.fetchall()]

        if not matches:
            print(f"❌ Error: No foods found matching '{food_query}'. Try a different keyword.")
            cursor.close()
            conn.close()
            sys.exit(1)

        # Check for exact (case-insensitive) match
        exact_match = None
        for m in matches:
            if m.lower().strip() == food_query.lower().strip():
                exact_match = m
                break

        if exact_match:
            chosen_food = exact_match
        elif len(matches) == 1:
            chosen_food = matches[0]
        else:
            print(f"⚠️ Multiple matches found for '{food_query}'. Please use the exact name:")
            for m in matches[:10]:
                print(f"  • \"{m}\"")
            if len(matches) > 10:
                print(f"  ...and {len(matches) - 10} more.")
            cursor.close()
            conn.close()
            sys.exit(1)

        # Insert diet entry
        insert_query = "INSERT INTO diet (item, date, grams, ml) VALUES (%s, %s, %s, %s)"
        cursor.execute(insert_query, (chosen_food, today_str, amount, None))
        conn.commit()
        
        print(f"✅ Success! Logged \033[92m{amount}g of \"{chosen_food}\"\033[0m for today ({today_str}).")
        cursor.close()
        conn.close()

    except Exception as e:
        print(f"❌ Database error: {e}")

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print_usage()
        sys.exit(1)

    action = sys.argv[1].lower()
    if action == "water":
        log_water(sys.argv[2])
    elif action == "food":
        if len(sys.argv) < 4:
            print_usage()
            sys.exit(1)
        log_food(sys.argv[2], sys.argv[3])
    else:
        print_usage()
        sys.exit(1)
