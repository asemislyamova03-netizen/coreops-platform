"""Canonical SecretRef value object for Marketing publishing vault bindings."""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from urllib.parse import urlsplit

_SCHEME = "secret"
_MAX_LEN = 255
_PATH_RE = re.compile(
    r"^/tenants/"
    r"(?P<tenant_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/"
    r"publishing-connections/"
    r"(?P<connection_id>[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12})/"
    r"versions/"
    r"(?P<version>[1-9][0-9]*)$"
)
_TOKEN_LIKE_RE = re.compile(
    r"(?i)\b(bearer\s+\S+|eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]+\.|sk-[A-Za-z0-9]{16,})"
)


class SecretRefValidationError(ValueError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class SecretRef:
    tenant_id: uuid.UUID
    connection_id: uuid.UUID
    version: int

    def __post_init__(self) -> None:
        if self.version < 1:
            raise SecretRefValidationError("secret_ref_version_must_be_positive")
        if len(self.render()) > _MAX_LEN:
            raise SecretRefValidationError("secret_ref_too_long")

    def render(self) -> str:
        return (
            f"secret://marketing/tenants/{self.tenant_id}/"
            f"publishing-connections/{self.connection_id}/versions/{self.version}"
        )

    def assert_ownership(self, *, tenant_id: uuid.UUID, connection_id: uuid.UUID) -> None:
        if self.tenant_id != tenant_id or self.connection_id != connection_id:
            raise SecretRefValidationError("secret_ref_ownership_mismatch")

    def __str__(self) -> str:
        return "<SecretRef:redacted>"

    def __repr__(self) -> str:
        return (
            f"SecretRef(tenant_id=<redacted>, connection_id=<redacted>, version={self.version})"
        )


def build_secret_ref(
    *,
    tenant_id: uuid.UUID,
    connection_id: uuid.UUID,
    version: int,
) -> SecretRef:
    return SecretRef(tenant_id=tenant_id, connection_id=connection_id, version=version)


def parse_secret_ref(value: str) -> SecretRef:
    if not isinstance(value, str):
        raise SecretRefValidationError("secret_ref_must_be_str")
    raw = value.strip()
    if not raw:
        raise SecretRefValidationError("secret_ref_empty")
    if len(raw) > _MAX_LEN:
        raise SecretRefValidationError("secret_ref_too_long")
    if _TOKEN_LIKE_RE.search(raw) or raw.casefold().startswith("bearer "):
        raise SecretRefValidationError("secret_ref_looks_like_token")

    parts = urlsplit(raw)
    if parts.scheme != _SCHEME:
        raise SecretRefValidationError("secret_ref_invalid_scheme")
    if parts.netloc != "marketing":
        raise SecretRefValidationError("secret_ref_invalid_authority")
    if parts.query or parts.fragment or parts.username or parts.password:
        raise SecretRefValidationError("secret_ref_forbidden_components")

    match = _PATH_RE.match(parts.path)
    if match is None:
        raise SecretRefValidationError("secret_ref_invalid_path")

    try:
        tenant_id = uuid.UUID(match.group("tenant_id"))
        connection_id = uuid.UUID(match.group("connection_id"))
    except ValueError as exc:
        raise SecretRefValidationError("secret_ref_invalid_uuid") from exc

    return SecretRef(
        tenant_id=tenant_id,
        connection_id=connection_id,
        version=int(match.group("version")),
    )
