import uuid
from collections.abc import Callable
from datetime import UTC, datetime

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.deps import get_db
from app.core.exceptions import FeatureNotEntitledError, UsageLimitExceededError
from app.core.modules import ModuleGuard
from app.core.tenancy import TenantContext, get_tenant_context
from app.modules.subscriptions.repository import SubscriptionRepository


class EntitlementService:
    def __init__(self, db: Session, tenant_id: uuid.UUID):
        self.db = db
        self.tenant_id = tenant_id
        self.subscriptions = SubscriptionRepository(db)
        self.modules = ModuleGuard(db, tenant_id)

    def has_feature(self, feature_code: str) -> bool:
        subscription = self.subscriptions.get_active_for_tenant(self.tenant_id)
        if not subscription:
            return False
        return self.subscriptions.plan_has_feature(subscription.plan_id, feature_code)

    def assert_feature(self, feature_code: str) -> None:
        feature = self.subscriptions.get_feature(feature_code)
        if feature and feature.module_code:
            self.modules.assert_enabled(feature.module_code)

        if not self.has_feature(feature_code):
            raise FeatureNotEntitledError(
                f"Feature '{feature_code}' is not included in the current subscription"
            )

    def record_usage(self, limit_code: str, quantity: int = 1, metadata: dict | None = None) -> None:
        self.subscriptions.record_usage_event(
            tenant_id=self.tenant_id,
            limit_code=limit_code,
            quantity=quantity,
            metadata_json=metadata or {},
        )
        self.db.commit()

    def assert_within_limit(self, limit_code: str, increment: int = 1) -> None:
        subscription = self.subscriptions.get_active_for_tenant(self.tenant_id)
        if not subscription:
            raise FeatureNotEntitledError("No active subscription for tenant")

        usage_limit = self.subscriptions.get_plan_limit(subscription.plan_id, limit_code)
        if usage_limit is None:
            return

        period_start = self._period_start(usage_limit.period.value)
        current_usage = self.subscriptions.sum_usage(
            self.tenant_id,
            limit_code,
            since=period_start,
        )
        if current_usage + increment > usage_limit.limit_value:
            raise UsageLimitExceededError(
                f"Usage limit '{limit_code}' exceeded ({current_usage + increment}"
                f"/{usage_limit.limit_value})"
            )

    def _period_start(self, period: str) -> datetime:
        now = datetime.now(UTC)
        if period == "daily":
            return now.replace(hour=0, minute=0, second=0, microsecond=0)
        if period == "monthly":
            return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if period == "yearly":
            return now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
        return datetime.min.replace(tzinfo=UTC)


def require_feature(feature_code: str) -> Callable:
    def dependency(
        ctx: TenantContext = Depends(get_tenant_context),
        db: Session = Depends(get_db),
    ) -> TenantContext:
        EntitlementService(db, ctx.tenant.id).assert_feature(feature_code)
        return ctx

    return dependency
