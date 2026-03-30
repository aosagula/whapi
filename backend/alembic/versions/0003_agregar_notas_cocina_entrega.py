"""agregar kitchen_notes y delivery_notes a orders

Revision ID: 0003
Revises: a0a5b0bdb649
Create Date: 2026-03-30 12:00:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "a0a5b0bdb649"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("orders", sa.Column("kitchen_notes", sa.Text(), nullable=True))
    op.add_column("orders", sa.Column("delivery_notes", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("orders", "delivery_notes")
    op.drop_column("orders", "kitchen_notes")
