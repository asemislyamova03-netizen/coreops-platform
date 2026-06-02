import uuid
from datetime import datetime

from sqlalchemy.orm import Session

from app.core.enums import AuditAction, SecurityEventType, TenantRole
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import get_provider_staff
from app.modules.audit.repository import AuditRepository
from app.modules.audit.schemas import (
    AuditLogResponse,
    DataAccessLogResponse,
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
