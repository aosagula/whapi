"""Fase 5: agregar order_number, delivery_person_id, internal_notes y tabla order_status_history

Revision ID: 0002
Revises: 0dea99306ec4
Create Date: 2026-03-29

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0dea99306ec4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Nuevas columnas en orders ──────────────────────────────────────────
    op.add_column("orders", sa.Column("order_number", sa.Integer(), nullable=True))
    op.add_column(
        "orders",
        sa.Column(
            "delivery_person_id",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("orders", sa.Column("internal_notes", sa.Text(), nullable=True))

    # Secuencia de número de pedido por comercio — se rellena con trigger o a nivel app
    # Por ahora asignamos valores temporales a filas existentes
    op.execute("UPDATE orders SET order_number = 1 WHERE order_number IS NULL")

    # Hacer la columna NOT NULL con default de secuencia (la app la gestiona)
    op.alter_column("orders", "order_number", nullable=False)

    op.create_index("ix_orders_delivery_person_id", "orders", ["delivery_person_id"])

    # ── Tabla order_status_history ─────────────────────────────────────────
    # Usamos sa.Text y un server_default cast porque el tipo order_status
    # ya fue creado en la migración 0001 y no queremos redefinirlo.
    op.create_table(
        "order_status_history",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "order_id",
            sa.UUID(),
            sa.ForeignKey("orders.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "previous_status",
            sa.String(50),
            nullable=True,
        ),
        sa.Column(
            "new_status",
            sa.String(50),
            nullable=False,
        ),
        sa.Column(
            "changed_by",
            sa.UUID(),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "changed_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("note", sa.Text(), nullable=True),
    )
    # Castear las columnas de texto al tipo ENUM existente
    op.execute(
        "ALTER TABLE order_status_history "
        "ALTER COLUMN previous_status TYPE order_status USING previous_status::order_status, "
        "ALTER COLUMN new_status TYPE order_status USING new_status::order_status"
    )
    op.create_index("ix_order_status_history_order_id", "order_status_history", ["order_id"])


def downgrade() -> None:
    op.drop_index("ix_order_status_history_order_id", table_name="order_status_history")
    op.drop_table("order_status_history")
    op.drop_index("ix_orders_delivery_person_id", table_name="orders")
    op.drop_column("orders", "internal_notes")
    op.drop_column("orders", "delivery_person_id")
    op.drop_column("orders", "order_number")
