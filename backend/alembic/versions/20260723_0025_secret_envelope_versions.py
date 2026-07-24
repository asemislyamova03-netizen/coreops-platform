"""M8-B2: envelope-encrypted secret versions table (platform secrets core).

Revision ID: 0025_secret_envelope_versions
Revises: 0024_task_run_automation_key
Create Date: 2026-07-23

Local/schema readiness only. Do not run against production without separate approval.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).

Creates secret_envelope_versions with Design Lock columns/constraints/indexes.
No FK to marketing tables (portable vault adapter).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0025_secret_envelope_versions"
down_revision: Union[str, None] = "0024_task_run_automation_key"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "secret_envelope_versions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("connection_id", sa.Uuid(), nullable=False),
        sa.Column("purpose", sa.String(length=64), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("state", sa.String(length=32), nullable=False),
        sa.Column("algorithm", sa.String(length=32), nullable=False),
        sa.Column("crypto_schema_version", sa.Integer(), nullable=False),
        sa.Column("kek_version", sa.Integer(), nullable=False),
        sa.Column("ciphertext", sa.LargeBinary(), nullable=False),
        sa.Column("ciphertext_nonce", sa.LargeBinary(), nullable=False),
        sa.Column("wrapped_dek", sa.LargeBinary(), nullable=False),
        sa.Column("wrapped_dek_nonce", sa.LargeBinary(), nullable=False),
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
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "tenant_id",
            "connection_id",
            "purpose",
            "version",
            name="uq_secret_envelope_versions_owner_version",
        ),
        sa.CheckConstraint(
            "version >= 1",
            name="ck_secret_envelope_versions_version_positive",
        ),
        sa.CheckConstraint(
            "state IN ('pending', 'active', 'deactivated')",
            name="ck_secret_envelope_versions_state",
        ),
        sa.CheckConstraint(
            "algorithm = 'aes-256-gcm'",
            name="ck_secret_envelope_versions_algorithm",
        ),
        sa.CheckConstraint(
            "crypto_schema_version >= 1",
            name="ck_secret_envelope_versions_schema",
        ),
        sa.CheckConstraint(
            "kek_version >= 1",
            name="ck_secret_envelope_versions_kek_version",
        ),
        sa.CheckConstraint(
            "octet_length(ciphertext_nonce) = 12",
            name="ck_secret_envelope_versions_ct_nonce_len",
        ),
        sa.CheckConstraint(
            "octet_length(wrapped_dek_nonce) = 12",
            name="ck_secret_envelope_versions_wrap_nonce_len",
        ),
    )
    op.create_index(
        "ix_secret_envelope_versions_owner_state",
        "secret_envelope_versions",
        ["tenant_id", "connection_id", "purpose", "state"],
        unique=False,
    )
    op.create_index(
        "ix_secret_envelope_versions_owner_version",
        "secret_envelope_versions",
        ["tenant_id", "connection_id", "purpose", "version"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        "ix_secret_envelope_versions_owner_version",
        table_name="secret_envelope_versions",
    )
    op.drop_index(
        "ix_secret_envelope_versions_owner_state",
        table_name="secret_envelope_versions",
    )
    op.drop_table("secret_envelope_versions")
