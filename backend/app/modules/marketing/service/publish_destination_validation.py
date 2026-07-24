"""Validation helpers for M8-D publish destination metadata / display_name (no secret material)."""

from __future__ import annotations

import re

from app.modules.marketing.exceptions import MarketingPublishDestinationValidationError

# Canonical forbidden key names (case-insensitive; separators / camelCase normalized away).
_FORBIDDEN_METADATA_KEYS: frozenset[str] = frozenset(
    {
        "token",
        "accesstoken",
        "refreshtoken",
        "secret",
        "secretref",
        "password",
        "credential",
        "credentials",
        "authorization",
        "apikey",
        "bottoken",
        "clientsecret",
        "privatekey",
        "ciphertext",
        "nonce",
        "wrappedkey",
        "credentialsjson",
    }
)

_MAX_DISPLAY_NAME_LENGTH = 255
_CONTROL_CHAR_RE = re.compile(r"[\x00-\x1f\x7f]")
_SEPARATORS_RE = re.compile(r"[-_./\s]+")
_CAMEL_BOUNDARY_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])")


def normalize_metadata_key(key: str) -> str:
    """Normalize metadata key for forbidden-key checks (casefold + separators + camelCase)."""
    # Split camelCase / PascalCase before casefold so AccessToken → access + token.
    spaced = _CAMEL_BOUNDARY_RE.sub(" ", key)
    collapsed = _SEPARATORS_RE.sub("", spaced.casefold())
    return collapsed


def validate_destination_display_name(display_name: str | None) -> str:
    """Require non-empty display_name within length limit and without control characters."""
    if display_name is None:
        raise MarketingPublishDestinationValidationError("display_name_required")
    if not isinstance(display_name, str):
        raise MarketingPublishDestinationValidationError("display_name_must_be_string")
    name = display_name.strip()
    if not name:
        raise MarketingPublishDestinationValidationError("display_name_required")
    if len(name) > _MAX_DISPLAY_NAME_LENGTH:
        raise MarketingPublishDestinationValidationError("display_name_too_long")
    if _CONTROL_CHAR_RE.search(name):
        raise MarketingPublishDestinationValidationError("display_name_control_characters")
    return name


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
        if normalize_metadata_key(key) in _FORBIDDEN_METADATA_KEYS:
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
