import uuid

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db
from app.core.enums import AuditAction, SecurityEventType
from app.core.tenancy import TenantContext, get_tenant_context
from app.modules.audit.schemas import (
    AuditLogResponse,
    DataAccessLogResponse,
    SecurityEventResponse,
)
from app.modules.audit.service import AuditService
from app.modules.auth.models import User

router = APIRouter(prefix="/audit", tags=["audit"])


def _service(db: Session) -> AuditService:
    return AuditService(db)


@router.get("/logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    action: AuditAction | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[AuditLogResponse]:
    return _service(db).list_audit_logs(
        current_user,
        tenant_id=tenant_id,
        user_id=user_id,
        entity_type=entity_type,
        action=action,
        limit=limit,
    )


@router.get("/data-access", response_model=list[DataAccessLogResponse])
def list_data_access_logs(
    ctx: TenantContext = Depends(get_tenant_context),
    user_id: uuid.UUID | None = None,
    entity_type: str | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    db: Session = Depends(get_db),
) -> list[DataAccessLogResponse]:
    return _service(db).list_data_access(
        ctx.user,
        ctx.tenant.id,
        user_id=user_id,
        entity_type=entity_type,
        limit=limit,
    )


@router.get("/security-events", response_model=list[SecurityEventResponse])
def list_security_events(
    tenant_id: uuid.UUID | None = None,
    user_id: uuid.UUID | None = None,
    event_type: SecurityEventType | None = None,
    limit: int = Query(default=100, ge=1, le=500),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[SecurityEventResponse]:
    return _service(db).list_security_events(
        current_user,
        tenant_id=tenant_id,
        user_id=user_id,
        event_type=event_type,
        limit=limit,
    )
