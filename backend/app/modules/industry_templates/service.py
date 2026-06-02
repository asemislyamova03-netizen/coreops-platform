import uuid

from sqlalchemy.orm import Session

from app.core.exceptions import ConflictError, NotFoundError, PermissionDeniedError
from app.core.permissions import get_provider_staff
from app.modules.auth.models import User
from app.modules.industry_templates.repository import IndustryTemplateRepository
from app.modules.industry_templates.schemas import (
    ApplyTemplateResponse,
    IndustryTemplateCreate,
    IndustryTemplateUpdate,
)
from app.modules.industry_templates.seed import INDUSTRY_TEMPLATES
from app.modules.ai.service import AIService
from app.modules.documents.service import DocumentService
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.tenants.repository import TenantRepository


class IndustryTemplateService:
    def __init__(self, db: Session):
        self.db = db
        self.templates = IndustryTemplateRepository(db)
        self.tenants = TenantRepository(db)
        self.modules = ModuleRegistryService(db)

    def seed_templates(self) -> None:
        for item in INDUSTRY_TEMPLATES:
            self.templates.upsert(dict(item))
        self.db.commit()

    def list_templates(self, active_only: bool = True) -> list:
        return self.templates.list_templates(active_only=active_only)

    def get_template(self, template_id: uuid.UUID):
        template = self.templates.get_by_id(template_id)
        if not template:
            raise NotFoundError("Industry template not found")
        return template

    def create_template(self, payload: IndustryTemplateCreate):
        if self.templates.get_by_code(payload.code):
            raise ConflictError("Template code already exists")
        template = self.templates.upsert(payload.model_dump())
        self.db.commit()
        self.db.refresh(template)
        return template

    def update_template(self, template_id: uuid.UUID, payload: IndustryTemplateUpdate):
        template = self.get_template(template_id)
        for key, value in payload.model_dump(exclude_unset=True).items():
            setattr(template, key, value)
        self.db.commit()
        self.db.refresh(template)
        return template

    def apply_to_tenant(
        self,
        user: User,
        tenant_id: uuid.UUID,
        template_id: uuid.UUID,
    ) -> ApplyTemplateResponse:
        self._ensure_provider_access(user, tenant_id)
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")

        template = self.get_template(template_id)
        if not template.is_active:
            raise ConflictError("Industry template is not active")

        modules_enabled = self.modules.enable_modules_ordered(
            tenant_id,
            list(template.default_modules),
            as_trial=True,
        )

        tenant.industry_template_id = template.id
        settings = self.templates.get_or_create_tenant_settings(tenant_id)
        settings.labels_config = dict(template.labels_config)
        settings.industry_config_json = {
            "template_code": template.code,
            "default_roles": template.default_roles,
            "default_statuses": template.default_statuses,
            "default_document_templates": template.default_document_templates,
            "default_catalog_items": template.default_catalog_items,
            "default_dashboards": template.default_dashboards,
            "default_ai_agents": template.default_ai_agents,
            "settings_schema": template.settings_schema,
        }

        pipelines_created = self._apply_pipelines(tenant_id, template.default_pipelines)
        custom_fields_created = self._apply_custom_fields(
            tenant_id,
            template.code,
            template.default_custom_fields,
        )
        DocumentService(self.db, tenant_id).import_templates_from_config(
            user,
            list(template.default_document_templates),
        )
        AIService(self.db, tenant_id).import_agents_from_config(
            user,
            list(template.default_ai_agents),
        )

        self.db.flush()

        return ApplyTemplateResponse(
            tenant_id=tenant_id,
            template_id=template.id,
            template_code=template.code,
            modules_enabled=modules_enabled,
            pipelines_created=pipelines_created,
            custom_fields_created=custom_fields_created,
            labels_applied=True,
        )

    def get_tenant_labels(self, user: User, tenant_id: uuid.UUID) -> dict:
        self._ensure_tenant_read_access(user, tenant_id)
        settings = self.templates.get_tenant_settings(tenant_id)
        if not settings:
            return {}
        return settings.labels_config

    def _apply_pipelines(self, tenant_id: uuid.UUID, pipelines: list) -> list[str]:
        created_codes: list[str] = []
        for pipeline_data in pipelines:
            code = pipeline_data["code"]
            existing = self.templates.get_pipeline(tenant_id, code)
            if existing:
                continue

            pipeline = self.templates.create_pipeline(
                tenant_id=tenant_id,
                code=code,
                name=pipeline_data["name"],
                entity_type=pipeline_data.get("entity_type", "work_item"),
                is_default=pipeline_data.get("is_default", False),
            )
            for stage_data in pipeline_data.get("stages", []):
                self.templates.create_pipeline_stage(
                    pipeline_id=pipeline.id,
                    code=stage_data["code"],
                    name=stage_data["name"],
                    sort_order=stage_data.get("sort_order", 0),
                    is_terminal=stage_data.get("is_terminal", False),
                )
            created_codes.append(code)
        return created_codes

    def _apply_custom_fields(
        self,
        tenant_id: uuid.UUID,
        template_code: str,
        fields: list,
    ) -> int:
        created = 0
        for field_data in fields:
            existing = self.templates.get_custom_field(
                tenant_id,
                field_data["entity_type"],
                field_data["field_key"],
            )
            if existing:
                continue
            self.templates.create_custom_field(
                tenant_id=tenant_id,
                entity_type=field_data["entity_type"],
                field_key=field_data["field_key"],
                field_type=field_data["field_type"],
                label=field_data["label"],
                applies_to_json=field_data.get("applies_to_json", {}),
                options_json=field_data.get("options_json", {}),
                is_required=field_data.get("is_required", False),
                sort_order=field_data.get("sort_order", 0),
                source_template_code=template_code,
            )
            created += 1
        return created

    def _ensure_provider_access(self, user: User, tenant_id: uuid.UUID) -> None:
        staff = get_provider_staff(user)
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        if not staff or staff.provider_company_id != tenant.provider_company_id:
            raise PermissionDeniedError("Only provider staff can apply industry templates")

    def _ensure_tenant_read_access(self, user: User, tenant_id: uuid.UUID) -> None:
        staff = get_provider_staff(user)
        tenant = self.tenants.get_by_id(tenant_id)
        if not tenant:
            raise NotFoundError("Tenant not found")
        if staff and staff.provider_company_id == tenant.provider_company_id:
            return
        if any(m.tenant_id == tenant_id and m.is_active for m in user.tenant_memberships):
            return
        raise PermissionDeniedError("No access to this tenant")
