"""guardar payload y metadata whatsapp

Revision ID: f3b2c1d4e5f6
Revises: 676b100f5333
Create Date: 2026-04-29 18:40:00.000000

"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f3b2c1d4e5f6"
down_revision: Union[str, None] = "676b100f5333"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("customers", sa.Column("whatsapp_wa_id", sa.String(length=120), nullable=True))
    op.add_column("customers", sa.Column("whatsapp_display_name", sa.String(length=150), nullable=True))
    op.add_column("customers", sa.Column("whatsapp_profile_name", sa.String(length=150), nullable=True))
    op.add_column("customers", sa.Column("whatsapp_business_name", sa.String(length=150), nullable=True))
    op.add_column("customers", sa.Column("whatsapp_metadata", sa.JSON(), nullable=True))

    op.add_column("messages", sa.Column("external_message_id", sa.String(length=120), nullable=True))
    op.add_column("messages", sa.Column("sender_phone", sa.String(length=30), nullable=True))
    op.add_column("messages", sa.Column("sender_name", sa.String(length=150), nullable=True))
    op.add_column("messages", sa.Column("raw_payload", sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column("messages", "raw_payload")
    op.drop_column("messages", "sender_name")
    op.drop_column("messages", "sender_phone")
    op.drop_column("messages", "external_message_id")

    op.drop_column("customers", "whatsapp_metadata")
    op.drop_column("customers", "whatsapp_business_name")
    op.drop_column("customers", "whatsapp_profile_name")
    op.drop_column("customers", "whatsapp_display_name")
    op.drop_column("customers", "whatsapp_wa_id")
