"""M8-C2a Mode A managed-media lifecycle (dedicated UnitOfWork).

External storage side-effects are not atomic with DB:
  - storage put succeeds, DB commit fails → delete only the newly created orphan;
  - DB commit succeeds → later exception must NOT delete the bound object.
Never commit/rollback a caller/request Session.

Follow-up (production adapter): process-crash orphan sweeper for put-before-commit
is not implemented in M8-C2a.
"""

from __future__ import annotations

import re
import uuid
from collections.abc import Callable
from contextlib import contextmanager
from typing import Iterator

from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import AuditAction
from app.core.object_storage.content_validation import (
    ContentValidationPort,
    DeclaredMimeMagicByteValidator,
)
from app.core.object_storage.port import StorageError, StorageObjectRef, StoragePort
from app.modules.audit.recorder import AuditRecorder
from app.modules.marketing.enums import (
    C2A_ALLOWED_MEDIA_MIME_TYPES,
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
from app.modules.marketing.models import MarketingMediaAsset, MarketingStorageResourceProfile
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import ManagedMediaAssetView
from app.modules.marketing.service.media_resource import MediaResource, resolve_media_resource
from app.modules.marketing.service.storage_profiles import MarketingStorageProfileService

SessionFactory = Callable[[], Session] | sessionmaker[Session]
_SAFE_FILENAME = re.compile(r"^[A-Za-z0-9._-]+$")


def build_object_ref(
    *,
    tenant_id: uuid.UUID,
    asset_id: uuid.UUID,
    file_name: str,
) -> StorageObjectRef:
    safe = sanitize_filename(file_name)
    key = f"marketing/tenants/{tenant_id}/media/{asset_id}/{safe}"
    return StorageObjectRef(tenant_id=tenant_id, _object_key=key)


def sanitize_filename(file_name: str) -> str:
    name = (file_name or "").strip()
    if not name:
        raise MarketingManagedMediaLifecycleError("file_name_required")
    if "/" in name or "\\" in name or ".." in name:
        raise MarketingManagedMediaLifecycleError("path_traversal_filename")
    if not _SAFE_FILENAME.match(name):
        raise MarketingManagedMediaLifecycleError("unsafe_filename")
    if len(name) > 255:
        raise MarketingManagedMediaLifecycleError("file_name_too_long")
    return name


def normalize_c2a_mime(mime_type: str) -> str:
    mime = (mime_type or "").strip().lower()
    if mime == "image/jpg":
        mime = "image/jpeg"
    if mime not in C2A_ALLOWED_MEDIA_MIME_TYPES:
        raise MarketingManagedMediaLifecycleError(f"mime_not_allowed:{mime}")
    return mime


class ManagedMediaLifecycleService:
    """Mode A bytes → StoragePort → DB asset with compensation discipline."""

    def __init__(
        self,
        tenant_id: uuid.UUID,
        *,
        session_factory: SessionFactory,
        storage: StoragePort,
        content_validator: ContentValidationPort | None = None,
    ):
        self.tenant_id = tenant_id
        self._session_factory = session_factory
        self.storage = storage
        self.content_validator = content_validator or DeclaredMimeMagicByteValidator()

    @contextmanager
    def _uow(self) -> Iterator[Session]:
        db = self._session_factory()
        try:
            yield db
        finally:
            db.close()

    def store_managed_media(
        self,
        *,
        pack_id: uuid.UUID | None,
        file_name: str,
        mime_type: str,
        data: bytes,
        role: str = "instagram_feed",
        user_id: uuid.UUID | None = None,
    ) -> ManagedMediaAssetView:
        mime = normalize_c2a_mime(mime_type)
        safe_name = sanitize_filename(file_name)
        if not data:
            raise MarketingManagedMediaLifecycleError("empty_payload")

        asset_id = uuid.uuid4()
        object_ref = build_object_ref(
            tenant_id=self.tenant_id,
            asset_id=asset_id,
            file_name=safe_name,
        )
        stored = False
        db_commit_succeeded = False

        with self._uow() as db:
            try:
                profile = self._require_active_managed_profile(db)
                limits = MarketingStorageProfileService(db, self.tenant_id).resolve_effective_limits(
                    profile
                )
                max_upload, _, allowed = limits
                if mime not in allowed:
                    raise MarketingManagedMediaLifecycleError(f"mime_not_in_profile:{mime}")
                if len(data) > max_upload:
                    raise MarketingManagedMediaLifecycleError("payload_too_large")
                if not self.content_validator.validate_magic_bytes(data, mime):
                    raise MarketingManagedMediaLifecycleError("content_mime_mismatch")

                if pack_id is not None:
                    pack = MarketingRepository(db).get_pack(self.tenant_id, pack_id)
                    if pack is None:
                        raise MarketingManagedMediaLifecycleError("pack_not_found")

                try:
                    self.storage.put_object(
                        tenant_id=self.tenant_id,
                        object_ref=object_ref,
                        data=data,
                        content_type=mime,
                        metadata={"role": role},
                    )
                except StorageError as exc:
                    if exc.code == "object_key_collision":
                        raise MarketingManagedMediaLifecycleError("storage_object_collision") from None
                    raise MarketingManagedMediaLifecycleError("storage_put_failed") from None
                stored = True

                # Persist opaque internal key for StoragePort only — never in audit/errors.
                asset = MarketingMediaAsset(
                    id=asset_id,
                    tenant_id=self.tenant_id,
                    pack_id=pack_id,
                    role=role,
                    file_name=safe_name,
                    mime_type=mime,
                    storage_provider="flexity_managed",
                    storage_key=object_ref.unsafe_object_key_for_adapter(),
                    public_url=None,
                    preview_url=None,
                    status=MarketingMediaAssetStatus.STORED,
                    validation_status=MarketingMediaValidationStatus.VALIDATED_METADATA,
                    declared_mime_type=mime,
                    # No separate request-declared size in this API — do not fabricate.
                    declared_size_bytes=None,
                    verified_mime_type=None,  # magic header only ≠ verified
                    verified_size_bytes=len(data),
                    storage_profile_id=profile.id,
                    resource_mode=MarketingStorageResourceMode.FLEXITY_MANAGED,
                    metadata_json={"object_ref_id": object_ref.redacted_id},
                    created_by_user_id=user_id,
                    updated_by_user_id=user_id,
                )
                db.add(asset)
                AuditRecorder(db).audit_log(
                    action=AuditAction.CREATE,
                    summary="marketing_managed_media_stored",
                    tenant_id=self.tenant_id,
                    user_id=user_id,
                    entity_type="marketing_media_asset",
                    entity_id=asset_id,
                    changes_json={
                        "mode": MarketingStorageResourceMode.FLEXITY_MANAGED.value,
                        "mime": mime,
                        "byte_count": len(data),
                        "validation_status": MarketingMediaValidationStatus.VALIDATED_METADATA.value,
                        "object_ref_id": object_ref.redacted_id,
                        "result": "ok",
                    },
                )
                db.commit()
                db_commit_succeeded = True
                db.refresh(asset)
                return ManagedMediaAssetView.model_validate(asset)
            except Exception as exc:
                if stored and not db_commit_succeeded:
                    try:
                        self.storage.delete_object(
                            tenant_id=self.tenant_id,
                            object_ref=object_ref,
                        )
                    except StorageError:
                        raise MarketingManagedMediaLifecycleError(
                            "storage_orphan_compensation_failed"
                        ) from None
                try:
                    db.rollback()
                except Exception:
                    pass
                if isinstance(
                    exc,
                    (
                        MarketingManagedMediaLifecycleError,
                        MarketingStorageProfileNotFoundError,
                        MarketingStorageProfileValidationError,
                    ),
                ):
                    raise
                # Never leak raw keys/bytes via chained messages.
                raise MarketingManagedMediaLifecycleError("managed_media_store_failed") from None

    def resolve_resource(self, asset_id: uuid.UUID) -> MediaResource:
        with self._uow() as db:
            asset = MarketingRepository(db).get_media_asset(self.tenant_id, asset_id)
            if asset is None:
                raise MarketingManagedMediaLifecycleError("media_asset_not_found")
            object_ref = StorageObjectRef(
                tenant_id=self.tenant_id,
                _object_key=asset.storage_key,
            )
            handle = self.storage.generate_temporary_access(
                tenant_id=self.tenant_id,
                object_ref=object_ref,
                purpose="adapter_read",
                ttl_seconds=60,
            )
            return resolve_media_resource(asset, temporary_access=handle)

    def _require_active_managed_profile(
        self, db: Session
    ) -> MarketingStorageResourceProfile:
        profile = MarketingRepository(db).get_active_storage_profile(
            self.tenant_id,
            MarketingStorageResourceMode.FLEXITY_MANAGED,
        )
        if profile is None:
            raise MarketingStorageProfileNotFoundError()
        if profile.status != MarketingStorageProfileStatus.ACTIVE:
            raise MarketingStorageProfileValidationError("profile_not_active")
        if profile.mode != MarketingStorageResourceMode.FLEXITY_MANAGED:
            raise MarketingManagedMediaLifecycleError("active_profile_not_flexity_managed")
        return profile
