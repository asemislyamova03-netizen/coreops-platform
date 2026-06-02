import uuid
from datetime import UTC, datetime

from fastapi import Request
from sqlalchemy.orm import Session

from app.core.enums import AuditAction, DataAccessType, SecurityEventType
from app.modules.audit.repository import AuditRepository
from app.modules.audit.request_meta import client_ip, user_agent


class AuditRecorder:
    """Append-only audit writer; callers commit the session when appropriate."""

    def __init__(self, db: Session):
        self.db = db
        self.repo = AuditRepository(db)

    def audit_log(
        self,
        *,
        action: AuditAction,
        summary: str,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        changes_json: dict | None = None,
        request: Request | None = None,
        ai_proposal_id: uuid.UUID | None = None,
        approved_by_user_id: uuid.UUID | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        self.repo.create_audit_log(
            tenant_id=tenant_id,
            user_id=user_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            summary=summary,
            changes_json=changes_json or {},
            ip_address=client_ip(request),
            user_agent=user_agent(request),
            ai_proposal_id=ai_proposal_id,
            approved_by_user_id=approved_by_user_id,
            metadata_json=metadata_json or {},
        )

    def data_access(
        self,
        *,
        tenant_id: uuid.UUID,
        user_id: uuid.UUID,
        entity_type: str,
        access_type: DataAccessType = DataAccessType.READ,
        entity_id: uuid.UUID | None = None,
        resource_label: str | None = None,
        request: Request | None = None,
        metadata_json: dict | None = None,
    ) -> None:
        self.repo.create_data_access_log(
            tenant_id=tenant_id,
            user_id=user_id,
            access_type=access_type,
            entity_type=entity_type,
            entity_id=entity_id,
            resource_label=resource_label,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
            metadata_json=metadata_json or {},
        )

    def security_event(
        self,
        *,
        event_type: SecurityEventType,
        user_id: uuid.UUID | None = None,
        tenant_id: uuid.UUID | None = None,
        email: str | None = None,
        request: Request | None = None,
        details_json: dict | None = None,
    ) -> None:
        self.repo.create_security_event(
            tenant_id=tenant_id,
            user_id=user_id,
            event_type=event_type,
            email=email,
            ip_address=client_ip(request),
            user_agent=user_agent(request),
            details_json=details_json or {},
            occurred_at=datetime.now(UTC),
        )
