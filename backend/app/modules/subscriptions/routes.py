import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core.deps import get_current_user, get_db, require_provider_owner
from app.modules.auth.models import User
from app.modules.subscriptions.schemas import (
    PlanDetailResponse,
    SubscriptionAssign,
    SubscriptionResponse,
)
from app.modules.subscriptions.service import SubscriptionService

router = APIRouter(tags=["subscriptions"])


@router.get("/plans", response_model=list[PlanDetailResponse])
def list_plans(
    db: Session = Depends(get_db),
    _: User = Depends(get_current_user),
) -> list[PlanDetailResponse]:
    return SubscriptionService(db).list_plans()


@router.get(
    "/tenants/{tenant_id}/subscription",
    response_model=SubscriptionResponse | None,
)
def get_tenant_subscription(
    tenant_id: uuid.UUID,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> SubscriptionResponse | None:
    return SubscriptionService(db).get_tenant_subscription(current_user, tenant_id)


@router.post(
    "/tenants/{tenant_id}/subscription",
    response_model=SubscriptionResponse,
    status_code=201,
)
def assign_tenant_subscription(
    tenant_id: uuid.UUID,
    payload: SubscriptionAssign,
    current_user: User = Depends(require_provider_owner),
    db: Session = Depends(get_db),
) -> SubscriptionResponse:
    result = SubscriptionService(db).assign_plan(
        current_user, tenant_id, payload.plan_code
    )
    db.commit()
    return result
