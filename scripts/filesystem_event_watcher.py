#!/usr/bin/env python3
"""Publish file-arrival and file-change events for health data directories."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from typing import Dict, Tuple

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.event_stream import publish_event

WATCH_ROOTS = {
    "raw": os.path.join(REPO_ROOT, "raw_files"),
    "processed": os.path.join(REPO_ROOT, "processed_files"),
}
STATE_PATH = os.getenv(
    "HEALTH_FILE_WATCH_STATE", os.path.join(REPO_ROOT, "health_file_watch_state.json")
)
POLL_SECONDS = float(os.getenv("HEALTH_FILE_WATCH_INTERVAL", "2"))


def scan_files() -> Dict[str, Tuple[int, int]]:
    files: Dict[str, Tuple[int, int]] = {}
    for source, root in WATCH_ROOTS.items():
        if not os.path.isdir(root):
            continue
        # Health data is organized as raw_files/<category>/<file> and
        # processed_files/<category>/<file>; avoid recursive traversal so a
        # problematic nested filesystem entry cannot stall the API host.
        try:
            category_directories = os.listdir(root)
        except OSError:
            continue
        for category in category_directories:
            if category.startswith('.'):
                continue
            category_directory = os.path.join(root, category)
            if not os.path.isdir(category_directory):
                continue
            try:
                filenames = os.listdir(category_directory)
            except OSError:
                continue
            for filename in filenames:
                if filename.startswith('.'):
                    continue
                path = os.path.join(category_directory, filename)
                try:
                    if not os.path.isfile(path):
                        continue
                    stat = os.stat(path)
                    files[f"{source}:{path}"] = (stat.st_mtime_ns, stat.st_size)
                except OSError:
                    continue
    return files


def category_for(path: str, source: str) -> str:
    root = WATCH_ROOTS[source]
    relative = os.path.relpath(path, root)
    return relative.split(os.sep, 1)[0]


def load_state() -> Dict[str, Tuple[int, int]]:
    try:
        with open(STATE_PATH, encoding="utf-8") as state_file:
            raw_state = json.load(state_file)
        return {key: (int(value[0]), int(value[1])) for key, value in raw_state.items()}
    except (FileNotFoundError, json.JSONDecodeError, TypeError, ValueError):
        return {}


def save_state(state: Dict[str, Tuple[int, int]]) -> None:
    temporary_path = f"{STATE_PATH}.tmp"
    with open(temporary_path, "w", encoding="utf-8") as state_file:
        json.dump(state, state_file)
    os.replace(temporary_path, STATE_PATH)


def publish_changes(previous: Dict[str, Tuple[int, int]], current: Dict[str, Tuple[int, int]]) -> None:
    for key, (mtime_ns, size) in current.items():
        if previous.get(key) == (mtime_ns, size):
            continue
        source, path = key.split(":", 1)
        category = category_for(path, source)
        event_type = "FILE_DETECTED" if source == "raw" else "FILE_PROCESSED"
        publish_event(event_type, {
            "category": category,
            "fileName": os.path.basename(path),
            "path": os.path.relpath(path, REPO_ROOT),
            "source": source,
            "sizeBytes": size,
            "modifiedAt": datetime.fromtimestamp(
                mtime_ns / 1_000_000_000, timezone.utc
            ).isoformat(),
        })
        print(f"Published {event_type}: {path}", flush=True)


def main() -> None:
    previous = load_state()
    current = scan_files()
    if not previous:
        save_state(current)
        print("Initialized filesystem watcher baseline", flush=True)
    else:
        publish_changes(previous, current)
        save_state(current)

    while True:
        time.sleep(POLL_SECONDS)
        current = scan_files()
        publish_changes(previous, current)
        save_state(current)
        previous = current


if __name__ == "__main__":
    main()