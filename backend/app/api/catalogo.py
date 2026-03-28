from __future__ import annotations

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import exists, select

from app.core.deps import (
    ActivePizzeriaId,
    DBSession,
    OwnerOrAdminRequired,
)
from app.models.catalog import (
    CatalogItem,
    Combo,
    ComboItem,
    PizzeriaConfig,
    Product,
)
from app.models.order import OrderItem
from app.schemas.catalog import (
    CatalogItemCreate,
    CatalogItemRead,
    CatalogItemUpdate,
    ComboCreate,
    ComboRead,
    ComboUpdate,
    PizzeriaConfigRead,
    PizzeriaConfigUpdate,
    ProductCreate,
    ProductRead,
    ProductUpdate,
)

router = APIRouter(tags=["catalogo"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_product(product_id: int, pizzeria_id: int, db: DBSession) -> Product:
    """Devuelve el producto si pertenece a la pizzería activa. Lanza 404 si no."""
    result = await db.execute(
        select(Product).where(
            Product.id == product_id,
            Product.pizzeria_id == pizzeria_id,
            Product.deleted_at.is_(None),
        )
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


async def _get_combo(combo_id: int, pizzeria_id: int, db: DBSession) -> Combo:
    """Devuelve el combo si pertenece a la pizzería activa. Lanza 404 si no."""
    result = await db.execute(
        select(Combo).where(
            Combo.id == combo_id,
            Combo.pizzeria_id == pizzeria_id,
            Combo.deleted_at.is_(None),
        )
    )
    combo = result.scalar_one_or_none()
    if combo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Combo no encontrado")
    return combo


async def _product_has_orders(product_id: int, db: DBSession) -> bool:
    """Indica si el producto tiene al menos un pedido asociado."""
    result = await db.execute(
        select(exists().where(OrderItem.product_id == product_id))
    )
    return result.scalar()


# ---------------------------------------------------------------------------
# Productos
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/productos",
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_product(
    pizzeria_id: int,
    body: ProductCreate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> ProductRead:
    """Crea un producto en el catálogo de la pizzería activa."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    # Código único dentro de la pizzería
    dup = await db.execute(
        select(Product).where(
            Product.pizzeria_id == active_pid,
            Product.code == body.code,
            Product.deleted_at.is_(None),
        )
    )
    if dup.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con el código '{body.code}'",
        )

    product = Product(pizzeria_id=active_pid, **body.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.get("/pizzerias/{pizzeria_id}/productos", response_model=list[ProductRead])
async def list_products(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    include_unavailable: bool = False,
) -> list[ProductRead]:
    """Lista productos de la pizzería. Por defecto solo los disponibles."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    stmt = select(Product).where(
        Product.pizzeria_id == active_pid,
        Product.deleted_at.is_(None),
    )
    if not include_unavailable:
        stmt = stmt.where(Product.is_available.is_(True))

    result = await db.execute(stmt.order_by(Product.code))
    return [ProductRead.model_validate(p) for p in result.scalars()]


@router.get("/pizzerias/{pizzeria_id}/productos/{product_id}", response_model=ProductRead)
async def get_product(
    pizzeria_id: int,
    product_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> ProductRead:
    """Detalle de un producto."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    product = await _get_product(product_id, active_pid, db)
    return ProductRead.model_validate(product)


@router.patch("/pizzerias/{pizzeria_id}/productos/{product_id}", response_model=ProductRead)
async def update_product(
    pizzeria_id: int,
    product_id: int,
    body: ProductUpdate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> ProductRead:
    """Actualiza campos de un producto. El código es inmutable."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    product = await _get_product(product_id, active_pid, db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(product, field, value)

    await db.commit()
    await db.refresh(product)
    return ProductRead.model_validate(product)


@router.delete("/pizzerias/{pizzeria_id}/productos/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_product(
    pizzeria_id: int,
    product_id: int,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """
    Elimina un producto. Si tiene pedidos históricos aplica soft delete
    (is_available=false). Si no tiene pedidos lo elimina físicamente.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    product = await _get_product(product_id, active_pid, db)

    if await _product_has_orders(product_id, db):
        product.is_available = False
        await db.commit()
    else:
        await db.delete(product)
        await db.commit()


# ---------------------------------------------------------------------------
# Catálogo (precios / variantes)
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/catalog-items",
    response_model=CatalogItemRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_catalog_item(
    pizzeria_id: int,
    body: CatalogItemCreate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> CatalogItemRead:
    """Agrega un precio/variante a un producto del catálogo."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    # Verificar que el producto pertenece a esta pizzería
    await _get_product(body.product_id, active_pid, db)

    item = CatalogItem(pizzeria_id=active_pid, **body.model_dump())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return CatalogItemRead.model_validate(item)


@router.get("/pizzerias/{pizzeria_id}/catalog-items", response_model=list[CatalogItemRead])
async def list_catalog_items(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    product_id: int | None = None,
) -> list[CatalogItemRead]:
    """Lista ítems del catálogo. Opcionalmente filtra por producto."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    stmt = select(CatalogItem).where(CatalogItem.pizzeria_id == active_pid)
    if product_id is not None:
        stmt = stmt.where(CatalogItem.product_id == product_id)

    result = await db.execute(stmt.order_by(CatalogItem.product_id, CatalogItem.size))
    return [CatalogItemRead.model_validate(i) for i in result.scalars()]


@router.patch(
    "/pizzerias/{pizzeria_id}/catalog-items/{item_id}",
    response_model=CatalogItemRead,
)
async def update_catalog_item(
    pizzeria_id: int,
    item_id: int,
    body: CatalogItemUpdate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> CatalogItemRead:
    """Actualiza precio o estado de un ítem del catálogo."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    result = await db.execute(
        select(CatalogItem).where(
            CatalogItem.id == item_id,
            CatalogItem.pizzeria_id == active_pid,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado")

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await db.commit()
    await db.refresh(item)
    return CatalogItemRead.model_validate(item)


@router.delete(
    "/pizzerias/{pizzeria_id}/catalog-items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_catalog_item(
    pizzeria_id: int,
    item_id: int,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """Elimina un ítem del catálogo (precio/variante)."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    result = await db.execute(
        select(CatalogItem).where(
            CatalogItem.id == item_id,
            CatalogItem.pizzeria_id == active_pid,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem no encontrado")

    await db.delete(item)
    await db.commit()


# ---------------------------------------------------------------------------
# Combos
# ---------------------------------------------------------------------------

@router.post(
    "/pizzerias/{pizzeria_id}/combos",
    response_model=ComboRead,
    status_code=status.HTTP_201_CREATED,
)
async def create_combo(
    pizzeria_id: int,
    body: ComboCreate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> ComboRead:
    """Crea un combo en la pizzería activa."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    combo = Combo(pizzeria_id=active_pid, **body.model_dump())
    db.add(combo)
    await db.commit()
    await db.refresh(combo)
    return ComboRead.model_validate(combo)


@router.get("/pizzerias/{pizzeria_id}/combos", response_model=list[ComboRead])
async def list_combos(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
    include_unavailable: bool = False,
) -> list[ComboRead]:
    """Lista combos de la pizzería."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    stmt = select(Combo).where(
        Combo.pizzeria_id == active_pid,
        Combo.deleted_at.is_(None),
    )
    if not include_unavailable:
        stmt = stmt.where(Combo.is_available.is_(True))

    result = await db.execute(stmt.order_by(Combo.name))
    return [ComboRead.model_validate(c) for c in result.scalars()]


@router.get("/pizzerias/{pizzeria_id}/combos/{combo_id}", response_model=ComboRead)
async def get_combo(
    pizzeria_id: int,
    combo_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> ComboRead:
    """Detalle de un combo."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")
    combo = await _get_combo(combo_id, active_pid, db)
    return ComboRead.model_validate(combo)


@router.patch("/pizzerias/{pizzeria_id}/combos/{combo_id}", response_model=ComboRead)
async def update_combo(
    pizzeria_id: int,
    combo_id: int,
    body: ComboUpdate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> ComboRead:
    """Actualiza un combo."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    combo = await _get_combo(combo_id, active_pid, db)

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(combo, field, value)

    await db.commit()
    await db.refresh(combo)
    return ComboRead.model_validate(combo)


@router.delete(
    "/pizzerias/{pizzeria_id}/combos/{combo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def delete_combo(
    pizzeria_id: int,
    combo_id: int,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """
    Elimina un combo. Si tiene pedidos históricos aplica soft delete.
    Si no tiene pedidos lo elimina físicamente.
    """
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    combo = await _get_combo(combo_id, active_pid, db)

    has_orders = await db.execute(
        select(exists().where(OrderItem.combo_id == combo_id))
    )
    if has_orders.scalar():
        combo.is_available = False
        await db.commit()
    else:
        await db.delete(combo)
        await db.commit()


# ---------------------------------------------------------------------------
# Combo Items (productos dentro de un combo)
# ---------------------------------------------------------------------------

class ComboItemAdd(BaseModel):
    """Producto a agregar a un combo."""

    product_id: int
    quantity: int = 1


@router.post(
    "/pizzerias/{pizzeria_id}/combos/{combo_id}/items",
    status_code=status.HTTP_201_CREATED,
)
async def add_combo_item(
    pizzeria_id: int,
    combo_id: int,
    body: ComboItemAdd,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> dict:
    """Agrega un producto a un combo."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_combo(combo_id, active_pid, db)
    await _get_product(body.product_id, active_pid, db)

    if body.quantity < 1:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="La cantidad debe ser al menos 1",
        )

    combo_item = ComboItem(combo_id=combo_id, product_id=body.product_id, quantity=body.quantity)
    db.add(combo_item)
    await db.commit()
    await db.refresh(combo_item)
    return {"id": combo_item.id, "combo_id": combo_id, "product_id": body.product_id, "quantity": body.quantity}


@router.delete(
    "/pizzerias/{pizzeria_id}/combos/{combo_id}/items/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def remove_combo_item(
    pizzeria_id: int,
    combo_id: int,
    item_id: int,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> None:
    """Elimina un producto de un combo."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    await _get_combo(combo_id, active_pid, db)

    result = await db.execute(
        select(ComboItem).where(
            ComboItem.id == item_id,
            ComboItem.combo_id == combo_id,
        )
    )
    combo_item = result.scalar_one_or_none()
    if combo_item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Ítem de combo no encontrado")

    await db.delete(combo_item)
    await db.commit()


# ---------------------------------------------------------------------------
# Configuración de pizzería
# ---------------------------------------------------------------------------

@router.get("/pizzerias/{pizzeria_id}/config", response_model=PizzeriaConfigRead)
async def get_config(
    pizzeria_id: int,
    active_pid: ActivePizzeriaId,
    db: DBSession,
) -> PizzeriaConfigRead:
    """Devuelve la configuración operativa de la pizzería."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    result = await db.execute(
        select(PizzeriaConfig).where(PizzeriaConfig.pizzeria_id == active_pid)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada. Contacte al administrador.",
        )
    return PizzeriaConfigRead.model_validate(config)


@router.patch("/pizzerias/{pizzeria_id}/config", response_model=PizzeriaConfigRead)
async def update_config(
    pizzeria_id: int,
    body: PizzeriaConfigUpdate,
    active_pid: ActivePizzeriaId,
    _: OwnerOrAdminRequired,
    db: DBSession,
) -> PizzeriaConfigRead:
    """Actualiza la configuración operativa de la pizzería (recargo media-media, horarios, etc.)."""
    if pizzeria_id != active_pid:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Acceso denegado")

    result = await db.execute(
        select(PizzeriaConfig).where(PizzeriaConfig.pizzeria_id == active_pid)
    )
    config = result.scalar_one_or_none()
    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Configuración no encontrada. Contacte al administrador.",
        )

    for field, value in body.model_dump(exclude_unset=True).items():
        setattr(config, field, value)

    await db.commit()
    await db.refresh(config)
    return PizzeriaConfigRead.model_validate(config)
