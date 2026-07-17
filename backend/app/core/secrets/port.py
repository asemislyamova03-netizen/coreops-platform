"""Vendor-neutral SecretVaultPort for Marketing publishing credentials."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from enum import Enum
from typing import Protocol

from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.ref import SecretRef


class SecretVersionState(str, Enum):
    PENDING = "pending"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


@dataclass(frozen=True, slots=True)
class SecretStoreMetadata:
    provider: str | None = None
    purpose: str = "publishing_connection"


class SecretVaultError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class SecretVaultPort(Protocol):
    def store_secret(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        version: int,
        plaintext: SecretPlaintext,
        metadata: SecretStoreMetadata | None = None,
    ) -> SecretRef:
        """Store a new pending/readable version and return typed SecretRef."""

    def read_secret(self, ref: SecretRef) -> SecretPlaintext:
        """Read plaintext for narrowly scoped adapter execution only."""

    def activate_version(self, ref: SecretRef) -> None:
        """Mark version active after successful DB bind."""

    def deactivate_version(self, ref: SecretRef) -> None:
        """Soft-revoke: version becomes unreadable."""

    def delete_version(self, ref: SecretRef) -> None:
        """Hard-delete orphan version (bind/rotate compensation)."""

    def confirm_inactive(self, ref: SecretRef) -> bool:
        """Return True when version is deactivated or absent after revoke."""

    def version_exists(self, ref: SecretRef) -> bool: ...

    def get_version_state(self, ref: SecretRef) -> SecretVersionState | None: ...
