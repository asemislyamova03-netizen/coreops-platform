"""Add client onboarding idempotency keys table.

Revision ID: 0030_client_onboarding_idempotency
Revises: 0029_mkt_timestamp_defaults
Create Date: 2026-08-01
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0030_client_onboarding_idempotency"
down_revision: Union[str, None] = "0029_mkt_timestamp_defaults"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "client_onboarding_idempotency_keys",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("request_hash", sa.String(length=64), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("tenant_id", sa.Uuid(), nullable=True),
        sa.Column("tenant_slug", sa.String(length=100), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("key"),
    )
    op.create_index(
        op.f("ix_client_onboarding_idempotency_keys_key"),
        "client_onboarding_idempotency_keys",
        ["key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_onboarding_idempotency_keys_user_id"),
        "client_onboarding_idempotency_keys",
        ["user_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_client_onboarding_idempotency_keys_tenant_id"),
        "client_onboarding_idempotency_keys",
        ["tenant_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_client_onboarding_idempotency_keys_tenant_id"),
        table_name="client_onboarding_idempotency_keys",
    )
    op.drop_index(
        op.f("ix_client_onboarding_idempotency_keys_user_id"),
        table_name="client_onboarding_idempotency_keys",
    )
    op.drop_index(
        op.f("ix_client_onboarding_idempotency_keys_key"),
        table_name="client_onboarding_idempotency_keys",
    )
    op.drop_table("client_onboarding_idempotency_keys")
