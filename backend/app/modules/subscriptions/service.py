import uuid

from sqlalchemy.orm import Session

from app.core.enums import ModuleStatus, SubscriptionStatus, UsagePeriod
from app.core.exceptions import NotFoundError, PermissionDeniedError
from app.core.permissions import get_provider_staff
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.subscriptions.repository import SubscriptionRepository
from app.modules.subscriptions.schemas import PlanDetailResponse, SubscriptionResponse, UsageLimitResponse
from app.modules.subscriptions.seed import FEATURES, PLANS
from app.modules.tenants.repository import TenantRepository


class SubscriptionService:
    def __init__(self, db: Session):
        self.db = db
        self.subscriptions = SubscriptionRepository(db)
        self.tenants = TenantRepository(db)
        self.modules = ModuleRegistryService(db)

    def seed_catalog(self) -> None:
        feature_ids: dict[str, uuid.UUID] = {}
        for item in FEATURES:
            feature = self.subscriptions.upsert_feature(**item)
            feature_ids[feature.code] = feature.id

        for plan_data in PLANS:
            data = dict(plan_data)
            features = data.pop("features")
            limits = data.pop("limits")
            plan = self.subscriptions.upsert_plan(**data)
            for feature_code in features:
                feature_id = feature_ids.get(feature_code)
                if feature_id:
                    self.subscriptions.link_plan_feature(plan.id, feature_id)
            for limit_data in limits:
                self.subscriptions.upsert_usage_limit(
                    plan_id=plan.id,
                    limit_code=limit_data["limit_code"],
                    limit_value=limit_data["limit_value"],
                    period=UsagePeriod(limit_data["period"]),
                )

        self.db.commit()

    def list_plans(self) -> list[PlanDetailResponse]:
        plans = self.subscriptions.list_plans()
        result = []
        for plan in plans:
            feature_codes = [pf.feature.code for pf in plan.plan_features]
            limits = [
                UsageLimitResponse(
                    limit_code=limit.limit_code,
                    limit_value=limit.limit_value,
                    period=limit.period,
                )
                for limit in plan.usage_limits
            ]
            result.append(
                PlanDetailResponse(
                    id=plan.id,
                    code=plan.code,
                    name=plan.name,
                    description=plan.description,
                    default_modules_json=plan.default_modules_json,
                    is_active=plan.is_active,
                    features=feature_codes,
                    limits=limits,
                )
            )
        return result

    def assign_plan(self, user: User, tenant_id: uuid.UUID, plan_code: str) -> SubscriptionResponse:
        self._ensure_provider_access(user, tenant_id)
        plan = self.subscriptions.get_plan_by_code(plan_code)
        if not plan:
            raise NotFoundError(f"Plan '{plan_code}' not found")

        self.modules.provision_tenant_modules(tenant_id)
        subscription = self.subscriptions.upsert_subscription(
            tenant_id=tenant_id,
            plan_id=plan.id,
            status=SubscriptionStatus.TRIAL,
        )
        self.modules.apply_plan_modules(tenant_id, plan.default_modules_json, as_trial=True)
        self.db.flush()
        self.db.refresh(subscription)

        return SubscriptionResponse(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_id=plan.id,
            plan_code=plan.code,
            plan_name=plan.name,
            status=subscription.status,
            created_at=subscription.created_at,
        )

    def get_tenant_subscription(self, user: User, tenant_id: uuid.UUID) -> SubscriptionResponse | None:
        self._ensure_provider_access(user, tenant_id)
        subscription = self.subscriptions.get_active_for_tenant(tenant_id)
        if not subscription:
            return None
        return SubscriptionResponse(
            id=subscription.id,
            tenant_id=subscription.tenant_id,
            plan_id=subscription.plan.id,
            plan_code=subscription.plan.code,
            plan_name=subscription.plan.name,
            status=subscription.status,
            created_at=subscription.created_at,
        )

    def _ensure_provider_access(self, user: User, tenant_id: uuid.UUID) -> None:
        staff = get_provider_staff(user)
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        if not staff or staff.provider_company_id != tenant.provider_company_id:
            raise PermissionDeniedError("Only provider staff can manage subscriptions")
