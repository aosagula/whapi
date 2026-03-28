"""
Importar todos los modelos aquí para que SQLAlchemy registre las clases
en el mapper antes de la primera query o migración de Alembic.
El orden importa: las tablas referenciadas por FK deben cargarse primero.
"""

from app.models.base import TimestampMixin, SoftDeleteMixin  # noqa: F401
from app.models.account import Account, Pizzeria, PanelUser, UserPizzeriaRole, PizzeriaRole  # noqa: F401
from app.models.whatsapp import WhatsAppNumber, WhatsAppSessionStatus  # noqa: F401
from app.models.catalog import (  # noqa: F401
    Product,
    CatalogItem,
    Combo,
    ComboItem,
    PizzeriaConfig,
    ProductCategory,
    ProductSize,
)
from app.models.customer import Customer, CustomerCredit  # noqa: F401
from app.models.order import (  # noqa: F401
    Order,
    OrderItem,
    Payment,
    Incident,
    OrderOrigin,
    OrderStatus,
    PaymentMethod,
    PaymentStatus,
)
from app.models.conversation import ChatSession, ChatSessionStatus  # noqa: F401
