import uuid
from datetime import datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.core.enums import SubscriptionStatus
from app.modules.subscriptions.models import (
    Feature,
    Plan,
    PlanFeature,
    Subscription,
    UsageEvent,
    UsageLimit,
)


class SubscriptionRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_plans(self, active_only: bool = True) -> list[Plan]:
        stmt = select(Plan).order_by(Plan.code)
        if active_only:
            stmt = stmt.where(Plan.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_plan_by_code(self, code: str) -> Plan | None:
        stmt = select(Plan).where(Plan.code == code)
        return self.db.scalar(stmt)

    def get_plan(self, plan_id: uuid.UUID) -> Plan | None:
        return self.db.get(Plan, plan_id)

    def get_feature(self, code: str) -> Feature | None:
        stmt = select(Feature).where(Feature.code == code)
        return self.db.scalar(stmt)

    def get_active_for_tenant(self, tenant_id: uuid.UUID) -> Subscription | None:
        stmt = (
            select(Subscription)
            .where(
                Subscription.tenant_id == tenant_id,
                Subscription.status.in_(
                    [SubscriptionStatus.ACTIVE, SubscriptionStatus.TRIAL]
                ),
            )
            .options(selectinload(Subscription.plan))
        )
        return self.db.scalar(stmt)

    def plan_has_feature(self, plan_id: uuid.UUID, feature_code: str) -> bool:
        stmt = (
            select(PlanFeature)
            .join(Feature)
            .where(PlanFeature.plan_id == plan_id, Feature.code == feature_code)
        )
        return self.db.scalar(stmt) is not None

    def get_plan_limit(self, plan_id: uuid.UUID, limit_code: str) -> UsageLimit | None:
        stmt = select(UsageLimit).where(
            UsageLimit.plan_id == plan_id,
            UsageLimit.limit_code == limit_code,
        )
        return self.db.scalar(stmt)

    def sum_usage(
        self,
        tenant_id: uuid.UUID,
        limit_code: str,
        since: datetime,
    ) -> int:
        stmt = select(func.coalesce(func.sum(UsageEvent.quantity), 0)).where(
            UsageEvent.tenant_id == tenant_id,
            UsageEvent.limit_code == limit_code,
            UsageEvent.created_at >= since,
        )
        return int(self.db.scalar(stmt) or 0)

    def record_usage_event(
        self,
        *,
        tenant_id: uuid.UUID,
        limit_code: str,
        quantity: int,
        metadata_json: dict,
    ) -> UsageEvent:
        event = UsageEvent(
            tenant_id=tenant_id,
            limit_code=limit_code,
            quantity=quantity,
            metadata_json=metadata_json,
        )
        self.db.add(event)
        self.db.flush()
        return event

    def upsert_subscription(
        self,
        *,
        tenant_id: uuid.UUID,
        plan_id: uuid.UUID,
        status: SubscriptionStatus = SubscriptionStatus.TRIAL,
    ) -> Subscription:
        existing = self.db.scalar(
            select(Subscription).where(Subscription.tenant_id == tenant_id)
        )
        if existing:
            existing.plan_id = plan_id
            existing.status = status
            self.db.flush()
            return existing
        subscription = Subscription(tenant_id=tenant_id, plan_id=plan_id, status=status)
        self.db.add(subscription)
        self.db.flush()
        return subscription

    def upsert_feature(self, **kwargs) -> Feature:
        existing = self.get_feature(kwargs["code"])
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        feature = Feature(**kwargs)
        self.db.add(feature)
        self.db.flush()
        return feature

    def upsert_plan(self, **kwargs) -> Plan:
        existing = self.get_plan_by_code(kwargs["code"])
        if existing:
            for key, value in kwargs.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        plan = Plan(**kwargs)
        self.db.add(plan)
        self.db.flush()
        return plan

    def link_plan_feature(self, plan_id: uuid.UUID, feature_id: uuid.UUID) -> None:
        exists = self.db.scalar(
            select(PlanFeature).where(
                PlanFeature.plan_id == plan_id,
                PlanFeature.feature_id == feature_id,
            )
        )
        if not exists:
            self.db.add(PlanFeature(plan_id=plan_id, feature_id=feature_id))
            self.db.flush()

    def upsert_usage_limit(self, **kwargs) -> UsageLimit:
        existing = self.db.scalar(
            select(UsageLimit).where(
                UsageLimit.plan_id == kwargs["plan_id"],
                UsageLimit.limit_code == kwargs["limit_code"],
            )
        )
        if existing:
            existing.limit_value = kwargs["limit_value"]
            existing.period = kwargs["period"]
            self.db.flush()
            return existing
        limit = UsageLimit(**kwargs)
        self.db.add(limit)
        self.db.flush()
        return limit
