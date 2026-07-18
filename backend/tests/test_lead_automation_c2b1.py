"""C2b1 ProcessRun first-contact task automation tests."""

from __future__ import annotations

import copy
import inspect
import os
import shutil
import subprocess
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime, timedelta
from pathlib import Path
from urllib.parse import urlparse

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session, sessionmaker

from app.core.enums import ActivityType, TaskStatus, TenantRole, TenantStatus
from app.core.exceptions import CoreOpsError
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.models import ProcessRun
from app.modules.process_overlay.policy_schema import parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import PublishDefinitionVersionRequest
from app.modules.process_overlay.seed import PROCESS_TEMPLATE_DEFINITIONS
from app.modules.process_overlay.service import (
    ProcessOverlayBootstrapService,
    ProcessOverlayCatalogService,
    ProcessOverlayConfigurationService,
    ProcessOverlayPublicationService,
    ProcessOverlayRunService,
)
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant, TenantSettings, UserTenantMembership
from app.modules.workflows.models import Activity, PipelineStage, Task, WorkItem
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.schemas import WorkItemCreate
from app.modules.workflows.service import WorkflowService
from app.modules.workflows.service.lead_automation import (
    DEFAULT_SLA_MINUTES,
    DEFAULT_TASK_TEMPLATE_CODE,
    TASK_TITLE,
    LeadAutomationConfigError,
    maybe_create_process_run_first_contact_task,
)


def _bootstrap_tenant(db_session: Session, slug: str) -> Tenant:
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


def _create_flexity_sales_pipeline(db_session: Session, tenant_id: uuid.UUID, *, code: str = "flexity_sales"):
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


def _get_stage_by_code(db_session: Session, pipeline_id: uuid.UUID, code: str) -> PipelineStage | None:
    return db_session.scalar(
        select(PipelineStage).where(
            PipelineStage.pipeline_id == pipeline_id,
            PipelineStage.code == code,
        )
    )


def _policy_from_blueprint():
    blueprint = PROCESS_TEMPLATE_DEFINITIONS[0]["default_policy_blueprint_json"]
    return parse_policy_snapshot(copy.deepcopy(blueprint))


def _enable_overlay_modules(db_session: Session, tenant_id: uuid.UUID) -> None:
    ModuleRegistryService(db_session).enable_modules_ordered(tenant_id, ["parties", "crm"])


def _make_user(db_session: Session, email: str, *, is_active: bool = True) -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        full_name="C2b1 User",
        is_active=is_active,
    )
    db_session.add(user)
    db_session.flush()
    return user


def _add_membership(
    db_session: Session,
    *,
    tenant_id: uuid.UUID,
    user_id: uuid.UUID,
    is_active: bool = True,
) -> UserTenantMembership:
    membership = UserTenantMembership(
        tenant_id=tenant_id,
        user_id=user_id,
        role=TenantRole.TENANT_ADMIN,
        is_active=is_active,
    )
    db_session.add(membership)
    db_session.flush()
    return membership


def _set_lead_automation(
    db_session: Session,
    tenant_id: uuid.UUID,
    config: dict | None,
) -> TenantSettings:
    settings = db_session.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    )
    if settings is None:
        settings = TenantSettings(tenant_id=tenant_id, labels_config={}, industry_config_json={})
        db_session.add(settings)
        db_session.flush()
    industry = dict(settings.industry_config_json or {})
    consulting = dict(industry.get("consulting") or {})
    if config is None:
        consulting.pop("lead_automation", None)
    else:
        consulting["lead_automation"] = config
    if consulting:
        industry["consulting"] = consulting
    elif "consulting" in industry:
        industry.pop("consulting")
    settings.industry_config_json = industry
    db_session.flush()
    return settings


def _setup_configuration(db_session: Session, slug: str = "c2b1-tenant"):
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
            publish_reason="C2b1 test publish",
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
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    return version, config_orm


def _create_work_item(db_session, tenant, pipeline, user, *, title: str = "C2b1 lead"):
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


def _count_tasks(db_session, *, tenant_id: uuid.UUID, process_run_id: uuid.UUID | None = None) -> int:
    stmt = select(Task).where(Task.tenant_id == tenant_id)
    if process_run_id is not None:
        stmt = stmt.where(Task.process_run_id == process_run_id)
    return len(list(db_session.scalars(stmt).all()))


def _count_activities(db_session, *, work_item_id: uuid.UUID) -> int:
    return len(
        list(
            db_session.scalars(
                select(Activity).where(Activity.work_item_id == work_item_id)
            ).all()
        )
    )


def _count_work_items(db_session, *, tenant_id: uuid.UUID) -> int:
    return len(list(db_session.scalars(select(WorkItem).where(WorkItem.tenant_id == tenant_id)).all()))


def _count_runs(db_session, *, tenant_id: uuid.UUID) -> int:
    return len(list(db_session.scalars(select(ProcessRun).where(ProcessRun.tenant_id == tenant_id)).all()))


def _setup_active_with_assignee(db_session, slug: str):
    tenant, pipeline, config, actor = _setup_configuration(db_session, slug)
    _, config_orm = _activate_overlay(db_session, tenant, config, actor)
    assignee = _make_user(db_session, f"{slug}-assignee@test.com")
    _add_membership(db_session, tenant_id=tenant.id, user_id=assignee.id)
    actor_user = _make_user(db_session, f"{slug}-actor@test.com")
    _add_membership(db_session, tenant_id=tenant.id, user_id=actor_user.id)
    return tenant, pipeline, config_orm, actor_user, assignee


# --- Config / no-op ---


def test_no_config_is_noop(db_session):
    tenant, pipeline, config_orm, actor_user, _assignee = _setup_active_with_assignee(
        db_session, "c2b1-noconfig"
    )
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    run = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == created.id))
    assert run is not None
    assert _count_tasks(db_session, tenant_id=tenant.id) == 0
    assert _count_activities(db_session, work_item_id=created.id) == 0


def test_disabled_config_is_noop(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-disabled"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {
            "enabled": False,
            "default_assignee_user_id": str(assignee.id),
        },
    )
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    assert _count_tasks(db_session, tenant_id=tenant.id) == 0
    assert _count_activities(db_session, work_item_id=created.id) == 0


def test_enabled_creates_task_and_activity_default_sla(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-enabled"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {
            "enabled": True,
            "default_assignee_user_id": str(assignee.id),
        },
    )
    before = datetime.now(UTC)
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    after = datetime.now(UTC)

    run = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == created.id))
    assert run is not None
    tasks = list(
        db_session.scalars(
            select(Task).where(Task.tenant_id == tenant.id, Task.process_run_id == run.id)
        ).all()
    )
    assert len(tasks) == 1
    task = tasks[0]
    assert task.title == TASK_TITLE
    assert task.automation_key == DEFAULT_TASK_TEMPLATE_CODE
    assert task.assigned_to_user_id == assignee.id
    assert task.status == TaskStatus.PENDING
    assert task.due_at is not None
    due = task.due_at if task.due_at.tzinfo is not None else task.due_at.replace(tzinfo=UTC)
    expected_min = before + timedelta(minutes=DEFAULT_SLA_MINUTES)
    expected_max = after + timedelta(minutes=DEFAULT_SLA_MINUTES)
    assert expected_min <= due <= expected_max

    activities = list(
        db_session.scalars(select(Activity).where(Activity.work_item_id == created.id)).all()
    )
    assert len(activities) == 1
    assert activities[0].activity_type == ActivityType.NOTE
    assert str(assignee.id) in (activities[0].description or "")


def test_custom_sla_minutes(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-sla"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {
            "enabled": True,
            "default_assignee_user_id": str(assignee.id),
            "first_contact_sla_minutes": 60,
        },
    )
    before = datetime.now(UTC)
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    after = datetime.now(UTC)
    run = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == created.id))
    task = db_session.scalar(select(Task).where(Task.process_run_id == run.id))
    assert task is not None
    due = task.due_at if task.due_at.tzinfo is not None else task.due_at.replace(tzinfo=UTC)
    assert before + timedelta(minutes=60) <= due <= after + timedelta(minutes=60)


def test_create_activity_false_skips_activity(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-noact"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {
            "enabled": True,
            "default_assignee_user_id": str(assignee.id),
            "create_activity": False,
        },
    )
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    run = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == created.id))
    assert _count_tasks(db_session, tenant_id=tenant.id, process_run_id=run.id) == 1
    assert _count_activities(db_session, work_item_id=created.id) == 0


# --- Fail-closed assignee ---


def test_cross_tenant_assignee_fail_closed(db_session):
    tenant, pipeline, config_orm, actor_user, _ = _setup_active_with_assignee(
        db_session, "c2b1-xtenant"
    )
    other = _bootstrap_tenant(db_session, "c2b1-other")
    foreign = _make_user(db_session, "foreign@test.com")
    _add_membership(db_session, tenant_id=other.id, user_id=foreign.id)
    _set_lead_automation(
        db_session,
        tenant.id,
        {"enabled": True, "default_assignee_user_id": str(foreign.id)},
    )
    before_items = _count_work_items(db_session, tenant_id=tenant.id)
    before_runs = _count_runs(db_session, tenant_id=tenant.id)
    with pytest.raises(LeadAutomationConfigError):
        _create_work_item(db_session, tenant, pipeline, actor_user)
    db_session.rollback()
    assert _count_work_items(db_session, tenant_id=tenant.id) == before_items
    assert _count_runs(db_session, tenant_id=tenant.id) == before_runs


def test_inactive_user_fail_closed(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-inactive-user"
    )
    assignee.is_active = False
    db_session.flush()
    _set_lead_automation(
        db_session,
        tenant.id,
        {"enabled": True, "default_assignee_user_id": str(assignee.id)},
    )
    before_items = _count_work_items(db_session, tenant_id=tenant.id)
    with pytest.raises(LeadAutomationConfigError):
        _create_work_item(db_session, tenant, pipeline, actor_user)
    db_session.rollback()
    assert _count_work_items(db_session, tenant_id=tenant.id) == before_items


def test_inactive_membership_fail_closed(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-inactive-mem"
    )
    membership = db_session.scalar(
        select(UserTenantMembership).where(
            UserTenantMembership.tenant_id == tenant.id,
            UserTenantMembership.user_id == assignee.id,
        )
    )
    assert membership is not None
    membership.is_active = False
    db_session.flush()
    _set_lead_automation(
        db_session,
        tenant.id,
        {"enabled": True, "default_assignee_user_id": str(assignee.id)},
    )
    before_items = _count_work_items(db_session, tenant_id=tenant.id)
    with pytest.raises(LeadAutomationConfigError):
        _create_work_item(db_session, tenant, pipeline, actor_user)
    db_session.rollback()
    assert _count_work_items(db_session, tenant_id=tenant.id) == before_items


def test_enabled_missing_assignee_fail_closed(db_session):
    tenant, pipeline, config_orm, actor_user, _ = _setup_active_with_assignee(
        db_session, "c2b1-noassignee"
    )
    _set_lead_automation(db_session, tenant.id, {"enabled": True})
    before_items = _count_work_items(db_session, tenant_id=tenant.id)
    with pytest.raises(LeadAutomationConfigError):
        _create_work_item(db_session, tenant, pipeline, actor_user)
    db_session.rollback()
    assert _count_work_items(db_session, tenant_id=tenant.id) == before_items
    assert isinstance(LeadAutomationConfigError("x"), CoreOpsError)


# --- Idempotency ---


def test_repeated_hook_same_run_one_task_one_activity(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-repeat"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {"enabled": True, "default_assignee_user_id": str(assignee.id)},
    )
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    run = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == created.id))
    assert run is not None
    assert _count_tasks(db_session, tenant_id=tenant.id, process_run_id=run.id) == 1
    assert _count_activities(db_session, work_item_id=created.id) == 1

    maybe_create_process_run_first_contact_task(
        db_session,
        tenant_id=tenant.id,
        process_run_id=run.id,
        work_item_id=created.id,
        actor_user_id=actor_user.id,
    )
    assert _count_tasks(db_session, tenant_id=tenant.id, process_run_id=run.id) == 1
    assert _count_activities(db_session, work_item_id=created.id) == 1


def test_completed_task_same_run_not_recreated(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-done"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {"enabled": True, "default_assignee_user_id": str(assignee.id)},
    )
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    run = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == created.id))
    task = db_session.scalar(select(Task).where(Task.process_run_id == run.id))
    assert task is not None
    task.status = TaskStatus.DONE
    db_session.flush()

    maybe_create_process_run_first_contact_task(
        db_session,
        tenant_id=tenant.id,
        process_run_id=run.id,
        work_item_id=created.id,
        actor_user_id=actor_user.id,
    )
    assert _count_tasks(db_session, tenant_id=tenant.id, process_run_id=run.id) == 1
    assert _count_activities(db_session, work_item_id=created.id) == 1


def test_new_process_run_may_reuse_automation_key(db_session):
    tenant, pipeline, config_orm, actor_user, assignee = _setup_active_with_assignee(
        db_session, "c2b1-newrun"
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {"enabled": True, "default_assignee_user_id": str(assignee.id)},
    )
    first = _create_work_item(db_session, tenant, pipeline, actor_user, title="First")
    run1 = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == first.id))
    ProcessOverlayRunService(db_session).complete_run(
        tenant_id=tenant.id,
        process_run_id=run1.id,
        actor_user_id=actor_user.id,
        reason="done for retest",
    )

    second = _create_work_item(db_session, tenant, pipeline, actor_user, title="Second")
    run2 = db_session.scalar(select(ProcessRun).where(ProcessRun.work_item_id == second.id))
    assert run2 is not None
    assert run2.id != run1.id
    task1 = db_session.scalar(select(Task).where(Task.process_run_id == run1.id))
    task2 = db_session.scalar(select(Task).where(Task.process_run_id == run2.id))
    assert task1 is not None and task2 is not None
    assert task1.automation_key == task2.automation_key == DEFAULT_TASK_TEMPLATE_CODE
    assert task1.id != task2.id


# --- CRM without config unchanged ---


def test_crm_create_without_config_unchanged(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "c2b1-crm-plain")
    # No overlay activation → no ProcessRun; no automation config.
    user = _make_user(db_session, "crm-plain@test.com")
    created = _create_work_item(db_session, tenant, pipeline, user)
    assert _count_runs(db_session, tenant_id=tenant.id) == 0
    assert _count_tasks(db_session, tenant_id=tenant.id) == 0
    assert created.title == "C2b1 lead"


def test_tenant_without_automation_unchanged_with_overlay(db_session):
    tenant, pipeline, config_orm, actor_user, _ = _setup_active_with_assignee(
        db_session, "c2b1-noauto"
    )
    # Overlay active, but no lead_automation config.
    created = _create_work_item(db_session, tenant, pipeline, actor_user)
    assert _count_runs(db_session, tenant_id=tenant.id) == 1
    assert _count_tasks(db_session, tenant_id=tenant.id) == 0
    assert _count_activities(db_session, work_item_id=created.id) == 0


def test_start_run_hook_wired():
    src = inspect.getsource(ProcessOverlayRunService.start_run)
    assert "maybe_create_process_run_first_contact_task" in src
    assert "lead_automation" in src


def test_workflow_auto_start_uses_start_run():
    hook = inspect.getsource(WorkflowService._maybe_auto_start_process_run)
    assert "start_run" in hook
    assert "ProcessOverlayRunService" in hook


# --- Public lead e2e ---


def test_public_lead_e2e_with_overlay_and_config(
    client,
    db_session: Session,
    monkeypatch,
):
    from app.core.config import get_settings
    from app.core.enums import SubscriptionStatus
    from app.modules.public_leads.rate_limit import public_leads_rate_limiter
    from app.modules.subscriptions.repository import SubscriptionRepository
    from app.modules.subscriptions.service import SubscriptionService

    public_leads_rate_limiter.reset()
    settings = get_settings()
    monkeypatch.setattr(settings, "public_leads_enabled", False)
    monkeypatch.setattr(settings, "public_leads_allowed_origins", "")
    monkeypatch.setattr(settings, "process_overlay_bootstrap_enabled", True)
    if settings.app_env.strip().lower() == "production":
        monkeypatch.setattr(settings, "app_env", "development")

    provider = ProviderCompany(name="Flexity", slug=f"flexity-{uuid.uuid4().hex[:8]}")
    user = User(
        email=f"sales-owner-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="not-used",
        full_name="Sales Owner",
        is_active=True,
    )
    db_session.add_all([provider, user])
    db_session.flush()

    tenant = Tenant(
        provider_company_id=provider.id,
        name="Flexity Sales",
        slug=f"flexity-sales-{uuid.uuid4().hex[:8]}",
        status=TenantStatus.TRIAL,
    )
    db_session.add(tenant)
    db_session.flush()
    _add_membership(db_session, tenant_id=tenant.id, user_id=user.id)

    ModuleRegistryService(db_session).enable_modules_ordered(
        tenant.id, ["parties", "crm"], as_trial=True
    )
    SubscriptionService(db_session).seed_catalog()
    plan = SubscriptionRepository(db_session).get_plan_by_code("starter")
    assert plan is not None
    SubscriptionRepository(db_session).upsert_subscription(
        tenant_id=tenant.id,
        plan_id=plan.id,
        status=SubscriptionStatus.TRIAL,
    )

    repo = WorkflowRepository(db_session)
    pipeline = repo.create_pipeline(
        tenant_id=tenant.id,
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
    stage_ids = {}
    for code, order, terminal in stages:
        stage = repo.create_stage(
            pipeline_id=pipeline.id,
            code=code,
            name=code,
            sort_order=order,
            is_terminal=terminal,
        )
        stage_ids[code] = stage.id
    db_session.flush()

    ProcessOverlayBootstrapService(db_session).bootstrap_flexity_sales_intake(
        tenant_id=tenant.id,
        actor_user_id=user.id,
        pipeline_code="flexity_sales",
        activate=True,
    )
    _set_lead_automation(
        db_session,
        tenant.id,
        {
            "enabled": True,
            "default_assignee_user_id": str(user.id),
            "first_contact_sla_minutes": 240,
        },
    )
    db_session.commit()

    monkeypatch.setattr(settings, "public_leads_enabled", True)
    monkeypatch.setattr(settings, "public_leads_target_tenant_id", str(tenant.id))
    monkeypatch.setattr(settings, "public_leads_pipeline_id", str(pipeline.id))
    monkeypatch.setattr(settings, "public_leads_stage_id", str(stage_ids["new_lead"]))
    monkeypatch.setattr(settings, "public_leads_created_by_user_id", str(user.id))
    monkeypatch.setattr(settings, "public_leads_allowed_origins", "https://www.flexity.asia")

    response = client.post(
        "/api/v1/public/leads",
        json={
            "name": "Lead Auto",
            "phone": "+77001112233",
            "email": f"lead-{uuid.uuid4().hex[:8]}@example.com",
            "company": "ACME",
            "preferred_channel": "telegram",
            "process_area": "content operations",
            "message": "Need consulting",
            "source_page": "https://www.flexity.asia/demo/",
            "utm_source": "insights",
            "utm_medium": "site",
            "utm_campaign": "c2b1",
            "utm_content": "hero",
            "utm_term": "automation",
            "referrer": "https://www.flexity.asia/insights/",
            "consent_accepted": True,
            "website": "",
        },
        headers={"Origin": "https://www.flexity.asia"},
    )
    assert response.status_code == 201, response.text

    work_item = (
        db_session.query(WorkItem)
        .filter(WorkItem.tenant_id == tenant.id)
        .order_by(WorkItem.created_at.desc())
        .first()
    )
    assert work_item is not None
    run = db_session.query(ProcessRun).filter(ProcessRun.work_item_id == work_item.id).one()
    task = db_session.query(Task).filter(Task.process_run_id == run.id).one()
    assert task.title == TASK_TITLE
    assert task.assigned_to_user_id == user.id
    assert db_session.query(Activity).filter(Activity.work_item_id == work_item.id).count() == 1
    public_leads_rate_limiter.reset()


# --- Postgres race ---


def _postgres_available() -> bool:
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
        database_url = get_settings().database_url
        if not database_url.startswith("postgresql"):
            return False

        parsed = urlparse(database_url.replace("postgresql+psycopg://", "postgresql://"))
        host = parsed.hostname or "127.0.0.1"
        port = str(parsed.port or 5432)
        user = parsed.username or "postgres"

        pg_isready = shutil.which("pg_isready")
        if pg_isready:
            ready = subprocess.run(
                [pg_isready, "-h", host, "-p", port, "-U", user],
                capture_output=True,
                timeout=5,
                check=False,
            )
            if ready.returncode != 0:
                return False

        engine = create_engine(database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


postgres_required = pytest.mark.skipif(
    not _postgres_available(),
    reason="Local Postgres is required for concurrent automation race tests",
)


@postgres_required
def test_postgres_concurrent_automation_one_task():
    """Two sessions race after ProcessRun exists — exactly one Task."""
    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings
    from app.modules.industry_templates.service import IndustryTemplateService
    from app.modules.integrations.service import IntegrationService
    from app.modules.subscriptions.service import SubscriptionService

    get_settings.cache_clear()
    database_url = get_settings().database_url
    if not database_url.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not PostgreSQL")

    backend_root = Path(__file__).resolve().parents[1]
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)

    # Reconcile stale alembic_version when 0021–0023 DDL already applied.
    engine_probe = create_engine(database_url)
    try:
        with engine_probe.connect() as conn:
            version = conn.execute(text("SELECT version_num FROM alembic_version")).scalar()
            has_0023 = conn.execute(
                text("SELECT to_regclass('public.marketing_storage_resource_profiles')")
            ).scalar()
            has_0024 = False
            if conn.execute(text("SELECT to_regclass('public.tasks')")).scalar():
                cols = {
                    row[0]
                    for row in conn.execute(
                        text(
                            "SELECT column_name FROM information_schema.columns "
                            "WHERE table_name = 'tasks'"
                        )
                    )
                }
                has_0024 = "process_run_id" in cols
        if has_0024 and version != "0024_task_run_automation_key":
            command.stamp(cfg, "0024_task_run_automation_key")
        elif has_0023 and version not in {
            "0023_mkt_storage_profiles",
            "0024_task_run_automation_key",
        }:
            command.stamp(cfg, "0023_mkt_storage_profiles")
    finally:
        engine_probe.dispose()

    command.upgrade(cfg, "head")

    engine = create_engine(database_url, pool_size=5, max_overflow=5)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    setup = SessionLocal()
    try:
        ModuleRegistryService(setup).seed_definitions()
        SubscriptionService(setup).seed_catalog()
        IndustryTemplateService(setup).seed_templates()
        IntegrationService(setup).seed_providers()
        ProcessOverlayCatalogService(setup).seed_templates()
        setup.commit()

        from app.core.enums import WorkItemStatus

        slug = f"pg-auto-{uuid.uuid4().hex[:8]}"
        tenant, pipeline, config, actor = _setup_configuration(setup, slug)
        _, config_orm = _activate_overlay(setup, tenant, config, actor)
        assignee = _make_user(setup, f"{slug}@test.com")
        _add_membership(setup, tenant_id=tenant.id, user_id=assignee.id)
        actor_user = _make_user(setup, f"{slug}-actor@test.com")
        _add_membership(setup, tenant_id=tenant.id, user_id=actor_user.id)

        # Start ProcessRun with automation disabled, then enable for the race.
        stage = _get_stage_by_code(setup, pipeline.id, "new_lead")
        assert stage is not None
        work_item = WorkflowRepository(setup).create_work_item(
            tenant_id=tenant.id,
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            work_item_type="lead",
            title="PG race lead",
            status=WorkItemStatus.OPEN,
            created_by_user_id=actor_user.id,
            updated_by_user_id=actor_user.id,
        )
        run = ProcessOverlayRunService(setup).start_run(
            tenant_id=tenant.id,
            work_item_id=work_item.id,
            configuration_id=config_orm.id,
            actor_user_id=actor_user.id,
        )
        assert _count_tasks(setup, tenant_id=tenant.id, process_run_id=run.id) == 0
        _set_lead_automation(
            setup,
            tenant.id,
            {"enabled": True, "default_assignee_user_id": str(assignee.id)},
        )
        setup.commit()

        tenant_id = tenant.id
        process_run_id = run.id
        work_item_id = work_item.id
        actor_id = actor_user.id
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    results: list[object] = []
    lock = threading.Lock()

    def _worker() -> None:
        session = SessionLocal()
        try:
            barrier.wait(timeout=30)
            try:
                task = maybe_create_process_run_first_contact_task(
                    session,
                    tenant_id=tenant_id,
                    process_run_id=process_run_id,
                    work_item_id=work_item_id,
                    actor_user_id=actor_id,
                )
                session.commit()
                with lock:
                    results.append(("ok", getattr(task, "id", None)))
            except Exception as exc:  # noqa: BLE001
                session.rollback()
                with lock:
                    results.append(("err", exc))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_worker) for _ in range(2)]
        for fut in futures:
            fut.result(timeout=60)

    errors = [r for r in results if r[0] == "err"]
    assert not errors, f"Unexpected errors: {errors}"
    assert len(results) == 2

    verify = SessionLocal()
    try:
        tasks = list(
            verify.scalars(
                select(Task).where(
                    Task.tenant_id == tenant_id,
                    Task.process_run_id == process_run_id,
                )
            ).all()
        )
        assert len(tasks) == 1
        activities = list(
            verify.scalars(select(Activity).where(Activity.work_item_id == work_item_id)).all()
        )
        # Only the insert winner creates Activity.
        assert len(activities) == 1
    finally:
        verify.close()
        engine.dispose()
