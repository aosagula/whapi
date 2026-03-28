"""Endpoints del catálogo: productos, precios y combos."""
from __future__ import annotations

import math
import uuid

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.core.permisos import get_membresia, get_membresia_gestion
from app.models.account import Business, UserBusiness
from app.schemas.catalogo import (
    CatalogItemCreate,
    CatalogItemResponse,
    CatalogItemUpdate,
    ComboCreate,
    ComboResponse,
    ComboUpdate,
    ProductCreate,
    ProductListResponse,
    ProductResponse,
    ProductUpdate,
)
from app.services.catalogo import (
    actualizar_catalog_item,
    crear_combo,
    crear_o_actualizar_catalog_item,
    crear_producto,
    editar_combo,
    editar_producto,
    eliminar_combo,
    eliminar_producto,
    listar_combos,
    listar_productos,
    obtener_combo,
    obtener_producto,
)

router = APIRouter(tags=["catálogo"])


# ── Productos ─────────────────────────────────────────────────────────────────

@router.get(
    "/comercios/{comercio_id}/products",
    response_model=ProductListResponse,
)
async def listar(
    comercio_id: uuid.UUID,
    category: str | None = Query(None),
    is_available: bool | None = Query(None),
    search: str | None = Query(None),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ProductListResponse:
    """Lista productos del comercio con filtros y paginación."""
    business, _ = ctx
    products, total = await listar_productos(
        business.id, db,
        category=category,
        is_available=is_available,
        search=search,
        page=page,
        page_size=page_size,
    )
    return ProductListResponse(
        items=products,  # type: ignore[arg-type]
        total=total,
        page=page,
        page_size=page_size,
        total_pages=max(1, math.ceil(total / page_size)),
    )


@router.post(
    "/comercios/{comercio_id}/products",
    response_model=ProductResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear(
    comercio_id: uuid.UUID,
    data: ProductCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Crea un producto en el inventario (requiere owner o admin)."""
    business, _ = ctx
    return await crear_producto(business.id, data, db)  # type: ignore[return-value]


@router.get(
    "/comercios/{comercio_id}/products/{product_id}",
    response_model=ProductResponse,
)
async def detalle(
    comercio_id: uuid.UUID,
    product_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Retorna el detalle de un producto."""
    business, _ = ctx
    return await obtener_producto(product_id, business.id, db)  # type: ignore[return-value]


@router.patch(
    "/comercios/{comercio_id}/products/{product_id}",
    response_model=ProductResponse,
)
async def editar(
    comercio_id: uuid.UUID,
    product_id: uuid.UUID,
    data: ProductUpdate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> ProductResponse:
    """Edita nombre, descripción o disponibilidad de un producto. El código es inmutable."""
    business, _ = ctx
    return await editar_producto(product_id, business.id, data, db)  # type: ignore[return-value]


@router.delete(
    "/comercios/{comercio_id}/products/{product_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar(
    comercio_id: uuid.UUID,
    product_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina o desactiva un producto (soft delete si tiene pedidos)."""
    business, _ = ctx
    await eliminar_producto(product_id, business.id, db)


# ── Catálogo (precios) ────────────────────────────────────────────────────────

@router.post(
    "/comercios/{comercio_id}/catalog",
    response_model=CatalogItemResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_precios(
    comercio_id: uuid.UUID,
    data: CatalogItemCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> CatalogItemResponse:
    """Crea o reemplaza los precios de un producto en el catálogo."""
    business, _ = ctx
    return await crear_o_actualizar_catalog_item(business.id, data, db)  # type: ignore[return-value]


@router.patch(
    "/comercios/{comercio_id}/catalog/{item_id}",
    response_model=CatalogItemResponse,
)
async def actualizar_precios(
    comercio_id: uuid.UUID,
    item_id: uuid.UUID,
    data: CatalogItemUpdate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> CatalogItemResponse:
    """Actualiza los precios de un item del catálogo."""
    business, _ = ctx
    return await actualizar_catalog_item(item_id, business.id, data, db)  # type: ignore[return-value]


# ── Combos ────────────────────────────────────────────────────────────────────

@router.get(
    "/comercios/{comercio_id}/combos",
    response_model=list[ComboResponse],
)
async def listar_combos_endpoint(
    comercio_id: uuid.UUID,
    is_available: bool | None = Query(None),
    search: str | None = Query(None),
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> list[ComboResponse]:
    """Lista todos los combos del comercio."""
    business, _ = ctx
    return await listar_combos(business.id, db, is_available=is_available, search=search)  # type: ignore[return-value]


@router.post(
    "/comercios/{comercio_id}/combos",
    response_model=ComboResponse,
    status_code=status.HTTP_201_CREATED,
)
async def crear_combo_endpoint(
    comercio_id: uuid.UUID,
    data: ComboCreate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> ComboResponse:
    """Crea un combo con sus productos."""
    business, _ = ctx
    return await crear_combo(business.id, data, db)  # type: ignore[return-value]


@router.get(
    "/comercios/{comercio_id}/combos/{combo_id}",
    response_model=ComboResponse,
)
async def detalle_combo(
    comercio_id: uuid.UUID,
    combo_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia),
    db: AsyncSession = Depends(get_db),
) -> ComboResponse:
    """Retorna el detalle de un combo."""
    business, _ = ctx
    return await obtener_combo(combo_id, business.id, db)  # type: ignore[return-value]


@router.patch(
    "/comercios/{comercio_id}/combos/{combo_id}",
    response_model=ComboResponse,
)
async def editar_combo_endpoint(
    comercio_id: uuid.UUID,
    combo_id: uuid.UUID,
    data: ComboUpdate,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> ComboResponse:
    """Edita los datos o productos de un combo. El código es inmutable."""
    business, _ = ctx
    return await editar_combo(combo_id, business.id, data, db)  # type: ignore[return-value]


@router.delete(
    "/comercios/{comercio_id}/combos/{combo_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def eliminar_combo_endpoint(
    comercio_id: uuid.UUID,
    combo_id: uuid.UUID,
    ctx: tuple[Business, UserBusiness] = Depends(get_membresia_gestion),
    db: AsyncSession = Depends(get_db),
) -> None:
    """Elimina o desactiva un combo (soft delete si tiene pedidos)."""
    business, _ = ctx
    await eliminar_combo(combo_id, business.id, db)
