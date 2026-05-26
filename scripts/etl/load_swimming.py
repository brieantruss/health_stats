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
table_name = "swimming" # Changed to swimming as per request

def load_single_csv_to_mysql(db_config, file_path, table_name):
    """
    Loads data from a single CSV file into the specified MySQL table ('swimming').
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
            header = next(csv_reader) # Skip the header row

            # Define the SQL INSERT statement matching the 'swimming' table schema
            sql = f"""
            INSERT INTO {table_name} (
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
                max_speed
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            """

            data_to_insert = []
            for row_num, row in enumerate(csv_reader, start=2): # Start counting from line 2 for errors
                # Ensure row has enough columns based on the CSV header (13 columns)
                if len(row) < 13:
                    print(f"Skipping malformed row {row_num} in {os.path.basename(file_path)} (too few columns): {row}")
                    continue

                try:
                    # Extract and convert data according to the 'swimming' table schema
                    activity_type = row[0]
                    activity_name = row[1]
                    activity_date = row[2] # Kept as VARCHAR(50)
                    activity_time = row[3] # Kept as VARCHAR(50)

                    # Safely convert numeric fields, defaulting to None if conversion fails
                    elapsed_time_seconds = int(float(row[4])) if row[4] else None
                    active_time_seconds = int(float(row[5])) if row[5] else None
                    distance_miles = float(row[6]) if row[6] else None
                    calories_kcal = float(row[7]) if row[7] else None
                    steps = int(row[8]) if row[8] else None
                    avg_heart_rate = int(row[9]) if row[9] else None
                    max_heart_rate = int(row[10]) if row[10] else None
                    avg_speed = float(row[11]) if row[11] else None
                    max_speed = float(row[12]) if row[12] else None

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
                        max_speed
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
        print("Usage: python3 load_swimming_data.py <processed_files_base_directory>")
        sys.exit(1)

    processed_files_base_dir = sys.argv[1]

    # Ensure the base directory exists
    if not os.path.isdir(processed_files_base_dir):
        print(f"Error: Processed files directory not found: {processed_files_base_dir}")
        sys.exit(1)

    files_found = False
    for filename in os.listdir(processed_files_base_dir):
        # Changed to look for "SWIMMING*.csv" files
        if filename.startswith("SWIMMING") and filename.endswith(".csv"):
            full_file_path = os.path.join(processed_files_base_dir, filename)
            load_single_csv_to_mysql(db_config, full_file_path, table_name)
            files_found = True

    if not files_found:
        print(f"No swimming CSV files (e.g., 'SWIMMING*.csv') found in {processed_files_base_dir} to load.")
