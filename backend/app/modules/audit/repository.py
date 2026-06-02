import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.enums import AuditAction, SecurityEventType
from app.modules.audit.models import AuditLog, DataAccessLog, SecurityEvent


class AuditRepository:
    def __init__(self, db: Session):
        self.db = db

    def create_audit_log(self, **kwargs) -> AuditLog:
        entry = AuditLog(**kwargs)
        self.db.add(entry)
        self.db.flush()
        return entry

    def create_data_access_log(self, **kwargs) -> DataAccessLog:
        entry = DataAccessLog(**kwargs)
        self.db.add(entry)
        self.db.flush()
        return entry

    def create_security_event(self, **kwargs) -> SecurityEvent:
        entry = SecurityEvent(**kwargs)
        self.db.add(entry)
        self.db.flush()
        return entry

    def list_audit_logs(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        action: AuditAction | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[AuditLog]:
        stmt = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
        if tenant_id:
            stmt = stmt.where(AuditLog.tenant_id == tenant_id)
        if user_id:
            stmt = stmt.where(AuditLog.user_id == user_id)
        if entity_type:
            stmt = stmt.where(AuditLog.entity_type == entity_type)
        if action:
            stmt = stmt.where(AuditLog.action == action)
        if since:
            stmt = stmt.where(AuditLog.created_at >= since)
        return list(self.db.scalars(stmt).all())

    def list_data_access_logs(
        self,
        tenant_id: uuid.UUID,
        *,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[DataAccessLog]:
        stmt = (
            select(DataAccessLog)
            .where(DataAccessLog.tenant_id == tenant_id)
            .order_by(DataAccessLog.created_at.desc())
            .limit(limit)
        )
        if user_id:
            stmt = stmt.where(DataAccessLog.user_id == user_id)
        if entity_type:
            stmt = stmt.where(DataAccessLog.entity_type == entity_type)
        if since:
            stmt = stmt.where(DataAccessLog.created_at >= since)
        return list(self.db.scalars(stmt).all())

    def list_security_events(
        self,
        *,
        tenant_id: uuid.UUID | None = None,
        user_id: uuid.UUID | None = None,
        event_type: SecurityEventType | None = None,
        since: datetime | None = None,
        limit: int = 100,
    ) -> list[SecurityEvent]:
        stmt = select(SecurityEvent).order_by(SecurityEvent.occurred_at.desc()).limit(limit)
        if tenant_id:
            stmt = stmt.where(SecurityEvent.tenant_id == tenant_id)
        if user_id:
            stmt = stmt.where(SecurityEvent.user_id == user_id)
        if event_type:
            stmt = stmt.where(SecurityEvent.event_type == event_type)
        if since:
            stmt = stmt.where(SecurityEvent.occurred_at >= since)
        return list(self.db.scalars(stmt).all())
