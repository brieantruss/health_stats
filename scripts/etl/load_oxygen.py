import mysql.connector
import csv
import os
from datetime import datetime

# --- Database Configuration ---
# IMPORTANT: Replace with your actual MySQL database credentials
DB_CONFIG = {
    'host': 'your_mysql_host',
    'user': 'your_mysql_user',
    'password': 'your_mysql_password',
    'database': 'your_database_name'
}

# --- File Path Configuration ---
# Assuming the VO2 max CSV files are in this directory
# This should match the local_save_path from your previous script
VO2_MAX_FILES_DIR = '/home/***/development/health_stats/raw_files/vo2max'

# --- Table Schema Assumption ---
# This script assumes your 'oxygen' table has at least these columns:
# id INT PRIMARY KEY AUTO_INCREMENT,
# vo2_max DECIMAL(5,2),
# record_date DATE, # Or DATETIME if your CSV includes time
# last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP

def connect_db():
    """Establishes a connection to the MySQL database."""
    try:
        conn = mysql.connector.connect(**DB_CONFIG)
        print("Successfully connected to the database.")
        return conn
    except mysql.connector.Error as err:
        print(f"Error connecting to MySQL: {err}")
        return None

def create_oxygen_table_if_not_exists(cursor):
    """
    Creates the 'oxygen' table if it doesn't already exist.
    This is for demonstration/setup. In a production environment,
    you might manage schema migrations differently.
    """
    table_create_query = """
    CREATE TABLE IF NOT EXISTS oxygen (
        id INT AUTO_INCREMENT PRIMARY KEY,
        vo2_max DECIMAL(5,2) NOT NULL,
        record_date DATE NOT NULL,
        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
    );
    """
    try:
        cursor.execute(table_create_query)
        print("Table 'oxygen' ensured to exist.")
    except mysql.connector.Error as err:
        print(f"Error creating table: {err}")

def load_vo2_max_data(file_path, db_connection):
    """
    Loads VO2 max data from a CSV file into the 'oxygen' table.
    Assumes CSV format: VO2 max value, Date (e.g., '2025.07.27')
    Adjust column indices based on your actual CSV file structure.
    """
    cursor = db_connection.cursor()
    create_oxygen_table_if_not_exists(cursor) # Ensure table exists before inserting

    # SQL query to insert data. Note: 'last_updated' is omitted as it's auto-handled.
    insert_query = "INSERT INTO oxygen (vo2_max, record_date) VALUES (%s, %s)"
    update_query = """
    UPDATE oxygen
    SET vo2_max = %s
    WHERE record_date = %s;
    """
    # Query to check if a record for a given date already exists
    check_query = "SELECT COUNT(*) FROM oxygen WHERE record_date = %s"

    data_loaded_count = 0
    try:
        with open(file_path, 'r', newline='') as csvfile:
            reader = csv.reader(csvfile)
            # Assuming the first row is a header, skip it.
            # If your CSV has no header, remove this line.
            next(reader, None)

            for row in reader:
                try:
                    # Adjust these indices based on your CSV structure
                    # Example: if CSV is "VO2_VALUE,DATE"
                    vo2_max_str = row[0].strip() # Assuming VO2 max is in the first column
                    date_str = row[1].strip()   # Assuming Date is in the second column

                    vo2_max = float(vo2_max_str)
                    # Convert date string from 'YYYY.MM.DD' to 'YYYY-MM-DD' for MySQL DATE type
                    record_date = datetime.strptime(date_str, '%Y.%m.%d').strftime('%Y-%m-%d')

                    # Check if record for this date already exists
                    cursor.execute(check_query, (record_date,))
                    exists = cursor.fetchone()[0] > 0

                    if exists:
                        # Update existing record
                        cursor.execute(update_query, (vo2_max, record_date))
                        print(f"Updated VO2 max for {record_date}: {vo2_max}")
                    else:
                        # Insert new record
                        cursor.execute(insert_query, (vo2_max, record_date))
                        print(f"Inserted new VO2 max for {record_date}: {vo2_max}")

                    data_loaded_count += 1
                except (ValueError, IndexError) as e:
                    print(f"Skipping malformed row in {os.path.basename(file_path)}: {row}. Error: {e}")
                except mysql.connector.Error as err:
                    print(f"Database error inserting/updating row {row}: {err}")
                    # Decide whether to commit partial data or rollback on error
                    db_connection.rollback() # Rollback on error for this row
                    continue # Continue to next row

        db_connection.commit() # Commit all changes after processing the file
        print(f"Successfully processed {data_loaded_count} data entries from {os.path.basename(file_path)}.")

    except FileNotFoundError:
        print(f"Error: File not found at {file_path}")
    except Exception as e:
        print(f"An unexpected error occurred while loading data from {os.path.basename(file_path)}: {e}")
    finally:
        cursor.close()

if __name__ == '__main__':
    conn = connect_db()
    if conn:
        # Example: Iterate through all CSV files in the specified directory
        # You might want to get the latest downloaded file from the previous script
        # and pass its path here directly.
        for filename in os.listdir(VO2_MAX_FILES_DIR):
            if filename.startswith("VO2 max") and filename.endswith("Health Connect.csv"):
                full_file_path = os.path.join(VO2_MAX_FILES_DIR, filename)
                print(f"\n--- Loading data from {filename} ---")
                load_vo2_max_data(full_file_path, conn)
        conn.close()
        print("Database connection closed.")
    else:
        print("Could not establish database connection. Exiting.")
