# scripts/etl/drive_config.py

# Configuration of Google Drive Folder IDs for extraction scripts.
# Migrated to folders on the btruss@moduloinsights.com Google account.

FOLDER_BLOOD_PRESSURE = '1TKu8AeVUnrhW_6PaSGi6womCDbWAlLGb'
FOLDER_HEART_RATE = '1xx_FFcTqKdG4QS-cJqamFt0LTnD0ATuH'
FOLDER_OXYGEN = '1X6BX7SNdxxvs81-qJ2ALl3DU3EeD-xEL'
FOLDER_STEPS = '1KO2gm2B1W64DbMxF5m8j_vp6YHfsuzAD'

# Sleep uses multiple folder IDs (list)
FOLDER_SLEEP_IDS = [
    '1Hfqkt3x9ewE3TWlFndcrEuQ2ll6N8CMH',  # New Folder on btruss@moduloinsights.com
    '122phx23TZI52gKoJDoT28zuaR5Ah9Bpm'   # Current Folder fallback (Sleep Folder 2)
]

FOLDER_VO2MAX = '1HHoijUL5ma8xQc6z-W4Ty9fRbPVA2ilM'

# Workouts (Cycling, Running, Swimming, Walking, Shootaround all share this folder)
FOLDER_WORKOUTS = '1qQVSZ5-V_HSru2QrNbuCC_XpFPb8v1bp'

# Locations (GPS Logger)
FOLDER_LOCATIONS = '1ZZ9u1hxaSbN5zy-pBhnF7tNl2-KtjnFr'
