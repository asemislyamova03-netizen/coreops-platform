"""E1b: Process Overlay ProcessRun runtime binding.

Revision ID: 0020_process_overlay_e1b
Revises: 0019_process_overlay_e1a
Create Date: 2026-07-17

Local/schema readiness only. Creates process_runs table.
Does not hook CRM create_work_item / move_stage.
Does not enforce transitions. Does not auto-start runs.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).

Config/version ownership (E1a active-version style):
- composite FK fk_process_run_config_version
  (tenant_process_configuration_id, process_definition_version_id)
  -> process_definition_versions (tenant_process_configuration_id, id)
  using E1a unique uq_process_def_version_config_id
  ON DELETE RESTRICT
- No separate single-column FKs to tenant_process_configurations.id or
  process_definition_versions.id; the composite is the ownership guard.
- Keep single-column FKs: tenant_id -> tenants, work_item_id -> work_items.

CHECK:
- ck_process_run_state_valid:
  run_state IN ('active', 'completed', 'cancelled')  (lowercase only)

Partial unique index:
- uq_process_run_one_active_per_work_item ON (work_item_id)
  WHERE run_state = 'active'
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0020_process_overlay_e1b"
down_revision: Union[str, None] = "0019_process_overlay_e1a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "process_runs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("tenant_process_configuration_id", sa.Uuid(), nullable=False),
        sa.Column("process_definition_version_id", sa.Uuid(), nullable=False),
        sa.Column("work_item_id", sa.Uuid(), nullable=False),
        sa.Column(
            "run_state",
            sa.Enum(
                "active",
                "completed",
                "cancelled",
                name="process_run_state",
                native_enum=False,
            ),
            nullable=False,
            server_default="active",
        ),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_by_user_id", sa.Uuid(), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_by_user_id", sa.Uuid(), nullable=True),
        sa.Column("completion_reason", sa.Text(), nullable=True),
        sa.Column("current_stage_code", sa.String(length=64), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["tenant_id"], ["tenants.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["work_item_id"], ["work_items.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(
            ["tenant_process_configuration_id", "process_definition_version_id"],
            [
                "process_definition_versions.tenant_process_configuration_id",
                "process_definition_versions.id",
            ],
            name="fk_process_run_config_version",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "run_state IN ('active', 'completed', 'cancelled')",
            name="ck_process_run_state_valid",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_process_runs_tenant_id"), "process_runs", ["tenant_id"])
    op.create_index(
        op.f("ix_process_runs_tenant_process_configuration_id"),
        "process_runs",
        ["tenant_process_configuration_id"],
    )
    op.create_index(
        op.f("ix_process_runs_process_definition_version_id"),
        "process_runs",
        ["process_definition_version_id"],
    )
    op.create_index(op.f("ix_process_runs_work_item_id"), "process_runs", ["work_item_id"])
    op.create_index(op.f("ix_process_runs_run_state"), "process_runs", ["run_state"])
    op.create_index(
        "uq_process_run_one_active_per_work_item",
        "process_runs",
        ["work_item_id"],
        unique=True,
        postgresql_where=sa.text("run_state = 'active'"),
        sqlite_where=sa.text("run_state = 'active'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_process_run_one_active_per_work_item",
        table_name="process_runs",
    )
    op.drop_index(op.f("ix_process_runs_run_state"), table_name="process_runs")
    op.drop_index(op.f("ix_process_runs_work_item_id"), table_name="process_runs")
    op.drop_index(
        op.f("ix_process_runs_process_definition_version_id"),
        table_name="process_runs",
    )
    op.drop_index(
        op.f("ix_process_runs_tenant_process_configuration_id"),
        table_name="process_runs",
    )
    op.drop_index(op.f("ix_process_runs_tenant_id"), table_name="process_runs")
    op.drop_table("process_runs")

    sa.Enum(name="process_run_state").drop(op.get_bind(), checkfirst=True)
