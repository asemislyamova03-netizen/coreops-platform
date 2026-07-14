"""C1c: first-class payment direction for Consulting write-import readiness

Revision ID: 0013_c1c_payment_direction
Revises: 0012_booking_e1
Create Date: 2026-07-08

Local/schema readiness only. Do not run against production without separate approval.
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0013_c1c_payment_direction"
down_revision: Union[str, None] = "0012_booking_e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "payments",
        sa.Column(
            "direction",
            sa.Enum(
                "incoming",
                "outgoing",
                "needs_review",
                name="payment_direction",
                native_enum=False,
            ),
            nullable=False,
            server_default="incoming",
        ),
    )
    op.create_index(op.f("ix_payments_direction"), "payments", ["direction"])


def downgrade() -> None:
    op.drop_index(op.f("ix_payments_direction"), table_name="payments")
    op.drop_column("payments", "direction")
