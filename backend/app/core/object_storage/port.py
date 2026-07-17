"""Vendor-neutral StoragePort for Marketing Mode A media objects."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Protocol


class StorageError(Exception):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, slots=True)
class StorageObjectRef:
    """Opaque tenant-scoped object reference for StoragePort internals.

    Marketing-facing DTOs must never serialize the raw key. Use
    ``redacted_id`` / ``__repr__`` / ``__str__`` only.
    """

    tenant_id: uuid.UUID
    _object_key: str

    def __post_init__(self) -> None:
        prefix = f"marketing/tenants/{self.tenant_id}/"
        key = self._object_key
        if not key.startswith(prefix):
            raise StorageError("object_key_tenant_prefix_mismatch")
        if ".." in key or key.startswith("/") or "\\" in key:
            raise StorageError("object_key_path_traversal")

    @property
    def redacted_id(self) -> str:
        """Stable non-reversible-looking handle id for logs/DTO (not the key)."""
        # Short opaque token derived from UUID namespace of key — not the path itself.
        digest = uuid.uuid5(self.tenant_id, self._object_key)
        return f"objref:{digest}"

    def unsafe_object_key_for_adapter(self) -> str:
        """Adapter-internal only — never pass to MediaResource/audit/errors."""
        return self._object_key

    def __repr__(self) -> str:
        return f"StorageObjectRef(tenant_id={self.tenant_id!s}, id={self.redacted_id!r})"

    def __str__(self) -> str:
        return self.redacted_id

    def __iter__(self):
        # Block accidental dict(dataclass) / model_dump style expansion of raw key.
        raise TypeError("StorageObjectRef is opaque; use redacted_id")


@dataclass(frozen=True, slots=True)
class StoredObjectDescriptor:
    """Opaque stored-object identity — never a filesystem path."""

    tenant_id: uuid.UUID
    object_ref: StorageObjectRef
    content_type: str
    size_bytes: int

    def __repr__(self) -> str:
        return (
            f"StoredObjectDescriptor(tenant_id={self.tenant_id!s}, "
            f"object_ref={self.object_ref.redacted_id!r}, "
            f"content_type={self.content_type!r}, size_bytes={self.size_bytes})"
        )


@dataclass(frozen=True, slots=True)
class TemporaryAccessHandle:
    """Ephemeral access descriptor for adapters — not a permanent private URL."""

    tenant_id: uuid.UUID
    object_ref: StorageObjectRef
    purpose: str
    ttl_seconds: int
    opaque_token: str

    def __repr__(self) -> str:
        return (
            f"TemporaryAccessHandle(tenant_id={self.tenant_id!s}, "
            f"object_ref={self.object_ref.redacted_id!r}, "
            f"purpose={self.purpose!r}, ttl_seconds={self.ttl_seconds}, "
            f"opaque_token='***')"
        )

    def __str__(self) -> str:
        return f"temp:{self.opaque_token[:6]}…/{self.object_ref.redacted_id}"


class StoragePort(Protocol):
    def put_object(
        self,
        *,
        tenant_id: uuid.UUID,
        object_ref: StorageObjectRef,
        data: bytes,
        content_type: str,
        metadata: dict[str, str] | None = None,
    ) -> StoredObjectDescriptor:
        """Store bytes under a tenant-scoped opaque object ref."""

    def get_object_metadata(
        self,
        *,
        tenant_id: uuid.UUID,
        object_ref: StorageObjectRef,
    ) -> StoredObjectDescriptor:
        """Return typed metadata; never exposes backend credentials."""

    def delete_object(self, *, tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> None:
        """Delete orphan object (pre-commit compensation only for newly created refs)."""

    def archive_object(self, *, tenant_id: uuid.UUID, object_ref: StorageObjectRef) -> None:
        """Soft archive / lifecycle marker — hard retention jobs deferred."""

    def generate_temporary_access(
        self,
        *,
        tenant_id: uuid.UUID,
        object_ref: StorageObjectRef,
        purpose: str,
        ttl_seconds: int,
    ) -> TemporaryAccessHandle:
        """Issue ephemeral handle — not a permanent signed URL."""
