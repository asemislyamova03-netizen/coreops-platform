import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import TenantRole, TenantStatus


class TenantCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    status: TenantStatus = TenantStatus.TRIAL
    owner_user_id: uuid.UUID | None = None
    owner_email: EmailStr | None = None
    plan_code: str | None = Field(
        default=None,
        description="Optional subscription plan to assign on creation",
    )
    industry_template_code: str | None = Field(
        default=None,
        description="Optional industry template to apply on creation",
    )


class TenantUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    status: TenantStatus | None = None


class TenantResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    provider_company_id: uuid.UUID
    name: str
    slug: str
    industry_template_id: uuid.UUID | None
    status: TenantStatus
    created_at: datetime
    updated_at: datetime


class TenantMembershipCreate(BaseModel):
    user_id: uuid.UUID
    role: TenantRole = TenantRole.TENANT_OWNER


class TenantMembershipResponse(BaseModel):
    membership_id: uuid.UUID
    user_id: uuid.UUID
    email: EmailStr
    full_name: str
    user_is_active: bool
    role: TenantRole
    membership_is_active: bool
    created_at: datetime
