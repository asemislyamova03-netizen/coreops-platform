"""In-memory StoragePort adapter — unit/integration tests only."""

from __future__ import annotations

import secrets
import uuid
from dataclasses import dataclass, field

from app.core.object_storage.port import (
    StorageError,
    StorageObjectRef,
    StoredObjectDescriptor,
    TemporaryAccessHandle,
)

_ALLOWED_ENVS = frozenset({"test", "testing", "development", "dev", "local"})


@dataclass
class _StoredObject:
    tenant_id: uuid.UUID
    data: bytes
    content_type: str
    metadata: dict[str, str] = field(default_factory=dict)
    archived: bool = False


class InMemoryStorage:
    """Ephemeral object store for tests. Deny-by-default outside allow-listed envs."""

    def __init__(self, *, app_env: str = "test") -> None:
        env = (app_env or "").strip().lower()
        if env not in _ALLOWED_ENVS:
            raise StorageError("in_memory_storage_forbidden_in_runtime")
        self._app_env = env
        self._objects: dict[str, _StoredObject] = {}

    def put_object(
        self,
        *,
        tenant_id: uuid.UUID,
        object_ref: StorageObjectRef,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObjectDescriptor:
        key = self._key(tenant_id, object_ref)
        if key in self._objects:
            raise StorageError("object_key_collision")
        self._objects[key] = _StoredObject(
            tenant_id=tenant_id,
            data=data,
            content_type=content_type,
            metadata=dict(metadata or {}),
        )
        return StoredObjectDescriptor(
            tenant_id=tenant_id,
            object_ref=object_ref,
            content_type=content_type,
            size_bytes=len(data),
        )

    def get_object_metadata(
        self,
        *,
        tenant_id: uuid.UUID,
        object_ref: StorageObjectRef,
    ) -> StoredObjectDescriptor:
        entry = self._require(tenant_id, object_ref)
        return StoredObjectDescriptor(
            tenant_id=tenant_id,
            object_ref=object_ref,
            content_type=entry.content_type,
            size_bytes=len(entry.data),
        )

    def delete_object(self, *, tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> None:
        key = object_ref.unsafe_object_key_for_adapter()
        entry = self._objects.get(key)
        if entry is None:
            return
        if entry.tenant_id != tenant_id:
            raise StorageError("storage_tenant_mismatch")
        del self._objects[key]

    def archive_object(self, *, tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> None:
        entry = self._require(tenant_id, object_ref)
        entry.archived = True

    def generate_temporary_access(
        self,
        *,
        tenant_id: uuid.UUID,
        object_ref: StorageObjectRef,
        purpose: str,
        ttl_seconds: int,
    ) -> TemporaryAccessHandle:
        self._require(tenant_id, object_ref)
        if ttl_seconds <= 0:
            raise StorageError("invalid_ttl")
        return TemporaryAccessHandle(
            tenant_id=tenant_id,
            object_ref=object_ref,
            purpose=purpose,
            ttl_seconds=ttl_seconds,
            opaque_token=secrets.token_urlsafe(16),
        )

    def read_bytes_for_tests(self, *, tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> bytes:
        """Test-only helper — not part of StoragePort."""
        return self._require(tenant_id, object_ref).data

    def contains_ref(self, object_ref: StorageObjectRef) -> bool:
        return object_ref.unsafe_object_key_for_adapter() in self._objects

    def _require(self, tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> _StoredObject:
        key = self._key(tenant_id, object_ref)
        entry = self._objects.get(key)
        if entry is None:
            raise StorageError("object_not_found")
        if entry.tenant_id != tenant_id:
            raise StorageError("storage_tenant_mismatch")
        return entry

    @staticmethod
    def _key(tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> str:
        if object_ref.tenant_id != tenant_id:
            raise StorageError("storage_tenant_mismatch")
        return object_ref.unsafe_object_key_for_adapter()

    def __repr__(self) -> str:
        return f"InMemoryStorage(env={self._app_env!r}, objects={len(self._objects)})"
