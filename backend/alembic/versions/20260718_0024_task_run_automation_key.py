"""C2b1: Task process_run + automation_key for ProcessRun automation.

Revision ID: 0024_task_run_automation_key
Revises: 0023_mkt_storage_profiles
Create Date: 2026-07-18

Local/schema readiness only. Do not run against production without separate approval.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).

Adds nullable process_run_id + automation_key on tasks with:
- unique on process_runs (tenant_id, id) for composite FK target
- composite FK (tenant_id, process_run_id) → process_runs(tenant_id, id) ON DELETE RESTRICT
- CHECK pair: both NULL or both NOT NULL
- CHECK automation_key nonempty when set (btrim)
- partial unique (tenant_id, process_run_id, automation_key) WHERE both NOT NULL
- index ix_tasks_process_run_id
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0024_task_run_automation_key"
down_revision: Union[str, None] = "0023_mkt_storage_profiles"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_unique_constraint(
        "uq_process_runs_tenant_id_id",
        "process_runs",
        ["tenant_id", "id"],
    )
    op.add_column("tasks", sa.Column("process_run_id", sa.Uuid(), nullable=True))
    op.add_column("tasks", sa.Column("automation_key", sa.String(length=64), nullable=True))
    op.create_foreign_key(
        "fk_tasks_tenant_process_run",
        "tasks",
        "process_runs",
        ["tenant_id", "process_run_id"],
        ["tenant_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_index(op.f("ix_tasks_process_run_id"), "tasks", ["process_run_id"], unique=False)
    op.create_check_constraint(
        "ck_tasks_process_run_automation_key_pair",
        "tasks",
        "("
        " (process_run_id IS NULL AND automation_key IS NULL)"
        " OR "
        " (process_run_id IS NOT NULL AND automation_key IS NOT NULL)"
        ")",
    )
    op.create_check_constraint(
        "ck_tasks_automation_key_nonempty",
        "tasks",
        "automation_key IS NULL OR length(btrim(automation_key)) > 0",
    )
    op.create_index(
        "uq_tasks_tenant_process_run_automation_key",
        "tasks",
        ["tenant_id", "process_run_id", "automation_key"],
        unique=True,
        postgresql_where=sa.text(
            "process_run_id IS NOT NULL AND automation_key IS NOT NULL"
        ),
        sqlite_where=sa.text(
            "process_run_id IS NOT NULL AND automation_key IS NOT NULL"
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_tasks_tenant_process_run_automation_key",
        table_name="tasks",
    )
    op.drop_constraint(
        "ck_tasks_automation_key_nonempty",
        "tasks",
        type_="check",
    )
    op.drop_constraint(
        "ck_tasks_process_run_automation_key_pair",
        "tasks",
        type_="check",
    )
    op.drop_index(op.f("ix_tasks_process_run_id"), table_name="tasks")
    op.drop_constraint("fk_tasks_tenant_process_run", "tasks", type_="foreignkey")
    op.drop_column("tasks", "automation_key")
    op.drop_column("tasks", "process_run_id")
    op.drop_constraint(
        "uq_process_runs_tenant_id_id",
        "process_runs",
        type_="unique",
    )
