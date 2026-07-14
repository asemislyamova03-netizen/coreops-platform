"""Editorial topic metadata helpers for Marketing M7-A (no migration).

Column `source` remains row provenance (manual/console).
Editorial reference lives in metadata_json['source_ref'].
"""

from __future__ import annotations

from typing import Any

EDITORIAL_METADATA_KEYS: tuple[str, ...] = (
    "audience",
    "pain",
    "insight",
    "source_ref",
    "cta",
    "funnel_stage",
    "notes",
    "planned_date",
)


def _normalize_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def extract_editorial_fields(metadata: dict | None) -> dict[str, str | None]:
    raw = metadata or {}
    return {key: _normalize_str(raw.get(key)) for key in EDITORIAL_METADATA_KEYS}


def build_topic_metadata_for_create(payload) -> dict:
    merged: dict[str, Any] = dict(getattr(payload, "metadata_json", None) or {})
    for key in EDITORIAL_METADATA_KEYS:
        value = getattr(payload, key, None)
        normalized = _normalize_str(value)
        if normalized is not None:
            merged[key] = normalized
    return merged


def build_topic_metadata_for_update(existing: dict | None, payload) -> dict | None:
    """Return new metadata_json if metadata/editorial fields were sent; else None."""
    fields_set = payload.model_fields_set
    editorial_touched = any(key in fields_set for key in EDITORIAL_METADATA_KEYS)
    bag_touched = "metadata_json" in fields_set
    if not editorial_touched and not bag_touched:
        return None

    merged = dict(existing or {})
    if bag_touched and payload.metadata_json is not None:
        merged.update(payload.metadata_json)

    for key in EDITORIAL_METADATA_KEYS:
        if key not in fields_set:
            continue
        normalized = _normalize_str(getattr(payload, key))
        if normalized is None:
            merged.pop(key, None)
        else:
            merged[key] = normalized
    return merged
