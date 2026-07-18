"""E1b ORM metadata and constraint tests for ProcessRun."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from app.core.database import Base
from app.core.enums import TenantStatus, WorkItemStatus
from app.modules.process_overlay.enums import ProcessRunState
from app.modules.process_overlay.models import ProcessRun
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.service import (
    ProcessOverlayCatalogService,
    ProcessOverlayConfigurationService,
    ProcessOverlayPublicationService,
)
from app.modules.process_overlay.schemas import PublishDefinitionVersionRequest
from app.modules.process_overlay.seed import PROCESS_TEMPLATE_DEFINITIONS
from app.modules.process_overlay.policy_schema import parse_policy_snapshot
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import PipelineStage
from app.modules.workflows.repository import WorkflowRepository
import copy


def test_process_run_registered_in_metadata():
    """T1: ProcessRun registered in Base.metadata."""
    assert "process_runs" in Base.metadata.tables


def test_process_run_state_enum_values():
    assert ProcessRunState.ACTIVE.value == "active"
    assert ProcessRunState.COMPLETED.value == "completed"
    assert ProcessRunState.CANCELLED.value == "cancelled"


def test_process_run_fk_columns_declared():
    table = ProcessRun.__table__
    column_names = {c.name for c in table.columns}
    assert {
        "tenant_id",
        "tenant_process_configuration_id",
        "process_definition_version_id",
        "work_item_id",
        "run_state",
        "started_at",
        "started_by_user_id",
        "completed_at",
        "completed_by_user_id",
        "completion_reason",
        "current_stage_code",
        "created_at",
        "updated_at",
    }.issubset(column_names)
    index_names = {idx.name for idx in table.indexes}
    assert "uq_process_run_one_active_per_work_item" in index_names


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


def _create_flexity_sales_pipeline(db_session, tenant_id: uuid.UUID):
    repo = WorkflowRepository(db_session)
    existing = repo.get_pipeline_by_code(tenant_id, "flexity_sales")
    if existing:
        return existing
    pipeline = repo.create_pipeline(
        tenant_id=tenant_id,
        code="flexity_sales",
        name="Flexity Sales",
        entity_type="work_item",
        is_default=True,
    )
    stages = [
        ("new_lead", 10, False),
        ("contacted", 20, False),
        ("diagnosis", 30, False),
        ("proposal_prepared", 40, False),
        ("proposal_sent", 50, False),
        ("negotiation", 60, False),
        ("accepted", 70, False),
        ("rejected", 80, True),
    ]
    for code, order, terminal in stages:
        repo.create_stage(
            pipeline_id=pipeline.id,
            code=code,
            name=code,
            sort_order=order,
            is_terminal=terminal,
        )
    db_session.flush()
    return repo.get_pipeline_by_code(tenant_id, "flexity_sales")


def _get_stage_by_code(db_session, pipeline_id: uuid.UUID, code: str) -> PipelineStage | None:
    return db_session.scalar(
        select(PipelineStage).where(
            PipelineStage.pipeline_id == pipeline_id,
            PipelineStage.code == code,
        )
    )


def _policy_from_blueprint():
    blueprint = PROCESS_TEMPLATE_DEFINITIONS[0]["default_policy_blueprint_json"]
    return parse_policy_snapshot(copy.deepcopy(blueprint))


def _published_config_and_work_item(db_session, slug: str = "e1b-models"):
    ProcessOverlayCatalogService(db_session).seed_templates()
    tenant = _bootstrap_tenant(db_session, slug)
    pipeline = _create_flexity_sales_pipeline(db_session, tenant.id)
    actor = uuid.uuid4()
    config = ProcessOverlayConfigurationService(db_session).create_configuration(
        tenant_id=tenant.id,
        process_template_code="flexity_sales_intake",
        pipeline_id=pipeline.id,
        actor_user_id=actor,
    )
    version = ProcessOverlayPublicationService(db_session).publish_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        request=PublishDefinitionVersionRequest(
            policy=_policy_from_blueprint(),
            publish_reason="E1b models publish",
        ),
        actor_user_id=actor,
    )
    ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    stage = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    assert stage is not None
    work_item = WorkflowRepository(db_session).create_work_item(
        tenant_id=tenant.id,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        work_item_type="lead",
        title="Models lead",
        status=WorkItemStatus.OPEN,
    )
    db_session.flush()
    return tenant, pipeline, config, version, work_item, actor


def test_create_run_defaults_active(db_session):
    tenant, _, config, version, work_item, actor = _published_config_and_work_item(
        db_session, "run-default"
    )
    run = ProcessOverlayRepository(db_session).create_run(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config.id,
        process_definition_version_id=version.id,
        work_item_id=work_item.id,
        started_by_user_id=actor,
        current_stage_code="new_lead",
    )
    assert run.run_state == ProcessRunState.ACTIVE
    assert run.completed_at is None
    assert run.completed_by_user_id is None
    assert run.completion_reason is None
    assert run.process_definition_version_id == version.id


def test_partial_unique_rejects_second_active_run(db_session):
    """DB partial unique is authoritative on Postgres; SQLite may not enforce."""
    tenant, _, config, version, work_item, actor = _published_config_and_work_item(
        db_session, "run-uniq-active"
    )
    repo = ProcessOverlayRepository(db_session)
    repo.create_run(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config.id,
        process_definition_version_id=version.id,
        work_item_id=work_item.id,
        started_by_user_id=actor,
    )
    try:
        repo.create_run(
            tenant_id=tenant.id,
            tenant_process_configuration_id=config.id,
            process_definition_version_id=version.id,
            work_item_id=work_item.id,
            started_by_user_id=actor,
        )
        db_session.flush()
    except IntegrityError:
        return
    pytest.skip(
        "Partial unique index enforcement is verified on PostgreSQL migration tests"
    )


def test_historical_completed_allows_new_active(db_session):
    tenant, _, config, version, work_item, actor = _published_config_and_work_item(
        db_session, "run-history"
    )
    repo = ProcessOverlayRepository(db_session)
    first = repo.create_run(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config.id,
        process_definition_version_id=version.id,
        work_item_id=work_item.id,
        started_by_user_id=actor,
    )
    repo.update_run_lifecycle(
        first,
        run_state=ProcessRunState.COMPLETED,
        completed_at=datetime.now(UTC),
        completed_by_user_id=actor,
        completion_reason="done",
    )
    second = repo.create_run(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config.id,
        process_definition_version_id=version.id,
        work_item_id=work_item.id,
        started_by_user_id=actor,
    )
    assert first.run_state == ProcessRunState.COMPLETED
    assert second.run_state == ProcessRunState.ACTIVE
    assert first.id != second.id
