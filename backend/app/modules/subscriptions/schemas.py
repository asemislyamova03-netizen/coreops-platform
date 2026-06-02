import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.core.enums import SubscriptionStatus, UsagePeriod


class FeatureResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    module_code: str | None
    name: str
    description: str | None


class PlanResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    default_modules_json: list[str]
    is_active: bool


class UsageLimitResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    limit_code: str
    limit_value: int
    period: UsagePeriod


class PlanDetailResponse(PlanResponse):
    features: list[str] = Field(default_factory=list)
    limits: list[UsageLimitResponse] = Field(default_factory=list)


class SubscriptionAssign(BaseModel):
    plan_code: str = Field(min_length=1, max_length=64)


class SubscriptionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    tenant_id: uuid.UUID
    plan_id: uuid.UUID
    plan_code: str
    plan_name: str
    status: SubscriptionStatus
    created_at: datetime
