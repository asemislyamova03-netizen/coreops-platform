"""C2b1: optional ProcessRun first-contact task automation via tenant config.

Config path: TenantSettings.industry_config_json["consulting"]["lead_automation"]

Universal hook — no hardcoded tenant slug or assignee UUID.
Does not commit; caller owns the outer transaction.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.enums import ActivityType, TaskStatus
from app.core.exceptions import ConflictError, CoreOpsError
from app.modules.auth.models import User
from app.modules.tenants.models import TenantSettings, UserTenantMembership
from app.modules.workflows.models import Activity, Task

DEFAULT_SLA_MINUTES = 240
DEFAULT_TASK_TEMPLATE_CODE = "consulting_first_contact"
DEFAULT_CREATE_ACTIVITY = True
TASK_TITLE = "Связаться с лидом"


class LeadAutomationError(CoreOpsError):
    """Base error for lead automation fail-closed paths."""


class LeadAutomationConfigError(LeadAutomationError):
    """enabled=true but config/assignee is invalid."""


class LeadAutomationConflictError(ConflictError, LeadAutomationError):
    """Automation conflict (e.g. unexpected race outside nested txn recovery)."""


@dataclass(frozen=True)
class LeadAutomationConfig:
    enabled: bool
    default_assignee_user_id: uuid.UUID
    first_contact_sla_minutes: int
    task_template_code: str
    create_activity: bool


def _parse_uuid(value: object, *, field: str) -> uuid.UUID:
    if isinstance(value, uuid.UUID):
        return value
    if isinstance(value, str):
        try:
            return uuid.UUID(value.strip())
        except ValueError as exc:
            raise LeadAutomationConfigError(
                f"lead_automation.{field} must be a valid UUID"
            ) from exc
    raise LeadAutomationConfigError(f"lead_automation.{field} must be a valid UUID")


def load_lead_automation_config(
    db: Session, tenant_id: uuid.UUID
) -> LeadAutomationConfig | None:
    """Return validated config when enabled; None for missing/disabled (no-op)."""
    settings = db.scalar(
        select(TenantSettings).where(TenantSettings.tenant_id == tenant_id)
    )
    if settings is None:
        return None
    industry = settings.industry_config_json or {}
    consulting = industry.get("consulting")
    if not isinstance(consulting, dict):
        return None
    raw = consulting.get("lead_automation")
    if not isinstance(raw, dict):
        return None
    if raw.get("enabled") is not True:
        return None

    assignee_raw = raw.get("default_assignee_user_id")
    if assignee_raw is None or assignee_raw == "":
        raise LeadAutomationConfigError(
            "lead_automation.enabled requires default_assignee_user_id"
        )
    assignee_id = _parse_uuid(assignee_raw, field="default_assignee_user_id")

    sla_raw = raw.get("first_contact_sla_minutes", DEFAULT_SLA_MINUTES)
    try:
        sla_minutes = int(sla_raw)
    except (TypeError, ValueError) as exc:
        raise LeadAutomationConfigError(
            "lead_automation.first_contact_sla_minutes must be an integer"
        ) from exc
    if sla_minutes <= 0:
        raise LeadAutomationConfigError(
            "lead_automation.first_contact_sla_minutes must be positive"
        )

    template = raw.get("task_template_code", DEFAULT_TASK_TEMPLATE_CODE)
    if not isinstance(template, str) or not template.strip():
        raise LeadAutomationConfigError(
            "lead_automation.task_template_code must be a non-empty string"
        )
    template_code = template.strip()
    if len(template_code) > 64:
        raise LeadAutomationConfigError(
            "lead_automation.task_template_code must be at most 64 characters"
        )

    create_activity = raw.get("create_activity", DEFAULT_CREATE_ACTIVITY)
    if not isinstance(create_activity, bool):
        raise LeadAutomationConfigError(
            "lead_automation.create_activity must be a boolean"
        )

    return LeadAutomationConfig(
        enabled=True,
        default_assignee_user_id=assignee_id,
        first_contact_sla_minutes=sla_minutes,
        task_template_code=template_code,
        create_activity=create_activity,
    )


def _assert_assignee_active_same_tenant(
    db: Session, *, tenant_id: uuid.UUID, user_id: uuid.UUID
) -> User:
    membership = db.scalar(
        select(UserTenantMembership).where(
            UserTenantMembership.tenant_id == tenant_id,
            UserTenantMembership.user_id == user_id,
        )
    )
    if membership is None or not membership.is_active:
        raise LeadAutomationConfigError(
            "lead_automation.default_assignee_user_id must be an active member of the tenant"
        )

    user = db.get(User, user_id)
    if user is None or not user.is_active:
        raise LeadAutomationConfigError(
            "lead_automation.default_assignee_user_id must be an active user"
        )
    return user


def _get_existing_automation_task(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    process_run_id: uuid.UUID,
    automation_key: str,
) -> Task | None:
    return db.scalar(
        select(Task).where(
            Task.tenant_id == tenant_id,
            Task.process_run_id == process_run_id,
            Task.automation_key == automation_key,
        )
    )


def maybe_create_process_run_first_contact_task(
    db: Session,
    *,
    tenant_id: uuid.UUID,
    process_run_id: uuid.UUID,
    work_item_id: uuid.UUID,
    actor_user_id: uuid.UUID,
) -> Task | None:
    """Create first-contact Task (+ optional Activity) after ProcessRun start.

    No-op when config missing or disabled. Fail-closed when enabled but invalid.
    Idempotent under concurrency via partial unique + begin_nested.
    Does not call db.commit().
    """
    config = load_lead_automation_config(db, tenant_id)
    if config is None:
        return None

    _assert_assignee_active_same_tenant(
        db, tenant_id=tenant_id, user_id=config.default_assignee_user_id
    )

    existing = _get_existing_automation_task(
        db,
        tenant_id=tenant_id,
        process_run_id=process_run_id,
        automation_key=config.task_template_code,
    )
    if existing is not None:
        # Same ProcessRun already has this automation task (pending or completed).
        return existing

    due_at = datetime.now(UTC) + timedelta(minutes=config.first_contact_sla_minutes)
    created_new = False
    task: Task | None = None

    try:
        with db.begin_nested():
            task = Task(
                tenant_id=tenant_id,
                work_item_id=work_item_id,
                process_run_id=process_run_id,
                automation_key=config.task_template_code,
                title=TASK_TITLE,
                description=None,
                status=TaskStatus.PENDING,
                due_at=due_at,
                assigned_to_user_id=config.default_assignee_user_id,
                created_by_user_id=actor_user_id,
                updated_by_user_id=actor_user_id,
            )
            db.add(task)
            db.flush()
            created_new = True
    except IntegrityError:
        task = _get_existing_automation_task(
            db,
            tenant_id=tenant_id,
            process_run_id=process_run_id,
            automation_key=config.task_template_code,
        )
        if task is None:
            raise LeadAutomationConflictError(
                "Failed to create or recover process-run automation task"
            ) from None
        return task

    if created_new and config.create_activity and task is not None:
        assignee_label = str(config.default_assignee_user_id)
        activity = Activity(
            tenant_id=tenant_id,
            work_item_id=work_item_id,
            activity_type=ActivityType.NOTE,
            title="Автозадача первого контакта создана",
            description=(
                f"Создана задача «{TASK_TITLE}» "
                f"(automation_key={config.task_template_code}, "
                f"assignee={assignee_label}, due_at={due_at.isoformat()})."
            ),
            occurred_at=datetime.now(UTC),
            created_by_user_id=actor_user_id,
            updated_by_user_id=actor_user_id,
        )
        db.add(activity)
        db.flush()

    return task


__all__ = [
    "DEFAULT_CREATE_ACTIVITY",
    "DEFAULT_SLA_MINUTES",
    "DEFAULT_TASK_TEMPLATE_CODE",
    "TASK_TITLE",
    "LeadAutomationConfig",
    "LeadAutomationConfigError",
    "LeadAutomationConflictError",
    "LeadAutomationError",
    "load_lead_automation_config",
    "maybe_create_process_run_first_contact_task",
]
