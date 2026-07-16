import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import NotFoundError
from app.modules.auth.models import User
from app.modules.marketing.enums import (
    ALLOWED_MEDIA_MIME_TYPES,
    MarketingMediaAssetStatus,
    MarketingMediaValidationStatus,
)
from app.modules.marketing.exceptions import MarketingInvalidMimeTypeError
from app.modules.marketing.models import MarketingMediaAsset, MarketingPublicationPack
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import MediaCreate, MediaUpdate, PackMediaAssetResponse
from app.modules.marketing.service.approval_reset import reset_pack_after_content_change


def _normalize_mime(mime_type: str) -> str:
    return mime_type.strip().lower()


def _validate_mime(mime_type: str) -> str:
    normalized = _normalize_mime(mime_type)
    if normalized not in ALLOWED_MEDIA_MIME_TYPES:
        raise MarketingInvalidMimeTypeError(mime_type)
    return normalized


class MarketingMediaService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def list_pack_media(self, pack_id: uuid.UUID) -> list[PackMediaAssetResponse]:
        self._get_pack_or_404(pack_id)
        rows = self.repo.list_pack_media(self.tenant_id, pack_id)
        return [PackMediaAssetResponse.model_validate(row) for row in rows]

    def attach_media(
        self,
        user: User,
        pack_id: uuid.UUID,
        payload: MediaCreate,
    ) -> PackMediaAssetResponse:
        """Legacy attach path (git_path / existing API).

        Compatibility: existing assets stay legacy_unverified — never auto-validated.
        Mode A/B lifecycle services are separate domain entrypoints.
        """
        pack = self._get_pack_or_404(pack_id)
        mime_type = _validate_mime(payload.mime_type)

        asset = self.repo.create_media_asset(
            tenant_id=self.tenant_id,
            pack_id=pack.id,
            role=payload.role,
            file_name=payload.file_name,
            mime_type=mime_type,
            storage_provider=payload.storage_provider,
            storage_key=payload.storage_key,
            public_url=payload.public_url,
            preview_url=payload.preview_url,
            width=payload.width,
            height=payload.height,
            alt_text=payload.alt_text,
            status=MarketingMediaAssetStatus.STORED,
            validation_status=MarketingMediaValidationStatus.LEGACY_UNVERIFIED,
            declared_mime_type=mime_type,
            metadata_json=payload.metadata_json,
            created_by_user_id=user.id,
            updated_by_user_id=user.id,
        )
        reset_pack_after_content_change(pack, user_id=user.id)
        self.db.flush()
        return PackMediaAssetResponse.model_validate(asset)

    def update_media(
        self,
        user: User,
        asset_id: uuid.UUID,
        payload: MediaUpdate,
    ) -> PackMediaAssetResponse:
        asset = self._get_asset_or_404(asset_id)

        if payload.file_name is not None:
            asset.file_name = payload.file_name
        if payload.mime_type is not None:
            asset.mime_type = _validate_mime(payload.mime_type)
        if payload.storage_provider is not None:
            asset.storage_provider = payload.storage_provider
        if payload.storage_key is not None:
            asset.storage_key = payload.storage_key
        if payload.public_url is not None:
            asset.public_url = payload.public_url
        if payload.preview_url is not None:
            asset.preview_url = payload.preview_url
        if payload.width is not None:
            asset.width = payload.width
        if payload.height is not None:
            asset.height = payload.height
        if payload.role is not None:
            asset.role = payload.role
        if payload.alt_text is not None:
            asset.alt_text = payload.alt_text
        if payload.status is not None:
            asset.status = payload.status
        if payload.metadata_json is not None:
            asset.metadata_json = payload.metadata_json

        asset.updated_by_user_id = user.id
        self.db.flush()
        pack = self._get_pack_or_404(asset.pack_id) if asset.pack_id else None
        if pack is not None:
            reset_pack_after_content_change(pack, user_id=user.id)
            self.db.flush()
        return PackMediaAssetResponse.model_validate(asset)

    def archive_media(self, user: User, asset_id: uuid.UUID) -> PackMediaAssetResponse:
        asset = self._get_asset_or_404(asset_id)
        pack_id = asset.pack_id
        asset.status = MarketingMediaAssetStatus.ARCHIVED
        asset.updated_by_user_id = user.id
        self.db.flush()
        if pack_id is not None:
            pack = self._get_pack_or_404(pack_id)
            reset_pack_after_content_change(pack, user_id=user.id)
            self.db.flush()
        return PackMediaAssetResponse.model_validate(asset)

    def _get_pack_or_404(self, pack_id: uuid.UUID) -> MarketingPublicationPack:
        pack = self.repo.get_pack(self.tenant_id, pack_id)
        if pack is None:
            raise NotFoundError("Pack not found")
        return pack

    def _get_asset_or_404(self, asset_id: uuid.UUID) -> MarketingMediaAsset:
        asset = self.repo.get_media_asset(self.tenant_id, asset_id)
        if asset is None:
            raise NotFoundError("Media asset not found")
        return asset
