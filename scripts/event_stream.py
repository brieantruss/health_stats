#!/usr/bin/env python3
import os
import json
import sqlite3
from datetime import datetime

# Place health_events.db in the repository root directory
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
DB_PATH = os.path.join(REPO_ROOT, "health_events.db")

def init_db():
    """Initializes the database and sets up the tables if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    # Enable WAL mode for smooth, concurrent concurrent read/write operations
    conn.execute("PRAGMA journal_mode=WAL;")
    cursor = conn.cursor()
    
    # Event Queue Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS event_queue (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            event_type TEXT NOT NULL,
            payload TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending',
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            processed_at DATETIME
        )
    """)
    
    # Operational Snapshot Table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS latest_health_snapshot (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL,
            updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    conn.commit()
    conn.close()

def publish_event(event_type: str, payload_dict: dict):
    """Publishes a new event to the SQLite local queue."""
    # Ensure tables are initialized
    init_db()
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    try:
        payload_json = json.dumps(payload_dict)
        cursor.execute(
            "INSERT INTO event_queue (event_type, payload, status) VALUES (?, ?, ?)",
            (event_type, payload_json, "pending")
        )
        conn.commit()
        print(f"📡 [Event Stream] Published '{event_type}' event successfully.")
    except Exception as e:
        print(f"❌ [Event Stream] Error publishing event: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    # If run directly, initialize database
    init_db()
    print(f"✅ Event Stream SQLite database initialized at: {DB_PATH}")
