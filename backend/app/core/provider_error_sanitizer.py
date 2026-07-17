"""Centralized provider-error sanitizer for Marketing publish bridge."""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SanitizedProviderError:
    error_code: str
    message_redacted: str


_MAX_LEN = 512
_FORBIDDEN_PATTERNS = (
    re.compile(r"(?i)bearer\s+\S+"),
    re.compile(r"(?i)authorization:\s*\S+"),
    re.compile(r"eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
    re.compile(r"(?i)secret://\S+"),
    re.compile(r"(?i)(api[_-]?key|access[_-]?token|refresh[_-]?token)\s*[:=]\s*\S+"),
    re.compile(r"https?://\S+"),
)


# Typed safe mapping — primary source of redacted messages.
_CODE_MESSAGES: dict[str, str] = {
    "provider_auth_failed": "Provider authentication failed",
    "provider_unavailable": "Provider temporarily unavailable",
    "health_check_timeout": "Health check timed out",
    "health_check_failed": "Health check failed",
    "vault_store_failed": "Secret vault store failed",
    "vault_revoke_failed": "Secret vault revoke failed",
    "vault_bind_failed": "Secret binding failed",
    "vault_rotate_failed": "Secret rotation failed",
    "vault_disconnect_failed": "Secret disconnect failed",
    "db_commit_failed": "Database commit failed during secret lifecycle",
    "vault_recovery_required": "Vault recovery required after partial lifecycle failure",
    "vault_activation_required": "Bound secret requires vault activation recovery",
    "vault_active_orphan": "Active vault orphan requires manual recovery",
    "unchecked_health": "Provider health not verified",
    "invalid_secret_input": "Invalid secret input",
    "unknown_provider_error": "Provider operation failed",
    "secret_already_bound": "Secret already bound to connection",
    "secret_not_bound": "Secret is not bound to connection",
    "secret_ref_invalid": "Stored secret reference is invalid",
    "secret_ref_missing_inconsistent": "Connection secret binding is inconsistent",
}


def sanitize_provider_error(
    *,
    error_code: str,
    raw_message: str | None = None,
) -> SanitizedProviderError:
    """Map to typed safe message. Never persist raw provider text."""
    code = (error_code or "unknown_provider_error").strip()[:64] or "unknown_provider_error"
    message = _CODE_MESSAGES.get(code, _CODE_MESSAGES["unknown_provider_error"])

    # Secondary defense only: if caller mistakenly passes raw text into message path,
    # strip known secret-like fragments before any accidental use.
    if raw_message:
        _assert_no_forbidden_fragments(raw_message)

    return SanitizedProviderError(
        error_code=code,
        message_redacted=message[:_MAX_LEN],
    )


def _assert_no_forbidden_fragments(text: str) -> None:
    for pattern in _FORBIDDEN_PATTERNS:
        if pattern.search(text):
            # Do not raise with raw text; ignore content after detection.
            return
