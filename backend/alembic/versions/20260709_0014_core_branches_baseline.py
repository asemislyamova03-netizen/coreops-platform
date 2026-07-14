"""E3a: branches baseline + tenants.default_branch_id

Revision ID: 0014_core_branches_baseline
Revises: 0013_c1c_payment_direction
Create Date: 2026-07-09

Local/schema readiness only. Do not run against production without separate approval.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0014_core_branches_baseline"
down_revision: Union[str, None] = "0013_c1c_payment_direction"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _backfill_default_branches() -> None:
    bind = op.get_bind()
    tenant_rows = bind.execute(
        sa.text("SELECT id FROM tenants WHERE default_branch_id IS NULL")
    ).fetchall()

    now = datetime.now(UTC)
    for (tenant_id,) in tenant_rows:
        existing = bind.execute(
            sa.text(
                """
                SELECT id
                FROM branches
                WHERE tenant_id = :tenant_id AND is_default = true
                ORDER BY created_at ASC, id ASC
                LIMIT 1
                """
            ),
            {"tenant_id": tenant_id},
        ).fetchone()

        if existing:
            branch_id = existing[0]
        else:
            branch_id = uuid.uuid4()
            bind.execute(
                sa.text(
                    """
                    INSERT INTO branches (
                        id, tenant_id, code, name, is_active, is_default, created_at, updated_at
                    )
                    VALUES (
                        :id, :tenant_id, 'main', 'Main branch', :is_active, :is_default, :created_at, :updated_at
                    )
                    """
                ),
                {
                    "id": branch_id,
                    "tenant_id": tenant_id,
                    "is_active": True,
                    "is_default": True,
                    "created_at": now,
                    "updated_at": now,
                },
            )

        bind.execute(
            sa.text(
                "UPDATE tenants SET default_branch_id = :branch_id WHERE id = :tenant_id"
            ),
            {"branch_id": branch_id, "tenant_id": tenant_id},
        )


def upgrade() -> None:
    op.create_table(
        "branches",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_default", sa.Boolean(), nullable=False, server_default=sa.text("false")),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "code", name="uq_branch_tenant_code"),
    )
    op.create_index(op.f("ix_branches_tenant_id"), "branches", ["tenant_id"])

    op.add_column("tenants", sa.Column("default_branch_id", sa.Uuid(), nullable=True))
    op.create_index(
        op.f("ix_tenants_default_branch_id"),
        "tenants",
        ["default_branch_id"],
    )
    op.create_foreign_key(
        "fk_tenants_default_branch_id_branches",
        "tenants",
        "branches",
        ["default_branch_id"],
        ["id"],
        ondelete="SET NULL",
    )

    _backfill_default_branches()


def downgrade() -> None:
    op.execute(sa.text("UPDATE tenants SET default_branch_id = NULL"))
    op.drop_constraint(
        "fk_tenants_default_branch_id_branches",
        "tenants",
        type_="foreignkey",
    )
    op.drop_index(op.f("ix_tenants_default_branch_id"), table_name="tenants")
    op.drop_column("tenants", "default_branch_id")
    op.drop_index(op.f("ix_branches_tenant_id"), table_name="branches")
    op.drop_table("branches")
