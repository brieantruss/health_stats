import os
import csv
import mysql.connector
import sys # Import sys for command-line arguments

# MySQL connection details
db_config = {
    "host": "localhost", # Assuming MySQL is on the same RPi5 as Airflow
    "user": "modulo",
    "password": "modulo",
    "database": "health_stats"
}

# Table name in your MySQL database
table_name = "walking"

def load_single_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single CSV file into the specified MySQL table ('walking').
    Assumes the CSV header matches the schema from the previous step.
    """
    cnx = None
    cursor = None

    print(f"Attempting to load data from: {file_path}")

    try:
        cnx = mysql.connector.connect(
            host=db_config["host"],
            user=db_config["user"],
            password=db_config["password"],
            database=db_config["database"]
        )
        cursor = cnx.cursor()

        with open(file_path, 'r', newline='', encoding='utf-8') as csv_file:
            csv_reader = csv.reader(csv_file)
            # Read and verify the header row before skipping
            header = next(csv_reader)
            
            # The CSV file has 14 original columns + 1 'last_updated' = 15 total fields.
            # Your INSERT statement uses 14 of them (skipping 'Source app').
            required_columns = 15 

            # Define the SQL INSERT statement matching the 'walking' table schema
            sql = f"""
            INSERT INTO {table_name} (
            activity_type,
            activity_name,
            Date,
            Time,
            elapsed_time,
            active_time,
            distance_miles,
            calories_kcal,
            Steps,
            average_heart_rate,
            max_heart_rate,
            average_speed,
            max_speed,
            last_updated 
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            data_to_insert = []
            for row_num, row in enumerate(csv_reader, start=2):
                
                # Check for the correct number of columns
                if len(row) < required_columns:
                    print(f"Skipping malformed row {row_num} in {os.path.basename(file_path)} (too few columns, expected {required_columns}): {row}")
                    continue

                try:
                    # --- CRITICAL FIX: CORRECTED INDICES TO MATCH CSV FILE ---
                    # CSV Index 0: 'Source app' (Skipped, not in SQL schema)
                    
                    # CSV Index 1 -> SQL activity_type
                    activity_type = row[1]
                    # CSV Index 2 -> SQL activity_name
                    activity_name = row[2]
                    # CSV Index 3 -> SQL Date
                    activity_date = row[3] 
                    # CSV Index 4 -> SQL Time (string, no conversion)
                    activity_time = row[4] 

                    # CSV Index 5 -> SQL elapsed_time (Fix: was incorrectly row[4])
                    # Ensure conversion logic is applied to the correct field
                    elapsed_time_seconds = int(float(row[5])) if row[5] else None
                    
                    # CSV Index 6 -> SQL active_time (Fix: was incorrectly row[5])
                    active_time_seconds = int(float(row[6])) if row[6] else None
                    
                    # CSV Index 7 -> SQL distance_miles (Fix: was incorrectly row[6])
                    distance_miles = float(row[7]) if row[7] else None
                    
                    # CSV Index 8 -> SQL calories_kcal (Fix: was incorrectly row[7])
                    calories_kcal = float(row[8]) if row[8] else None
                    
                    # CSV Index 9 -> SQL Steps (Fix: was incorrectly row[8])
                    steps = int(row[9]) if row[9] else None
                    
                    # CSV Index 10 -> SQL average_heart_rate (Fix: was incorrectly row[9])
                    avg_heart_rate = int(row[10]) if row[10] else None
                    
                    # CSV Index 11 -> SQL max_heart_rate (Fix: was incorrectly row[10])
                    max_heart_rate = int(row[11]) if row[11] else None
                    
                    # CSV Index 12 -> SQL average_speed (Fix: was incorrectly row[11])
                    avg_speed = float(row[12]) if row[12] else None
                    
                    # CSV Index 13 -> SQL max_speed (Fix: was incorrectly row[12])
                    max_speed = float(row[13]) if row[13] else None
                    
                    # CSV Index 14 -> SQL last_updated (Fix: was incorrectly row[13])
                    last_updated = row[14]

                    data_to_insert.append((
                        activity_type,
                        activity_name,
                        activity_date,
                        activity_time,
                        elapsed_time_seconds,
                        active_time_seconds,
                        distance_miles,
                        calories_kcal,
                        steps,
                        avg_heart_rate,
                        max_heart_rate,
                        avg_speed,
                        max_speed,
                        last_updated
                    ))

                except ValueError as e:
                    print(f"Skipping row {row_num} in {os.path.basename(file_path)} due to data conversion error: {e}. Row: {row}")
                except IndexError as e:
                    print(f"Skipping row {row_num} in {os.path.basename(file_path)} due to index error (missing data): {e}. Row: {row}")
                except Exception as e:
                    print(f"An unexpected error occurred processing row {row_num} in {os.path.basename(file_path)}: {e}. Row: {row}")

            if data_to_insert:
                cursor.executemany(sql, data_to_insert)
                cnx.commit()
                print(f"{cursor.rowcount} records inserted successfully from {os.path.basename(file_path)} into {table_name}")
            else:
                print(f"No valid data found in {os.path.basename(file_path)} to insert after processing.")

    except mysql.connector.Error as err:
        print(f"MySQL Connector Error for {os.path.basename(file_path)}: {err}")
    except FileNotFoundError:
        print(f"Error: CSV file not found at {file_path}. Please check the path.")
    except Exception as e:
        print(f"An unexpected error occurred while processing {os.path.basename(file_path)}: {e}")
    finally:
        if cursor:
            cursor.close()
        if cnx and cnx.is_connected():
            cnx.close()
        elif cnx:
            print("MySQL connection was not successfully established or was already closed for this file.")


if __name__ == "__main__":
    # Expecting one argument: the base directory for processed files
    if len(sys.argv) != 2:
        print("Usage: python3 load_walking_data.py <processed_files_base_directory>")
        sys.exit(1)

    processed_files_base_dir = sys.argv[1]

    # Ensure the base directory exists
    if not os.path.isdir(processed_files_base_dir):
        print(f"Error: Processed files directory not found: {processed_files_base_dir}")
        sys.exit(1)

    files_found = False
    for filename in os.listdir(processed_files_base_dir):
        # Changed to look for "WALKING*.csv" files
        if filename.startswith("WALKING") and filename.endswith(".csv"):
            full_file_path = os.path.join(processed_files_base_dir, filename)
            load_single_csv_to_mysql(db_config, full_file_path, table_name)
            files_found = True

    if not files_found:
        print(f"No walking CSV files (e.g., 'WALKING*.csv') found in {processed_files_base_dir} to load.")
