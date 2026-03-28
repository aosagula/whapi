from __future__ import annotations

from contextlib import asynccontextmanager
from collections.abc import AsyncGenerator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.api.health import router as health_router
from app.api.auth import router as auth_router
from app.api.pizzerias import router as pizzerias_router
from app.api.empleados import router as empleados_router
from app.api.catalogo import router as catalogo_router
from app.api.clientes import router as clientes_router
from app.api.pedidos import router as pedidos_router
from app.api.webhooks import router as webhooks_router
from app.api.conversaciones import router as conversaciones_router
from app.api.reportes import router as reportes_router


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

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",")],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router)
app.include_router(auth_router)
app.include_router(pizzerias_router)
app.include_router(empleados_router)
app.include_router(catalogo_router)
app.include_router(clientes_router)
app.include_router(pedidos_router)
app.include_router(webhooks_router)
app.include_router(conversaciones_router)
app.include_router(reportes_router)
