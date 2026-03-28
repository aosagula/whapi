from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from sqlalchemy import text

from app.core.db import engine
from app.api.health import router as health_router
from app.api.auth import router as auth_router


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Verifica la conexión a PostgreSQL al iniciar el servidor."""
    async with engine.connect() as conn:
        await conn.execute(text("SELECT 1"))
    print("Conexion a PostgreSQL exitosa")
    yield
    await engine.dispose()


app = FastAPI(
    title="Pizzería Chatbot API",
    version="0.1.0",
    lifespan=lifespan,
)

app.include_router(health_router)
app.include_router(auth_router)
