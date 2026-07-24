"""One-shot ops activation for flexity-sales lead automation (Process Overlay + tenant config).

Uses ProcessOverlayConfigurationService / ProcessOverlayPublicationService only.
Never imports or calls ProcessOverlayBootstrapService.
"""

from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
import shutil
import sys
import tempfile
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from sqlalchemy import inspect, select, text
from sqlalchemy.orm import Session

from app.core.config import Settings, get_settings
from app.core.enums import AuditAction, TenantStatus
from app.core.exceptions import ConflictError, CoreOpsError, NotFoundError, PermissionDeniedError
from app.core.modules import ModuleGuard
from app.core.permissions import get_provider_staff
from app.modules.audit.recorder import AuditRecorder
from app.modules.auth.models import User
from app.modules.process_overlay.enums import ProcessOverlayActivationState
from app.modules.process_overlay.policy_schema import parse_policy_snapshot
from app.modules.process_overlay.repository import ProcessOverlayRepository
from app.modules.process_overlay.schemas import PublishDefinitionVersionRequest
from app.modules.process_overlay.service.catalog import ProcessOverlayCatalogService
from app.modules.process_overlay.service.configuration import ProcessOverlayConfigurationService
from app.modules.process_overlay.service.policy_fingerprint import (
    find_matching_published_version,
    policy_fingerprint,
)
from app.modules.process_overlay.service.publication import ProcessOverlayPublicationService
from app.modules.tenants.models import Tenant, TenantSettings, UserTenantMembership
from app.modules.workflows.repository import WorkflowRepository
from app.modules.workflows.service.lead_automation import (
    DEFAULT_CREATE_ACTIVITY,
    DEFAULT_SLA_MINUTES,
    DEFAULT_TASK_TEMPLATE_CODE,
    MAX_SLA_MINUTES,
    LeadAutomationConfigError,
    load_lead_automation_config,
)

SCRIPT_NAME = "activate_flexity_sales_lead_automation"
ENTITY_OPS_SCRIPT = "ops_script"
ENTITY_TENANT_SETTINGS = "tenant_settings"

FLEXITY_SALES_PIPELINE = "flexity_sales"
FLEXITY_SALES_TEMPLATE = "flexity_sales_intake"

PHRASE_DRY_RUN = "DRY-RUN flexity-sales lead automation"
PHRASE_APPLY = "APPLY flexity-sales lead automation"
PHRASE_ROLLBACK = "ROLLBACK flexity-sales lead automation"

DEFAULT_PUBLISH_REASON = "Ops activation — flexity-sales lead automation"
REQUIRED_MODULES = ("crm", "parties")

EXIT_OK = 0
EXIT_ERROR = 1
EXIT_VALIDATION = 2

BACKUP_SCHEMA_VERSION = 1
PRODUCTION_DATABASE_NAME = "coreops"
BACKUP_FILE_MODE = 0o600
BACKUP_DIR_MODE = 0o700
WORKTREE_ROOT = Path(__file__).resolve().parents[5]


class OpsActivationError(CoreOpsError):
    """Expected validation/ops failure for this script."""


@dataclass
class ResolvedContext:
    tenant: Tenant
    pipeline_id: uuid.UUID
    pipeline_code: str
    operator_user_id: uuid.UUID
    assignee_user_id: uuid.UUID | None = None
    settings: TenantSettings | None = None
    industry_config_json: dict = field(default_factory=dict)
    config_hash: str = ""


@dataclass
class OverlayPlanStep:
    action: str
    skip_reason: str | None = None


@dataclass
class ActivationPlan:
    mode: str
    tenant_id: uuid.UUID
    tenant_slug: str
    pipeline_id: uuid.UUID
    pipeline_code: str
    operator_user_id: uuid.UUID
    assignee_user_id: uuid.UUID | None
    config_hash: str
    expected_config_hash: str
    overlay_steps: list[OverlayPlanStep] = field(default_factory=list)
    config_merge_needed: bool = True
    production_allowed: bool = False
    environment: str = "development"
    configuration_id: uuid.UUID | None = None
    activation_state: str | None = None
    active_version_id: uuid.UUID | None = None
    policy_fingerprint: str | None = None
    backup_path: str | None = None
    public_leads_enabled: bool = False
    warnings: list[str] = field(default_factory=list)


def canonical_json_hash(document: dict | None) -> str:
    payload = document if isinstance(document, dict) else {}
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def mask_database_target(database_url: str) -> str:
    parsed = urlparse(_normalize_database_url(database_url))
    host = parsed.hostname or "localhost"
    port = parsed.port or 5432
    db_name = (parsed.path or "/").lstrip("/") or "?"
    return f"{host}:{port}/{db_name}"


def _normalize_database_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://").replace(
        "postgresql+asyncpg://",
        "postgresql://",
    )


def parse_database_name(database_url: str) -> str:
    parsed = urlparse(_normalize_database_url(database_url))
    return (parsed.path or "/").lstrip("/") or ""


def is_exact_production_database_name(database_name: str) -> bool:
    return database_name == PRODUCTION_DATABASE_NAME


def _backup_allowlist_roots() -> list[Path]:
    roots: list[Path] = [Path(tempfile.gettempdir()).resolve()]
    extra = os.environ.get("OPS_BACKUP_ROOTS", "").strip()
    if extra:
        for item in extra.split(","):
            item = item.strip()
            if item:
                roots.append(Path(item).expanduser().resolve())
    return roots


def _path_is_under_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except ValueError:
        return False


def resolve_and_validate_backup_dir(backup_dir: str) -> Path:
    raw = Path(backup_dir).expanduser()
    if not raw.is_absolute():
        raise OpsActivationError("--backup-dir must be an absolute path")

    if raw.exists() and raw.is_symlink():
        raise OpsActivationError("--backup-dir must not be a symlink")

    resolved = raw.resolve()
    if _path_is_under_root(resolved, WORKTREE_ROOT):
        raise OpsActivationError("--backup-dir must be outside the repository/worktree root")

    allowed_roots = _backup_allowlist_roots()
    if not any(_path_is_under_root(resolved, root) for root in allowed_roots):
        raise OpsActivationError(
            "--backup-dir must be under an allowed ops backup root "
            f"(system temp or OPS_BACKUP_ROOTS); got {resolved}"
        )

    for part in resolved.parts:
        if part == "..":
            raise OpsActivationError("--backup-dir must not contain path traversal segments")

    return resolved


def _secure_mkdir(path: Path) -> None:
    resolved = path.resolve()
    if resolved.exists():
        if resolved.is_symlink():
            raise OpsActivationError(f"Refusing to use symlink backup path: {resolved}")
        if not resolved.is_dir():
            raise OpsActivationError(f"Backup path exists and is not a directory: {resolved}")
        os.chmod(resolved, BACKUP_DIR_MODE)
        return

    to_create: list[Path] = []
    current = resolved
    while not current.exists():
        to_create.append(current)
        if current.parent == current:
            break
        current = current.parent

    for directory in reversed(to_create):
        if directory.exists():
            if directory.is_symlink() or not directory.is_dir():
                raise OpsActivationError(f"Invalid backup path component: {directory}")
        else:
            os.mkdir(directory, BACKUP_DIR_MODE)
        os.chmod(directory, BACKUP_DIR_MODE)


def _secure_write_new_file(path: Path, content: str) -> None:
    if path.exists():
        raise OpsActivationError(f"Backup file already exists: {path}")
    if path.is_symlink():
        raise OpsActivationError(f"Refusing to write through symlink: {path}")

    parent = path.parent.resolve()
    if not parent.is_dir():
        raise OpsActivationError(f"Backup parent directory missing: {parent}")
    if not _path_is_under_root(path.resolve(), parent):
        raise OpsActivationError(f"Backup path escapes parent directory: {path}")

    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, BACKUP_FILE_MODE)
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, BACKUP_FILE_MODE)


def _secure_overwrite_file(path: Path, content: str) -> None:
    if path.is_symlink():
        raise OpsActivationError(f"Refusing to overwrite symlink: {path}")
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(str(path), flags, BACKUP_FILE_MODE)
    try:
        os.write(fd, content.encode("utf-8"))
    finally:
        os.close(fd)
    os.chmod(path, BACKUP_FILE_MODE)


def _remove_backup_tree(backup_dir: Path) -> None:
    if backup_dir.exists() and backup_dir.is_dir():
        shutil.rmtree(backup_dir, ignore_errors=True)


def merge_lead_automation_config(
    industry_config_json: dict | None,
    *,
    assignee_user_id: uuid.UUID,
    sla_minutes: int,
    task_template_code: str,
    create_activity: bool,
    enabled: bool = True,
) -> dict:
    current = copy.deepcopy(industry_config_json or {})
    consulting = current.get("consulting")
    if not isinstance(consulting, dict):
        consulting = {}
    consulting["lead_automation"] = {
        "enabled": enabled,
        "default_assignee_user_id": str(assignee_user_id),
        "first_contact_sla_minutes": sla_minutes,
        "task_template_code": task_template_code,
        "create_activity": create_activity,
    }
    current["consulting"] = consulting
    return current


def lead_automation_block_matches(current: dict | None, desired_block: dict) -> bool:
    if not isinstance(current, dict):
        return False
    existing = ((current.get("consulting") or {}).get("lead_automation") or {})
    if not isinstance(existing, dict):
        return False
    return existing == desired_block


def redact_uuid(value: uuid.UUID | str | None) -> str:
    if value is None:
        return "[UUID]"
    text_value = str(value)
    if len(text_value) < 8:
        return "[UUID]"
    return f"...{text_value[-4:]}"


def assert_migration_0024_present(db: Session) -> None:
    bind = db.get_bind()
    inspector = inspect(bind)
    if "tasks" not in inspector.get_table_names():
        raise OpsActivationError("Migration 0024 required: tasks table missing")
    columns = {col["name"] for col in inspector.get_columns("tasks")}
    if "automation_key" not in columns or "process_run_id" not in columns:
        raise OpsActivationError(
            "Migration 0024 required: tasks.automation_key / process_run_id missing"
        )
    if bind.dialect.name == "postgresql":
        row = db.execute(
            text(
                "SELECT 1 FROM pg_indexes "
                "WHERE tablename = 'tasks' "
                "AND indexname = 'uq_tasks_tenant_process_run_automation_key'"
            )
        ).first()
        if row is None:
            raise OpsActivationError(
                "Migration 0024 required: partial unique index "
                "uq_tasks_tenant_process_run_automation_key missing"
            )


def resolve_tenant(db: Session, *, tenant_slug: str | None, tenant_id: uuid.UUID | None) -> Tenant:
    if tenant_slug and tenant_id:
        raise OpsActivationError("Provide exactly one of --tenant-slug or --tenant-id")
    if not tenant_slug and not tenant_id:
        raise OpsActivationError("One of --tenant-slug or --tenant-id is required")

    if tenant_id:
        tenant = db.get(Tenant, tenant_id)
    else:
        tenant = db.scalar(select(Tenant).where(Tenant.slug == tenant_slug))
    if tenant is None:
        raise NotFoundError("Tenant not found")
    if tenant.status != TenantStatus.ACTIVE:
        raise OpsActivationError(f"Tenant status must be ACTIVE, got {tenant.status.value}")
    return tenant


def load_tenant_settings(
    db: Session,
    tenant_id: uuid.UUID,
    *,
    for_update: bool = False,
    create_if_missing: bool = True,
) -> TenantSettings:
    stmt = select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    if for_update:
        stmt = stmt.with_for_update()
    settings = db.scalar(stmt)
    if settings is None:
        if not create_if_missing:
            return TenantSettings(
                tenant_id=tenant_id,
                labels_config={},
                industry_config_json={},
            )
        settings = TenantSettings(
            tenant_id=tenant_id,
            labels_config={},
            industry_config_json={},
        )
        db.add(settings)
        db.flush()
    return settings


def assert_operator_access(
    db: Session,
    *,
    tenant: Tenant,
    operator_user_id: uuid.UUID,
) -> User:
    user = db.get(User, operator_user_id)
    if user is None or not user.is_active:
        raise OpsActivationError("operator-user-id must reference an active user")

    membership = db.scalar(
        select(UserTenantMembership).where(
            UserTenantMembership.tenant_id == tenant.id,
            UserTenantMembership.user_id == operator_user_id,
            UserTenantMembership.is_active.is_(True),
        )
    )
    staff = get_provider_staff(user)
    if membership is None and staff is None:
        raise OpsActivationError(
            "operator-user-id must have active tenant membership or provider staff role"
        )
    if staff is not None and staff.provider_company_id != tenant.provider_company_id:
        if membership is None:
            raise OpsActivationError(
                "provider staff operator must belong to tenant provider company"
            )
    return user


def assert_modules_enabled(db: Session, tenant_id: uuid.UUID) -> None:
    guard = ModuleGuard(db, tenant_id)
    for module_code in REQUIRED_MODULES:
        guard.assert_enabled(module_code)


def assert_environment_guards(
    settings: Settings,
    *,
    apply_mode: bool,
    rollback_mode: bool,
    skip_overlay: bool,
    production_ack: bool,
    confirm_production_database: bool,
) -> None:
    env = settings.app_env.strip().lower()
    db_name = parse_database_name(settings.database_url)
    mutating = apply_mode or rollback_mode

    if is_exact_production_database_name(db_name) and mutating:
        if env == "staging":
            raise OpsActivationError(
                "Refusing apply/rollback against production database name 'coreops' "
                "while APP_ENV=staging"
            )
        if env != "production":
            raise OpsActivationError(
                "Production database name 'coreops' requires APP_ENV=production"
            )
        if not production_ack:
            raise OpsActivationError(
                "Production apply/rollback requires --i-understand-production"
            )
        if not confirm_production_database:
            raise OpsActivationError(
                "Production apply/rollback requires --confirm-production-database"
            )

    if env == "production":
        if skip_overlay:
            raise OpsActivationError("--skip-overlay is forbidden in production")
        if mutating and not production_ack:
            raise OpsActivationError(
                "Production apply/rollback requires --i-understand-production"
            )
        if mutating and not confirm_production_database:
            raise OpsActivationError(
                "Production apply/rollback requires --confirm-production-database"
            )


def validate_confirm_phrase(
    *,
    phrase: str,
    apply_mode: bool,
    rollback_mode: bool,
) -> None:
    expected = PHRASE_DRY_RUN
    if apply_mode:
        expected = PHRASE_APPLY
    elif rollback_mode:
        expected = PHRASE_ROLLBACK
    if phrase != expected:
        raise OpsActivationError(
            f"confirm-phrase mismatch; expected exact phrase for mode: {expected!r}"
        )


def build_overlay_plan(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_code: str,
    process_template_code: str,
    skip_overlay: bool,
) -> tuple[list[OverlayPlanStep], uuid.UUID | None, str | None, uuid.UUID | None, str | None]:
    if skip_overlay:
        return ([OverlayPlanStep("skip_overlay", "config-only path")], None, None, None, None)

    repo = ProcessOverlayRepository(db)
    workflows = WorkflowRepository(db)
    pipeline = workflows.get_pipeline_by_code(tenant_id, pipeline_code)
    if pipeline is None:
        raise NotFoundError(f"Pipeline '{pipeline_code}' not found for tenant")

    template = repo.get_template_by_code(process_template_code)
    if template is None or not template.is_active:
        raise NotFoundError(f"Process template '{process_template_code}' not found")

    if template.default_pipeline_code != pipeline_code:
        raise OpsActivationError(
            f"Pipeline code must match template default ({template.default_pipeline_code})"
        )

    desired_policy = parse_policy_snapshot(copy.deepcopy(template.default_policy_blueprint_json))
    desired_fp = policy_fingerprint(desired_policy)

    steps: list[OverlayPlanStep] = []
    steps.append(OverlayPlanStep("seed_catalog", None))

    existing = repo.get_configuration_by_pipeline(tenant_id, pipeline.id)
    if existing is None:
        by_template = next(
            (
                cfg
                for cfg in repo.list_configurations(tenant_id)
                if cfg.process_template_id == template.id
            ),
            None,
        )
        if by_template is None:
            steps.append(OverlayPlanStep("create_configuration", None))
            configuration_id = None
        else:
            configuration_id = by_template.id
            steps.append(OverlayPlanStep("reuse_configuration", "template configuration exists"))
    else:
        configuration_id = existing.id
        steps.append(OverlayPlanStep("reuse_configuration", "pipeline configuration exists"))

    activation_state = None
    active_version_id = None
    if configuration_id is not None:
        config = repo.get_configuration(tenant_id, configuration_id)
        assert config is not None
        activation_state = config.activation_state.value
        active_version_id = config.active_definition_version_id
        matching = find_matching_published_version(
            repo,
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            fingerprint=desired_fp,
        )
        if matching is None:
            steps.append(OverlayPlanStep("publish_definition_version", None))
            steps.append(OverlayPlanStep("set_active_definition_version", None))
        else:
            if config.active_definition_version_id != matching.id:
                steps.append(
                    OverlayPlanStep(
                        "set_active_definition_version",
                        "fingerprint match but active version differs",
                    )
                )
            else:
                steps.append(
                    OverlayPlanStep(
                        "set_active_definition_version",
                        "already pinned to matching version",
                    )
                )
        if config.activation_state == ProcessOverlayActivationState.ACTIVE:
            steps.append(OverlayPlanStep("activate_configuration", "already ACTIVE"))
        else:
            steps.append(OverlayPlanStep("activate_configuration", None))
    else:
        steps.extend(
            [
                OverlayPlanStep("publish_definition_version", None),
                OverlayPlanStep("set_active_definition_version", None),
                OverlayPlanStep("activate_configuration", None),
            ]
        )

    return steps, configuration_id, desired_fp, active_version_id, activation_state


def resolve_context(
    db: Session,
    args: argparse.Namespace,
    *,
    require_assignee: bool,
    lock_settings: bool = False,
    create_settings_if_missing: bool = True,
) -> ResolvedContext:
    tenant = resolve_tenant(
        db,
        tenant_slug=args.tenant_slug,
        tenant_id=_parse_uuid(args.tenant_id, field="tenant-id") if args.tenant_id else None,
    )
    assert_operator_access(
        db,
        tenant=tenant,
        operator_user_id=_parse_uuid(args.operator_user_id, field="operator-user-id"),
    )
    assert_migration_0024_present(db)

    pipeline_code = str(args.pipeline_code).strip()
    if pipeline_code != FLEXITY_SALES_PIPELINE:
        raise OpsActivationError(
            f"--pipeline-code must be '{FLEXITY_SALES_PIPELINE}' for this command"
        )

    workflows = WorkflowRepository(db)
    pipeline = workflows.get_pipeline_by_code(tenant.id, pipeline_code)
    if pipeline is None:
        raise NotFoundError(f"Pipeline '{pipeline_code}' not found for tenant")

    assignee_id: uuid.UUID | None = None
    if require_assignee:
        assignee_id = _parse_uuid(args.assignee_user_id, field="assignee-user-id")
        from app.modules.workflows.service.lead_automation import (
            _assert_assignee_active_same_tenant,
        )

        _assert_assignee_active_same_tenant(db, tenant_id=tenant.id, user_id=assignee_id)
        assert_modules_enabled(db, tenant.id)

    settings = load_tenant_settings(
        db,
        tenant.id,
        for_update=lock_settings,
        create_if_missing=create_settings_if_missing,
    )
    industry = copy.deepcopy(settings.industry_config_json or {})
    config_hash = canonical_json_hash(industry)

    expected = str(args.expected_config_hash).strip() if args.expected_config_hash else ""
    if expected and config_hash != expected:
        raise OpsActivationError(
            "expected-config-hash mismatch; re-run dry-run and refresh hash "
            f"(current={config_hash})"
        )

    return ResolvedContext(
        tenant=tenant,
        pipeline_id=pipeline.id,
        pipeline_code=pipeline_code,
        operator_user_id=_parse_uuid(args.operator_user_id, field="operator-user-id"),
        assignee_user_id=assignee_id,
        settings=settings,
        industry_config_json=industry,
        config_hash=config_hash,
    )


def _parse_uuid(value: str, *, field: str) -> uuid.UUID:
    try:
        return uuid.UUID(str(value).strip())
    except ValueError as exc:
        raise OpsActivationError(f"{field} must be a valid UUID") from exc


def _clamp_sla(value: int) -> int:
    return max(1, min(MAX_SLA_MINUTES, value))


def write_backup(
    backup_dir: Path,
    *,
    tenant_id: uuid.UUID,
    operator_user_id: uuid.UUID,
    industry_config_json: dict,
    config_hash_before: str,
) -> Path:
    _secure_mkdir(backup_dir)
    config_path = backup_dir / "industry_config_json.json"
    manifest_path = backup_dir / "manifest.json"
    config_payload = json.dumps(
        industry_config_json,
        sort_keys=True,
        indent=2,
        ensure_ascii=False,
    )
    _secure_write_new_file(config_path, config_payload)
    manifest = {
        "script": SCRIPT_NAME,
        "script_id": SCRIPT_NAME,
        "schema_version": BACKUP_SCHEMA_VERSION,
        "tenant_id": str(tenant_id),
        "operator_user_id": str(operator_user_id),
        "config_hash_before": config_hash_before,
        "config_hash_after": None,
        "config_hash": config_hash_before,
        "timestamp": datetime.now(UTC).isoformat(),
        "industry_config_file": config_path.name,
    }
    _secure_write_new_file(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True),
    )
    return backup_dir


def finalize_backup_manifest(backup_dir: Path, *, config_hash_after: str) -> None:
    manifest_path = backup_dir / "manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise OpsActivationError(f"Backup manifest missing for finalize: {manifest_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["config_hash_after"] = config_hash_after
    _secure_overwrite_file(
        manifest_path,
        json.dumps(manifest, indent=2, sort_keys=True),
    )


def validate_backup_manifest(
    manifest: dict,
    *,
    tenant_id: uuid.UUID,
    industry_config: dict | None = None,
) -> None:
    script_id = manifest.get("script_id") or manifest.get("script")
    if script_id != SCRIPT_NAME:
        raise OpsActivationError(
            f"Backup manifest script_id mismatch: expected {SCRIPT_NAME!r}, got {script_id!r}"
        )

    schema_version = manifest.get("schema_version")
    if schema_version != BACKUP_SCHEMA_VERSION:
        raise OpsActivationError(
            f"Backup manifest schema_version mismatch: expected {BACKUP_SCHEMA_VERSION}, "
            f"got {schema_version!r}"
        )

    manifest_tenant = manifest.get("tenant_id")
    if manifest_tenant and str(tenant_id) != str(manifest_tenant):
        raise OpsActivationError("Backup tenant_id does not match target tenant")

    config_hash_before = manifest.get("config_hash_before") or manifest.get("config_hash")
    if industry_config is not None and config_hash_before:
        loaded_hash = canonical_json_hash(industry_config)
        if loaded_hash != config_hash_before:
            raise OpsActivationError(
                "Backup industry_config_json integrity check failed (config_hash_before mismatch)"
            )


def load_backup_manifest(
    backup_path: Path,
    *,
    tenant_id: uuid.UUID | None = None,
    verify_config_integrity: bool = False,
) -> tuple[dict, dict]:
    path = backup_path
    if path.is_dir():
        if path.is_symlink():
            raise OpsActivationError("--rollback-from directory must not be a symlink")
        resolved_dir = path.resolve()
        manifest_path = resolved_dir / "manifest.json"
        config_path = resolved_dir / "industry_config_json.json"
    else:
        if path.is_symlink():
            raise OpsActivationError("--rollback-from path must not be a symlink")
        resolved_dir = path.resolve().parent
        manifest_path = resolved_dir / "manifest.json"
        config_path = path.resolve()

    if manifest_path.is_symlink() or not manifest_path.is_file():
        raise OpsActivationError(f"Backup manifest not found: {manifest_path}")
    if config_path.is_symlink():
        raise OpsActivationError(f"Backup config path is a symlink: {config_path}")

    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if config_path.is_file():
        industry_config = json.loads(config_path.read_text(encoding="utf-8"))
    else:
        industry_config = {}

    if tenant_id is not None:
        validate_backup_manifest(
            manifest,
            tenant_id=tenant_id,
            industry_config=industry_config if verify_config_integrity else None,
        )
    return manifest, industry_config


def assert_rollback_config_hash_gate(
    *,
    current_hash: str,
    expected_hash: str,
    manifest: dict,
) -> None:
    manifest_after = manifest.get("config_hash_after")
    if expected_hash:
        if current_hash != expected_hash:
            raise OpsActivationError(
                "expected-config-hash mismatch for rollback; refusing to overwrite tenant config"
            )
        return

    if manifest_after:
        if current_hash != manifest_after:
            raise OpsActivationError(
                "Current tenant config hash does not match backup manifest config_hash_after; "
                "pass --expected-config-hash only after verifying the post-apply state"
            )
        return

    raise OpsActivationError(
        "Rollback requires --expected-config-hash or a manifest with config_hash_after"
    )


def execute_overlay(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    pipeline_id: uuid.UUID,
    pipeline_code: str,
    process_template_code: str,
    operator_user_id: uuid.UUID,
    publish_reason: str,
    skip_overlay: bool,
) -> tuple[uuid.UUID | None, bool]:
    if skip_overlay:
        return None, False

    catalog = ProcessOverlayCatalogService(db)
    configuration_svc = ProcessOverlayConfigurationService(db)
    publication_svc = ProcessOverlayPublicationService(db)
    repo = ProcessOverlayRepository(db)

    catalog.seed_templates()

    existing = repo.get_configuration_by_pipeline(tenant_id, pipeline_id)
    published_new = False
    if existing is None:
        template = repo.get_template_by_code(process_template_code)
        assert template is not None
        by_template = next(
            (
                cfg
                for cfg in repo.list_configurations(tenant_id)
                if cfg.process_template_id == template.id
            ),
            None,
        )
        if by_template is None:
            try:
                created = configuration_svc.create_configuration(
                    tenant_id=tenant_id,
                    process_template_code=process_template_code,
                    pipeline_id=pipeline_id,
                    actor_user_id=operator_user_id,
                )
                configuration_id = created.id
            except ConflictError:
                existing = repo.get_configuration_by_pipeline(tenant_id, pipeline_id)
                if existing is None:
                    raise
                configuration_id = existing.id
        else:
            configuration_id = by_template.id
    else:
        configuration_id = existing.id

    template = repo.get_template_by_code(process_template_code)
    if template is None or not template.is_active:
        raise NotFoundError(f"Process template '{process_template_code}' not found")

    desired_policy = parse_policy_snapshot(copy.deepcopy(template.default_policy_blueprint_json))
    desired_fp = policy_fingerprint(desired_policy)

    matching = find_matching_published_version(
        repo,
        tenant_id=tenant_id,
        configuration_id=configuration_id,
        fingerprint=desired_fp,
    )
    if matching is None:
        version = publication_svc.publish_definition_version(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            request=PublishDefinitionVersionRequest(
                policy=desired_policy,
                publish_reason=publish_reason,
            ),
            actor_user_id=operator_user_id,
        )
        published_new = True
        version_id = version.id
    else:
        version_id = matching.id

    config = repo.get_configuration(tenant_id, configuration_id)
    assert config is not None
    if config.active_definition_version_id != version_id:
        publication_svc.set_active_definition_version(
            tenant_id=tenant_id,
            configuration_id=configuration_id,
            version_id=version_id,
            actor_user_id=operator_user_id,
        )

    configuration_svc.activate_configuration(
        tenant_id=tenant_id,
        configuration_id=configuration_id,
        actor_user_id=operator_user_id,
    )
    return configuration_id, published_new


def audit_script_event(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    operator_user_id: uuid.UUID,
    mode: str,
    summary: str,
    changes: dict[str, Any],
) -> None:
    AuditRecorder(db).audit_log(
        tenant_id=tenant_id,
        user_id=operator_user_id,
        action=AuditAction.UPDATE,
        entity_type=ENTITY_OPS_SCRIPT,
        entity_id=tenant_id,
        summary=summary,
        changes_json={
            "script": SCRIPT_NAME,
            "mode": mode,
            **changes,
        },
    )
    db.flush()


def require_expected_config_hash(args: argparse.Namespace) -> None:
    if not str(args.expected_config_hash or "").strip():
        raise OpsActivationError("--expected-config-hash is required for dry-run and apply")


def run_dry_run(db: Session, args: argparse.Namespace, settings: Settings) -> ActivationPlan:
    require_expected_config_hash(args)
    ctx = resolve_context(
        db,
        args,
        require_assignee=not args.rollback_from,
        lock_settings=False,
        create_settings_if_missing=False,
    )
    overlay_steps, configuration_id, desired_fp, active_version_id, activation_state = (
        build_overlay_plan(
            db,
            tenant_id=ctx.tenant.id,
            pipeline_code=ctx.pipeline_code,
            process_template_code=args.process_template_code,
            skip_overlay=args.skip_overlay,
        )
    )

    desired_block = None
    config_merge_needed = True
    if ctx.assignee_user_id is not None:
        desired_block = {
            "enabled": True,
            "default_assignee_user_id": str(ctx.assignee_user_id),
            "first_contact_sla_minutes": _clamp_sla(args.sla_minutes),
            "task_template_code": args.task_template_code.strip(),
            "create_activity": not args.no_create_activity,
        }
        config_merge_needed = not lead_automation_block_matches(
            ctx.industry_config_json,
            desired_block,
        )

    production_allowed = True
    try:
        assert_environment_guards(
            settings,
            apply_mode=False,
            rollback_mode=bool(args.rollback_from),
            skip_overlay=args.skip_overlay,
            production_ack=args.i_understand_production,
            confirm_production_database=args.confirm_production_database,
        )
    except OpsActivationError:
        production_allowed = False

    return ActivationPlan(
        mode="dry-run",
        tenant_id=ctx.tenant.id,
        tenant_slug=ctx.tenant.slug,
        pipeline_id=ctx.pipeline_id,
        pipeline_code=ctx.pipeline_code,
        operator_user_id=ctx.operator_user_id,
        assignee_user_id=ctx.assignee_user_id,
        config_hash=ctx.config_hash,
        expected_config_hash=str(args.expected_config_hash or "").strip(),
        overlay_steps=overlay_steps,
        config_merge_needed=config_merge_needed,
        production_allowed=production_allowed,
        environment=settings.app_env,
        configuration_id=configuration_id,
        activation_state=activation_state,
        active_version_id=active_version_id,
        policy_fingerprint=desired_fp,
        public_leads_enabled=settings.public_leads_enabled,
    )


def run_apply(db: Session, args: argparse.Namespace, settings: Settings) -> ActivationPlan:
    require_expected_config_hash(args)
    if not args.backup_dir:
        raise OpsActivationError("--backup-dir is required for --apply")

    ctx = resolve_context(
        db,
        args,
        require_assignee=True,
        lock_settings=True,
        create_settings_if_missing=True,
    )
    backup_dir = resolve_and_validate_backup_dir(args.backup_dir)
    backup_dir = write_backup(
        backup_dir,
        tenant_id=ctx.tenant.id,
        operator_user_id=ctx.operator_user_id,
        industry_config_json=ctx.industry_config_json,
        config_hash_before=ctx.config_hash,
    )

    try:
        desired_block = {
            "enabled": True,
            "default_assignee_user_id": str(ctx.assignee_user_id),
            "first_contact_sla_minutes": _clamp_sla(args.sla_minutes),
            "task_template_code": args.task_template_code.strip(),
            "create_activity": not args.no_create_activity,
        }
        merged = merge_lead_automation_config(
            ctx.industry_config_json,
            assignee_user_id=ctx.assignee_user_id,
            sla_minutes=desired_block["first_contact_sla_minutes"],
            task_template_code=desired_block["task_template_code"],
            create_activity=desired_block["create_activity"],
        )
        config_changed = not lead_automation_block_matches(ctx.industry_config_json, desired_block)
        config_hash_after = canonical_json_hash(merged)

        configuration_id = None
        published_new = False
        if not args.skip_overlay:
            configuration_id, published_new = execute_overlay(
                db,
                tenant_id=ctx.tenant.id,
                pipeline_id=ctx.pipeline_id,
                pipeline_code=ctx.pipeline_code,
                process_template_code=args.process_template_code,
                operator_user_id=ctx.operator_user_id,
                publish_reason=args.publish_reason.strip() or DEFAULT_PUBLISH_REASON,
                skip_overlay=False,
            )

        if config_changed:
            assert ctx.settings is not None
            ctx.settings.industry_config_json = merged
            db.flush()
            load_lead_automation_config(db, ctx.tenant.id)
            audit_script_event(
                db,
                tenant_id=ctx.tenant.id,
                operator_user_id=ctx.operator_user_id,
                mode="apply",
                summary="Lead automation tenant config merged",
                changes={
                    "entity_type": ENTITY_TENANT_SETTINGS,
                    "config_hash_before": ctx.config_hash,
                    "config_hash_after": config_hash_after,
                    "backup_path": str(backup_dir),
                    "assignee_user_id": redact_uuid(ctx.assignee_user_id),
                },
            )

        audit_script_event(
            db,
            tenant_id=ctx.tenant.id,
            operator_user_id=ctx.operator_user_id,
            mode="apply",
            summary="Flexity sales lead automation ops apply completed",
            changes={
                "configuration_id": str(configuration_id) if configuration_id else None,
                "published_new_version": published_new,
                "skip_overlay": args.skip_overlay,
                "backup_path": str(backup_dir),
                "public_leads_enabled_unchanged": True,
            },
        )

        finalize_backup_manifest(backup_dir, config_hash_after=config_hash_after)
        db.commit()
    except Exception:
        db.rollback()
        _remove_backup_tree(backup_dir)
        raise

    repo = ProcessOverlayRepository(db)
    activation_state = None
    active_version_id = None
    if configuration_id is not None:
        config = repo.get_configuration(ctx.tenant.id, configuration_id)
        if config is not None:
            activation_state = config.activation_state.value
            active_version_id = config.active_definition_version_id

    return ActivationPlan(
        mode="apply",
        tenant_id=ctx.tenant.id,
        tenant_slug=ctx.tenant.slug,
        pipeline_id=ctx.pipeline_id,
        pipeline_code=ctx.pipeline_code,
        operator_user_id=ctx.operator_user_id,
        assignee_user_id=ctx.assignee_user_id,
        config_hash=canonical_json_hash(merged),
        expected_config_hash=str(args.expected_config_hash or "").strip(),
        overlay_steps=[],
        config_merge_needed=config_changed,
        production_allowed=True,
        environment=settings.app_env,
        configuration_id=configuration_id,
        activation_state=activation_state,
        active_version_id=active_version_id,
        backup_path=str(backup_dir),
        public_leads_enabled=settings.public_leads_enabled,
    )


def run_rollback(db: Session, args: argparse.Namespace, settings: Settings) -> ActivationPlan:
    tenant = resolve_tenant(
        db,
        tenant_slug=args.tenant_slug,
        tenant_id=_parse_uuid(args.tenant_id, field="tenant-id") if args.tenant_id else None,
    )
    operator_id = _parse_uuid(args.operator_user_id, field="operator-user-id")
    assert_operator_access(db, tenant=tenant, operator_user_id=operator_id)

    manifest, industry_config = load_backup_manifest(
        Path(args.rollback_from),
        tenant_id=tenant.id,
        verify_config_integrity=True,
    )

    settings_row = load_tenant_settings(
        db,
        tenant.id,
        for_update=True,
        create_if_missing=True,
    )
    current_hash = canonical_json_hash(settings_row.industry_config_json or {})
    expected_hash = str(args.expected_config_hash or "").strip()
    assert_rollback_config_hash_gate(
        current_hash=current_hash,
        expected_hash=expected_hash,
        manifest=manifest,
    )

    warnings: list[str] = []
    if industry_config:
        settings_row.industry_config_json = industry_config
    else:
        warnings.append("Backup config missing; disabling lead_automation only")
        merged = merge_lead_automation_config(
            settings_row.industry_config_json,
            assignee_user_id=uuid.uuid4(),
            sla_minutes=DEFAULT_SLA_MINUTES,
            task_template_code=DEFAULT_TASK_TEMPLATE_CODE,
            create_activity=DEFAULT_CREATE_ACTIVITY,
            enabled=False,
        )
        consulting = merged.get("consulting") or {}
        if isinstance(consulting, dict):
            block = consulting.get("lead_automation") or {}
            if isinstance(block, dict):
                block["enabled"] = False
                consulting["lead_automation"] = block
                merged["consulting"] = consulting
        settings_row.industry_config_json = merged

    db.flush()

    repo = ProcessOverlayRepository(db)
    configuration_id = None
    workflows = WorkflowRepository(db)
    pipeline = workflows.get_pipeline_by_code(tenant.id, FLEXITY_SALES_PIPELINE)
    if pipeline is not None:
        config = repo.get_configuration_by_pipeline(tenant.id, pipeline.id)
        if config is not None:
            configuration_id = config.id
            ProcessOverlayConfigurationService(db).deactivate_configuration(
                tenant_id=tenant.id,
                configuration_id=config.id,
                actor_user_id=operator_id,
            )

    audit_script_event(
        db,
        tenant_id=tenant.id,
        operator_user_id=operator_id,
        mode="rollback",
        summary="Flexity sales lead automation ops rollback completed",
        changes={
            "backup_path": str(args.rollback_from),
            "configuration_id": str(configuration_id) if configuration_id else None,
            "public_leads_enabled_unchanged": True,
        },
    )
    db.commit()

    activation_state = None
    if configuration_id is not None:
        config = repo.get_configuration(tenant.id, configuration_id)
        if config is not None:
            activation_state = config.activation_state.value

    return ActivationPlan(
        mode="rollback",
        tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        pipeline_id=pipeline.id if pipeline else uuid.UUID(int=0),
        pipeline_code=FLEXITY_SALES_PIPELINE,
        operator_user_id=operator_id,
        assignee_user_id=None,
        config_hash=canonical_json_hash(settings_row.industry_config_json),
        expected_config_hash="",
        warnings=warnings,
        production_allowed=True,
        environment=settings.app_env,
        configuration_id=configuration_id,
        activation_state=activation_state,
        backup_path=str(args.rollback_from),
        public_leads_enabled=settings.public_leads_enabled,
    )


def plan_to_dict(plan: ActivationPlan) -> dict[str, Any]:
    return {
        "mode": plan.mode,
        "tenant_id": str(plan.tenant_id),
        "tenant_slug": plan.tenant_slug,
        "pipeline_id": str(plan.pipeline_id),
        "pipeline_code": plan.pipeline_code,
        "operator_user_id": redact_uuid(plan.operator_user_id),
        "assignee_user_id": redact_uuid(plan.assignee_user_id),
        "config_hash": plan.config_hash,
        "expected_config_hash": plan.expected_config_hash,
        "overlay_steps": [
            {"action": step.action, "skip_reason": step.skip_reason}
            for step in plan.overlay_steps
        ],
        "config_merge_needed": plan.config_merge_needed,
        "production_allowed": plan.production_allowed,
        "environment": plan.environment,
        "configuration_id": str(plan.configuration_id) if plan.configuration_id else None,
        "activation_state": plan.activation_state,
        "active_version_id": str(plan.active_version_id) if plan.active_version_id else None,
        "policy_fingerprint": plan.policy_fingerprint,
        "backup_path": plan.backup_path,
        "public_leads_enabled": plan.public_leads_enabled,
        "public_leads_reminder": (
            "PUBLIC_LEADS_ENABLED remains unchanged — enable separately per public leads runbook"
        ),
        "warnings": plan.warnings,
    }


def print_plan(plan: ActivationPlan, *, emit_json: str | None = None) -> None:
    payload = plan_to_dict(plan)
    if emit_json:
        Path(emit_json).write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")
    print(json.dumps(payload, indent=2, sort_keys=True))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="One-shot ops activation for flexity-sales lead automation."
    )
    parser.add_argument("--tenant-slug", help="Target tenant slug (flexity-sales)")
    parser.add_argument("--tenant-id", help="Target tenant UUID")
    parser.add_argument(
        "--pipeline-code",
        default=FLEXITY_SALES_PIPELINE,
        help=f"Pipeline code (must be {FLEXITY_SALES_PIPELINE})",
    )
    parser.add_argument("--assignee-user-id", help="default_assignee_user_id for lead_automation")
    parser.add_argument("--operator-user-id", required=True, help="Actor UUID for audit events")
    parser.add_argument(
        "--expected-config-hash",
        help="SHA-256 of canonical industry_config_json before apply/dry-run",
    )
    parser.add_argument("--confirm-phrase", required=True, help="Exact confirmation phrase")
    parser.add_argument(
        "--process-template-code",
        default=FLEXITY_SALES_TEMPLATE,
        help=f"Process template code (default {FLEXITY_SALES_TEMPLATE})",
    )
    parser.add_argument("--publish-reason", default=DEFAULT_PUBLISH_REASON)
    parser.add_argument("--sla-minutes", type=int, default=DEFAULT_SLA_MINUTES)
    parser.add_argument(
        "--task-template-code",
        default=DEFAULT_TASK_TEMPLATE_CODE,
    )
    parser.add_argument("--no-create-activity", action="store_true")
    parser.add_argument("--backup-dir", help="Directory for pre-apply backup artifacts")
    parser.add_argument("--emit-plan-json", help="Write machine-readable plan to PATH")
    parser.add_argument(
        "--rollback-from",
        help="Restore industry_config_json from backup manifest/path",
    )
    parser.add_argument("--apply", action="store_true", help="Execute writes (default is dry-run)")
    parser.add_argument(
        "--skip-overlay",
        action="store_true",
        help="Config-only emergency path (forbidden in production)",
    )
    parser.add_argument(
        "--i-understand-production",
        action="store_true",
        help="Required for apply/rollback when APP_ENV=production",
    )
    parser.add_argument(
        "--confirm-production-database",
        action="store_true",
        help="Second explicit ack for production apply/rollback against production database",
    )
    return parser


def run_with_session(db: Session, args: argparse.Namespace) -> ActivationPlan:
    settings = get_settings()
    assert_environment_guards(
        settings,
        apply_mode=args.apply,
        rollback_mode=bool(args.rollback_from),
        skip_overlay=args.skip_overlay,
        production_ack=args.i_understand_production,
        confirm_production_database=args.confirm_production_database,
    )
    validate_confirm_phrase(
        phrase=args.confirm_phrase,
        apply_mode=args.apply,
        rollback_mode=bool(args.rollback_from),
    )
    if args.apply and args.rollback_from:
        raise OpsActivationError("--apply and --rollback-from are mutually exclusive")

    if args.rollback_from:
        return run_rollback(db, args, settings)
    if args.apply:
        return run_apply(db, args, settings)
    return run_dry_run(db, args, settings)


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.public_leads_enabled if hasattr(args, "public_leads_enabled") else False:
        print("This script never toggles public leads settings.", file=sys.stderr)
        return EXIT_VALIDATION

    settings = get_settings()
    print(f"Target database: {mask_database_target(settings.database_url)}", file=sys.stderr)
    print(f"Environment: {settings.app_env}", file=sys.stderr)

    from app.core.database import SessionLocal

    db = SessionLocal()
    try:
        plan = run_with_session(db, args)
        print_plan(plan, emit_json=args.emit_plan_json)
        return EXIT_OK
    except OpsActivationError as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        if "confirm-phrase mismatch" in str(exc):
            return EXIT_VALIDATION
        return EXIT_VALIDATION
    except (NotFoundError, PermissionDeniedError, LeadAutomationConfigError) as exc:
        db.rollback()
        print(str(exc.message if hasattr(exc, "message") else exc), file=sys.stderr)
        return EXIT_ERROR
    except Exception:  # noqa: BLE001
        db.rollback()
        print(
            "Unexpected error during ops activation; see application logs for details.",
            file=sys.stderr,
        )
        return EXIT_ERROR
    finally:
        db.close()


__all__ = [
    "ActivationPlan",
    "BACKUP_DIR_MODE",
    "BACKUP_FILE_MODE",
    "BACKUP_SCHEMA_VERSION",
    "OpsActivationError",
    "PRODUCTION_DATABASE_NAME",
    "WORKTREE_ROOT",
    "assert_rollback_config_hash_gate",
    "build_parser",
    "canonical_json_hash",
    "finalize_backup_manifest",
    "is_exact_production_database_name",
    "load_backup_manifest",
    "main",
    "merge_lead_automation_config",
    "parse_database_name",
    "resolve_and_validate_backup_dir",
    "run_with_session",
    "validate_backup_manifest",
    "validate_confirm_phrase",
    "write_backup",
]
