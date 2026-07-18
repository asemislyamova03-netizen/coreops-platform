"""E1b2 Process Overlay opt-in auto-start on WorkItem create."""

from __future__ import annotations

import copy
import inspect
import uuid

import pytest
from sqlalchemy import select

from app.core.enums import TenantStatus, WorkItemStatus
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.exceptions import ProcessOverlayValidationError
from app.modules.process_overlay.models import ProcessRun
from app.modules.process_overlay.policy_schema import parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import PublishDefinitionVersionRequest
from app.modules.process_overlay.seed import PROCESS_TEMPLATE_DEFINITIONS
from app.modules.process_overlay.service import (
    ProcessOverlayCatalogService,
    ProcessOverlayConfigurationService,
    ProcessOverlayPublicationService,
    ProcessOverlayRunService,
)
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import PipelineStage, WorkItem
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.schemas import MoveStageRequest, WorkItemCreate
from app.modules.workflows.service import WorkflowService


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


def _create_flexity_sales_pipeline(db_session, tenant_id: uuid.UUID, *, code: str = "flexity_sales"):
    repo = WorkflowRepository(db_session)
    existing = repo.get_pipeline_by_code(tenant_id, code)
    if existing:
        return existing
    pipeline = repo.create_pipeline(
        tenant_id=tenant_id,
        code=code,
        name=code.replace("_", " ").title(),
        entity_type="work_item",
        is_default=code == "flexity_sales",
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
    for stage_code, order, terminal in stages:
        repo.create_stage(
            pipeline_id=pipeline.id,
            code=stage_code,
            name=stage_code,
            sort_order=order,
            is_terminal=terminal,
        )
    db_session.flush()
    return repo.get_pipeline_by_code(tenant_id, code)


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


def _enable_overlay_modules(db_session, tenant_id: uuid.UUID) -> None:
    ModuleRegistryService(db_session).enable_modules_ordered(tenant_id, ["parties", "crm"])


def _setup_configuration(db_session, slug: str = "e1b2-tenant"):
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
    return tenant, pipeline, config, actor


def _publish_v1(db_session, tenant_id, config_id, actor_id):
    return ProcessOverlayPublicationService(db_session).publish_definition_version(
        tenant_id=tenant_id,
        configuration_id=config_id,
        request=PublishDefinitionVersionRequest(
            policy=_policy_from_blueprint(),
            publish_reason="E1b2 test publish",
        ),
        actor_user_id=actor_id,
    )


def _activate_overlay(db_session, tenant, config, actor):
    _enable_overlay_modules(db_session, tenant.id)
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    publication = ProcessOverlayPublicationService(db_session)
    publication.set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    activated = ProcessOverlayConfigurationService(db_session).activate_configuration(
        tenant_id=tenant.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    assert activated.activation_state == ProcessOverlayActivationState.ACTIVE
    assert activated.active_definition_version_id == version.id
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    return version, config_orm


def _make_user(db_session, email: str) -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        full_name="E1b2 User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _create_via_service(db_session, tenant, pipeline, user, *, title: str = "E1b2 lead"):
    stage = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    assert stage is not None
    return WorkflowService(db_session, tenant.id).create_work_item(
        user,
        WorkItemCreate(
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            work_item_type="lead",
            title=title,
        ),
    )


def _count_runs(db_session, *, tenant_id: uuid.UUID | None = None) -> int:
    stmt = select(ProcessRun)
    if tenant_id is not None:
        stmt = stmt.where(ProcessRun.tenant_id == tenant_id)
    return len(list(db_session.scalars(stmt).all()))


def _count_work_items(db_session, *, tenant_id: uuid.UUID) -> int:
    stmt = select(WorkItem).where(WorkItem.tenant_id == tenant_id)
    return len(list(db_session.scalars(stmt).all()))


def _audit_started_for_run(db_session, run_id: uuid.UUID) -> list[AuditLog]:
    rows = list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "process_run",
                AuditLog.entity_id == run_id,
            )
        ).all()
    )
    return [
        row
        for row in rows
        if isinstance(row.changes_json, dict)
        and row.changes_json.get("event") == "process_run.started"
    ]


# --- A1 no config ---


def test_a1_no_config_create_unchanged(db_session):
    tenant = _bootstrap_tenant(db_session, "e1b2-a1")
    pipeline = _create_flexity_sales_pipeline(db_session, tenant.id)
    _enable_overlay_modules(db_session, tenant.id)
    user = _make_user(db_session, "e1b2-a1@test.com")

    created = _create_via_service(db_session, tenant, pipeline, user, title="No overlay")
    assert created.id is not None
    assert _count_runs(db_session, tenant_id=tenant.id) == 0
    assert (
        ProcessOverlayRepository(db_session).get_configuration_by_pipeline(
            tenant.id, pipeline.id
        )
        is None
    )


# --- A2 inactive config ---


def test_a2_inactive_config_create_zero_runs(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a2")
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    _enable_overlay_modules(db_session, tenant.id)
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    assert config_orm.activation_state == ProcessOverlayActivationState.INACTIVE

    user = _make_user(db_session, "e1b2-a2@test.com")
    created = _create_via_service(db_session, tenant, pipeline, user, title="Inactive overlay")
    assert created.id is not None
    assert _count_runs(db_session, tenant_id=tenant.id) == 0


# --- A3 active happy path ---


def test_a3_active_config_auto_starts_one_run(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a3")
    version, config_orm = _activate_overlay(db_session, tenant, config, actor)
    user = _make_user(db_session, "e1b2-a3@test.com")

    created = _create_via_service(db_session, tenant, pipeline, user, title="Active overlay")
    assert _count_runs(db_session, tenant_id=tenant.id) == 1
    active = ProcessOverlayRepository(db_session).get_active_run_for_work_item(
        tenant.id, created.id
    )
    assert active is not None
    assert active.run_state == ProcessRunState.ACTIVE
    assert active.process_definition_version_id == version.id
    assert active.process_definition_version_id == config_orm.active_definition_version_id
    assert active.tenant_process_configuration_id == config_orm.id
    assert active.current_stage_code == "new_lead"


# --- A4 audit ---


def test_a4_auto_start_writes_process_run_started_audit(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a4")
    version, _ = _activate_overlay(db_session, tenant, config, actor)
    user = _make_user(db_session, "e1b2-a4@test.com")

    created = _create_via_service(db_session, tenant, pipeline, user, title="Audit overlay")
    active = ProcessOverlayRepository(db_session).get_active_run_for_work_item(
        tenant.id, created.id
    )
    assert active is not None
    started = _audit_started_for_run(db_session, active.id)
    assert len(started) == 1
    assert started[0].changes_json["definition_version_id"] == str(version.id)
    assert started[0].changes_json["work_item_id"] == str(created.id)
    assert started[0].user_id == user.id


# --- A5 tenant isolation ---


def test_a5_tenant_b_active_config_does_not_affect_tenant_a_create(db_session):
    tenant_b, pipeline_b, config_b, actor_b = _setup_configuration(db_session, "e1b2-a5-b")
    _activate_overlay(db_session, tenant_b, config_b, actor_b)

    tenant_a = _bootstrap_tenant(db_session, "e1b2-a5-a")
    pipeline_a = _create_flexity_sales_pipeline(db_session, tenant_a.id)
    _enable_overlay_modules(db_session, tenant_a.id)
    user_a = _make_user(db_session, "e1b2-a5-a@test.com")

    created = _create_via_service(db_session, tenant_a, pipeline_a, user_a, title="Tenant A")
    assert created.tenant_id == tenant_a.id
    assert _count_runs(db_session, tenant_id=tenant_a.id) == 0
    assert _count_runs(db_session, tenant_id=tenant_b.id) == 0


# --- A6 pipeline isolation ---


def test_a6_active_config_on_other_pipeline_does_not_auto_start(db_session):
    tenant, pipeline_x, config, actor = _setup_configuration(db_session, "e1b2-a6")
    _activate_overlay(db_session, tenant, config, actor)
    pipeline_y = _create_flexity_sales_pipeline(
        db_session, tenant.id, code="other_sales_pipeline"
    )
    user = _make_user(db_session, "e1b2-a6@test.com")

    created = _create_via_service(
        db_session, tenant, pipeline_y, user, title="Wrong pipeline create"
    )
    assert created.pipeline_id == pipeline_y.id
    assert created.pipeline_id != pipeline_x.id
    assert _count_runs(db_session, tenant_id=tenant.id) == 0


# --- A7 fail-closed / rollback atomicity ---


def test_a7_active_without_version_fail_closed_rolls_back_work_item(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a7")
    _enable_overlay_modules(db_session, tenant.id)
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    # Bypass activate_configuration guard: ACTIVE without version.
    config_orm.activation_state = ProcessOverlayActivationState.ACTIVE
    config_orm.active_definition_version_id = None
    db_session.flush()

    user = _make_user(db_session, "e1b2-a7@test.com")
    before_items = _count_work_items(db_session, tenant_id=tenant.id)
    before_runs = _count_runs(db_session, tenant_id=tenant.id)

    with pytest.raises(ProcessOverlayValidationError):
        _create_via_service(db_session, tenant, pipeline, user, title="Should rollback")

    db_session.rollback()
    assert _count_work_items(db_session, tenant_id=tenant.id) == before_items
    assert _count_runs(db_session, tenant_id=tenant.id) == before_runs


def test_a7b_monkeypatch_start_run_failure_rolls_back_work_item(db_session, monkeypatch):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a7b")
    _activate_overlay(db_session, tenant, config, actor)
    user = _make_user(db_session, "e1b2-a7b@test.com")

    def _boom(*args, **kwargs):
        raise ProcessOverlayValidationError("forced auto-start failure", errors=["test"])

    monkeypatch.setattr(ProcessOverlayRunService, "start_run", _boom)
    before_items = _count_work_items(db_session, tenant_id=tenant.id)

    with pytest.raises(ProcessOverlayValidationError, match="forced auto-start failure"):
        _create_via_service(db_session, tenant, pipeline, user, title="Boom")

    db_session.rollback()
    assert _count_work_items(db_session, tenant_id=tenant.id) == before_items
    assert _count_runs(db_session, tenant_id=tenant.id) == 0


# --- A8 explicit start still works after inactive create ---


def test_a8_explicit_start_after_inactive_create(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a8")
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    _enable_overlay_modules(db_session, tenant.id)
    user = _make_user(db_session, "e1b2-a8@test.com")

    created = _create_via_service(db_session, tenant, pipeline, user, title="Inactive first")
    assert _count_runs(db_session, tenant_id=tenant.id) == 0

    ProcessOverlayConfigurationService(db_session).activate_configuration(
        tenant_id=tenant.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    run = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=created.id,
        configuration_id=config.id,
        actor_user_id=user.id,
    )
    assert run.run_state == ProcessRunState.ACTIVE
    assert run.process_definition_version_id == version.id


# --- A9 source / integration hook present ---


def test_a9_create_work_item_source_calls_overlay_hook(db_session):
    source = inspect.getsource(WorkflowService.create_work_item)
    assert "_maybe_auto_start_process_run" in source
    hook = inspect.getsource(WorkflowService._maybe_auto_start_process_run)
    assert "ProcessOverlayRunService" in hook
    assert "start_run" in hook
    assert "get_configuration_by_pipeline" in hook


# --- A10 move_stage with auto-started run: E1c enforces allowed edge + pin freeze ---


def test_a10_move_stage_still_works_with_auto_started_run(db_session):
    """E1c rewrite of E1b2 A10: allowed move works; pin preserved; run stays ACTIVE."""
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a10")
    _activate_overlay(db_session, tenant, config, actor)
    user = _make_user(db_session, "e1b2-a10@test.com")

    created = _create_via_service(db_session, tenant, pipeline, user, title="Move stage")
    active = ProcessOverlayRepository(db_session).get_active_run_for_work_item(
        tenant.id, created.id
    )
    assert active is not None
    run_id = active.id
    pinned = active.process_definition_version_id

    contacted = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert contacted is not None
    moved = WorkflowService(db_session, tenant.id).move_stage(
        user,
        created.id,
        MoveStageRequest(stage_id=contacted.id),
    )
    assert moved.stage_id == contacted.id
    assert moved.status == WorkItemStatus.IN_PROGRESS

    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, run_id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE
    assert stored.process_definition_version_id == pinned
    assert stored.current_stage_code == "contacted"


# --- A11 no retrospective runs on activation ---


def test_a11_activation_does_not_create_retrospective_runs(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1b2-a11")
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    _enable_overlay_modules(db_session, tenant.id)
    user = _make_user(db_session, "e1b2-a11@test.com")

    preexisting = _create_via_service(
        db_session, tenant, pipeline, user, title="Pre-existing"
    )
    assert _count_runs(db_session, tenant_id=tenant.id) == 0

    ProcessOverlayConfigurationService(db_session).activate_configuration(
        tenant_id=tenant.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    assert (
        ProcessOverlayRepository(db_session).get_active_run_for_work_item(
            tenant.id, preexisting.id
        )
        is None
    )
    assert _count_runs(db_session, tenant_id=tenant.id) == 0

    # New creates after activation do auto-start.
    newer = _create_via_service(db_session, tenant, pipeline, user, title="After activate")
    assert (
        ProcessOverlayRepository(db_session).get_active_run_for_work_item(tenant.id, newer.id)
        is not None
    )


# --- repo helper ---


def test_get_configuration_by_pipeline_tenant_scoped(db_session):
    tenant_a, pipeline_a, config_a, _ = _setup_configuration(db_session, "e1b2-repo-a")
    tenant_b, pipeline_b, config_b, _ = _setup_configuration(db_session, "e1b2-repo-b")
    repo = ProcessOverlayRepository(db_session)

    found_a = repo.get_configuration_by_pipeline(tenant_a.id, pipeline_a.id)
    assert found_a is not None
    assert found_a.id == config_a.id

    assert repo.get_configuration_by_pipeline(tenant_b.id, pipeline_a.id) is None
    assert repo.get_configuration_by_pipeline(tenant_a.id, pipeline_b.id) is None
    found_b = repo.get_configuration_by_pipeline(tenant_b.id, pipeline_b.id)
    assert found_b is not None
    assert found_b.id == config_b.id
