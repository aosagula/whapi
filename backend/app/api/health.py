from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health() -> dict[str, str]:
    """Verificación de disponibilidad del servicio."""
    return {"status": "ok"}
