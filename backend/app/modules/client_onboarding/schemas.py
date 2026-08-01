import uuid

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.core.enums import TenantRole


class ClientSignupRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    full_name: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    tenant_name: str = Field(min_length=1, max_length=255)
    tenant_slug: str = Field(
        min_length=2,
        max_length=100,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )


class ClientSignupUser(BaseModel):
    id: uuid.UUID
    email: EmailStr
    full_name: str


class ClientSignupTenant(BaseModel):
    id: uuid.UUID
    name: str
    slug: str
    default_branch_id: uuid.UUID
    role: TenantRole = TenantRole.TENANT_OWNER


class ClientSignupResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user: ClientSignupUser
    tenant: ClientSignupTenant
    modules_enabled: list[str]
    redirect_path: str
