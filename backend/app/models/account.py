from __future__ import annotations

import enum
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, Enum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base
from app.models.base import TimestampMixin

if TYPE_CHECKING:
    from app.models.whatsapp import WhatsAppNumber
    from app.models.catalog import PizzeriaConfig, Product
    from app.models.customer import Customer
    from app.models.order import Order
    from app.models.conversation import ChatSession


class PizzeriaRole(str, enum.Enum):
    owner = "owner"
    admin = "admin"
    cashier = "cashier"
    cook = "cook"
    delivery = "delivery"


class Account(Base, TimestampMixin):
    """Cuenta del dueño. Nivel cross-tenant."""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(30))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pizzerias: Mapped[list[Pizzeria]] = relationship(back_populates="account")


class Pizzeria(Base, TimestampMixin):
    """Tenant principal. Cada pizzería es un tenant aislado."""

    __tablename__ = "pizzerias"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    address: Mapped[str | None] = mapped_column(String(255))
    city: Mapped[str | None] = mapped_column(String(100))
    logo_url: Mapped[str | None] = mapped_column(String(500))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    account: Mapped[Account] = relationship(back_populates="pizzerias")
    user_roles: Mapped[list[UserPizzeriaRole]] = relationship(back_populates="pizzeria")
    whatsapp_numbers: Mapped[list[WhatsAppNumber]] = relationship(back_populates="pizzeria")
    config: Mapped[PizzeriaConfig | None] = relationship(back_populates="pizzeria", uselist=False)
    products: Mapped[list[Product]] = relationship(back_populates="pizzeria")
    customers: Mapped[list[Customer]] = relationship(back_populates="pizzeria")
    orders: Mapped[list[Order]] = relationship(back_populates="pizzeria")
    chat_sessions: Mapped[list[ChatSession]] = relationship(back_populates="pizzeria")


class PanelUser(Base, TimestampMixin):
    """Usuario del panel (empleado). Puede tener roles en múltiples pizzerías."""

    __tablename__ = "panel_users"

    id: Mapped[int] = mapped_column(primary_key=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(254), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    pizzeria_roles: Mapped[list[UserPizzeriaRole]] = relationship(back_populates="user")


class UserPizzeriaRole(Base):
    """Asignación de rol de un usuario a una pizzería específica."""

    __tablename__ = "user_pizzeria_roles"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("panel_users.id"), nullable=False)
    pizzeria_id: Mapped[int] = mapped_column(ForeignKey("pizzerias.id"), nullable=False)
    role: Mapped[PizzeriaRole] = mapped_column(
        Enum(PizzeriaRole, name="pizzeria_role"), nullable=False
    )

    user: Mapped[PanelUser] = relationship(back_populates="pizzeria_roles")
    pizzeria: Mapped[Pizzeria] = relationship(back_populates="user_roles")
