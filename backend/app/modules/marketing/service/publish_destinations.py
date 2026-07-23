"""M8-D2 tenant-scoped publish destination HTTP orchestration (no adapters / dry-run / execute)."""

from __future__ import annotations

import uuid

from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import AuditAction
from app.modules.audit.recorder import AuditRecorder
from app.modules.marketing.enums import (
    MarketingDestinationStatus,
    MarketingDestinationValidationStatus,
    MarketingPublishDestinationType,
    destination_capability_enabled,
)
from app.modules.marketing.exceptions import (
    MarketingPublishDestinationNotFoundError,
    MarketingPublishDestinationValidationError,
    MarketingPublishingConnectionNotFoundError,
)
from app.modules.marketing.models import MarketingPublishDestination
from app.modules.marketing.repository import MarketingRepository
from app.modules.marketing.schemas import PublishDestinationView

_ENTITY_TYPE = "marketing_publish_destination"
_PROVIDER_ADAPTER_UNAVAILABLE = "provider_adapter_unavailable"
_CAPABILITY_DISABLED = "capability_disabled"


class MarketingPublishDestinationService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.repo = MarketingRepository(db)

    def create_destination(
        self,
        *,
        publishing_connection_id: uuid.UUID,
        destination_type: MarketingPublishDestinationType,
        external_id: str,
        display_name: str,
        metadata_json: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> PublishDestinationView:
        try:
            row = self.repo.create_publish_destination(
                tenant_id=self.tenant_id,
                publishing_connection_id=publishing_connection_id,
                destination_type=destination_type,
                external_id=external_id,
                display_name=display_name,
                metadata_json=metadata_json,
                created_by_user_id=user_id,
                updated_by_user_id=user_id,
            )
            self.db.flush()
        except MarketingPublishingConnectionNotFoundError:
            # Cross-tenant or missing connection → 404 (fail closed).
            raise
        except IntegrityError as exc:
            self.db.rollback()
            raise MarketingPublishDestinationValidationError(
                "publish_destination_duplicate"
            ) from exc

        self._audit(
            action=AuditAction.CREATE,
            summary=f"Publish destination created: {destination_type.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={
                "destination_type": destination_type.value,
                "publishing_connection_id": str(publishing_connection_id),
                "status": row.status.value,
            },
        )
        return self._to_view(row)

    def get_destination(self, destination_id: uuid.UUID) -> PublishDestinationView:
        return self._to_view(self._get_or_404(destination_id))

    def list_destinations(
        self,
        *,
        status: MarketingDestinationStatus | None = None,
        publishing_connection_id: uuid.UUID | None = None,
        destination_type: MarketingPublishDestinationType | None = None,
        include_archived: bool = False,
    ) -> list[PublishDestinationView]:
        if publishing_connection_id is not None:
            connection = self.repo.get_publishing_connection(
                self.tenant_id, publishing_connection_id
            )
            if connection is None:
                raise MarketingPublishingConnectionNotFoundError()

        rows = self.repo.list_publish_destinations_by_tenant(
            self.tenant_id,
            status=status,
            publishing_connection_id=publishing_connection_id,
            destination_type=destination_type,
            exclude_archived=not include_archived,
        )
        return [self._to_view(row) for row in rows]

    def update_destination(
        self,
        destination_id: uuid.UUID,
        *,
        display_name: str | None = None,
        external_id: str | None = None,
        metadata_json: dict | None = None,
        user_id: uuid.UUID | None = None,
    ) -> PublishDestinationView:
        row = self._get_or_404(destination_id)
        changes: dict[str, object] = {}

        if display_name is not None or metadata_json is not None:
            before_name = row.display_name
            self.repo.update_publish_destination_display(
                self.tenant_id,
                destination_id,
                display_name=display_name,
                metadata_json=metadata_json,
                updated_by_user_id=user_id,
            )
            if display_name is not None and before_name != row.display_name:
                changes["display_name"] = {"before": before_name, "after": row.display_name}
            if metadata_json is not None:
                changes["metadata_changed"] = True

        if external_id is not None:
            before_ext = row.external_id
            try:
                self.repo.update_publish_destination_external_id(
                    self.tenant_id,
                    destination_id,
                    external_id,
                    updated_by_user_id=user_id,
                )
            except IntegrityError as exc:
                self.db.rollback()
                raise MarketingPublishDestinationValidationError(
                    "publish_destination_duplicate"
                ) from exc
            if before_ext != row.external_id:
                changes["external_id"] = {"before": before_ext, "after": row.external_id}

        if not changes and display_name is None and external_id is None and metadata_json is None:
            return self._to_view(row)

        try:
            self.db.flush()
        except IntegrityError as exc:
            self.db.rollback()
            raise MarketingPublishDestinationValidationError(
                "publish_destination_duplicate"
            ) from exc

        if changes:
            self._audit(
                action=AuditAction.UPDATE,
                summary=f"Publish destination updated: {row.destination_type.value}",
                entity_id=row.id,
                user_id=user_id,
                changes_json=changes,
            )
        return self._to_view(row)

    def enable_destination(
        self,
        destination_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> PublishDestinationView:
        row = self.repo.enable_publish_destination(
            self.tenant_id, destination_id, updated_by_user_id=user_id
        )
        self.db.flush()
        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publish destination enabled: {row.destination_type.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={"status": row.status.value},
        )
        return self._to_view(row)

    def disable_destination(
        self,
        destination_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> PublishDestinationView:
        row = self.repo.disable_publish_destination(
            self.tenant_id, destination_id, updated_by_user_id=user_id
        )
        self.db.flush()
        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publish destination disabled: {row.destination_type.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={"status": row.status.value},
        )
        return self._to_view(row)

    def archive_destination(
        self,
        destination_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> PublishDestinationView:
        row = self.repo.archive_publish_destination(
            self.tenant_id, destination_id, updated_by_user_id=user_id
        )
        self.db.flush()
        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publish destination archived: {row.destination_type.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={"status": row.status.value},
        )
        return self._to_view(row)

    def validate_destination(
        self,
        destination_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
    ) -> PublishDestinationView:
        """Structural validation only.

        Without a provider adapter this never claims provider success:
        capability-disabled → unavailable; otherwise → unavailable (adapter missing).
        Structural invalid shapes → invalid.
        """
        row = self._get_or_404(destination_id)
        if row.status == MarketingDestinationStatus.ARCHIVED:
            raise MarketingPublishDestinationValidationError("archived_destination_immutable")

        external = (row.external_id or "").strip()
        display = (row.display_name or "").strip()
        if not external or not display:
            row = self.repo.structural_validate_publish_destination(
                self.tenant_id,
                destination_id,
                validation_status=MarketingDestinationValidationStatus.INVALID,
                validation_error_code="structural_required_fields",
                updated_by_user_id=user_id,
            )
        elif not destination_capability_enabled(row.destination_type):
            row = self.repo.structural_validate_publish_destination(
                self.tenant_id,
                destination_id,
                validation_status=MarketingDestinationValidationStatus.UNAVAILABLE,
                validation_error_code=_CAPABILITY_DISABLED,
                updated_by_user_id=user_id,
            )
        else:
            # No provider adapter in D2 — explicit unavailable; never invent VALID.
            row = self.repo.structural_validate_publish_destination(
                self.tenant_id,
                destination_id,
                validation_status=MarketingDestinationValidationStatus.UNAVAILABLE,
                validation_error_code=_PROVIDER_ADAPTER_UNAVAILABLE,
                updated_by_user_id=user_id,
            )

        self.db.flush()
        self._audit(
            action=AuditAction.UPDATE,
            summary=f"Publish destination structural validate: {row.destination_type.value}",
            entity_id=row.id,
            user_id=user_id,
            changes_json={
                "validation_status": row.validation_status.value,
                "validation_error_code": row.validation_error_code,
            },
        )
        return self._to_view(row)

    def _get_or_404(self, destination_id: uuid.UUID) -> MarketingPublishDestination:
        row = self.repo.get_publish_destination(self.tenant_id, destination_id)
        if row is None:
            raise MarketingPublishDestinationNotFoundError()
        return row

    def _to_view(self, row: MarketingPublishDestination) -> PublishDestinationView:
        return PublishDestinationView.model_validate(row)

    def _audit(
        self,
        *,
        action: AuditAction,
        summary: str,
        entity_id: uuid.UUID,
        user_id: uuid.UUID | None,
        changes_json: dict[str, object],
    ) -> None:
        AuditRecorder(self.db).audit_log(
            action=action,
            summary=summary,
            tenant_id=self.tenant_id,
            user_id=user_id,
            entity_type=_ENTITY_TYPE,
            entity_id=entity_id,
            changes_json=changes_json,
        )
