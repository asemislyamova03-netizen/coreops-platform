"""E1b ProcessRun service tests (start / complete / cancel + CRM non-hooks)."""

from __future__ import annotations

import copy
import inspect
import uuid

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import IntegrityError, OperationalError

from app.core.enums import TenantStatus, WorkItemStatus
from app.core.exceptions import NotFoundError
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.exceptions import (
    ProcessOverlayActivationError,
    ProcessOverlayValidationError,
    ProcessRunConflictError,
    ProcessRunStateError,
)
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
from app.modules.workflows.models import PipelineStage
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


def _enable_overlay_modules(db_session, tenant_id: uuid.UUID) -> None:
    ModuleRegistryService(db_session).enable_modules_ordered(tenant_id, ["parties", "crm"])


def _setup_configuration(db_session, slug: str = "e1b-run-tenant"):
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
            publish_reason="E1b test publish",
        ),
        actor_user_id=actor_id,
    )


def _activate_overlay(db_session, tenant, config, actor):
    """Publish, set active version, activate. Returns (version, config_orm)."""
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


def _create_work_item(db_session, tenant_id, pipeline, *, title: str = "E1b lead"):
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


def _setup_active_run_context(db_session, slug: str):
    tenant, pipeline, config, actor = _setup_configuration(db_session, slug)
    version, config_orm = _activate_overlay(db_session, tenant, config, actor)
    work_item = _create_work_item(db_session, tenant.id, pipeline, title=f"Lead {slug}")
    return tenant, pipeline, config_orm, version, work_item, actor


def _audit_events_for_run(db_session, run_id: uuid.UUID) -> list[AuditLog]:
    return list(
        db_session.scalars(
            select(AuditLog).where(
                AuditLog.entity_type == "process_run",
                AuditLog.entity_id == run_id,
            )
        ).all()
    )


def _count_runs(db_session, *, tenant_id: uuid.UUID | None = None) -> int:
    stmt = select(ProcessRun)
    if tenant_id is not None:
        stmt = stmt.where(ProcessRun.tenant_id == tenant_id)
    return len(list(db_session.scalars(stmt).all()))


# --- T2 tenant isolation ---


def test_tenant_b_cannot_load_tenant_a_run(db_session):
    tenant_a, _, config_a, _, work_item_a, actor = _setup_active_run_context(db_session, "iso-a")
    tenant_b = _bootstrap_tenant(db_session, "iso-b")
    run = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant_a.id,
        work_item_id=work_item_a.id,
        configuration_id=config_a.id,
        actor_user_id=actor,
    )
    assert ProcessOverlayRepository(db_session).get_run(tenant_b.id, run.id) is None


# --- T3 pin active version ---


def test_start_pins_active_definition_version(db_session):
    tenant, _, config, version, work_item, actor = _setup_active_run_context(db_session, "pin")
    run = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    assert run.process_definition_version_id == version.id
    assert run.process_definition_version_id == config.active_definition_version_id
    assert run.run_state == ProcessRunState.ACTIVE
    assert run.current_stage_code == "new_lead"


# --- T4 inactive config ---


def test_start_fails_if_config_inactive(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "inactive")
    version = _publish_v1(db_session, tenant.id, config.id, actor)
    ProcessOverlayPublicationService(db_session).set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version.id,
        actor_user_id=actor,
    )
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    work_item = _create_work_item(db_session, tenant.id, pipeline)
    assert config_orm.activation_state == ProcessOverlayActivationState.INACTIVE

    with pytest.raises(ProcessOverlayActivationError):
        ProcessOverlayRunService(db_session).start_run(
            tenant_id=tenant.id,
            work_item_id=work_item.id,
            configuration_id=config.id,
            actor_user_id=actor,
        )
    assert _count_runs(db_session, tenant_id=tenant.id) == 0


# --- T5 no active version ---


def test_start_fails_if_no_active_version(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "no-version")
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    # Force ACTIVE without active version (bypass activate_configuration guard).
    config_orm.activation_state = ProcessOverlayActivationState.ACTIVE
    config_orm.active_definition_version_id = None
    db_session.flush()
    work_item = _create_work_item(db_session, tenant.id, pipeline)

    with pytest.raises(ProcessOverlayValidationError):
        ProcessOverlayRunService(db_session).start_run(
            tenant_id=tenant.id,
            work_item_id=work_item.id,
            configuration_id=config.id,
            actor_user_id=actor,
        )
    assert _count_runs(db_session, tenant_id=tenant.id) == 0


# --- T6 pipeline mismatch ---


def test_start_fails_if_work_item_pipeline_mismatch(db_session):
    tenant, pipeline, config, actor = _setup_configuration(db_session, "pipe-mismatch")
    _, config = _activate_overlay(db_session, tenant, config, actor)

    other_pipeline = WorkflowRepository(db_session).create_pipeline(
        tenant_id=tenant.id,
        code="other_sales",
        name="Other Sales",
        entity_type="work_item",
        is_default=False,
    )
    WorkflowRepository(db_session).create_stage(
        pipeline_id=other_pipeline.id,
        code="new_lead",
        name="new_lead",
        sort_order=10,
        is_terminal=False,
    )
    db_session.flush()
    work_item = _create_work_item(db_session, tenant.id, other_pipeline, title="Wrong pipeline")

    with pytest.raises(ProcessOverlayValidationError):
        ProcessOverlayRunService(db_session).start_run(
            tenant_id=tenant.id,
            work_item_id=work_item.id,
            configuration_id=config.id,
            actor_user_id=actor,
        )
    assert _count_runs(db_session, tenant_id=tenant.id) == 0


# --- T7 cross-tenant work item ---


def test_start_fails_cross_tenant_work_item(db_session):
    tenant_a, _, config_a, actor_a = _setup_configuration(db_session, "cross-a")
    _, config_a = _activate_overlay(db_session, tenant_a, config_a, actor_a)
    tenant_b, pipeline_b, _, _ = _setup_configuration(db_session, "cross-b")
    work_item_b = _create_work_item(db_session, tenant_b.id, pipeline_b)

    with pytest.raises(NotFoundError):
        ProcessOverlayRunService(db_session).start_run(
            tenant_id=tenant_a.id,
            work_item_id=work_item_b.id,
            configuration_id=config_a.id,
            actor_user_id=actor_a,
        )
    assert _count_runs(db_session) == 0


# --- T8 second ACTIVE rejected ---


def test_second_active_run_rejected(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "second-active")
    service = ProcessOverlayRunService(db_session)
    first = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    with pytest.raises(ProcessRunConflictError):
        service.start_run(
            tenant_id=tenant.id,
            work_item_id=work_item.id,
            configuration_id=config.id,
            actor_user_id=actor,
        )
    active = ProcessOverlayRepository(db_session).get_active_run_for_work_item(
        tenant.id, work_item.id
    )
    assert active is not None
    assert active.id == first.id
    assert _count_runs(db_session, tenant_id=tenant.id) == 1


# --- T8b race / IntegrityError → ProcessRunConflictError ---


def _postgres_available() -> bool:
    try:
        from app.core.config import get_settings

        engine = create_engine(get_settings().database_url)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except OperationalError:
        return False


postgres_required = pytest.mark.skipif(
    not _postgres_available(),
    reason="Local Postgres is required for concurrent start_run race tests",
)


def _count_active_runs(db_session, *, tenant_id: uuid.UUID, work_item_id: uuid.UUID) -> int:
    return len(
        list(
            db_session.scalars(
                select(ProcessRun).where(
                    ProcessRun.tenant_id == tenant_id,
                    ProcessRun.work_item_id == work_item_id,
                    ProcessRun.run_state == ProcessRunState.ACTIVE,
                )
            ).all()
        )
    )


def test_start_run_integrity_error_maps_to_conflict(db_session, monkeypatch):
    """TOCTOU race path: pre-check misses ACTIVE; IntegrityError → ProcessRunConflictError."""
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "race-map")
    service = ProcessOverlayRunService(db_session)
    first = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )

    # Simulate race window: both callers pass the active-run pre-check.
    monkeypatch.setattr(
        ProcessOverlayRepository,
        "get_active_run_for_work_item",
        lambda self, tenant_id, work_item_id: None,
    )

    def _boom_create_run(self, **kwargs):
        raise IntegrityError(
            "INSERT INTO process_runs",
            {},
            Exception("uq_process_run_one_active_per_work_item"),
        )

    monkeypatch.setattr(ProcessOverlayRepository, "create_run", _boom_create_run)

    with pytest.raises(ProcessRunConflictError) as ei:
        service.start_run(
            tenant_id=tenant.id,
            work_item_id=work_item.id,
            configuration_id=config.id,
            actor_user_id=actor,
        )
    assert type(ei.value) is ProcessRunConflictError
    assert isinstance(ei.value.__cause__, IntegrityError)

    assert _count_active_runs(db_session, tenant_id=tenant.id, work_item_id=work_item.id) == 1
    assert _count_runs(db_session, tenant_id=tenant.id) == 1
    stored = db_session.get(ProcessRun, first.id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE


@postgres_required
def test_postgres_concurrent_start_run_one_active():
    """True concurrent start_run on Postgres: one winner, loser → ProcessRunConflictError."""
    import threading
    from concurrent.futures import ThreadPoolExecutor
    from pathlib import Path

    from alembic import command
    from alembic.config import Config
    from sqlalchemy.orm import sessionmaker

    from app.core.config import get_settings

    get_settings.cache_clear()
    database_url = get_settings().database_url
    if not database_url.startswith("postgresql"):
        pytest.skip("DATABASE_URL is not PostgreSQL")

    backend_root = Path(__file__).resolve().parents[1]
    os_environ_database = database_url
    import os

    os.environ["DATABASE_URL"] = os_environ_database
    get_settings.cache_clear()
    cfg = Config(str(backend_root / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", database_url)
    command.upgrade(cfg, "head")

    engine = create_engine(database_url, pool_size=5, max_overflow=5)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    setup = SessionLocal()
    try:
        from app.modules.module_registry.service import ModuleRegistryService as MRS
        from app.modules.subscriptions.service import SubscriptionService
        from app.modules.industry_templates.service import IndustryTemplateService
        from app.modules.integrations.service import IntegrationService

        MRS(setup).seed_definitions()
        SubscriptionService(setup).seed_catalog()
        IndustryTemplateService(setup).seed_templates()
        IntegrationService(setup).seed_providers()
        ProcessOverlayCatalogService(setup).seed_templates()
        setup.commit()

        slug = f"pg-race-{uuid.uuid4().hex[:8]}"
        tenant, pipeline, config, actor = _setup_configuration(setup, slug)
        _, config_orm = _activate_overlay(setup, tenant, config, actor)
        work_item = _create_work_item(setup, tenant.id, pipeline, title="PG race lead")
        setup.commit()

        tenant_id = tenant.id
        work_item_id = work_item.id
        configuration_id = config_orm.id
        actor_id = actor
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
                run = ProcessOverlayRunService(session).start_run(
                    tenant_id=tenant_id,
                    work_item_id=work_item_id,
                    configuration_id=configuration_id,
                    actor_user_id=actor_id,
                )
                session.commit()
                with lock:
                    results.append(run)
            except ProcessRunConflictError as exc:
                session.rollback()
                with lock:
                    results.append(exc)
            except IntegrityError as exc:
                session.rollback()
                with lock:
                    results.append(("LEAKED_INTEGRITY", exc))
            except Exception as exc:  # noqa: BLE001 — collect unexpected for assertion
                session.rollback()
                with lock:
                    results.append(exc)
        finally:
            session.close()

    with ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(_worker) for _ in range(2)]
        for fut in futures:
            fut.result(timeout=60)

    successes = [r for r in results if hasattr(r, "id") and hasattr(r, "run_state")]
    conflicts = [r for r in results if isinstance(r, ProcessRunConflictError)]
    leaked = [r for r in results if isinstance(r, tuple) and r and r[0] == "LEAKED_INTEGRITY"]
    other = [
        r
        for r in results
        if r not in successes
        and r not in conflicts
        and not (isinstance(r, tuple) and r and r[0] == "LEAKED_INTEGRITY")
    ]

    assert not leaked, f"IntegrityError leaked to caller: {leaked}"
    assert not other, f"Unexpected worker outcomes: {other}"
    assert len(successes) == 1, f"Expected exactly one success, got {results!r}"
    assert len(conflicts) == 1, f"Expected exactly one conflict, got {results!r}"
    assert successes[0].run_state == ProcessRunState.ACTIVE

    verify = SessionLocal()
    try:
        active_count = len(
            list(
                verify.scalars(
                    select(ProcessRun).where(
                        ProcessRun.tenant_id == tenant_id,
                        ProcessRun.work_item_id == work_item_id,
                        ProcessRun.run_state == ProcessRunState.ACTIVE,
                    )
                ).all()
            )
        )
        assert active_count == 1
    finally:
        verify.close()
        engine.dispose()


# --- T9 complete ---


def test_complete_run_from_active(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "complete")
    service = ProcessOverlayRunService(db_session)
    started = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    completed = service.complete_run(
        tenant_id=tenant.id,
        process_run_id=started.id,
        actor_user_id=actor,
        reason="finished",
    )
    assert completed.run_state == ProcessRunState.COMPLETED
    assert completed.completed_by_user_id == actor
    assert completed.completion_reason == "finished"
    assert completed.completed_at is not None

    events = {log.changes_json.get("event") for log in _audit_events_for_run(db_session, started.id)}
    assert "process_run.completed" in events


# --- T10 cancel ---


def test_cancel_run_from_active(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "cancel")
    service = ProcessOverlayRunService(db_session)
    started = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    cancelled = service.cancel_run(
        tenant_id=tenant.id,
        process_run_id=started.id,
        actor_user_id=actor,
        reason="operator cancelled",
    )
    assert cancelled.run_state == ProcessRunState.CANCELLED
    assert cancelled.completion_reason == "operator cancelled"
    assert cancelled.completed_at is not None

    logs = _audit_events_for_run(db_session, started.id)
    cancel_log = next(log for log in logs if log.changes_json.get("event") == "process_run.cancelled")
    assert cancel_log.changes_json["completion_reason"] == "operator cancelled"


def test_cancel_requires_nonempty_reason(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "cancel-reason")
    service = ProcessOverlayRunService(db_session)
    started = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    with pytest.raises(ProcessOverlayValidationError):
        service.cancel_run(
            tenant_id=tenant.id,
            process_run_id=started.id,
            actor_user_id=actor,
            reason="   ",
        )


# --- T11 non-ACTIVE terminal ---


def test_complete_cancel_from_non_active_rejected(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "terminal")
    service = ProcessOverlayRunService(db_session)
    started = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    service.complete_run(
        tenant_id=tenant.id,
        process_run_id=started.id,
        actor_user_id=actor,
    )
    with pytest.raises(ProcessRunStateError):
        service.complete_run(
            tenant_id=tenant.id,
            process_run_id=started.id,
            actor_user_id=actor,
        )
    with pytest.raises(ProcessRunStateError):
        service.cancel_run(
            tenant_id=tenant.id,
            process_run_id=started.id,
            actor_user_id=actor,
            reason="too late",
        )


# --- T12 start does not mutate WorkItem ---


def test_start_does_not_change_work_item_stage_or_status(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "wi-unchanged")
    original_stage_id = work_item.stage_id
    original_status = work_item.status
    ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    db_session.refresh(work_item)
    assert work_item.stage_id == original_stage_id
    assert work_item.status == original_status


# --- T13 create_work_item auto-starts when overlay ACTIVE (E1b2) ---


def test_create_work_item_auto_starts_run_when_config_active(db_session):
    """E1b2: ACTIVE config → WorkflowService.create_work_item starts one ProcessRun.

    Former E1b anti-hook (zero runs + no start_run in source) inverted here.
    Full matrix: tests/test_process_overlay_e1b2_auto_start.py
    """
    tenant, pipeline, config, actor = _setup_configuration(db_session, "crm-create")
    version, config_orm = _activate_overlay(db_session, tenant, config, actor)

    user = User(
        email="e1b-create@test.com",
        hashed_password="hashed",
        full_name="E1b User",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    stage = _get_stage_by_code(db_session, pipeline.id, "new_lead")
    assert stage is not None

    workflows = WorkflowService(db_session, tenant.id)
    created = workflows.create_work_item(
        user,
        WorkItemCreate(
            pipeline_id=pipeline.id,
            stage_id=stage.id,
            work_item_type="lead",
            title="CRM create with overlay",
        ),
    )
    assert created.id is not None
    assert _count_runs(db_session, tenant_id=tenant.id) == 1
    active = ProcessOverlayRepository(db_session).get_active_run_for_work_item(
        tenant.id, created.id
    )
    assert active is not None
    assert active.run_state == ProcessRunState.ACTIVE
    assert active.process_definition_version_id == version.id
    assert active.process_definition_version_id == config_orm.active_definition_version_id
    assert "_maybe_auto_start_process_run" in inspect.getsource(WorkflowService.create_work_item)
    assert "ProcessOverlayRunService" in inspect.getsource(WorkflowService._maybe_auto_start_process_run)


# --- T14 move_stage with ACTIVE run: E1c allows edge + syncs stage (no auto-complete) ---


def test_move_stage_leaves_active_run_unchanged(db_session):
    """E1c rewrite of E1b T14: allowed edge applies; run stays ACTIVE; stage cache syncs."""
    tenant, pipeline, config, _, work_item, actor = _setup_active_run_context(db_session, "crm-move")
    service = ProcessOverlayRunService(db_session)
    started = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )

    user = User(
        email="e1b-move@test.com",
        hashed_password="hashed",
        full_name="E1b Mover",
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()
    second = _get_stage_by_code(db_session, pipeline.id, "contacted")
    assert second is not None

    moved = WorkflowService(db_session, tenant.id).move_stage(
        user,
        work_item.id,
        MoveStageRequest(stage_id=second.id),
    )
    assert moved.stage_id == second.id

    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, started.id)
    assert stored is not None
    assert stored.run_state == ProcessRunState.ACTIVE
    assert stored.current_stage_code == "contacted"  # E1c: sync after applied transition


# --- T15 version pin immutable (no repo update path) ---


def test_version_pin_has_no_repository_update_path():
    public_methods = {
        name
        for name in dir(ProcessOverlayRepository)
        if not name.startswith("_") and callable(getattr(ProcessOverlayRepository, name))
    }
    assert "update_run_definition_version" not in public_methods
    assert "rebind_run_version" not in public_methods
    sig = inspect.signature(ProcessOverlayRepository.update_run_lifecycle)
    assert "process_definition_version_id" not in sig.parameters


def test_update_run_lifecycle_does_not_mutate_pin(db_session):
    tenant, _, config, version, work_item, actor = _setup_active_run_context(db_session, "pin-immut")
    repo = ProcessOverlayRepository(db_session)
    run = repo.create_run(
        tenant_id=tenant.id,
        tenant_process_configuration_id=config.id,
        process_definition_version_id=version.id,
        work_item_id=work_item.id,
        started_by_user_id=actor,
    )
    pinned = run.process_definition_version_id
    from datetime import UTC, datetime

    repo.update_run_lifecycle(
        run,
        run_state=ProcessRunState.COMPLETED,
        completed_at=datetime.now(UTC),
        completed_by_user_id=actor,
        completion_reason="done",
    )
    db_session.refresh(run)
    assert run.process_definition_version_id == pinned


# --- T16 after cancel, new start allowed ---


def test_after_cancel_new_start_allowed(db_session):
    tenant, _, config, _, work_item, actor = _setup_active_run_context(db_session, "restart")
    service = ProcessOverlayRunService(db_session)
    first = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    service.cancel_run(
        tenant_id=tenant.id,
        process_run_id=first.id,
        actor_user_id=actor,
        reason="retry later",
    )
    second = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    assert first.id != second.id
    assert second.run_state == ProcessRunState.ACTIVE
    stored_first = ProcessOverlayRepository(db_session).get_run(tenant.id, first.id)
    assert stored_first is not None
    assert stored_first.run_state == ProcessRunState.CANCELLED


# --- T19 audit started ---


def test_start_writes_process_run_started_audit(db_session):
    tenant, _, config, version, work_item, actor = _setup_active_run_context(db_session, "audit-start")
    run = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    logs = _audit_events_for_run(db_session, run.id)
    started = next(log for log in logs if log.changes_json.get("event") == "process_run.started")
    assert started.summary == "Process run started"
    assert started.changes_json["work_item_id"] == str(work_item.id)
    assert started.changes_json["configuration_id"] == str(config.id)
    assert started.changes_json["definition_version_id"] == str(version.id)
    assert started.changes_json["version_number"] == version.version_number


# --- T20 pin survives active version change ---


def test_changing_active_version_does_not_change_existing_run_pin(db_session):
    tenant, _, config, version_v1, work_item, actor = _setup_active_run_context(
        db_session, "pin-survive"
    )
    service = ProcessOverlayRunService(db_session)
    run = service.start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=actor,
    )
    pinned = run.process_definition_version_id
    assert pinned == version_v1.id

    publication = ProcessOverlayPublicationService(db_session)
    version_v2 = publication.publish_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        request=PublishDefinitionVersionRequest(
            policy=_policy_from_blueprint(),
            publish_reason="second version after run start",
        ),
        actor_user_id=actor,
    )
    publication.set_active_definition_version(
        tenant_id=tenant.id,
        configuration_id=config.id,
        version_id=version_v2.id,
        actor_user_id=actor,
    )
    config_orm = ProcessOverlayRepository(db_session).get_configuration(tenant.id, config.id)
    assert config_orm is not None
    assert config_orm.active_definition_version_id == version_v2.id

    stored = ProcessOverlayRepository(db_session).get_run(tenant.id, run.id)
    assert stored is not None
    assert stored.process_definition_version_id == pinned
    assert stored.process_definition_version_id != version_v2.id
