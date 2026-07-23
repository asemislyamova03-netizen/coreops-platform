"""Validation helpers for M8-D1 publish destination metadata (no secret material)."""

from __future__ import annotations

from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

# Exact key names (case-insensitive). Never log the associated values.
_FORBIDDEN_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "access_token",
        "refresh_token",
        "secret",
        "secret_ref",
        "password",
        "credential",
        "credentials",
        "authorization",
        "api_key",
    }
)


def validate_destination_metadata_json(metadata: dict | None) -> dict:
    """Reject nested/forbidden secret-like keys before persistence. Returns a shallow copy tree."""
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise MarketingPublishDestinationValidationError("metadata_json_must_be_object")
    return _sanitize_mapping(metadata)


def _sanitize_mapping(mapping: dict) -> dict:
    out: dict = {}
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise MarketingPublishDestinationValidationError("metadata_json_key_must_be_string")
        if key.casefold() in _FORBIDDEN_METADATA_KEYS:
            # Do not include the forbidden value in the exception message.
            raise MarketingPublishDestinationValidationError("metadata_json_forbidden_key")
        out[key] = _sanitize_value(value)
    return out


def _sanitize_value(value: object) -> object:
    if isinstance(value, dict):
        return _sanitize_mapping(value)
    if isinstance(value, list):
        return [_sanitize_value(item) for item in value]
    return value
