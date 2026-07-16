"""In-memory SecretVaultPort adapter — unit/integration tests only."""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from app.core.secrets.plaintext import SecretPlaintext
from app.core.secrets.port import (
    SecretStoreMetadata,
    SecretVaultError,
    SecretVersionState,
)
from app.core.secrets.ref import SecretRef, build_secret_ref

_ALLOWED_ENVS = frozenset({"test", "testing", "development", "dev", "local"})


@dataclass
class _StoredSecret:
    plaintext: SecretPlaintext
    state: SecretVersionState
    metadata: SecretStoreMetadata | None


class InMemorySecretVault:
    """Ephemeral vault for tests. Deny-by-default outside allow-listed envs."""

    def __init__(self, *, app_env: str = "test") -> None:
        env = (app_env or "").strip().lower()
        if env not in _ALLOWED_ENVS:
            raise SecretVaultError("in_memory_vault_forbidden_in_runtime")
        self._app_env = env
        self._store: dict[str, _StoredSecret] = {}

    def store_secret(
        self,
        *,
        tenant_id: uuid.UUID,
        connection_id: uuid.UUID,
        version: int,
        plaintext: SecretPlaintext,
        metadata: SecretStoreMetadata | None = None,
    ) -> SecretRef:
        if not isinstance(plaintext, SecretPlaintext):
            raise SecretVaultError("plaintext_must_be_SecretPlaintext")
        ref = build_secret_ref(
            tenant_id=tenant_id,
            connection_id=connection_id,
            version=version,
        )
        key = ref.render()
        if key in self._store:
            raise SecretVaultError("secret_version_already_exists")
        self._store[key] = _StoredSecret(
            plaintext=plaintext,
            state=SecretVersionState.PENDING,
            metadata=metadata,
        )
        return ref

    def read_secret(self, ref: SecretRef) -> SecretPlaintext:
        self._assert_typed_ref(ref)
        entry = self._require(ref)
        if entry.state == SecretVersionState.DEACTIVATED:
            raise SecretVaultError("secret_version_inactive")
        return entry.plaintext

    def activate_version(self, ref: SecretRef) -> None:
        self._assert_typed_ref(ref)
        entry = self._require(ref)
        if entry.state == SecretVersionState.DEACTIVATED:
            raise SecretVaultError("secret_version_inactive")
        entry.state = SecretVersionState.ACTIVE

    def deactivate_version(self, ref: SecretRef) -> None:
        self._assert_typed_ref(ref)
        entry = self._require(ref)
        entry.state = SecretVersionState.DEACTIVATED

    def delete_version(self, ref: SecretRef) -> None:
        self._assert_typed_ref(ref)
        key = ref.render()
        self._store.pop(key, None)

    def confirm_inactive(self, ref: SecretRef) -> bool:
        self._assert_typed_ref(ref)
        entry = self._store.get(ref.render())
        if entry is None:
            return True
        return entry.state == SecretVersionState.DEACTIVATED

    def version_exists(self, ref: SecretRef) -> bool:
        self._assert_typed_ref(ref)
        return ref.render() in self._store

    def get_version_state(self, ref: SecretRef) -> SecretVersionState | None:
        self._assert_typed_ref(ref)
        entry = self._store.get(ref.render())
        return entry.state if entry is not None else None

    def _assert_typed_ref(self, ref: SecretRef) -> None:
        if not isinstance(ref, SecretRef):
            raise SecretVaultError("secret_ref_must_be_SecretRef")
        expected = build_secret_ref(
            tenant_id=ref.tenant_id,
            connection_id=ref.connection_id,
            version=ref.version,
        )
        if expected.render() != ref.render():
            raise SecretVaultError("secret_ref_ownership_mismatch")

    def _require(self, ref: SecretRef) -> _StoredSecret:
        entry = self._store.get(ref.render())
        if entry is None:
            raise SecretVaultError("secret_version_not_found")
        return entry
