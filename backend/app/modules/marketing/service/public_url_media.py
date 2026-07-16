"""M8-C2a Mode B public URL registration (static validation only)."""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder
from app.modules.marketing.enums import (
    MarketingMediaAssetStatus,
    MarketingMediaValidationStatus,
    MarketingStorageProfileStatus,
    MarketingStorageResourceMode,
)
from app.modules.marketing.exceptions import (
    MarketingManagedMediaLifecycleError,
    MarketingStorageProfileNotFoundError,
    MarketingStorageProfileValidationError,
)
from app.modules.marketing.models import MarketingMediaAsset
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import ManagedMediaAssetView
from app.modules.marketing.service.managed_media_lifecycle import (
    normalize_c2a_mime,
    sanitize_filename,
)
from app.modules.marketing.service.media_resource import MediaResource, resolve_media_resource
from app.modules.marketing.service.public_url_validator import validate_public_url
from app.modules.marketing.service.storage_profiles import MarketingStorageProfileService


class PublicUrlMediaRegistrationService:
    """Register client public URLs without fetch — registered_unverified only."""

    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def register_public_url(
        self,
        *,
        pack_id: uuid.UUID | None,
        file_name: str,
        mime_type: str,
        public_url: str,
        role: str = "instagram_feed",
        user_id: uuid.UUID | None = None,
    ) -> ManagedMediaAssetView:
        mime = normalize_c2a_mime(mime_type)
        safe_name = sanitize_filename(file_name)

        profile = self.repo.get_active_storage_profile(
            self.tenant_id,
            MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
        )
        if profile is None:
            raise MarketingStorageProfileNotFoundError()
        if profile.status != MarketingStorageProfileStatus.ACTIVE:
            raise MarketingStorageProfileValidationError("profile_not_active")
        if profile.mode != MarketingStorageResourceMode.CLIENT_PUBLIC_URL:
            raise MarketingManagedMediaLifecycleError("active_profile_not_client_public_url")

        _, max_url_length, allowed = MarketingStorageProfileService(
            self.db, self.tenant_id
        ).resolve_effective_limits(profile)
        if mime not in allowed:
            raise MarketingManagedMediaLifecycleError(f"mime_not_in_profile:{mime}")

        validated = validate_public_url(public_url, max_url_length=max_url_length)

        if pack_id is not None:
            pack = self.repo.get_pack(self.tenant_id, pack_id)
            if pack is None:
                raise MarketingManagedMediaLifecycleError("pack_not_found")

        asset = MarketingMediaAsset(
            tenant_id=self.tenant_id,
            pack_id=pack_id,
            role=role,
            file_name=safe_name,
            mime_type=mime,
            storage_provider="client_public_url",
            storage_key=f"url:{validated.host_fingerprint}",
            public_url=validated.normalized_url,
            preview_url=None,
            status=MarketingMediaAssetStatus.STORED,
            validation_status=MarketingMediaValidationStatus.REGISTERED_UNVERIFIED,
            declared_mime_type=mime,
            declared_size_bytes=None,
            verified_mime_type=None,
            verified_size_bytes=None,  # Mode B: external URL size remains unverified
            storage_profile_id=profile.id,
            resource_mode=MarketingStorageResourceMode.CLIENT_PUBLIC_URL,
            metadata_json={"host_fingerprint": validated.host_fingerprint},
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        self.db.add(asset)
        self.db.flush()
        AuditRecorder(self.db).audit_log(
            action=AuditAction.CREATE,
            summary="marketing_public_url_registered",
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type="marketing_media_asset",
            entity_id=asset.id,
            changes_json={
                "mode": MarketingStorageResourceMode.CLIENT_PUBLIC_URL.value,
                "mime": mime,
                "validation_status": MarketingMediaValidationStatus.REGISTERED_UNVERIFIED.value,
                "host_fingerprint": validated.host_fingerprint,
                "result": "ok",
            },
        )
        return ManagedMediaAssetView.model_validate(asset)

    def resolve_resource(self, asset_id: uuid.UUID) -> MediaResource:
        asset = self.repo.get_media_asset(self.tenant_id, asset_id)
        if asset is None:
            raise MarketingManagedMediaLifecycleError("media_asset_not_found")
        fp = (asset.metadata_json or {}).get("host_fingerprint", "")
        return resolve_media_resource(asset, host_fingerprint=str(fp))
