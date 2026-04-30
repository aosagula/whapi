"""agregar agent_state a conversation_sessions

Revision ID: e7a1b2c3d4f5
Revises: c1d2e3f4a5b6
Create Date: 2026-04-29 22:40:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "e7a1b2c3d4f5"
down_revision = "c1d2e3f4a5b6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("conversation_sessions", sa.Column("agent_state", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("conversation_sessions", "agent_state")
