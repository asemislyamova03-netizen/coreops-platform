import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.enums import AuditAction, SecurityEventType, TenantRole
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import get_provider_staff
from app.modules.audit.recorder import AuditRecorder
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import (
    AuditLogResponse,
    DataAccessLogResponse,
    ImportBatchEntitySummary,
    ImportBatchSummary,
    SecurityEventResponse,
)
from app.modules.auth.models import User
from app.modules.tenants.repository import TenantRepository


class AuditService:
    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditRepository(db)
        self.tenants = TenantRepository(db)

    def list_audit_logs(
        self,
        user: User,
        *,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        action: AuditAction | None = None,
        limit: int = 100,
    ) -> list[AuditLogResponse]:
        if tenant_id:
            self._ensure_tenant_audit_access(user, tenant_id)
        else:
            self._ensure_provider_auditor(user)

        logs = self.repo.list_audit_logs(
            tenant_id=tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            action=action,
            limit=limit,
        )
        return [AuditLogResponse.model_validate(entry) for entry in logs]

    def list_data_access(
        self,
        user: User,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        limit: int = 100,
    ) -> list[DataAccessLogResponse]:
        self._ensure_tenant_audit_access(user, tenant_id)
        entries = self.repo.list_data_access_logs(
            tenant_id,
            user_id=user_id,
            entity_type=entity_type,
            limit=limit,
        )
        return [DataAccessLogResponse.model_validate(entry) for entry in entries]

    def list_security_events(
        self,
        user: User,
        *,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        event_type: SecurityEventType | None = None,
        limit: int = 100,
    ) -> list[SecurityEventResponse]:
        if tenant_id:
            self._ensure_tenant_audit_access(user, tenant_id)
        else:
            self._ensure_provider_auditor(user)

        events = self.repo.list_security_events(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            limit=limit,
        )
        return [SecurityEventResponse.model_validate(event) for event in events]

    def build_import_batch_summary(
        self,
        *,
        tenant_id: uuid.UUID,
        created_by_user_id: uuid.UUID | None,
        source_system: str,
        entities: list[ImportBatchEntitySummary],
        started_at: datetime | None = None,
        finished_at: datetime | None = None,
        notes: str | None = None,
    ) -> ImportBatchSummary:
        total_source_rows = sum(item.source_count for item in entities)
        total_imported_rows = sum(item.imported_count for item in entities)
        total_skipped_rows = sum(item.skipped_count for item in entities)
        total_error_rows = sum(item.error_count for item in entities)
        total_review_rows = sum(item.review_count for item in entities)

        if total_imported_rows + total_skipped_rows + total_error_rows > total_source_rows:
            raise ValueError("Import summary totals exceed source rows")

        return ImportBatchSummary(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            created_by_user_id=created_by_user_id,
            source_system=source_system,
            started_at=started_at or datetime.now(UTC),
            finished_at=finished_at,
            total_source_rows=total_source_rows,
            total_imported_rows=total_imported_rows,
            total_skipped_rows=total_skipped_rows,
            total_error_rows=total_error_rows,
            total_review_rows=total_review_rows,
            status_mapping_warnings=total_review_rows,
            entities=entities,
            notes=notes,
        )

    def record_import_batch_summary_event(
        self,
        *,
        summary: ImportBatchSummary,
        user_id: uuid.UUID | None = None,
    ) -> ImportBatchSummary:
        """
        Minimal C1c staging hook: persist summary as a typed audit log event.
        Does not create a dedicated /audit/import-batches REST API.
        """
        AuditRecorder(self.db).audit_log(
            action=AuditAction.EXECUTE,
            summary=f"Import batch summary: {summary.source_system}",
            tenant_id=summary.tenant_id,
            user_id=user_id or summary.created_by_user_id,
            entity_type="import_batch_summary",
            entity_id=summary.id,
            changes_json=summary.model_dump(mode="json"),
            metadata_json={
                "event": "import.batch.summary",
                "source_system": summary.source_system,
                "total_source_rows": summary.total_source_rows,
                "total_review_rows": summary.total_review_rows,
            },
        )
        return summary

    def _ensure_tenant_audit_access(self, user: User, tenant_id: uuid.UUID) -> None:
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        staff = get_provider_staff(user)
        if staff and staff.provider_company_id == tenant.provider_company_id:
            return

        if any(
            m.tenant_id == tenant_id
            and m.is_active
            and m.role in (TenantRole.TENANT_OWNER, TenantRole.TENANT_ADMIN)
            for m in user.tenant_memberships
        ):
            return

        raise PermissionDeniedError("Insufficient permissions to view audit data")

    def _ensure_provider_auditor(self, user: User) -> None:
        if not get_provider_staff(user):
            raise PermissionDeniedError("Provider staff access required for platform-wide audit")
