import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.industry_templates.models import IndustryTemplate
from app.modules.parties.models import CustomFieldDefinition
from app.modules.tenants.models import TenantSettings
from app.modules.workflows.models import Pipeline, PipelineStage


class IndustryTemplateRepository:
    def __init__(self, db: Session):
        self.db = db

    def list_templates(self, active_only: bool = True) -> list[IndustryTemplate]:
        stmt = select(IndustryTemplate).order_by(IndustryTemplate.code)
        if active_only:
            stmt = stmt.where(IndustryTemplate.is_active.is_(True))
        return list(self.db.scalars(stmt).all())

    def get_by_id(self, template_id: uuid.UUID) -> IndustryTemplate | None:
        return self.db.get(IndustryTemplate, template_id)

    def get_by_code(self, code: str) -> IndustryTemplate | None:
        stmt = select(IndustryTemplate).where(IndustryTemplate.code == code)
        return self.db.scalar(stmt)

    def upsert(self, data: dict) -> IndustryTemplate:
        existing = self.get_by_code(data["code"])
        if existing:
            for key, value in data.items():
                setattr(existing, key, value)
            self.db.flush()
            return existing
        template = IndustryTemplate(**data)
        self.db.add(template)
        self.db.flush()
        return template

    def get_tenant_settings(self, tenant_id: uuid.UUID) -> TenantSettings | None:
        stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
        return self.db.scalar(stmt)

    def get_or_create_tenant_settings(self, tenant_id: uuid.UUID) -> TenantSettings:
        settings = self.get_tenant_settings(tenant_id)
        if settings:
            return settings
        settings = TenantSettings(tenant_id=tenant_id)
        self.db.add(settings)
        self.db.flush()
        return settings

    def get_pipeline(self, tenant_id: uuid.UUID, code: str) -> Pipeline | None:
        stmt = select(Pipeline).where(Pipeline.tenant_id == tenant_id, Pipeline.code == code)
        return self.db.scalar(stmt)

    def create_pipeline(self, **kwargs) -> Pipeline:
        pipeline = Pipeline(**kwargs)
        self.db.add(pipeline)
        self.db.flush()
        return pipeline

    def create_pipeline_stage(self, **kwargs) -> PipelineStage:
        stage = PipelineStage(**kwargs)
        self.db.add(stage)
        self.db.flush()
        return stage

    def get_custom_field(
        self,
        tenant_id: uuid.UUID,
        entity_type: str,
        field_key: str,
    ) -> CustomFieldDefinition | None:
        stmt = select(CustomFieldDefinition).where(
            CustomFieldDefinition.tenant_id == tenant_id,
            CustomFieldDefinition.entity_type == entity_type,
            CustomFieldDefinition.field_key == field_key,
        )
        return self.db.scalar(stmt)

    def create_custom_field(self, **kwargs) -> CustomFieldDefinition:
        field = CustomFieldDefinition(**kwargs)
        self.db.add(field)
        self.db.flush()
        return field
