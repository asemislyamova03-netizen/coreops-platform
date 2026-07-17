"""M8-C1a: secret binding fields on marketing publishing connections.

Revision ID: 0022_mkt_secret_binding
Revises: 0021_mkt_publishing_conn
Create Date: 2026-07-16

Adds secret_version / secret_bound_at and consistency CHECK.
Local/schema readiness only. Do not run against production without separate approval.
Revision ID kept <= 32 chars for alembic_version.version_num (VARCHAR(32)).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0022_mkt_secret_binding"
down_revision: Union[str, None] = "0021_mkt_publishing_conn"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "marketing_publishing_connections",
        sa.Column("secret_version", sa.Integer(), nullable=True),
    )
    op.add_column(
        "marketing_publishing_connections",
        sa.Column("secret_bound_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_check_constraint(
        "ck_marketing_publishing_conn_secret_binding_consistent",
        "marketing_publishing_connections",
        "("
        " (secret_ref IS NULL AND secret_version IS NULL AND secret_bound_at IS NULL)"
        " OR "
        " (secret_ref IS NOT NULL AND trim(secret_ref) <> ''"
        "  AND secret_version IS NOT NULL AND secret_version > 0"
        "  AND secret_bound_at IS NOT NULL)"
        ")",
    )


def downgrade() -> None:
    op.drop_constraint(
        "ck_marketing_publishing_conn_secret_binding_consistent",
        "marketing_publishing_connections",
        type_="check",
    )
    op.drop_column("marketing_publishing_connections", "secret_bound_at")
    op.drop_column("marketing_publishing_connections", "secret_version")
