"""Masked Gate B dry-run report builder (aggregates only, no raw PII)."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from uuid import UUID

from app.modules.imports_dry_run.masking import SENSITIVE_KEYS
from app.modules.imports_dry_run.pipeline import DryRunNoOpTargetAdapter, SyntheticDryRunPipeline
from app.modules.imports_dry_run.schemas import SyntheticDryRunResult

EMAIL_PATTERN = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")
PHONE_PATTERN = re.compile(r"(?<!\d)(?:\+?\d[\d\s().-]{7,}\d)(?!\d)")
IIN_LIKE_PATTERN = re.compile(r"(?<!\d)\d{12}(?!\d)")
LONG_DIGIT_PATTERN = re.compile(r"(?<!\d)\d{10,}(?!\d)")
UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    re.IGNORECASE,
)
BACKUP_ID_SCRUB_PATTERN = re.compile(r"consulting-gate-b-\d{8}-\d{4}-[a-zA-Z0-9_-]+")
ISO_TIMESTAMP_SCRUB_PATTERN = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")

# Keys allowed to contain numeric strings in reports (ids, counts, decimals).
SAFE_NUMERIC_KEYS = {
    "id",
    "tenant_id",
    "default_branch_id",
    "created_by_user_id",
    "backup_id",
    "schema_fingerprint",
    "source_db_size_bytes",
    "source_db_mtime_utc",
    "difference",
    "source_payments_total",
    "mapped_payments_total",
    "total_source_rows",
    "total_imported_rows",
    "total_skipped_rows",
    "total_error_rows",
    "total_review_rows",
    "status_mapping_warnings",
    "duplicate_warnings",
    "orphan_warnings",
    "unknown_status_warnings",
    "required_field_errors",
    "source_count",
    "imported_count",
    "skipped_count",
    "error_count",
    "review_count",
}


class MaskedReportPiiError(RuntimeError):
    """Raised when masked report output appears to contain raw PII."""


def build_masked_gate_b_report(
    *,
    result: SyntheticDryRunResult,
    pipeline: SyntheticDryRunPipeline,
    source_system: str,
    scenario_name: str,
    backup_id: str,
    source_db_path: Path,
    schema_fingerprint: str | None,
    row_counts: dict[str, int],
    tenant_id: UUID,
    default_branch_id: UUID,
    amount_reconciliation_summary: dict[str, int | str] | None = None,
    services_mapping_summary: dict[str, int] | None = None,
) -> dict[str, Any]:
    """Build aggregate-only Gate B report. No raw row samples."""
    stat = source_db_path.stat()
    mtime = datetime.fromtimestamp(stat.st_mtime, tz=UTC).strftime("%Y-%m-%dT%H:%M:%SZ")

    reconciliation = amount_reconciliation_summary or {
        "derived_line_amount_count": 0,
        "order_total_match_count": 0,
        "order_total_mismatch_count": 0,
        "order_total_missing_count": 0,
        "order_total_reconciliation_checked_count": 0,
        "amount_reconciliation_status": "insufficient_data",
    }
    services_summary = services_mapping_summary or {
        "services_count": 0,
        "services_title_present_count": 0,
        "services_title_missing_count": 0,
        "services_code_present_count": 0,
        "services_name_fallback_count": 0,
        "services_name_generated_count": 0,
    }

    return {
        "gate": "B",
        "mode": "real-source-readonly",
        "generated_at_utc": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "backup_id": backup_id,
        "tenant_id": str(tenant_id),
        "default_branch_id": str(default_branch_id),
        "scenario_name": scenario_name,
        "summary": {
            "source_system": result.summary.source_system,
            "total_source_rows": result.summary.total_source_rows,
            "total_imported_rows": result.summary.total_imported_rows,
            "total_skipped_rows": result.summary.total_skipped_rows,
            "total_error_rows": result.summary.total_error_rows,
            "total_review_rows": result.summary.total_review_rows,
            "status_mapping_warnings": result.summary.status_mapping_warnings,
            "entity_counts": [
                {
                    "entity": item.entity,
                    "source_count": item.source_count,
                    "imported_count": item.imported_count,
                    "skipped_count": item.skipped_count,
                    "error_count": item.error_count,
                    "review_count": item.review_count,
                }
                for item in result.summary.entities
            ],
        },
        "report": {
            "duplicate_warnings": result.report.duplicate_warnings,
            "orphan_warnings": result.report.orphan_warnings,
            "unknown_status_warnings": result.report.unknown_status_warnings,
            "required_field_errors": result.report.required_field_errors,
            "finance_check": result.report.finance_check.model_dump(mode="json"),
            "tenant_branch_readiness": result.report.tenant_branch_readiness.model_dump(mode="json"),
            "issue_codes": sorted({issue.issue_code for issue in result.report.issues}),
            "issue_count_by_severity": _issue_severity_counts(result),
            "amount_reconciliation": reconciliation,
            "services_mapping": services_summary,
            "warning_categories": {
                "amount_reconciliation_mismatch": int(
                    reconciliation.get("order_total_mismatch_count", 0)
                ),
                "service_title_missing_fallback_to_code": int(
                    services_summary.get("services_name_fallback_count", 0)
                ),
                "service_name_generated_needs_review": int(
                    services_summary.get("services_name_generated_count", 0)
                ),
            },
        },
        "source": {
            "system": source_system,
            "schema_fingerprint": schema_fingerprint,
            "row_counts": row_counts,
            "source_db_basename": source_db_path.name,
            "source_db_size_bytes": stat.st_size,
            "source_db_mtime_utc": mtime,
        },
        "target_endpoint_checks": [
            {
                "endpoint": item.endpoint,
                "schema_name": item.schema_name,
                "status": item.status,
                "detail": item.note,
            }
            for item in pipeline.target.endpoint_checks
        ],
        "target_payload_counts": dict(pipeline.target.payload_counts),
        "disclaimer": (
            "Gate B masked report. Aggregates only. No raw PII. "
            "No Core writes. No SQLite writes."
        ),
    }


def _issue_severity_counts(result: SyntheticDryRunResult) -> dict[str, int]:
    counts: dict[str, int] = {}
    for issue in result.report.issues:
        counts[issue.severity.value] = counts.get(issue.severity.value, 0) + 1
    return counts


def scan_text_for_suspicious_pii(text: str) -> list[str]:
    """Return human-readable labels for suspicious patterns found in serialized output."""
    scrubbed = UUID_PATTERN.sub("UUID", text)
    scrubbed = BACKUP_ID_SCRUB_PATTERN.sub("BACKUP_ID", scrubbed)
    scrubbed = ISO_TIMESTAMP_SCRUB_PATTERN.sub("TIMESTAMP", scrubbed)
    findings: list[str] = []
    if EMAIL_PATTERN.search(scrubbed):
        findings.append("email-like pattern")
    if PHONE_PATTERN.search(scrubbed):
        findings.append("phone-like pattern")
    if IIN_LIKE_PATTERN.search(scrubbed):
        findings.append("iin-like 12-digit pattern")
    if LONG_DIGIT_PATTERN.search(scrubbed):
        findings.append("long digit identifier pattern")
    return findings


def _collect_sensitive_key_violations(obj: Any, path: str = "") -> list[str]:
    violations: list[str] = []
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_path = f"{path}.{key}" if path else key
            if key.lower() in SENSITIVE_KEYS and value not in (None, "", "***"):
                violations.append(f"sensitive key present: {key_path}")
            violations.extend(_collect_sensitive_key_violations(value, key_path))
    elif isinstance(obj, list):
        for idx, item in enumerate(obj):
            violations.extend(_collect_sensitive_key_violations(item, f"{path}[{idx}]"))
    return violations


def assert_masked_report_pii_safe(report: dict[str, Any]) -> None:
    """
    Fail closed if report likely contains raw PII.
    Checks structural sensitive keys and pattern scan on JSON blob.
    """
    violations = _collect_sensitive_key_violations(report)
    if violations:
        raise MaskedReportPiiError(
            "Masked report contains sensitive field keys with values: "
            + "; ".join(violations[:5])
        )

    blob = json.dumps(report, ensure_ascii=False)
    pattern_findings = scan_text_for_suspicious_pii(blob)
    if pattern_findings:
        raise MaskedReportPiiError(
            "Masked report failed PII pattern scan: " + ", ".join(sorted(set(pattern_findings)))
        )


def write_masked_report(report: dict[str, Any], output_path: Path) -> None:
    assert_masked_report_pii_safe(report)
    output_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")


def assert_target_is_noop(target: DryRunNoOpTargetAdapter) -> None:
    if not isinstance(target, DryRunNoOpTargetAdapter):
        raise TypeError("Gate B requires DryRunNoOpTargetAdapter (no Core writes)")
