"""Tests for flexity-sales lead automation one-shot ops CLI."""

from __future__ import annotations

import copy
import json
import os
import shutil
import socket
import stat
import subprocess
import tempfile
import uuid
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings
from app.core.enums import TenantRole, TenantStatus, WorkItemStatus
from app.modules.audit.models import AuditLog
from app.modules.auth.models import User
from app.modules.module_registry.service import ModuleRegistryService
from app.modules.process_overlay.enums import ProcessOverlayActivationState, ProcessRunState
from app.modules.process_overlay.models import ProcessRun
from app.modules.process_overlay.ops.lead_automation_activation import (
    BACKUP_FILE_MODE,
    BACKUP_SCHEMA_VERSION,
    PHRASE_APPLY,
    PHRASE_DRY_RUN,
    PHRASE_ROLLBACK,
    OpsActivationError,
    PRODUCTION_DATABASE_NAME,
    WORKTREE_ROOT,
    build_parser,
    canonical_json_hash,
    load_backup_manifest,
    merge_lead_automation_config,
    parse_database_name,
    resolve_and_validate_backup_dir,
    run_with_session,
    validate_confirm_phrase,
    write_backup,
)
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.service import ProcessOverlayRunService
from app.modules.provider.models import ProviderCompany
from app.modules.tenants.models import Tenant, TenantSettings, UserTenantMembership
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.service.lead_automation import load_lead_automation_config

BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKTREE_ROOT_FROM_TEST = BACKEND_ROOT.parent
EPHEMERAL_PG_DIR = WORKTREE_ROOT_FROM_TEST / ".ephemeral_pg"


@pytest.fixture(autouse=True)
def default_rehearsal_database_url(monkeypatch, request):
    if request.node.get_closest_marker("production_db"):
        return
    settings = get_settings()
    if parse_database_name(settings.database_url) == PRODUCTION_DATABASE_NAME:
        base_url = settings.database_url.rsplit("/", 1)[0]
        monkeypatch.setattr(
            settings,
            "database_url",
            f"{base_url}/coreops_rehearsal_ops_test",
        )


@pytest.fixture
def backup_dir():
    path = Path(tempfile.mkdtemp(prefix="ops_backup_"))
    assert not _path_is_under_worktree(path)
    yield path
    shutil.rmtree(path, ignore_errors=True)


def _path_is_under_worktree(path: Path) -> bool:
    try:
        path.resolve().relative_to(WORKTREE_ROOT.resolve())
        return True
    except ValueError:
        return False


def _absolute_backup_path(base: Path, name: str | None = None) -> Path:
    target = base / name if name else base
    target.mkdir(parents=True, exist_ok=True)
    return target.resolve()


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


def _create_flexity_sales_pipeline(db_session: Session, tenant_id: uuid.UUID):
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
    for stage_code, order, terminal in stages:
        repo.create_stage(
            pipeline_id=pipeline.id,
            code=stage_code,
            name=stage_code,
            sort_order=order,
            is_terminal=terminal,
        )
    db_session.flush()
    return repo.get_pipeline_by_code(tenant_id, "flexity_sales")


def _make_user(db_session: Session, email: str, *, is_active: bool = True) -> User:
    user = User(
        email=email,
        hashed_password="hashed",
        full_name="Ops User",
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


def _seed_tenant_settings(
    db_session: Session,
    tenant_id: uuid.UUID,
    industry_config: dict | None = None,
) -> TenantSettings:
    settings = TenantSettings(
        tenant_id=tenant_id,
        labels_config={},
        industry_config_json=industry_config or {"other_root_key": {"keep": True}},
    )
    db_session.add(settings)
    db_session.flush()
    return settings


def _setup_ops_fixture(db_session: Session, slug: str):
    tenant = _bootstrap_tenant(db_session, slug)
    _create_flexity_sales_pipeline(db_session, tenant.id)
    operator = _make_user(db_session, f"{slug}-operator@test.com")
    assignee = _make_user(db_session, f"{slug}-assignee@test.com")
    _add_membership(db_session, tenant_id=tenant.id, user_id=operator.id)
    _add_membership(db_session, tenant_id=tenant.id, user_id=assignee.id)
    settings = _seed_tenant_settings(
        db_session,
        tenant.id,
        {
            "other_root_key": {"keep": True},
            "consulting": {"other_consulting_key": "preserve-me"},
        },
    )
    ModuleRegistryService(db_session).enable_modules_ordered(tenant.id, ["parties", "crm"])
    db_session.commit()
    return tenant, operator, assignee, settings


def _args(
    *,
    tenant_slug: str,
    operator_id: uuid.UUID,
    assignee_id: uuid.UUID,
    config_hash: str,
    apply: bool = False,
    backup_dir: str | None = None,
    rollback_from: str | None = None,
    pipeline_code: str = "flexity_sales",
    confirm_phrase: str | None = None,
    production_ack: bool = False,
    confirm_production_database: bool = False,
):
    parser = build_parser()
    phrase = confirm_phrase
    if phrase is None:
        if rollback_from:
            phrase = PHRASE_ROLLBACK
        elif apply:
            phrase = PHRASE_APPLY
        else:
            phrase = PHRASE_DRY_RUN
    argv = [
        "--tenant-slug",
        tenant_slug,
        "--pipeline-code",
        pipeline_code,
        "--assignee-user-id",
        str(assignee_id),
        "--operator-user-id",
        str(operator_id),
        "--expected-config-hash",
        config_hash,
        "--confirm-phrase",
        phrase,
    ]
    if apply:
        argv.append("--apply")
    if backup_dir:
        argv.extend(["--backup-dir", backup_dir])
    if rollback_from:
        argv.extend(["--rollback-from", rollback_from])
    if production_ack:
        argv.append("--i-understand-production")
    if confirm_production_database:
        argv.append("--confirm-production-database")
    return parser.parse_args(argv)


def _audit_count(db_session: Session, tenant_id: uuid.UUID) -> int:
    return db_session.scalar(
        select(func.count()).select_from(AuditLog).where(AuditLog.tenant_id == tenant_id)
    )


# --- unit ---


def test_canonical_hash_stable_for_key_order():
    first = {"b": 2, "a": {"z": 1, "y": 2}}
    second = {"a": {"y": 2, "z": 1}, "b": 2}
    assert canonical_json_hash(first) == canonical_json_hash(second)


def test_merge_preserves_sibling_keys():
    assignee = uuid.uuid4()
    merged = merge_lead_automation_config(
        {
            "other_root_key": {"keep": True},
            "consulting": {"other_consulting_key": "preserve-me"},
        },
        assignee_user_id=assignee,
        sla_minutes=240,
        task_template_code="consulting_first_contact",
        create_activity=True,
    )
    assert merged["other_root_key"] == {"keep": True}
    assert merged["consulting"]["other_consulting_key"] == "preserve-me"
    assert merged["consulting"]["lead_automation"]["default_assignee_user_id"] == str(assignee)


def test_wrong_confirm_phrase_exit_code(db_session):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-phrase")
    config_hash = canonical_json_hash(settings.industry_config_json)
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        confirm_phrase="wrong phrase",
    )
    with pytest.raises(OpsActivationError, match="confirm-phrase mismatch"):
        run_with_session(db_session, args)
    with pytest.raises(OpsActivationError, match="confirm-phrase mismatch"):
        validate_confirm_phrase(
            phrase="wrong phrase",
            apply_mode=False,
            rollback_mode=False,
        )


# --- integration (sqlite db_session) ---


def test_dry_run_zero_writes(db_session):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-dryrun")
    config_hash = canonical_json_hash(settings.industry_config_json)
    before_audit = _audit_count(db_session, tenant.id)
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
    )
    plan = run_with_session(db_session, args)
    assert plan.mode == "dry-run"
    assert plan.config_merge_needed is True
    assert _audit_count(db_session, tenant.id) == before_audit
    refreshed = db_session.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    assert refreshed is not None
    assert "lead_automation" not in (refreshed.industry_config_json.get("consulting") or {})


def test_apply_and_idempotent_second_apply(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-apply")
    config_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "backup1")
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(apply_backup),
    )
    plan1 = run_with_session(db_session, args)
    assert plan1.mode == "apply"
    assert plan1.activation_state == ProcessOverlayActivationState.ACTIVE.value
    cfg = load_lead_automation_config(db_session, tenant.id)
    assert cfg is not None
    assert cfg.default_assignee_user_id == assignee.id

    manifest = json.loads((apply_backup / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["script_id"] == "activate_flexity_sales_lead_automation"
    assert manifest["schema_version"] == BACKUP_SCHEMA_VERSION
    assert manifest["config_hash_before"] == config_hash
    assert manifest["config_hash_after"] == plan1.config_hash
    assert "secret" not in json.dumps(manifest).lower()
    assert "industry_config_json" not in manifest

    second_backup = _absolute_backup_path(backup_dir, "backup2")
    args2 = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=plan1.config_hash,
        apply=True,
        backup_dir=str(second_backup),
    )
    plan2 = run_with_session(db_session, args2)
    assert plan2.config_merge_needed is False


def test_wrong_config_hash_aborts(db_session):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-hash")
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash="0" * 64,
    )
    with pytest.raises(OpsActivationError, match="expected-config-hash mismatch"):
        run_with_session(db_session, args)


def test_wrong_pipeline_code(db_session):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-pipeline")
    config_hash = canonical_json_hash(settings.industry_config_json)
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        pipeline_code="wrong_pipeline",
    )
    with pytest.raises(OpsActivationError, match="flexity_sales"):
        run_with_session(db_session, args)


def test_assignee_not_in_tenant_fails(db_session):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-assignee")
    outsider = _make_user(db_session, "outsider@test.com")
    db_session.commit()
    config_hash = canonical_json_hash(settings.industry_config_json)
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=outsider.id,
        config_hash=config_hash,
    )
    with pytest.raises(Exception, match="active member"):
        run_with_session(db_session, args)


@pytest.mark.production_db
def test_production_apply_denied_without_flag(db_session, monkeypatch, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-prod")
    config_hash = canonical_json_hash(settings.industry_config_json)
    monkeypatch.setenv("APP_ENV", "production")
    get_settings.cache_clear()
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(_absolute_backup_path(backup_dir, "prod-deny")),
    )
    with pytest.raises(OpsActivationError, match="--i-understand-production"):
        run_with_session(db_session, args)
    get_settings.cache_clear()


@pytest.mark.production_db
def test_staging_env_on_production_database_name_rejected(db_session, monkeypatch, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-staging-prod-db")
    config_hash = canonical_json_hash(settings.industry_config_json)
    settings_obj = get_settings()
    monkeypatch.setattr(settings_obj, "app_env", "staging")
    monkeypatch.setattr(
        settings_obj,
        "database_url",
        "postgresql+psycopg://coreops:coreops@localhost:5432/coreops",
    )
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(_absolute_backup_path(backup_dir, "staging-prod-db")),
    )
    with pytest.raises(OpsActivationError, match="APP_ENV=staging"):
        run_with_session(db_session, args)


@pytest.mark.production_db
def test_production_database_requires_dual_ack(db_session, monkeypatch, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-dual-ack")
    config_hash = canonical_json_hash(settings.industry_config_json)
    settings_obj = get_settings()
    monkeypatch.setattr(settings_obj, "app_env", "production")
    monkeypatch.setattr(
        settings_obj,
        "database_url",
        "postgresql+psycopg://coreops:coreops@localhost:5432/coreops",
    )
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(_absolute_backup_path(backup_dir, "dual-ack")),
        production_ack=True,
    )
    with pytest.raises(OpsActivationError, match="--confirm-production-database"):
        run_with_session(db_session, args)


def test_public_leads_setting_unchanged(db_session, backup_dir, monkeypatch):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-public")
    config_hash = canonical_json_hash(settings.industry_config_json)
    settings_obj = get_settings()
    monkeypatch.setattr(settings_obj, "public_leads_enabled", True)
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(_absolute_backup_path(backup_dir, "public")),
    )
    plan = run_with_session(db_session, args)
    assert get_settings().public_leads_enabled is True
    assert plan.public_leads_enabled is True


def test_rollback_restores_json_and_deactivates_overlay(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-rollback")
    original = copy.deepcopy(settings.industry_config_json)
    config_hash = canonical_json_hash(original)
    apply_backup = _absolute_backup_path(backup_dir, "rollback-backup")
    apply_args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(apply_backup),
    )
    apply_plan = run_with_session(db_session, apply_args)

    repo = ProcessOverlayRepository(db_session)
    pipeline = WorkflowRepository(db_session).get_pipeline_by_code(tenant.id, "flexity_sales")
    config = repo.get_configuration_by_pipeline(tenant.id, pipeline.id)
    assert config is not None
    stage = next(stage for stage in pipeline.stages if stage.code == "new_lead")
    work_item = WorkflowRepository(db_session).create_work_item(
        tenant_id=tenant.id,
        pipeline_id=pipeline.id,
        stage_id=stage.id,
        work_item_type="lead",
        title="Rollback keep run",
        status=WorkItemStatus.OPEN,
        created_by_user_id=operator.id,
        updated_by_user_id=operator.id,
    )
    run = ProcessOverlayRunService(db_session).start_run(
        tenant_id=tenant.id,
        work_item_id=work_item.id,
        configuration_id=config.id,
        actor_user_id=operator.id,
    )
    db_session.commit()
    run_id = run.id

    rollback_args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=apply_plan.config_hash,
        rollback_from=str(apply_backup),
    )
    plan = run_with_session(db_session, rollback_args)
    assert plan.mode == "rollback"
    assert plan.activation_state == ProcessOverlayActivationState.INACTIVE.value

    restored = db_session.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    assert restored is not None
    assert restored.industry_config_json == original
    assert load_lead_automation_config(db_session, tenant.id) is None

    still_active = db_session.get(ProcessRun, run_id)
    assert still_active is not None
    assert still_active.run_state == ProcessRunState.ACTIVE


def test_apply_failure_is_atomic(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-atomic")
    config_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "atomic")
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(apply_backup),
    )
    with patch(
        "app.modules.process_overlay.ops.lead_automation_activation.execute_overlay",
        side_effect=RuntimeError("boom"),
    ):
        with pytest.raises(RuntimeError, match="boom"):
            run_with_session(db_session, args)
    refreshed = db_session.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    assert refreshed is not None
    assert "lead_automation" not in (refreshed.industry_config_json.get("consulting") or {})
    assert not apply_backup.exists()


def test_dry_run_missing_tenant_settings_no_flush(db_session):
    tenant = _bootstrap_tenant(db_session, "ops-dryrun-no-settings")
    _create_flexity_sales_pipeline(db_session, tenant.id)
    operator = _make_user(db_session, "ops-dryrun-no-settings-operator@test.com")
    assignee = _make_user(db_session, "ops-dryrun-no-settings-assignee@test.com")
    _add_membership(db_session, tenant_id=tenant.id, user_id=operator.id)
    _add_membership(db_session, tenant_id=tenant.id, user_id=assignee.id)
    ModuleRegistryService(db_session).enable_modules_ordered(tenant.id, ["parties", "crm"])
    db_session.commit()

    missing = db_session.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    assert missing is None

    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=canonical_json_hash({}),
    )
    plan = run_with_session(db_session, args)
    assert plan.mode == "dry-run"
    still_missing = db_session.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant.id)
    )
    assert still_missing is None


def test_backup_dir_must_be_outside_worktree():
    inside = WORKTREE_ROOT / ".test_backups" / "inside-repo"
    with pytest.raises(OpsActivationError, match="outside the repository"):
        resolve_and_validate_backup_dir(str(inside))


def test_backup_dir_rejects_symlink():
    real_dir = Path(tempfile.mkdtemp(prefix="ops_backup_real_"))
    link = real_dir.parent / f"{real_dir.name}-link"
    try:
        link.symlink_to(real_dir, target_is_directory=True)
    except (OSError, NotImplementedError):
        pytest.skip("Symlinks not supported in this environment")
    try:
        with pytest.raises(OpsActivationError, match="symlink"):
            resolve_and_validate_backup_dir(str(link))
    finally:
        if link.exists() or link.is_symlink():
            link.unlink(missing_ok=True)
        shutil.rmtree(real_dir, ignore_errors=True)


def test_backup_rejects_existing_manifest_file(backup_dir):
    target = _absolute_backup_path(backup_dir, "existing-files")
    (target / "manifest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(OpsActivationError, match="already exists"):
        write_backup(
            target,
            tenant_id=uuid.uuid4(),
            operator_user_id=uuid.uuid4(),
            industry_config_json={"a": 1},
            config_hash_before=canonical_json_hash({"a": 1}),
        )


@pytest.mark.skipif(os.name == "nt", reason="POSIX file modes are not enforced on Windows")
def test_backup_files_use_mode_0600(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-perms")
    config_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "perms")
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(apply_backup),
    )
    run_with_session(db_session, args)
    for path in (apply_backup / "manifest.json", apply_backup / "industry_config_json.json"):
        mode = stat.S_IMODE(path.stat().st_mode)
        assert mode == BACKUP_FILE_MODE


def test_tampered_backup_manifest_rejected(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-tamper")
    config_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "tamper")
    apply_plan = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=config_hash,
            apply=True,
            backup_dir=str(apply_backup),
        ),
    )
    manifest_path = apply_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config_hash_before"] = "0" * 64
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(OpsActivationError, match="integrity check failed"):
        run_with_session(
            db_session,
            _args(
                tenant_slug=tenant.slug,
                operator_id=operator.id,
                assignee_id=assignee.id,
                config_hash=apply_plan.config_hash,
                rollback_from=str(apply_backup),
            ),
        )


def test_wrong_backup_tenant_rejected(db_session, backup_dir):
    tenant_a, operator_a, assignee_a, settings_a = _setup_ops_fixture(db_session, "ops-tenant-a")
    tenant_b, operator_b, assignee_b, settings_b = _setup_ops_fixture(db_session, "ops-tenant-b")
    apply_backup = _absolute_backup_path(backup_dir, "wrong-tenant")
    apply_plan = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant_a.slug,
            operator_id=operator_a.id,
            assignee_id=assignee_a.id,
            config_hash=canonical_json_hash(settings_a.industry_config_json),
            apply=True,
            backup_dir=str(apply_backup),
        ),
    )
    with pytest.raises(OpsActivationError, match="tenant_id does not match"):
        run_with_session(
            db_session,
            _args(
                tenant_slug=tenant_b.slug,
                operator_id=operator_b.id,
                assignee_id=assignee_b.id,
                config_hash=apply_plan.config_hash,
                rollback_from=str(apply_backup),
            ),
        )


def test_wrong_backup_script_rejected(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-script")
    apply_backup = _absolute_backup_path(backup_dir, "wrong-script")
    apply_plan = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=canonical_json_hash(settings.industry_config_json),
            apply=True,
            backup_dir=str(apply_backup),
        ),
    )
    manifest_path = apply_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["script_id"] = "other_script"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(OpsActivationError, match="script_id mismatch"):
        load_backup_manifest(apply_backup, tenant_id=tenant.id, verify_config_integrity=True)


def test_wrong_backup_schema_rejected(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-schema")
    apply_backup = _absolute_backup_path(backup_dir, "wrong-schema")
    apply_plan = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=canonical_json_hash(settings.industry_config_json),
            apply=True,
            backup_dir=str(apply_backup),
        ),
    )
    manifest_path = apply_backup / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["schema_version"] = 999
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(OpsActivationError, match="schema_version mismatch"):
        load_backup_manifest(apply_backup, tenant_id=tenant.id, verify_config_integrity=True)


def test_rollback_wrong_expected_hash_rejected(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-rb-hash")
    config_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "rb-hash")
    apply_plan = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=config_hash,
            apply=True,
            backup_dir=str(apply_backup),
        ),
    )
    with pytest.raises(OpsActivationError, match="expected-config-hash mismatch for rollback"):
        run_with_session(
            db_session,
            _args(
                tenant_slug=tenant.slug,
                operator_id=operator.id,
                assignee_id=assignee.id,
                config_hash="0" * 64,
                rollback_from=str(apply_backup),
            ),
        )


def test_repeated_apply_and_rollback(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-repeat")
    original_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "repeat")
    apply_plan = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=original_hash,
            apply=True,
            backup_dir=str(apply_backup),
        ),
    )
    run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=apply_plan.config_hash,
            rollback_from=str(apply_backup),
        ),
    )
    second_apply = run_with_session(
        db_session,
        _args(
            tenant_slug=tenant.slug,
            operator_id=operator.id,
            assignee_id=assignee.id,
            config_hash=original_hash,
            apply=True,
            backup_dir=str(_absolute_backup_path(backup_dir, "repeat-2")),
        ),
    )
    assert second_apply.config_merge_needed is True


def test_concurrent_config_update_blocked(db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(db_session, "ops-concurrent")
    config_hash = canonical_json_hash(settings.industry_config_json)
    apply_backup = _absolute_backup_path(backup_dir, "concurrent")
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(apply_backup),
    )

    run_with_session(db_session, args)

    stale_args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(_absolute_backup_path(backup_dir, "concurrent-stale")),
    )
    with pytest.raises(OpsActivationError, match="expected-config-hash mismatch"):
        run_with_session(db_session, stale_args)


# --- ephemeral PostgreSQL (optional) ---


def _find_pg_binary(name: str) -> str | None:
    return shutil.which(name)


def _pick_free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.bind(("127.0.0.1", 0))
        return int(sock.getsockname()[1])


@pytest.fixture(scope="module")
def ephemeral_postgres_url():
    initdb = _find_pg_binary("initdb")
    pg_ctl = _find_pg_binary("pg_ctl")
    psql = _find_pg_binary("psql")
    if not initdb or not pg_ctl or not psql:
        pytest.skip("PostgreSQL binaries not available for ephemeral PG tests")

    pg_user = "ephemeral_pg_user"

    EPHEMERAL_PG_DIR.mkdir(parents=True, exist_ok=True)
    data_dir = EPHEMERAL_PG_DIR / "data"
    if data_dir.exists():
        subprocess.run(
            [pg_ctl, "-D", str(data_dir), "-m", "fast", "-w", "stop"],
            check=False,
        )
        shutil.rmtree(data_dir, ignore_errors=True)
    data_dir.mkdir(parents=True, exist_ok=True)

    port = _pick_free_port()
    subprocess.run([initdb, "-D", str(data_dir), "-U", pg_user, "-A", "trust"], check=True)
    conf = data_dir / "postgresql.conf"
    conf.write_text(
        conf.read_text(encoding="utf-8")
        + f"\nport = {port}\nlisten_addresses = '127.0.0.1'\n",
        encoding="utf-8",
    )
    hba = data_dir / "pg_hba.conf"
    hba.write_text(
        "local all all trust\nhost all all 127.0.0.1/32 trust\nhost all all ::1/128 trust\n",
        encoding="utf-8",
    )

    subprocess.run(
        [pg_ctl, "-D", str(data_dir), "-l", str(EPHEMERAL_PG_DIR / "log.txt"), "-w", "start"],
        check=True,
    )
    db_name = "ops_lead_activation_test"
    subprocess.run(
        [
            psql,
            "-h",
            "127.0.0.1",
            "-p",
            str(port),
            "-U",
            pg_user,
            "-d",
            "postgres",
            "-v",
            "ON_ERROR_STOP=1",
            "-c",
            f"CREATE DATABASE {db_name};",
        ],
        check=True,
    )
    url = f"postgresql+psycopg://{pg_user}@127.0.0.1:{port}/{db_name}"
    yield url

    subprocess.run([pg_ctl, "-D", str(data_dir), "-m", "fast", "-w", "stop"], check=False)
    shutil.rmtree(EPHEMERAL_PG_DIR, ignore_errors=True)


@pytest.fixture
def ephemeral_db_session(ephemeral_postgres_url, monkeypatch):
    from alembic import command
    from alembic.config import Config

    from app.modules.industry_templates.service import IndustryTemplateService
    from app.modules.integrations.service import IntegrationService
    from app.modules.process_overlay.service import ProcessOverlayCatalogService
    from app.modules.subscriptions.service import SubscriptionService

    monkeypatch.setenv("DATABASE_URL", ephemeral_postgres_url)
    get_settings.cache_clear()

    cfg = Config(str(BACKEND_ROOT / "alembic.ini"))
    cfg.set_main_option("sqlalchemy.url", ephemeral_postgres_url)
    command.upgrade(cfg, "head")

    engine = create_engine(ephemeral_postgres_url, pool_pre_ping=True)
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    session = session_factory()
    ModuleRegistryService(session).seed_definitions()
    SubscriptionService(session).seed_catalog()
    IndustryTemplateService(session).seed_templates()
    IntegrationService(session).seed_providers()
    ProcessOverlayCatalogService(session).seed_templates()
    session.commit()
    try:
        yield session
    finally:
        session.close()
        engine.dispose()
        get_settings.cache_clear()


def test_ephemeral_pg_apply_smoke(ephemeral_db_session, backup_dir):
    tenant, operator, assignee, settings = _setup_ops_fixture(
        ephemeral_db_session, "ops-pg-smoke"
    )
    config_hash = canonical_json_hash(settings.industry_config_json)
    args = _args(
        tenant_slug=tenant.slug,
        operator_id=operator.id,
        assignee_id=assignee.id,
        config_hash=config_hash,
        apply=True,
        backup_dir=str(_absolute_backup_path(backup_dir, "pg-smoke")),
    )
    plan = run_with_session(ephemeral_db_session, args)
    assert plan.activation_state == ProcessOverlayActivationState.ACTIVE.value
    assert load_lead_automation_config(ephemeral_db_session, tenant.id) is not None
