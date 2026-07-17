"""E1a ORM metadata and constraint tests for Process Overlay."""

from __future__ import annotations

import uuid

import pytest
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.core.enums import TenantStatus
from app.modules.process_overlay.enums import ProcessOverlayActivationState
from app.modules.process_overlay.models import (
    ProcessDefinitionVersion,
    ProcessTemplate,
    TenantProcessConfiguration,
)
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.seed import PROCESS_TEMPLATE_DEFINITIONS
from app.modules.process_overlay.service import ProcessOverlayCatalogService
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant
from app.modules.workflows.repository import WorkflowRepository

OVERLAY_TABLES = {
    "process_templates",
    "tenant_process_configurations",
    "process_definition_versions",
}


def test_overlay_tables_registered_in_metadata():
    table_names = set(Base.metadata.tables.keys())
    assert OVERLAY_TABLES.issubset(table_names)


def _bootstrap_tenant(db_session, slug: str) -> Tenant:
    provider = ProviderCompany(name=f"Provider {slug}", slug=f"prov-{slug}", is_active=True)
    db_session.add(provider)
    db_session.flush()
    tenant = Tenant(
        provider_company_id=provider.id,
        name=f"Tenant {slug}",
        slug=slug,
        status=TenantStatus.ACTIVE,
    )
    db_session.add(tenant)
    db_session.flush()
    return tenant


def _create_pipeline(db_session, tenant_id: uuid.UUID, code: str = "flexity_sales"):
    repo = WorkflowRepository(db_session)
    existing = repo.get_pipeline_by_code(tenant_id, code)
    if existing:
        return existing
    pipeline = repo.create_pipeline(
        tenant_id=tenant_id,
        code=code,
        name="Sales",
        entity_type="work_item",
        is_default=True,
    )
    for order, stage_code in enumerate(
        ["new_lead", "contacted", "diagnosis", "accepted", "rejected"],
        start=1,
    ):
        repo.create_stage(
            pipeline_id=pipeline.id,
            code=stage_code,
            name=stage_code,
            sort_order=order * 10,
            is_terminal=stage_code in {"accepted", "rejected"},
        )
    db_session.flush()
    return pipeline


def _seed_template(db_session) -> ProcessTemplate:
    ProcessOverlayCatalogService(db_session).seed_templates()
    template = ProcessOverlayRepository(db_session).get_template_by_code("flexity_sales_intake")
    assert template is not None
    return template


def test_config_unique_per_tenant_template(db_session):
    tenant = _bootstrap_tenant(db_session, "uniq-template")
    template = _seed_template(db_session)
    pipeline = _create_pipeline(db_session, tenant.id)
    repo = ProcessOverlayRepository(db_session)

    repo.create_configuration(
        tenant_id=tenant.id,
        process_template_id=template.id,
        pipeline_id=pipeline.id,
    )
    with pytest.raises(IntegrityError):
        repo.create_configuration(
            tenant_id=tenant.id,
            process_template_id=template.id,
            pipeline_id=pipeline.id,
        )
        db_session.flush()


def test_config_unique_per_tenant_pipeline(db_session):
    tenant = _bootstrap_tenant(db_session, "uniq-pipeline")
    template = _seed_template(db_session)
    pipeline = _create_pipeline(db_session, tenant.id)
    repo = ProcessOverlayRepository(db_session)

    repo.create_configuration(
        tenant_id=tenant.id,
        process_template_id=template.id,
        pipeline_id=pipeline.id,
    )

    other_template = ProcessTemplate(
        code="other_template",
        name="Other",
        default_pipeline_code="flexity_sales",
        default_policy_blueprint_json={},
        required_module_codes_json=[],
        is_active=True,
    )
    db_session.add(other_template)
    db_session.flush()

    with pytest.raises(IntegrityError):
        repo.create_configuration(
            tenant_id=tenant.id,
            process_template_id=other_template.id,
            pipeline_id=pipeline.id,
        )
        db_session.flush()


def test_version_unique_per_configuration_number(db_session):
    tenant = _bootstrap_tenant(db_session, "uniq-version")
    template = _seed_template(db_session)
    pipeline = _create_pipeline(db_session, tenant.id)
    repo = ProcessOverlayRepository(db_session)
    config = repo.create_configuration(
        tenant_id=tenant.id,
        process_template_id=template.id,
        pipeline_id=pipeline.id,
    )
    actor = uuid.uuid4()
    repo.insert_definition_version(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config.id,
        version_number=1,
        pipeline_id=pipeline.id,
        pipeline_code=pipeline.code,
        stage_codes_json=["new_lead"],
        policy_snapshot_json={"schema_version": 1},
        module_requirements_json=["crm"],
        published_by_user_id=actor,
        publish_reason="first",
    )
    with pytest.raises(IntegrityError):
        repo.insert_definition_version(
            tenant_id=tenant.id,
            tenant_process_configuration_id=config.id,
            version_number=1,
            pipeline_id=pipeline.id,
            pipeline_code=pipeline.code,
            stage_codes_json=["new_lead"],
            policy_snapshot_json={"schema_version": 1},
            module_requirements_json=["crm"],
            published_by_user_id=actor,
            publish_reason="dup",
        )
        db_session.flush()


def test_seed_idempotent(db_session):
    catalog = ProcessOverlayCatalogService(db_session)
    first = catalog.seed_templates()
    second = catalog.seed_templates()
    assert len(first) == len(PROCESS_TEMPLATE_DEFINITIONS)
    assert len(second) == len(PROCESS_TEMPLATE_DEFINITIONS)
    templates = ProcessOverlayRepository(db_session).list_templates(active_only=False)
    codes = [item.code for item in templates if item.code == "flexity_sales_intake"]
    assert len(codes) == 1


def test_new_configuration_defaults_inactive(db_session):
    tenant = _bootstrap_tenant(db_session, "inactive-default")
    template = _seed_template(db_session)
    pipeline = _create_pipeline(db_session, tenant.id)
    config = ProcessOverlayRepository(db_session).create_configuration(
        tenant_id=tenant.id,
        process_template_id=template.id,
        pipeline_id=pipeline.id,
    )
    assert config.activation_state == ProcessOverlayActivationState.INACTIVE
    assert config.active_definition_version_id is None
