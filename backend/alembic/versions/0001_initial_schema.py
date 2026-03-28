"""Schema inicial completo del proyecto Whapi

Revision ID: 0001
Revises:
Create Date: 2026-03-28

"""
from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# Definición centralizada de ENUMs (para reutilizar en create_table)
_user_role = sa.Enum("owner", "admin", "cashier", "cook", "delivery", name="user_role")
_whatsapp_status = sa.Enum("connected", "disconnected", "scanning", name="whatsapp_status")
_product_category = sa.Enum("pizza", "empanada", "drink", name="product_category")
_session_status = sa.Enum(
    "active_bot", "waiting_operator", "assigned_human", "closed", name="session_status"
)
_message_direction = sa.Enum("inbound", "outbound", name="message_direction")
_order_status = sa.Enum(
    "in_progress", "pending_payment", "pending_preparation",
    "in_preparation", "to_dispatch", "in_delivery",
    "delivered", "cancelled", "with_incident", "discarded",
    name="order_status",
)
_payment_status = sa.Enum(
    "paid", "cash_on_delivery", "pending_payment", "credit", "refunded", "no_charge",
    name="payment_status",
)
_order_origin = sa.Enum("whatsapp", "phone", "operator", name="order_origin")
_delivery_type = sa.Enum("delivery", "pickup", name="delivery_type")
_payment_method = sa.Enum("mercadopago", "cash", "transfer", name="payment_method")
_mp_payment_status = sa.Enum(
    "pending", "approved", "rejected", "refunded", name="mp_payment_status"
)
_incident_type = sa.Enum(
    "wrong_address", "wrong_order", "missing_item",
    "bad_condition", "customer_not_found", "other",
    name="incident_type",
)
_incident_status = sa.Enum(
    "open", "in_review", "resolved_redispatch", "resolved_cancel", name="incident_status"
)


def upgrade() -> None:
    # ── users ──────────────────────────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("email", sa.String(255), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("phone", sa.String(30), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    # ── businesses ─────────────────────────────────────────────────────────
    op.create_table(
        "businesses",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("owner_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("name", sa.String(150), nullable=False),
        sa.Column("address", sa.String(255), nullable=True),
        sa.Column("logo_url", sa.String(500), nullable=True),
        sa.Column("half_half_surcharge", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )

    # ── user_business ──────────────────────────────────────────────────────
    op.create_table(
        "user_business",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("user_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("role", _user_role, nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("user_id", "business_id", name="uq_user_business"),
    )

    # ── whatsapp_numbers ───────────────────────────────────────────────────
    op.create_table(
        "whatsapp_numbers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone_number", sa.String(30), nullable=False),
        sa.Column("session_name", sa.String(100), nullable=True),
        sa.Column("status", _whatsapp_status, nullable=False, server_default="disconnected"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("phone_number", name="uq_whatsapp_phone_number"),
    )
    op.create_index("ix_whatsapp_numbers_business_id", "whatsapp_numbers", ["business_id"])

    # ── products ───────────────────────────────────────────────────────────
    op.create_table(
        "products",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("short_name", sa.String(30), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("category", _product_category, nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("business_id", "code", name="uq_product_code_per_business"),
    )
    op.create_index("ix_products_business_id", "products", ["business_id"])

    # ── catalog_items ──────────────────────────────────────────────────────
    op.create_table(
        "catalog_items",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False, unique=True),
        sa.Column("price_large", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_small", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_unit", sa.Numeric(10, 2), nullable=True),
        sa.Column("price_dozen", sa.Numeric(10, 2), nullable=True),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_catalog_items_business_id", "catalog_items", ["business_id"])

    # ── combos ─────────────────────────────────────────────────────────────
    op.create_table(
        "combos",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("short_name", sa.String(30), nullable=False),
        sa.Column("full_name", sa.String(150), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("price", sa.Numeric(10, 2), nullable=False),
        sa.Column("is_available", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("business_id", "code", name="uq_combo_code_per_business"),
    )
    op.create_index("ix_combos_business_id", "combos", ["business_id"])

    # ── combo_items ────────────────────────────────────────────────────────
    op.create_table(
        "combo_items",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("combo_id", sa.UUID(), sa.ForeignKey("combos.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False, server_default="1"),
    )

    # ── customers ──────────────────────────────────────────────────────────
    op.create_table(
        "customers",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("name", sa.String(150), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("credit_balance", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.UniqueConstraint("business_id", "phone", name="uq_customer_phone_per_business"),
    )
    op.create_index("ix_customers_business_id", "customers", ["business_id"])

    # ── conversation_sessions ──────────────────────────────────────────────
    op.create_table(
        "conversation_sessions",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("whatsapp_number_id", sa.UUID(), sa.ForeignKey("whatsapp_numbers.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", _session_status, nullable=False, server_default="active_bot"),
        sa.Column("assigned_operator_id", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("last_message_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_conversation_sessions_business_id", "conversation_sessions", ["business_id"])

    # ── messages ───────────────────────────────────────────────────────────
    op.create_table(
        "messages",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("session_id", sa.UUID(), sa.ForeignKey("conversation_sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("direction", _message_direction, nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("sent_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_messages_session_id", "messages", ["session_id"])

    # ── orders ─────────────────────────────────────────────────────────────
    op.create_table(
        "orders",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("session_id", sa.UUID(), sa.ForeignKey("conversation_sessions.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", _order_status, nullable=False, server_default="in_progress"),
        sa.Column("payment_status", _payment_status, nullable=False, server_default="no_charge"),
        sa.Column("origin", _order_origin, nullable=False),
        sa.Column("delivery_type", _delivery_type, nullable=False),
        sa.Column("delivery_address", sa.Text(), nullable=True),
        sa.Column("total_amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("credit_applied", sa.Numeric(10, 2), nullable=False, server_default="0"),
        sa.Column("created_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_orders_business_id", "orders", ["business_id"])
    op.create_index("ix_orders_status", "orders", ["status"])

    # ── order_items ────────────────────────────────────────────────────────
    op.create_table(
        "order_items",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.UUID(), sa.ForeignKey("products.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("combo_id", sa.UUID(), sa.ForeignKey("combos.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("unit_price", sa.Numeric(10, 2), nullable=False),
        sa.Column("variant", sa.JSON(), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
    )

    # ── payments ───────────────────────────────────────────────────────────
    op.create_table(
        "payments",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("method", _payment_method, nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("mp_preference_id", sa.String(255), nullable=True),
        sa.Column("mp_payment_id", sa.String(255), nullable=True),
        sa.Column("status", _mp_payment_status, nullable=False, server_default="pending"),
        sa.Column("paid_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_payments_order_id", "payments", ["order_id"])

    # ── credits ────────────────────────────────────────────────────────────
    op.create_table(
        "credits",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("customer_id", sa.UUID(), sa.ForeignKey("customers.id", ondelete="CASCADE"), nullable=False),
        sa.Column("amount", sa.Numeric(10, 2), nullable=False),
        sa.Column("reason", sa.String(255), nullable=True),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id", ondelete="SET NULL"), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_credits_business_id", "credits", ["business_id"])

    # ── incidents ──────────────────────────────────────────────────────────
    op.create_table(
        "incidents",
        sa.Column("id", sa.UUID(), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("order_id", sa.UUID(), sa.ForeignKey("orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("business_id", sa.UUID(), sa.ForeignKey("businesses.id", ondelete="CASCADE"), nullable=False),
        sa.Column("type", _incident_type, nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("reported_by", sa.UUID(), sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("status", _incident_status, nullable=False, server_default="open"),
        sa.Column("resolved_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_incidents_order_id", "incidents", ["order_id"])
    op.create_index("ix_incidents_business_id", "incidents", ["business_id"])


def downgrade() -> None:
    # Eliminar tablas en orden inverso (respetando FKs)
    op.drop_table("incidents")
    op.drop_table("credits")
    op.drop_table("payments")
    op.drop_table("order_items")
    op.drop_table("orders")
    op.drop_table("messages")
    op.drop_table("conversation_sessions")
    op.drop_table("customers")
    op.drop_table("combo_items")
    op.drop_table("combos")
    op.drop_table("catalog_items")
    op.drop_table("products")
    op.drop_table("whatsapp_numbers")
    op.drop_table("user_business")
    op.drop_table("businesses")
    op.drop_table("users")

    # Eliminar tipos ENUM
    for enum_name in [
        "incident_status", "incident_type", "mp_payment_status",
        "payment_method", "delivery_type", "order_origin",
        "payment_status", "order_status", "message_direction",
        "session_status", "product_category", "whatsapp_status", "user_role",
    ]:
        op.execute(f"DROP TYPE IF EXISTS {enum_name}")
