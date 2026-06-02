import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class IndustryTemplateCreate(BaseModel):
    code: str = Field(min_length=2, max_length=64, pattern=r"^[a-z0-9_]+$")
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    default_modules: list[str] = Field(default_factory=list)
    default_roles: list[dict] = Field(default_factory=list)
    default_pipelines: list[dict] = Field(default_factory=list)
    default_statuses: dict = Field(default_factory=dict)
    default_custom_fields: list[dict] = Field(default_factory=list)
    default_document_templates: list[dict] = Field(default_factory=list)
    default_catalog_items: list[dict] = Field(default_factory=list)
    default_dashboards: list[dict] = Field(default_factory=list)
    default_ai_agents: list[dict] = Field(default_factory=list)
    labels_config: dict = Field(default_factory=dict)
    settings_schema: dict = Field(default_factory=dict)
    is_active: bool = True


class IndustryTemplateUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    default_modules: list[str] | None = None
    default_roles: list[dict] | None = None
    default_pipelines: list[dict] | None = None
    default_statuses: dict | None = None
    default_custom_fields: list[dict] | None = None
    default_document_templates: list[dict] | None = None
    default_catalog_items: list[dict] | None = None
    default_dashboards: list[dict] | None = None
    default_ai_agents: list[dict] | None = None
    labels_config: dict | None = None
    settings_schema: dict | None = None
    is_active: bool | None = None


class IndustryTemplateResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    code: str
    name: str
    description: str | None
    default_modules: list[str]
    default_roles: list[dict]
    default_pipelines: list[dict]
    default_statuses: dict
    default_custom_fields: list[dict]
    default_document_templates: list[dict]
    default_catalog_items: list[dict]
    default_dashboards: list[dict]
    default_ai_agents: list[dict]
    labels_config: dict
    settings_schema: dict
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ApplyTemplateResponse(BaseModel):
    tenant_id: uuid.UUID
    template_id: uuid.UUID
    template_code: str
    modules_enabled: list[str]
    pipelines_created: list[str]
    custom_fields_created: int
    labels_applied: bool
