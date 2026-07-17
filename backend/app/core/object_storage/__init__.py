"""Core object_storage package — StoragePort and test adapters.

Follow-up (production adapter gate): process-crash orphan sweeper for
put-before-commit failures is not implemented in M8-C2a.
"""

from app.core.object_storage.port import (
    StorageError,
    StorageObjectRef,
    StoragePort,
    StoredObjectDescriptor,
    TemporaryAccessHandle,
)

__all__ = [
    "StorageError",
    "StorageObjectRef",
    "StoragePort",
    "StoredObjectDescriptor",
    "TemporaryAccessHandle",
]
