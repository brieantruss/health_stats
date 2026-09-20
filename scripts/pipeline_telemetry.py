import os
from datetime import datetime
from typing import Dict, Any, List, Optional
import sqlite3
import json

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
PROCESSED_DIR = os.path.join(REPO_ROOT, "processed_files")
RAW_DIR = os.path.join(REPO_ROOT, "raw_files")
DB_PATH = os.path.join(REPO_ROOT, "health_events.db")

KNOWN_CATEGORIES = [
    "blood_pressure",
    "cycling",
    "heart_rate",
    "locations",
    "oxygen",
    "running",
    "shootaround",
    "sleep",
    "steps",
    "swimming",
    "vo2max",
    "walking",
    "weather",
]

def format_file_size(size_bytes: int) -> str:
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes / 1024:.1f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes / (1024 * 1024):.1f} MB"
    return f"{size_bytes / (1024 * 1024 * 1024):.2f} GB"

def get_category_telemetry(category: str) -> Dict[str, Any]:
    cat_dir = os.path.join(PROCESSED_DIR, category)
    raw_cat_dir = os.path.join(RAW_DIR, category)
    
    total_files = 0
    total_size_bytes = 0
    latest_filename: Optional[str] = None
    latest_mtime: Optional[float] = None
    latest_size_bytes: Optional[int] = None
    
    # Check processed directory
    if os.path.exists(cat_dir) and os.path.isdir(cat_dir):
        try:
            entries = [os.path.join(cat_dir, f) for f in os.listdir(cat_dir) if not f.startswith('.')]
            for entry in entries:
                if os.path.isfile(entry):
                    total_files += 1
                    try:
                        stat = os.stat(entry)
                        total_size_bytes += stat.st_size
                        if latest_mtime is None or stat.st_mtime > latest_mtime:
                            latest_mtime = stat.st_mtime
                            latest_filename = os.path.basename(entry)
                            latest_size_bytes = stat.st_size
                    except OSError:
                        pass
        except Exception as e:
            print(f"Error reading category {category}: {e}")

    # Check pending files in raw folder
    pending_raw_count = 0
    if os.path.exists(raw_cat_dir) and os.path.isdir(raw_cat_dir):
        try:
            pending_raw_count = len([f for f in os.listdir(raw_cat_dir) if not f.startswith('.') and os.path.isfile(os.path.join(raw_cat_dir, f))])
        except OSError:
            pass

    latest_iso = datetime.fromtimestamp(latest_mtime).isoformat() if latest_mtime else None

    return {
        "category": category,
        "totalFiles": total_files,
        "pendingRawFiles": pending_raw_count,
        "totalSizeBytes": total_size_bytes,
        "totalSizeFormatted": format_file_size(total_size_bytes),
        "latestFileName": latest_filename,
        "latestFileModifiedAt": latest_iso,
        "latestFileSizeBytes": latest_size_bytes,
        "latestFileSizeFormatted": format_file_size(latest_size_bytes) if latest_size_bytes is not None else None,
        "status": "active" if total_files > 0 else "idle",
    }

def get_all_categories_telemetry() -> Dict[str, Any]:
    categories_data = {}
    grand_total_files = 0
    grand_total_size = 0
    grand_latest_mtime: Optional[str] = None
    grand_latest_category: Optional[str] = None
    grand_latest_filename: Optional[str] = None

    for cat in KNOWN_CATEGORIES:
        data = get_category_telemetry(cat)
        categories_data[cat] = data
        grand_total_files += data["totalFiles"]
        grand_total_size += data["totalSizeBytes"]
        
        if data["latestFileModifiedAt"]:
            if grand_latest_mtime is None or data["latestFileModifiedAt"] > grand_latest_mtime:
                grand_latest_mtime = data["latestFileModifiedAt"]
                grand_latest_category = cat
                grand_latest_filename = data["latestFileName"]

    return {
        "serverTime": datetime.now().isoformat(),
        "totalCategories": len(KNOWN_CATEGORIES),
        "grandTotalFiles": grand_total_files,
        "grandTotalSizeBytes": grand_total_size,
        "grandTotalSizeFormatted": format_file_size(grand_total_size),
        "latestIngestion": {
            "category": grand_latest_category,
            "fileName": grand_latest_filename,
            "timestamp": grand_latest_mtime,
        },
        "categories": categories_data,
    }

def get_recent_events(limit: int = 50) -> List[Dict[str, Any]]:
    if not os.path.exists(DB_PATH):
        return []
    
    try:
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, event_type, payload, status, timestamp, processed_at
            FROM event_queue
            ORDER BY id DESC
            LIMIT ?
        """, (limit,))
        rows = cursor.fetchall()
        events = []
        for r in rows:
            try:
                parsed_payload = json.loads(r["payload"])
            except Exception:
                parsed_payload = {"raw": r["payload"]}
            events.append({
                "id": r["id"],
                "eventType": r["event_type"],
                "payload": parsed_payload,
                "status": r["status"],
                "timestamp": r["timestamp"],
                "processedAt": r["processed_at"]
            })
        conn.close()
        return events
    except Exception as e:
        print(f"Error fetching recent events: {e}")
        return []
