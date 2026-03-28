"""Lógica de negocio para catálogo: productos, precios y combos."""
from __future__ import annotations

import uuid

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.catalog import CatalogItem, Combo, ComboItem, Product
from app.models.order import OrderItem
from app.schemas.catalogo import (
    CatalogItemCreate,
    CatalogItemUpdate,
    ComboCreate,
    ComboUpdate,
    ProductCreate,
    ProductUpdate,
)


# ── Productos ─────────────────────────────────────────────────────────────────

async def listar_productos(
    business_id: uuid.UUID,
    db: AsyncSession,
    *,
    category: str | None = None,
    is_available: bool | None = None,
    search: str | None = None,
    page: int = 1,
    page_size: int = 20,
) -> tuple[list[Product], int]:
    """
    Retorna los productos del comercio con filtros opcionales.
    También incluye el catalog_item asociado.
    """
    q = (
        select(Product)
        .where(Product.business_id == business_id)
        .options(selectinload(Product.catalog_item))
    )
    if category is not None:
        q = q.where(Product.category == category)
    if is_available is not None:
        q = q.where(Product.is_available == is_available)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(
            func.lower(Product.code).like(like)
            | func.lower(Product.short_name).like(like)
            | func.lower(Product.full_name).like(like)
        )

    # Total para paginación
    count_q = select(func.count()).select_from(q.subquery())
    total = (await db.execute(count_q)).scalar_one()

    # Paginación
    q = q.order_by(Product.category, Product.short_name)
    q = q.offset((page - 1) * page_size).limit(page_size)
    result = await db.execute(q)
    return list(result.scalars()), total


async def obtener_producto(
    product_id: uuid.UUID,
    business_id: uuid.UUID,
    db: AsyncSession,
) -> Product:
    """Retorna un producto del comercio o lanza 404."""
    result = await db.execute(
        select(Product)
        .where(Product.id == product_id, Product.business_id == business_id)
        .options(selectinload(Product.catalog_item))
    )
    product = result.scalar_one_or_none()
    if product is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Producto no encontrado")
    return product


async def crear_producto(
    business_id: uuid.UUID,
    data: ProductCreate,
    db: AsyncSession,
) -> Product:
    """
    Crea un producto en el inventario del comercio.
    Lanza 409 si el código ya existe en el comercio.
    """
    existing = await db.execute(
        select(Product).where(Product.business_id == business_id, Product.code == data.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un producto con el código '{data.code}' en este comercio",
        )

    product = Product(
        business_id=business_id,
        code=data.code,
        short_name=data.short_name,
        full_name=data.full_name,
        description=data.description,
        category=data.category,
        is_available=data.is_available,
    )
    db.add(product)
    await db.commit()
    await db.refresh(product)
    # Recargar con relaciones
    return await obtener_producto(product.id, business_id, db)


async def editar_producto(
    product_id: uuid.UUID,
    business_id: uuid.UUID,
    data: ProductUpdate,
    db: AsyncSession,
) -> Product:
    """
    Edita nombre, descripción y disponibilidad de un producto.
    El código es inmutable y no se toca.
    """
    product = await obtener_producto(product_id, business_id, db)

    if data.short_name is not None:
        product.short_name = data.short_name
    if data.full_name is not None:
        product.full_name = data.full_name
    if data.description is not None:
        product.description = data.description
    if data.is_available is not None:
        product.is_available = data.is_available

    await db.commit()
    await db.refresh(product)
    return await obtener_producto(product.id, business_id, db)


async def eliminar_producto(
    product_id: uuid.UUID,
    business_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Elimina físicamente un producto si no tiene pedidos históricos.
    Si tiene pedidos, lo desactiva (soft delete).
    Regla de negocio: nunca eliminar físicamente si tiene pedidos.
    """
    product = await obtener_producto(product_id, business_id, db)

    # Verificar si tiene pedidos asociados
    tiene_pedidos = await db.execute(
        select(func.count()).where(OrderItem.product_id == product_id)
    )
    count = tiene_pedidos.scalar_one()

    if count > 0:
        # Soft delete: solo desactivar
        product.is_available = False
        await db.commit()
        return

    # Sin pedidos: eliminar físicamente
    await db.delete(product)
    await db.commit()


# ── Catálogo (precios) ────────────────────────────────────────────────────────

async def crear_o_actualizar_catalog_item(
    business_id: uuid.UUID,
    data: CatalogItemCreate,
    db: AsyncSession,
) -> CatalogItem:
    """Crea o actualiza el item de catálogo (precios) de un producto."""
    # Verificar que el producto pertenece al comercio
    await obtener_producto(data.product_id, business_id, db)

    result = await db.execute(
        select(CatalogItem).where(CatalogItem.product_id == data.product_id)
    )
    item = result.scalar_one_or_none()

    if item is None:
        item = CatalogItem(
            business_id=business_id,
            product_id=data.product_id,
            price_large=data.price_large,
            price_small=data.price_small,
            price_unit=data.price_unit,
            price_dozen=data.price_dozen,
            is_available=data.is_available,
        )
        db.add(item)
    else:
        item.price_large = data.price_large
        item.price_small = data.price_small
        item.price_unit = data.price_unit
        item.price_dozen = data.price_dozen
        item.is_available = data.is_available

    await db.commit()
    await db.refresh(item)
    return item


async def actualizar_catalog_item(
    item_id: uuid.UUID,
    business_id: uuid.UUID,
    data: CatalogItemUpdate,
    db: AsyncSession,
) -> CatalogItem:
    """Actualiza los precios de un item del catálogo."""
    result = await db.execute(
        select(CatalogItem).where(
            CatalogItem.id == item_id,
            CatalogItem.business_id == business_id,
        )
    )
    item = result.scalar_one_or_none()
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item de catálogo no encontrado")

    if data.price_large is not None:
        item.price_large = data.price_large
    if data.price_small is not None:
        item.price_small = data.price_small
    if data.price_unit is not None:
        item.price_unit = data.price_unit
    if data.price_dozen is not None:
        item.price_dozen = data.price_dozen
    if data.is_available is not None:
        item.is_available = data.is_available

    await db.commit()
    await db.refresh(item)
    return item


# ── Combos ────────────────────────────────────────────────────────────────────

def _combo_options() -> list:
    return [
        selectinload(Combo.items).selectinload(ComboItem.product).selectinload(Product.catalog_item)
    ]


async def listar_combos(
    business_id: uuid.UUID,
    db: AsyncSession,
    *,
    is_available: bool | None = None,
    search: str | None = None,
) -> list[Combo]:
    """Retorna todos los combos del comercio."""
    q = (
        select(Combo)
        .where(Combo.business_id == business_id)
        .options(*_combo_options())
    )
    if is_available is not None:
        q = q.where(Combo.is_available == is_available)
    if search:
        like = f"%{search.lower()}%"
        q = q.where(
            func.lower(Combo.code).like(like)
            | func.lower(Combo.short_name).like(like)
            | func.lower(Combo.full_name).like(like)
        )
    q = q.order_by(Combo.short_name)
    result = await db.execute(q)
    return list(result.scalars())


async def obtener_combo(
    combo_id: uuid.UUID,
    business_id: uuid.UUID,
    db: AsyncSession,
) -> Combo:
    """Retorna un combo del comercio o lanza 404."""
    result = await db.execute(
        select(Combo)
        .where(Combo.id == combo_id, Combo.business_id == business_id)
        .options(*_combo_options())
    )
    combo = result.scalar_one_or_none()
    if combo is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Combo no encontrado")
    return combo


async def crear_combo(
    business_id: uuid.UUID,
    data: ComboCreate,
    db: AsyncSession,
) -> Combo:
    """
    Crea un combo con sus productos.
    Lanza 409 si el código ya existe en el comercio.
    Lanza 404 si algún product_id no pertenece al comercio.
    """
    # Verificar código único
    existing = await db.execute(
        select(Combo).where(Combo.business_id == business_id, Combo.code == data.code)
    )
    if existing.scalar_one_or_none() is not None:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Ya existe un combo con el código '{data.code}' en este comercio",
        )

    combo = Combo(
        business_id=business_id,
        code=data.code,
        short_name=data.short_name,
        full_name=data.full_name,
        description=data.description,
        price=data.price,
        is_available=data.is_available,
    )
    db.add(combo)
    await db.flush()

    for item_data in data.items:
        if item_data.is_open:
            # Slot abierto: no hay producto fijo, solo categoría elegible
            db.add(ComboItem(
                combo_id=combo.id,
                product_id=None,
                quantity=item_data.quantity,
                is_open=True,
                open_category=item_data.open_category,
            ))
        else:
            # Producto fijo: verificar que pertenece al comercio
            await obtener_producto(item_data.product_id, business_id, db)
            db.add(ComboItem(
                combo_id=combo.id,
                product_id=item_data.product_id,
                quantity=item_data.quantity,
                is_open=False,
                open_category=None,
            ))

    await db.commit()
    return await obtener_combo(combo.id, business_id, db)


async def editar_combo(
    combo_id: uuid.UUID,
    business_id: uuid.UUID,
    data: ComboUpdate,
    db: AsyncSession,
) -> Combo:
    """
    Edita los datos de un combo. Si se envía `items`, reemplaza toda la lista.
    El código no es editable.
    """
    combo = await obtener_combo(combo_id, business_id, db)

    if data.short_name is not None:
        combo.short_name = data.short_name
    if data.full_name is not None:
        combo.full_name = data.full_name
    if data.description is not None:
        combo.description = data.description
    if data.price is not None:
        combo.price = data.price
    if data.is_available is not None:
        combo.is_available = data.is_available

    if data.items is not None:
        # Reemplazar items: eliminar los existentes y crear los nuevos
        existing_items = await db.execute(
            select(ComboItem).where(ComboItem.combo_id == combo_id)
        )
        for item in existing_items.scalars():
            await db.delete(item)
        await db.flush()

        for item_data in data.items:
            if item_data.is_open:
                db.add(ComboItem(
                    combo_id=combo_id,
                    product_id=None,
                    quantity=item_data.quantity,
                    is_open=True,
                    open_category=item_data.open_category,
                ))
            else:
                await obtener_producto(item_data.product_id, business_id, db)
                db.add(ComboItem(
                    combo_id=combo_id,
                    product_id=item_data.product_id,
                    quantity=item_data.quantity,
                    is_open=False,
                    open_category=None,
                ))

    await db.commit()
    return await obtener_combo(combo_id, business_id, db)


async def eliminar_combo(
    combo_id: uuid.UUID,
    business_id: uuid.UUID,
    db: AsyncSession,
) -> None:
    """
    Elimina físicamente un combo si no tiene pedidos históricos.
    Si tiene pedidos, lo desactiva (soft delete).
    """
    combo = await obtener_combo(combo_id, business_id, db)

    # Verificar pedidos asociados al combo
    tiene_pedidos = await db.execute(
        select(func.count()).where(OrderItem.combo_id == combo_id)
    )
    count = tiene_pedidos.scalar_one()

    if count > 0:
        combo.is_available = False
        await db.commit()
        return

    await db.delete(combo)
    await db.commit()
