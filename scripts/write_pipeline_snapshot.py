#!/usr/bin/env python3
"""Write a dashboard telemetry snapshot without requiring Flask or Pub/Sub."""

import json
import os
import sys
import tempfile

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from scripts.pipeline_telemetry import get_all_categories_telemetry

OUTPUT_PATH = os.getenv(
    "HEALTH_PIPELINE_SNAPSHOT",
    os.path.join(REPO_ROOT, "ops_dashboard", "public", "pipeline-status.json"),
)


def main() -> None:
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    fd, temporary_path = tempfile.mkstemp(
        prefix="pipeline-status-", suffix=".json", dir=os.path.dirname(OUTPUT_PATH)
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as snapshot_file:
            json.dump(get_all_categories_telemetry(), snapshot_file)
        os.replace(temporary_path, OUTPUT_PATH)
    finally:
        if os.path.exists(temporary_path):
            os.unlink(temporary_path)


if __name__ == "__main__":
    main()
