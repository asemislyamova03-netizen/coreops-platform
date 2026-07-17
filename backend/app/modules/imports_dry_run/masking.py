"""Field masking helpers for import dry-run logs/reports (no raw PII)."""

from __future__ import annotations

from typing import Any

SENSITIVE_KEYS = {
    "display_name",
    "name",
    "full_name",
    "email",
    "phone",
    "mobile",
    "iin",
    "iin_bin",
    "bin",
    "notes",
    "note",
    "comment",
    "body",
    "document_text",
    "address",
    "line1",
    "line2",
}


def mask_value(value: Any) -> str:
    if value is None:
        return "***"
    text = str(value)
    if not text:
        return "***"
    if "@" in text:
        local, _, domain = text.partition("@")
        return f"{local[:1]}***@{domain}" if domain else "***"
    if len(text) <= 2:
        return "***"
    return f"{text[:1]}***{text[-1:]}"


def mask_row_for_log(row: dict[str, Any]) -> dict[str, Any]:
    """Return a copy safe for logs/reports (sensitive fields masked)."""
    out: dict[str, Any] = {}
    for key, value in row.items():
        if key.lower() in SENSITIVE_KEYS:
            out[key] = mask_value(value)
        elif isinstance(value, dict):
            out[key] = mask_row_for_log(value)
        else:
            out[key] = value
    return out


def assert_no_raw_pii(payload: dict[str, Any], forbidden_substrings: list[str]) -> None:
    """Fail if any forbidden raw personal substring appears in serialized payload."""
    blob = str(payload)
    for item in forbidden_substrings:
        if item and item in blob:
            raise AssertionError(f"Raw PII leak detected for value fragment: {item[:8]}***")
