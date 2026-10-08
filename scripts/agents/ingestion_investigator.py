import logging
import re

from prefect import flow


_FAILURE_RULES = (
    (("credential", "unauthorized", "forbidden", "permission denied", "401", "403"),
     "Google Drive authentication or access failure",
     "Check the service-account key and confirm it has access to the source Drive folder."),
    (("quota", "rate limit", "429"),
     "Google API quota or rate limit",
     "Check Google API quotas and retry after the quota window resets."),
    (("mysql", "database", "connector", "access denied"),
     "MySQL connection or database operation failure",
     "Check the MySQL service, credentials, and the failing ETL script's database permissions."),
    (("timed out", "timeout", "connection reset", "name or service not known", "temporary failure"),
     "Network or remote-service connectivity failure",
     "Check VM connectivity and the availability of Google Drive or the named remote service."),
    (("no such file", "file not found", "script not found"),
     "Missing local file or ETL script path",
     "Confirm the expected source file and ETL script exist at the paths shown in the failure details."),
    (("csv", "unicode", "decode", "malformed", "invalid format"),
     "Input file or data-format problem",
     "Inspect the named source file and compare its columns and encoding with the ETL transform's expectations."),
)


def classify_ingestion_failure(failure_details: str) -> tuple[str, str, str]:
    normalized = failure_details.lower()
    for markers, cause, next_check in _FAILURE_RULES:
        if any(marker in normalized for marker in markers):
            return cause, next_check, "rule match"
    return (
        "Cause not recognized from the captured error",
        "Inspect the complete Prefect flow logs and the ETL script's stderr around this failure.",
        "no matching rule",
    )


@flow(name="ingestion_investigator_subagent")
def ingestion_investigator_flow(failing_flow: str, failure_details: str) -> str:
    cause, next_check, evidence_type = classify_ingestion_failure(failure_details)
    script_match = re.search(
        r"(?:extract_and_load|extract|transform|load)_[A-Za-z0-9_]+\.py",
        failure_details,
    )
    component = script_match.group(0) if script_match else failing_flow
    evidence = " ".join(failure_details.split())[-800:] or "No error details were captured."
    report = (
        "Ingestion failure investigation\n"
        f"Failed flow/component: {component}\n"
        f"Likely cause: {cause}\n"
        f"Suggested next check: {next_check}\n"
        f"Evidence ({evidence_type}): {evidence}"
    )
    logging.error(report)
    return report