"""Agregar configuración de asistente a businesses.

Revision ID: c1d2e3f4a5b6
Revises: f3b2c1d4e5f6
Create Date: 2026-04-29 22:40:00.000000
"""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = "c1d2e3f4a5b6"
down_revision = "f3b2c1d4e5f6"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("businesses", sa.Column("assistant_name", sa.String(length=150), nullable=True))
    op.add_column("businesses", sa.Column("assistant_system_prompt_master", sa.Text(), nullable=True))
    op.add_column("businesses", sa.Column("assistant_system_prompt_default", sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column("businesses", "assistant_system_prompt_default")
    op.drop_column("businesses", "assistant_system_prompt_master")
    op.drop_column("businesses", "assistant_name")
