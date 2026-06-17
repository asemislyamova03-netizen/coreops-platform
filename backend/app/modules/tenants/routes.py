import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_provider_owner
from app.modules.auth.models import User
from app.modules.tenants.schemas import (
    TenantCreate,
    TenantMembershipCreate,
    TenantMembershipResponse,
    TenantResponse,
    TenantUpdate,
)
from app.modules.tenants.service import TenantService

router = APIRouter(prefix="/tenants", tags=["tenants"])


@router.get("", response_model=list[TenantResponse])
def list_tenants(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TenantResponse]:
    tenants = TenantService(db).list_accessible(current_user)
    return [TenantResponse.model_validate(t) for t in tenants]


@router.post("", response_model=TenantResponse, status_code=201)
def create_tenant(
    payload: TenantCreate,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> TenantResponse:
    tenant = TenantService(db).create(current_user, payload)
    return TenantResponse.model_validate(tenant)


@router.get("/{tenant_id}", response_model=TenantResponse)
def get_tenant(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantResponse:
    tenant = TenantService(db).get_accessible(current_user, tenant_id)
    return TenantResponse.model_validate(tenant)


@router.patch("/{tenant_id}", response_model=TenantResponse)
def update_tenant(
    tenant_id: uuid.UUID,
    payload: TenantUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> TenantResponse:
    tenant = TenantService(db).update(current_user, tenant_id, payload)
    return TenantResponse.model_validate(tenant)


@router.get("/{tenant_id}/memberships", response_model=list[TenantMembershipResponse])
def list_tenant_memberships(
    tenant_id: uuid.UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[TenantMembershipResponse]:
    return TenantService(db).list_memberships(current_user, tenant_id)


@router.post("/{tenant_id}/memberships", status_code=201)
def add_tenant_membership(
    tenant_id: uuid.UUID,
    payload: TenantMembershipCreate,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
):
    membership = TenantService(db).add_membership(
        current_user,
        tenant_id,
        payload.user_id,
        payload.role,
    )
    return {"id": membership.id, "tenant_id": membership.tenant_id, "role": membership.role}
