"""E1c Process Overlay transition enforcement on CRM stage writers."""

from __future__ import annotations

import copy
import inspect
import os
import threading
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker

from app.core.enums import ActivityType, TenantStatus, WorkItemStatus
from app.core.exceptions import ConflictError, NotFoundError
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.parties.models import CustomFieldDefinition
from app.modules.process_overlay.constants import EVENT_PROCESS_TRANSITION_APPLIED
from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.exceptions import ProcessTransitionDeniedError
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
    ProcessOverlayTransitionGuard,
)
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant
from app.modules.workflows.models import Activity, PipelineStage, WorkItem
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.schemas import (
    CloseWorkItemRequest,
    MoveStageRequest,
    ReopenWorkItemRequest,
    WorkItemUpdate,
)
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


def _enable_overlay_modules(db_session, tenant_id: uuid.UUID) -> None:
    ModuleRegistryService(db_session).enable_modules_ordered(tenant_id, ["parties", "crm"])


def _seed_disposition_fields(db_session, tenant_id: uuid.UUID) -> None:
    db_session.add(
        CustomFieldDefinition(
            tenant_id=tenant_id,
            entity_type="work_item",
            field_key="disposition",
            field_type="select",
            label="Disposition",
            is_required=False,
            sort_order=200,
            options_json={
                "choices": [
                    "spam",
                    "off_topic",
                    "duplicate",
                    "test",
                    "no_response",
                    "other",
                ],
            },
        )
    )
    db_session.add(
        CustomFieldDefinition(
            tenant_id=tenant_id,
            entity_type="work_item",
            field_key="disposition_note",
            field_type="text",
            label="Disposition note",
            is_required=False,
            sort_order=210,
        )
    )
    db_session.flush()


def _make_user(db_session, email: str) -> User:
    user = User(email=email, hashed_password="hashed", full_name=email, is_active=True)
    db_session.add(user)
    db_session.flush()
    return user


def _setup_configuration(db_session, slug: str):
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
            publish_reason="E1c test publish",
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


def _create_work_item(db_session, tenant_id, pipeline, *, title: str = "E1c lead"):
    stage = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    assert stage is not None
    work_item = WorkflowRepository(db_session).create_work_item(
        tenant_id=tenant_id,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        work_item_type="lead",
        title=title,
        status=WorkItemStatus.OPEN,
    )
    db_session.flush()
    return work_item


def _setup_active_run(db_session, slug: str):
    tenant, pipeline, config, actor = _setup_configuration(db_session, slug)
    version, config_orm = _activate_overlay(db_session, tenant, config, actor)
    work_item = _create_work_item(db_session, tenant.id, pipeline, title=f"Lead {slug}")
    user = _make_user(db_session, f"{slug}@test.com")
    started = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config_orm.id,
        actor_user_id=user.id,
    )
    return tenant, pipeline, config_orm, version, work_item, user, started


def _audit_events_for_run(db_session, run_id: uuid.UUID) -> list[AuditLog]:
    return list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "process_run",
                AuditLog.entity_id == run_id,
            )
        ).all()
    )


def _applied_audits(db_session, run_id: uuid.UUID) -> list[AuditLog]:
    return [
        log
        for log in _audit_events_for_run(db_session, run_id)
        if (log.changes_json or {}).get("event") == EVENT_PROCESS_TRANSITION_APPLIED
    ]


def _activities_for_item(db_session, work_item_id: uuid.UUID) -> list[Activity]:
    return list(
        db_session.scalars(select(Activity).where(Activity.work_item_id == work_item_id)).all()
    )


def _move_along_path(db_session, tenant, pipeline, work_item, user, *codes: str):
    wf = WorkflowService(db_session, tenant.id)
    for code in codes:
        stage = _get_stage_by_code(db_session, pipeline.id, code)
        assert stage is not None
        wf.move_stage(user, work_item.id, MoveStageRequest(stage_id=stage.id))
    db_session.refresh(work_item)
    return work_item


# --- C1 / C2 legacy without ACTIVE run ---


def test_c1_no_run_move_stage_legacy(db_session):
    tenant, pipeline, _, _ = _setup_configuration(db_session, "e1c-c1")
    work_item = _create_work_item(db_session, tenant.id, pipeline)
    user = _make_user(db_session, "e1c-c1@test.com")
    target = _get_stage_by_code(db_session, pipeline.id, "proposal_prepared")
    assert target is not None

    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=target.id)
    )
    assert moved.stage_id == target.id
    assert ProcessOverlayRepository(db_session).get_active_run_for_work_item(
        tenant.id, work_item.id
    ) is None


def test_c2_no_run_update_work_item_stage_legacy(db_session):
    tenant, pipeline, _, _ = _setup_configuration(db_session, "e1c-c2")
    work_item = _create_work_item(db_session, tenant.id, pipeline)
    user = _make_user(db_session, "e1c-c2@test.com")
    target = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert target is not None

    updated = WorkflowService(db_session, tenant.id).update_work_item(
        user, work_item.id, WorkItemUpdate(stage_id=target.id)
    )
    assert updated.stage_id == target.id


# --- C3 / C4 / C5 allow / deny via move_stage ---


def test_c3_active_run_allowed_move_stage(db_session):
    tenant, pipeline, _, version, work_item, user, started = _setup_active_run(
        db_session, "e1c-c3"
    )
    contacted = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert contacted is not None

    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=contacted.id)
    )
    assert moved.stage_id == contacted.id
    assert moved.status == WorkItemStatus.IN_PROGRESS

    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE
    assert stored.current_stage_code == "contacted"
    assert stored.process_definition_version_id == version.id

    applied = _applied_audits(db_session, started.id)
    assert len(applied) == 1
    assert applied[0].changes_json["from_stage_code"] == "new_lead"
    assert applied[0].changes_json["to_stage_code"] == "contacted"
    assert applied[0].changes_json["via"] == "move_stage"

    activities = [
        a for a in _activities_for_item(db_session, work_item.id) if a.activity_type == ActivityType.STATUS_CHANGE
    ]
    assert len(activities) == 1


def test_c4_active_run_denied_jump(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c4")
    accepted = _get_stage_by_code(db_session, pipeline.id, "accepted")
    assert accepted is not None
    old_stage_id = work_item.stage_id

    with pytest.raises(ProcessTransitionDeniedError) as exc_info:
        WorkflowService(db_session, tenant.id).move_stage(
            user, work_item.id, MoveStageRequest(stage_id=accepted.id)
        )
    assert exc_info.value.code == "PROCESS_TRANSITION_DENIED"
    assert exc_info.value.from_stage_code == "new_lead"
    assert exc_info.value.to_stage_code == "accepted"

    db_session.refresh(work_item)
    assert work_item.stage_id == old_stage_id
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE
    assert stored.current_stage_code == "new_lead"
    assert _applied_audits(db_session, started.id) == []
    deny_like = [
        log
        for log in _audit_events_for_run(db_session, started.id)
        if "denied" in str((log.changes_json or {}).get("event", ""))
    ]
    assert deny_like == []


def test_c5_active_run_denied_non_edge_stage(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c5")
    proposal = _get_stage_by_code(db_session, pipeline.id, "proposal_prepared")
    assert proposal is not None

    with pytest.raises(ProcessTransitionDeniedError):
        WorkflowService(db_session, tenant.id).move_stage(
            user, work_item.id, MoveStageRequest(stage_id=proposal.id)
        )
    assert _applied_audits(db_session, started.id) == []


# --- C6 shared guard via update_work_item ---


def test_c6_update_work_item_shares_guard(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c6")
    contacted = _get_stage_by_code(db_session, pipeline.id, "contacted")
    accepted = _get_stage_by_code(db_session, pipeline.id, "accepted")
    assert contacted is not None and accepted is not None

    updated = WorkflowService(db_session, tenant.id).update_work_item(
        user, work_item.id, WorkItemUpdate(stage_id=contacted.id)
    )
    assert updated.stage_id == contacted.id
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.current_stage_code == "contacted"
    assert len(_applied_audits(db_session, started.id)) == 1
    assert _applied_audits(db_session, started.id)[0].changes_json["via"] == "update_work_item"

    with pytest.raises(ProcessTransitionDeniedError):
        WorkflowService(db_session, tenant.id).update_work_item(
            user, work_item.id, WorkItemUpdate(stage_id=accepted.id)
        )


# --- C7 same-stage is not a transition ---


def test_c7_same_stage_not_a_transition(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c7")
    current = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    assert current is not None

    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=current.id)
    )
    assert moved.stage_id == current.id
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.current_stage_code == "new_lead"
    assert _applied_audits(db_session, started.id) == []
    assert _activities_for_item(db_session, work_item.id) == []


# --- C8 corrupt policy fail-closed ---


def test_c8_corrupt_policy_fail_closed(db_session, monkeypatch):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c8")

    from app.modules.process_overlay.exceptions import ProcessOverlayValidationError

    def _boom(_payload):
        raise ProcessOverlayValidationError("corrupt pinned policy", errors=["schema"])

    monkeypatch.setattr(
        "app.modules.process_overlay.service.transitions.parse_policy_snapshot",
        _boom,
    )

    contacted = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert contacted is not None
    with pytest.raises(ProcessTransitionDeniedError):
        WorkflowService(db_session, tenant.id).move_stage(
            user, work_item.id, MoveStageRequest(stage_id=contacted.id)
        )
    assert _applied_audits(db_session, started.id) == []


# --- C9 tenant isolation ---


def test_c9_tenant_isolation(db_session):
    tenant_a, pipeline_a, _, _, work_item_a, user_a, _ = _setup_active_run(
        db_session, "e1c-c9a"
    )
    tenant_b, _, _, _ = _setup_configuration(db_session, "e1c-c9b")
    user_b = _make_user(db_session, "e1c-c9b@test.com")
    contacted = _get_stage_by_code(db_session, pipeline_a.id, "contacted")
    assert contacted is not None

    with pytest.raises(NotFoundError):
        WorkflowService(db_session, tenant_b.id).move_stage(
            user_b, work_item_a.id, MoveStageRequest(stage_id=contacted.id)
        )


# --- C10 CRM pipeline check before overlay ---


def test_c10_pipeline_mismatch_crm_conflict_first(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "e1c-c10")
    _activate_overlay(db_session, tenant, config, actor)
    work_item = _create_work_item(db_session, tenant.id, pipeline)
    user = _make_user(db_session, "e1c-c10@test.com")
    ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=user.id,
    )

    other = WorkflowRepository(db_session).create_pipeline(
        tenant_id=tenant.id,
        code="other_pipe",
        name="Other",
        entity_type="work_item",
        is_default=False,
    )
    foreign_stage = WorkflowRepository(db_session).create_stage(
        pipeline_id=other.id,
        code="foreign",
        name="foreign",
        sort_order=10,
        is_terminal=False,
    )
    db_session.flush()

    with pytest.raises(ConflictError, match="does not belong"):
        WorkflowService(db_session, tenant.id).move_stage(
            user, work_item.id, MoveStageRequest(stage_id=foreign_stage.id)
        )


# --- C11 pin freeze ---


def test_c11_pin_freeze_uses_old_edges(db_session):
    tenant, pipeline, config_orm, version, work_item, user, started = _setup_active_run(
        db_session, "e1c-c11"
    )
    pinned = started.process_definition_version_id

    # Publish a stricter v2 without new_lead→contacted, activate it.
    tight = copy.deepcopy(PROCESS_TEMPLATE_DEFINITIONS[0]["default_policy_blueprint_json"])
    tight["transitions"] = [
        {
            "from_stage_code": "contacted",
            "to_stage_code": "diagnosis",
            "conditions": {},
        }
    ]
    v2 = ProcessOverlayPublicationService(db_session).publish_definition_version(
        tenant_id=tenant.id,
        configuration_id=config_orm.id,
        request=PublishDefinitionVersionRequest(
            policy=parse_policy_snapshot(tight),
            publish_reason="stricter v2",
        ),
        actor_user_id=user.id,
    )
    ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config_orm.id,
        version_id=v2.id,
        actor_user_id=user.id,
    )

    contacted = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert contacted is not None
    # Pinned v1 still allows new_lead→contacted
    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=contacted.id)
    )
    assert moved.stage_id == contacted.id
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.process_definition_version_id == pinned
    assert stored.process_definition_version_id != v2.id
    assert version.id == pinned


# --- C12 COMPLETED / CANCELLED → legacy ---


def test_c12_completed_or_cancelled_legacy(db_session):
    tenant, pipeline, config_orm, _, work_item, user, started = _setup_active_run(
        db_session, "e1c-c12"
    )
    ProcessOverlayRunService(db_session).complete_run(
        tenant_id=tenant.id,
        process_run_id=started.id,
        actor_user_id=user.id,
        reason="done",
    )
    proposal = _get_stage_by_code(db_session, pipeline.id, "proposal_prepared")
    assert proposal is not None
    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=proposal.id)
    )
    assert moved.stage_id == proposal.id

    # Separate cancelled path
    work_item2 = _create_work_item(db_session, tenant.id, pipeline, title="c12-cancel")
    started2 = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item2.id,
        configuration_id=config_orm.id,
        actor_user_id=user.id,
    )
    ProcessOverlayRunService(db_session).cancel_run(
        tenant_id=tenant.id,
        process_run_id=started2.id,
        actor_user_id=user.id,
        reason="abort",
    )
    moved2 = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item2.id, MoveStageRequest(stage_id=proposal.id)
    )
    assert moved2.stage_id == proposal.id


# --- C13 conditions ignored ---


def test_c13_conditions_ignored(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c13")
    # Seed edge contacted→diagnosis has required_roles=["sales"]; E1c must still allow.
    _move_along_path(db_session, tenant, pipeline, work_item, user, "contacted")
    diagnosis = _get_stage_by_code(db_session, pipeline.id, "diagnosis")
    assert diagnosis is not None
    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=diagnosis.id)
    )
    assert moved.stage_id == diagnosis.id
    assert len(_applied_audits(db_session, started.id)) == 2


# --- C14 close / reopen ---


def test_c14_close_and_reopen_through_guard(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c14")
    _seed_disposition_fields(db_session, tenant.id)
    _move_along_path(db_session, tenant, pipeline, work_item, user, "contacted", "diagnosis")

    closed = WorkflowService(db_session, tenant.id).close_work_item(
        user, work_item.id, CloseWorkItemRequest(disposition="spam")
    )
    rejected = _get_stage_by_code(db_session, pipeline.id, "rejected")
    assert rejected is not None
    assert closed.stage_id == rejected.id
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.current_stage_code == "rejected"
    assert stored.run_state == ProcessRunState.ACTIVE

    with pytest.raises(ProcessTransitionDeniedError):
        WorkflowService(db_session, tenant.id).reopen_work_item(
            user, work_item.id, ReopenWorkItemRequest(note="try reopen")
        )
    db_session.refresh(work_item)
    assert work_item.stage_id == rejected.id


def test_c14b_close_denied_without_edge(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(
        db_session, "e1c-c14b"
    )
    _seed_disposition_fields(db_session, tenant.id)
    # new_lead → rejected is not an edge
    with pytest.raises(ProcessTransitionDeniedError):
        WorkflowService(db_session, tenant.id).close_work_item(
            user, work_item.id, CloseWorkItemRequest(disposition="spam")
        )
    assert _applied_audits(db_session, started.id) == []


# --- C15 source contract ---


def test_c15_source_contract_shared_guard():
    for method_name in (
        "move_stage",
        "update_work_item",
        "close_work_item",
        "reopen_work_item",
    ):
        source = inspect.getsource(getattr(WorkflowService, method_name))
        assert "_assert_process_transition" in source
    helper = inspect.getsource(WorkflowService._assert_process_transition)
    assert "ProcessOverlayTransitionGuard" in helper
    assert "assert_transition_allowed" in helper


# --- C16 no auto-complete ---


def test_c16_no_auto_complete_on_terminal(db_session):
    tenant, pipeline, _, _, work_item, user, started = _setup_active_run(db_session, "e1c-c16")
    _move_along_path(
        db_session, tenant, pipeline, work_item, user, "contacted", "diagnosis", "accepted"
    )
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE
    assert stored.current_stage_code == "accepted"


# --- deactivated config + ACTIVE run continues ---


def test_deactivated_config_active_run_still_enforced(db_session):
    tenant, pipeline, config_orm, _, work_item, user, started = _setup_active_run(
        db_session, "e1c-deact"
    )
    ProcessOverlayConfigurationService(db_session).deactivate_configuration(
        tenant_id=tenant.id,
        configuration_id=config_orm.id,
        actor_user_id=user.id,
    )
    accepted = _get_stage_by_code(db_session, pipeline.id, "accepted")
    assert accepted is not None
    with pytest.raises(ProcessTransitionDeniedError):
        WorkflowService(db_session, tenant.id).move_stage(
            user, work_item.id, MoveStageRequest(stage_id=accepted.id)
        )
    contacted = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert contacted is not None
    moved = WorkflowService(db_session, tenant.id).move_stage(
        user, work_item.id, MoveStageRequest(stage_id=contacted.id)
    )
    assert moved.stage_id == contacted.id
    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE


# --- lock helpers contract ---


def test_for_update_helpers_present():
    wi_src = inspect.getsource(WorkflowRepository.get_work_item_for_update)
    run_src = inspect.getsource(ProcessOverlayRepository.get_active_run_for_work_item_for_update)
    assert "with_for_update" in wi_src
    assert "with_for_update" in run_src
    assert "FOR UPDATE" in str(
        select(ProcessRun).with_for_update().compile(compile_kwargs={"literal_binds": False})
    ).upper()


def test_lock_order_work_item_then_active_run_identical():
    """move/update/close/reopen must lock WorkItem before ACTIVE ProcessRun."""
    for method_name in (
        "move_stage",
        "update_work_item",
        "close_work_item",
        "reopen_work_item",
    ):
        source = inspect.getsource(getattr(WorkflowService, method_name))
        wi_pos = source.find("_get_work_item_for_update_or_404")
        guard_pos = source.find("_assert_process_transition")
        assert wi_pos != -1, f"{method_name} must lock WorkItem via FOR UPDATE helper"
        assert guard_pos != -1, f"{method_name} must call shared transition guard"
        assert wi_pos < guard_pos, f"{method_name} lock order must be WorkItem → guard/ProcessRun"
    guard_src = inspect.getsource(ProcessOverlayTransitionGuard.assert_transition_allowed)
    assert "get_active_run_for_work_item_for_update" in guard_src


def test_guard_export_available():
    assert ProcessOverlayTransitionGuard is not None


# --- Postgres concurrent transition race (FOR UPDATE serialization) ---


def _postgres_available() -> bool:
    try:
        from app.core.config import get_settings

        get_settings.cache_clear()
        engine = create_engine(get_settings().database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except OperationalError:
        return False


postgres_required = pytest.mark.skipif(
    not _postgres_available(),
    reason="Local Postgres is required for concurrent transition race tests",
)


@postgres_required
def test_postgres_concurrent_move_stage_one_applied_transition():
    """True concurrent move_stage on Postgres: FOR UPDATE → one applied transition."""
    from alembic import command
    from alembic.config import Config

    from app.core.config import get_settings

    get_settings.cache_clear()
    database_url = get_settings().database_url
    if not database_url.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not PostgreSQL")

    backend_root = Path(__file__).resolve().parents[1]
    os.environ["DATABASE_URL"] = database_url
    get_settings.cache_clear()
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")

    engine = create_engine(database_url, pool_size=5, max_overflow=5)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    setup = SessionLocal()
    try:
        from app.modules.industry_templates.service import IndustryTemplateService
        from app.modules.integrations.service import IntegrationService
        from app.modules.subscriptions.service import SubscriptionService

        ModuleRegistryService(setup).seed_definitions()
        SubscriptionService(setup).seed_catalog()
        IndustryTemplateService(setup).seed_templates()
        IntegrationService(setup).seed_providers()
        ProcessOverlayCatalogService(setup).seed_templates()
        setup.commit()

        slug = f"pg-e1c-race-{uuid.uuid4().hex[:8]}"
        tenant, pipeline, config_orm, _, work_item, user, started = _setup_active_run(
            setup, slug
        )
        contacted = _get_stage_by_code(setup, pipeline.id, "contacted")
        assert contacted is not None
        setup.commit()

        tenant_id = tenant.id
        work_item_id = work_item.id
        user_id = user.id
        contacted_id = contacted.id
        run_id = started.id
        new_lead_id = work_item.stage_id
    finally:
        setup.close()

    barrier = threading.Barrier(2)
    results: list[object] = []
    lock = threading.Lock()

    def _worker() -> None:
        session = SessionLocal()
        try:
            actor = session.get(User, user_id)
            assert actor is not None
            barrier.wait(timeout=30)
            try:
                moved = WorkflowService(session, tenant_id).move_stage(
                    actor, work_item_id, MoveStageRequest(stage_id=contacted_id)
                )
                session.commit()
                with lock:
                    results.append(("ok", moved.stage_id))
            except ProcessTransitionDeniedError as exc:
                session.rollback()
                with lock:
                    results.append(("denied", exc))
            except Exception as exc:  # noqa: BLE001 — collect unexpected for assertion
                session.rollback()
                with lock:
                    results.append(("error", exc))
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_worker) for _ in range(2)]
        for fut in futures:
            fut.result(timeout=60)

    assert all(r[0] == "ok" for r in results), f"Unexpected worker outcomes: {results!r}"
    assert {r[1] for r in results} == {contacted_id}

    verify = SessionLocal()
    try:
        item = verify.get(WorkItem, work_item_id)
        assert item is not None
        assert item.stage_id == contacted_id
        assert item.stage_id != new_lead_id

        stored = ProcessOverlayRepository(verify).get_run(tenant_id, run_id)
        assert stored is not None
        assert stored.run_state == ProcessRunState.ACTIVE
        assert stored.current_stage_code == "contacted"

        stage = verify.get(PipelineStage, item.stage_id)
        assert stage is not None
        assert stored.current_stage_code == stage.code

        applied = _applied_audits(verify, run_id)
        assert len(applied) == 1
        assert applied[0].changes_json["from_stage_code"] == "new_lead"
        assert applied[0].changes_json["to_stage_code"] == "contacted"
        assert applied[0].changes_json["via"] == "move_stage"

        activities = [
            a
            for a in _activities_for_item(verify, work_item_id)
            if a.activity_type == ActivityType.STATUS_CHANGE
        ]
        assert len(activities) == 1

        deny_like = [
            log
            for log in _audit_events_for_run(verify, run_id)
            if "denied" in str((log.changes_json or {}).get("event", ""))
        ]
        assert deny_like == []
    finally:
        verify.close()
        engine.dispose()
