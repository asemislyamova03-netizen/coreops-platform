"""Typed MediaResource handle for future publish adapters (M8-E+)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass
from typing import Any, Literal

from app.core.object_storage.port import TemporaryAccessHandle
from app.modules.marketing.enums import (
    MarketingMediaValidationStatus,
    MarketingStorageResourceMode,
)
from app.modules.marketing.exceptions import MarketingManagedMediaLifecycleError
from app.modules.marketing.models import MarketingMediaAsset


@dataclass(frozen=True, slots=True)
class ExternalUrlReference:
    """Mode B external resource — host fingerprint only, never full URL here."""

    host_fingerprint: str
    declared_mime_type: str


@dataclass(frozen=True, slots=True)
class OpaqueAccessHandleView:
    """Marketing-facing redacted access handle — no raw object key."""

    tenant_id: uuid.UUID
    object_ref_id: str
    purpose: str
    ttl_seconds: int
    opaque_token: str

    def __repr__(self) -> str:
        return (
            f"OpaqueAccessHandleView(tenant_id={self.tenant_id!s}, "
            f"object_ref_id={self.object_ref_id!r}, purpose={self.purpose!r}, "
            f"ttl_seconds={self.ttl_seconds}, opaque_token='***')"
        )


@dataclass(frozen=True, slots=True)
class MediaResource:
    asset_id: uuid.UUID
    tenant_id: uuid.UUID
    mode: MarketingStorageResourceMode
    delivery_kind: Literal["temporary_handle", "external_registered", "legacy_unresolved"]
    validation_status: MarketingMediaValidationStatus
    declared_mime_type: str
    size_bytes: int | None
    access: OpaqueAccessHandleView | ExternalUrlReference | None

    def model_dump(self) -> dict[str, Any]:
        """Safe serialization — never includes raw storage keys."""
        access_payload: dict[str, Any] | None
        if isinstance(self.access, OpaqueAccessHandleView):
            access_payload = {
                "tenant_id": str(self.access.tenant_id),
                "object_ref_id": self.access.object_ref_id,
                "purpose": self.access.purpose,
                "ttl_seconds": self.access.ttl_seconds,
                "opaque_token": "***",
            }
        elif isinstance(self.access, ExternalUrlReference):
            access_payload = asdict(self.access)
        else:
            access_payload = None
        return {
            "asset_id": str(self.asset_id),
            "tenant_id": str(self.tenant_id),
            "mode": self.mode.value,
            "delivery_kind": self.delivery_kind,
            "validation_status": self.validation_status.value,
            "declared_mime_type": self.declared_mime_type,
            "size_bytes": self.size_bytes,
            "access": access_payload,
        }

    def __repr__(self) -> str:
        return (
            f"MediaResource(asset_id={self.asset_id!s}, tenant_id={self.tenant_id!s}, "
            f"mode={self.mode.value!r}, delivery_kind={self.delivery_kind!r}, "
            f"validation_status={self.validation_status.value!r}, access={self.access!r})"
        )


def _to_opaque_view(handle: TemporaryAccessHandle) -> OpaqueAccessHandleView:
    return OpaqueAccessHandleView(
        tenant_id=handle.tenant_id,
        object_ref_id=handle.object_ref.redacted_id,
        purpose=handle.purpose,
        ttl_seconds=handle.ttl_seconds,
        opaque_token=handle.opaque_token,
    )


def _safe_size_bytes(asset: MarketingMediaAsset) -> int | None:
    """Prefer verified bytes when present; otherwise declared metadata only."""
    if asset.verified_size_bytes is not None:
        return asset.verified_size_bytes
    return asset.declared_size_bytes


def resolve_media_resource(
    asset: MarketingMediaAsset,
    *,
    temporary_access: TemporaryAccessHandle | None = None,
    host_fingerprint: str | None = None,
) -> MediaResource:
    """Build adapter-facing MediaResource from persisted asset metadata."""
    mode = asset.resource_mode
    if mode is None:
        return MediaResource(
            asset_id=asset.id,
            tenant_id=asset.tenant_id,
            mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
            delivery_kind="legacy_unresolved",
            validation_status=asset.validation_status,
            declared_mime_type=asset.declared_mime_type or asset.mime_type,
            size_bytes=_safe_size_bytes(asset),
            access=None,
        )

    if mode == MarketingStorageResourceMode.FLEXITY_MANAGED:
        if temporary_access is None:
            raise MarketingManagedMediaLifecycleError("temporary_access_required")
        return MediaResource(
            asset_id=asset.id,
            tenant_id=asset.tenant_id,
            mode=mode,
            delivery_kind="temporary_handle",
            validation_status=asset.validation_status,
            declared_mime_type=asset.declared_mime_type or asset.mime_type,
            size_bytes=_safe_size_bytes(asset),
            access=_to_opaque_view(temporary_access),
        )

    if mode == MarketingStorageResourceMode.CLIENT_PUBLIC_URL:
        fp = host_fingerprint or ""
        return MediaResource(
            asset_id=asset.id,
            tenant_id=asset.tenant_id,
            mode=mode,
            delivery_kind="external_registered",
            validation_status=asset.validation_status,
            declared_mime_type=asset.declared_mime_type or asset.mime_type,
            size_bytes=_safe_size_bytes(asset),
            access=ExternalUrlReference(
                host_fingerprint=fp,
                declared_mime_type=asset.declared_mime_type or asset.mime_type,
            ),
        )

    raise MarketingManagedMediaLifecycleError("client_bucket_not_supported")
