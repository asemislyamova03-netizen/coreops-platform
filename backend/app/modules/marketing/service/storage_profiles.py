"""M8-C2a storage resource profile domain service (no HTTP).

Cardinality:
- at most one ACTIVE profile per (tenant_id, mode);
- Mode A and Mode B may be ACTIVE together;
- Mode C (client_bucket) activation forbidden;
- at most one is_default per tenant; default must be ACTIVE;
- default ≠ publish authorization.
"""

from __future__ import annotations

import uuid

from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder
from app.modules.marketing.enums import (
    C2A_ALLOWED_MEDIA_MIME_TYPES,
    DEFAULT_MAX_UPLOAD_BYTES,
    DEFAULT_MAX_URL_LENGTH,
    MAX_UPLOAD_BYTES_HARD_CAP,
    MAX_URL_LENGTH_HARD_CAP,
    MarketingStorageProfileStatus,
    MarketingStorageResourceMode,
)
from app.modules.marketing.exceptions import (
    MarketingStorageProfileDuplicateActiveError,
    MarketingStorageProfileNotFoundError,
    MarketingStorageProfileValidationError,
)
from app.modules.marketing.models import MarketingStorageResourceProfile
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import StorageResourceProfileView


def normalize_mime_list(raw: list[str] | None) -> list[str]:
    if raw is None:
        return sorted(C2A_ALLOWED_MEDIA_MIME_TYPES)
    normalized: list[str] = []
    seen: set[str] = set()
    for item in raw:
        mime = (item or "").strip().lower()
        if mime == "image/jpg":
            mime = "image/jpeg"
        if not mime:
            continue
        if mime not in C2A_ALLOWED_MEDIA_MIME_TYPES:
            raise MarketingStorageProfileValidationError(f"mime_not_allowed:{mime}")
        if mime in seen:
            continue
        seen.add(mime)
        normalized.append(mime)
    if not normalized:
        raise MarketingStorageProfileValidationError("allowed_mime_types_empty")
    return sorted(normalized)


class MarketingStorageProfileService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def create_profile(
        self,
        *,
        mode: MarketingStorageResourceMode,
        display_name: str,
        status: MarketingStorageProfileStatus = MarketingStorageProfileStatus.DISABLED,
        is_default: bool = False,
        max_upload_bytes: int | None = None,
        max_url_length: int | None = None,
        allowed_mime_types: list[str] | None = None,
        user_id: uuid.UUID | None = None,
    ) -> StorageResourceProfileView:
        self._assert_mode_status(mode, status)
        if is_default and status != MarketingStorageProfileStatus.ACTIVE:
            raise MarketingStorageProfileValidationError("default_requires_active")

        name = (display_name or "").strip()
        if not name:
            raise MarketingStorageProfileValidationError("display_name_required")

        upload = self._normalize_upload_bytes(max_upload_bytes)
        url_len = self._normalize_url_length(max_url_length)
        mimes = normalize_mime_list(allowed_mime_types)

        if status == MarketingStorageProfileStatus.ACTIVE:
            existing = self.repo.get_active_storage_profile(self.tenant_id, mode)
            if existing is not None:
                raise MarketingStorageProfileDuplicateActiveError()

        if is_default:
            existing_default = self.repo.get_default_storage_profile(self.tenant_id)
            if existing_default is not None:
                raise MarketingStorageProfileValidationError("default_already_exists")

        row = self.repo.create_storage_profile(
            tenant_id=self.tenant_id,
            mode=mode,
            status=status,
            is_default=is_default,
            display_name=name,
            max_upload_bytes=upload,
            max_url_length=url_len,
            allowed_mime_types=mimes,
            created_by_user_id=user_id,
            updated_by_user_id=user_id,
        )
        self.db.flush()
        AuditRecorder(self.db).audit_log(
            action=AuditAction.CREATE,
            summary="marketing_storage_profile_created",
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type="marketing_storage_resource_profile",
            entity_id=row.id,
            changes_json={
                "mode": mode.value,
                "status": status.value,
                "is_default": is_default,
                "max_upload_bytes": upload,
                "max_url_length": url_len,
                "allowed_mime_types": mimes,
            },
        )
        return StorageResourceProfileView.model_validate(row)

    def activate_profile(
        self,
        profile_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> StorageResourceProfileView:
        row = self._get_or_404(profile_id)
        self._assert_mode_status(row.mode, MarketingStorageProfileStatus.ACTIVE)
        if row.status == MarketingStorageProfileStatus.ACTIVE:
            return StorageResourceProfileView.model_validate(row)

        existing = self.repo.get_active_storage_profile(self.tenant_id, row.mode)
        if existing is not None and existing.id != row.id:
            raise MarketingStorageProfileDuplicateActiveError()

        row.status = MarketingStorageProfileStatus.ACTIVE
        row.updated_by_user_id = user_id
        self.db.flush()
        AuditRecorder(self.db).audit_log(
            action=AuditAction.UPDATE,
            summary="marketing_storage_profile_activated",
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type="marketing_storage_resource_profile",
            entity_id=row.id,
            changes_json={
                "status": row.status.value,
                "mode": row.mode.value,
                "is_default": row.is_default,
            },
        )
        return StorageResourceProfileView.model_validate(row)

    def disable_profile(
        self,
        profile_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> StorageResourceProfileView:
        row = self._get_or_404(profile_id)
        if row.is_default:
            raise MarketingStorageProfileValidationError("cannot_disable_default_profile")
        row.status = MarketingStorageProfileStatus.DISABLED
        row.updated_by_user_id = user_id
        self.db.flush()
        AuditRecorder(self.db).audit_log(
            action=AuditAction.UPDATE,
            summary="marketing_storage_profile_disabled",
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type="marketing_storage_resource_profile",
            entity_id=row.id,
            changes_json={"status": row.status.value, "mode": row.mode.value},
        )
        return StorageResourceProfileView.model_validate(row)

    def set_default_profile(
        self,
        profile_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> StorageResourceProfileView:
        row = self._get_or_404(profile_id)
        if row.status != MarketingStorageProfileStatus.ACTIVE:
            raise MarketingStorageProfileValidationError("default_requires_active")
        self._assert_mode_status(row.mode, row.status)

        current = self.repo.get_default_storage_profile(self.tenant_id)
        if current is not None and current.id != row.id:
            current.is_default = False
            current.updated_by_user_id = user_id
            self.db.flush()

        row.is_default = True
        row.updated_by_user_id = user_id
        self.db.flush()
        AuditRecorder(self.db).audit_log(
            action=AuditAction.UPDATE,
            summary="marketing_storage_profile_default_set",
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type="marketing_storage_resource_profile",
            entity_id=row.id,
            changes_json={
                "is_default": True,
                "mode": row.mode.value,
                "status": row.status.value,
            },
        )
        return StorageResourceProfileView.model_validate(row)

    def get_profile(self, profile_id: uuid.UUID) -> StorageResourceProfileView:
        return StorageResourceProfileView.model_validate(self._get_or_404(profile_id))

    def get_active_storage_profile(
        self, mode: MarketingStorageResourceMode
    ) -> StorageResourceProfileView | None:
        row = self.repo.get_active_storage_profile(self.tenant_id, mode)
        if row is None:
            return None
        return StorageResourceProfileView.model_validate(row)

    def get_default_profile(self) -> StorageResourceProfileView | None:
        """Default is used only when mode is not explicitly requested."""
        row = self.repo.get_default_storage_profile(self.tenant_id)
        if row is None:
            return None
        return StorageResourceProfileView.model_validate(row)

    def list_profiles(self) -> list[StorageResourceProfileView]:
        rows = self.repo.list_storage_profiles(self.tenant_id)
        return [StorageResourceProfileView.model_validate(r) for r in rows]

    def resolve_effective_limits(
        self, profile: MarketingStorageResourceProfile
    ) -> tuple[int, int, list[str]]:
        upload = profile.max_upload_bytes or DEFAULT_MAX_UPLOAD_BYTES
        url_len = profile.max_url_length or DEFAULT_MAX_URL_LENGTH
        mimes = list(profile.allowed_mime_types or sorted(C2A_ALLOWED_MEDIA_MIME_TYPES))
        return upload, url_len, mimes

    def _get_or_404(self, profile_id: uuid.UUID) -> MarketingStorageResourceProfile:
        row = self.repo.get_storage_profile(self.tenant_id, profile_id)
        if row is None:
            raise MarketingStorageProfileNotFoundError()
        return row

    @staticmethod
    def _assert_mode_status(
        mode: MarketingStorageResourceMode,
        status: MarketingStorageProfileStatus,
    ) -> None:
        if mode == MarketingStorageResourceMode.CLIENT_BUCKET:
            if status == MarketingStorageProfileStatus.ACTIVE:
                raise MarketingStorageProfileValidationError("client_bucket_not_supported")
            # Creating disabled reserved rows is still forbidden in C2a create path.
            raise MarketingStorageProfileValidationError("client_bucket_not_supported")

    @staticmethod
    def _normalize_upload_bytes(value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0 or value > MAX_UPLOAD_BYTES_HARD_CAP:
            raise MarketingStorageProfileValidationError("max_upload_bytes_out_of_range")
        return value

    @staticmethod
    def _normalize_url_length(value: int | None) -> int | None:
        if value is None:
            return None
        if value <= 0 or value > MAX_URL_LENGTH_HARD_CAP:
            raise MarketingStorageProfileValidationError("max_url_length_out_of_range")
        return value
