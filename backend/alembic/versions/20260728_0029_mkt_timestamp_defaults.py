"""M7.5 hotfix: add PostgreSQL now() defaults for 0027/0028 timestamps.

Revision ID: 0029_mkt_timestamp_defaults
Revises: 0028_mkt_content_plans
Create Date: 2026-07-28

Additive only. Aligns DB server defaults with TimestampMixin server_default=func.now()
for marketing tables created by 0027/0028 without changing nullability, data,
indexes, FKs, or lifecycle. SQLite no-op (tests use create_all / PG ephemeral).
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0029_mkt_timestamp_defaults"
down_revision: Union[str, None] = "0028_mkt_content_plans"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES: tuple[str, ...] = (
    "marketing_guides",
    "marketing_rubrics",
    "marketing_content_plans",
    "marketing_content_plan_items",
)
_COLUMNS: tuple[str, ...] = ("created_at", "updated_at")


def upgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _TABLES:
        for column in _COLUMNS:
            op.execute(
                sa.text(
                    f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT now()"
                )
            )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table in _TABLES:
        for column in _COLUMNS:
            op.execute(
                sa.text(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT")
            )
