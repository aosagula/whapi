"""Completar schema fase1 gaps

Revision ID: 9bb925a24f9d
Revises: 8147ef4be830
Create Date: 2026-03-28

Agrega los campos faltantes detectados en la revisión de Fase 1:
- orders: delivery_type, delivery_address
- order_items: size, second_product_id
- incidents: reported_by_id, resolved_by_id, resolved_at, resolution_notes
- customers: has_whatsapp
- combos: code, short_name, is_customizable + UniqueConstraint(pizzeria_id, code)
- catalog_items: UniqueConstraint(pizzeria_id, product_id, size)
- pizzeria_configs: delivery_surcharge, closing_message, bank_details
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "9bb925a24f9d"
down_revision = "8147ef4be830"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # --- orders ---
    op.execute("CREATE TYPE delivery_type AS ENUM ('delivery', 'pickup')")
    op.add_column("orders", sa.Column("delivery_type", sa.Enum("delivery", "pickup", name="delivery_type"), nullable=True))
    op.add_column("orders", sa.Column("delivery_address", sa.String(255), nullable=True))

    # --- order_items ---
    op.add_column("order_items", sa.Column("size", sa.String(10), nullable=True))
    op.add_column("order_items", sa.Column("second_product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=True))

    # --- incidents ---
    op.add_column("incidents", sa.Column("reported_by_id", sa.Integer(), sa.ForeignKey("panel_users.id"), nullable=True))
    op.add_column("incidents", sa.Column("resolved_by_id", sa.Integer(), sa.ForeignKey("panel_users.id"), nullable=True))
    op.add_column("incidents", sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("incidents", sa.Column("resolution_notes", sa.Text(), nullable=True))

    # --- customers ---
    op.add_column("customers", sa.Column("has_whatsapp", sa.Boolean(), nullable=False, server_default=sa.true()))

    # --- combos ---
    op.add_column("combos", sa.Column("code", sa.String(30), nullable=False, server_default=""))
    op.add_column("combos", sa.Column("short_name", sa.String(30), nullable=False, server_default=""))
    op.add_column("combos", sa.Column("is_customizable", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.create_unique_constraint("uq_combo_pizzeria_code", "combos", ["pizzeria_id", "code"])

    # --- catalog_items ---
    op.create_unique_constraint("uq_catalog_item_product_size", "catalog_items", ["pizzeria_id", "product_id", "size"])

    # --- pizzeria_configs ---
    op.add_column("pizzeria_configs", sa.Column("delivery_surcharge", sa.Numeric(10, 2), nullable=True))
    op.add_column("pizzeria_configs", sa.Column("closing_message", sa.Text(), nullable=True))
    op.add_column("pizzeria_configs", sa.Column("bank_details", sa.Text(), nullable=True))

    # Eliminar server_defaults temporales usados para NOT NULL migration
    op.alter_column("combos", "code", server_default=None)
    op.alter_column("combos", "short_name", server_default=None)


def downgrade() -> None:
    op.drop_column("pizzeria_configs", "bank_details")
    op.drop_column("pizzeria_configs", "closing_message")
    op.drop_column("pizzeria_configs", "delivery_surcharge")

    op.drop_constraint("uq_catalog_item_product_size", "catalog_items", type_="unique")

    op.drop_constraint("uq_combo_pizzeria_code", "combos", type_="unique")
    op.drop_column("combos", "is_customizable")
    op.drop_column("combos", "short_name")
    op.drop_column("combos", "code")

    op.drop_column("customers", "has_whatsapp")

    op.drop_column("incidents", "resolution_notes")
    op.drop_column("incidents", "resolved_at")
    op.drop_column("incidents", "resolved_by_id")
    op.drop_column("incidents", "reported_by_id")

    op.drop_column("order_items", "second_product_id")
    op.drop_column("order_items", "size")

    op.drop_column("orders", "delivery_address")
    op.drop_column("orders", "delivery_type")
    op.execute("DROP TYPE IF EXISTS delivery_type")
