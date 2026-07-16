"""Validation helpers for M8-B publishing connections (no secret material)."""

from __future__ import annotations

import re

from app.modules.marketing.exceptions import MarketingPublishingConnectionValidationError

_FORBIDDEN_KEY_FRAGMENTS = (
    "token",
    "secret",
    "credential",
    "private_key",
    "refresh",
    "access_token",
    "bot_token",
    "client_secret",
)

_TOKEN_LIKE_VALUE_RE = re.compile(r"^[A-Za-z0-9_\-]{40,}$")
_MAX_SCOPE_LENGTH = 128
_ALLOWED_METADATA_KEYS = {"public_username", "account_type", "is_verified"}


def normalize_scopes(scopes: list[str] | None) -> list[str]:
    if scopes is None:
        return []
    if not isinstance(scopes, list):
        raise MarketingPublishingConnectionValidationError("scopes_json_must_be_array")

    normalized: list[str] = []
    seen: set[str] = set()
    for raw in scopes:
        if not isinstance(raw, str):
            raise MarketingPublishingConnectionValidationError("scope_must_be_string")
        value = raw.strip()
        if not value:
            continue
        if len(value) > _MAX_SCOPE_LENGTH:
            raise MarketingPublishingConnectionValidationError("scope_too_long")
        _reject_token_like_string(value, field="scope")
        key = value.casefold()
        if key in seen:
            continue
        seen.add(key)
        normalized.append(value)
    return sorted(normalized, key=str.casefold)


def validate_metadata_json(metadata: dict | None) -> dict:
    if metadata is None:
        return {}
    if not isinstance(metadata, dict):
        raise MarketingPublishingConnectionValidationError("metadata_json_must_be_object")
    validated: dict = {}
    for key, value in metadata.items():
        if not isinstance(key, str):
            raise MarketingPublishingConnectionValidationError("metadata_json_key_must_be_string")
        if key not in _ALLOWED_METADATA_KEYS:
            raise MarketingPublishingConnectionValidationError("metadata_json_unknown_key")
        if value is None:
            raise MarketingPublishingConnectionValidationError("metadata_json_null_value_not_allowed")
        if isinstance(value, (dict, list)):
            raise MarketingPublishingConnectionValidationError("metadata_json_nested_not_allowed")

        if key == "public_username":
            if not isinstance(value, str):
                raise MarketingPublishingConnectionValidationError("metadata_json_public_username_type")
            normalized = value.strip()
            if not normalized or len(normalized) > 255:
                raise MarketingPublishingConnectionValidationError("metadata_json_public_username_length")
            _reject_token_like_string(normalized, field="metadata_json.public_username")
            validated[key] = normalized
            continue

        if key == "account_type":
            if not isinstance(value, str):
                raise MarketingPublishingConnectionValidationError("metadata_json_account_type_type")
            normalized = value.strip()
            if not normalized or len(normalized) > 64:
                raise MarketingPublishingConnectionValidationError("metadata_json_account_type_length")
            _reject_token_like_string(normalized, field="metadata_json.account_type")
            validated[key] = normalized
            continue

        if key == "is_verified":
            if not isinstance(value, bool):
                raise MarketingPublishingConnectionValidationError("metadata_json_is_verified_type")
            validated[key] = value
            continue

    return validated


def _validate_mapping_no_token_material(mapping: dict, *, field: str) -> None:
    for key, value in mapping.items():
        if not isinstance(key, str):
            raise MarketingPublishingConnectionValidationError(f"{field}_key_must_be_string")
        _reject_forbidden_key(key, field=field)
        _validate_value_no_token_material(value, field=field)


def _validate_value_no_token_material(value: object, *, field: str) -> None:
    if isinstance(value, str):
        _reject_token_like_string(value, field=field)
    elif isinstance(value, dict):
        _validate_mapping_no_token_material(value, field=field)
    elif isinstance(value, list):
        for item in value:
            _validate_value_no_token_material(item, field=field)


def _reject_forbidden_key(key: str, *, field: str) -> None:
    lowered = key.casefold()
    for fragment in _FORBIDDEN_KEY_FRAGMENTS:
        if fragment in lowered:
            raise MarketingPublishingConnectionValidationError(f"{field}_forbidden_key")


def _reject_token_like_string(value: str, *, field: str) -> None:
    if value.casefold().startswith("bearer "):
        raise MarketingPublishingConnectionValidationError(f"{field}_token_like_value")
    if _TOKEN_LIKE_VALUE_RE.match(value):
        raise MarketingPublishingConnectionValidationError(f"{field}_token_like_value")
