from __future__ import annotations

import logging

logging.basicConfig(level=logging.INFO, force=True)

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

import app.models  # noqa: F401 — registra todos los mappers de SQLAlchemy
from app.api.auth import router as auth_router
from app.api.agent import router as agent_router
from app.api.catalogo import router as catalogo_router
from app.api.clientes import router as clientes_router
from app.api.comercios import router as comercios_router
from app.api.conversaciones import router as conversaciones_router
from app.api.empleados import router as empleados_router
from app.api.pagos import router as pagos_router
from app.api.webhooks import router as webhooks_router
from app.api.whatsapp import router as whatsapp_router
from app.api.health import router as health_router
from app.api.n8n import router as n8n_router
from app.api.pedidos import router as pedidos_router
from app.core.config import settings
from app.core.db import AsyncSessionLocal
from app.services.agent_runtime import get_agent_runtime_status

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Whapi API",
    description="Plataforma multi-tenant de chatbot de pedidos para comercios gastronómicos.",
    version="0.1.0",
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def check_db_on_startup() -> None:
    """Verifica la conectividad con la base de datos al arrancar. Falla rápido si no conecta."""
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(text("SELECT 1"))
        logger.info("✅ Conexión a la base de datos establecida correctamente.")
    except Exception as exc:
        logger.critical("❌ No se pudo conectar a la base de datos: %s", exc)
        raise RuntimeError("Fallo en la conexión a la base de datos al iniciar") from exc

    agent_status = await get_agent_runtime_status()
    logger.info(
        "Agent runtime startup: enabled=%s orchestrator=%s provider=%s model=%s reachable=%s detail=%s",
        agent_status.enabled,
        agent_status.orchestrator,
        agent_status.provider,
        agent_status.model,
        agent_status.reachable,
        agent_status.detail,
    )


# Routers — se van agregando fase por fase
app.include_router(health_router)
app.include_router(agent_router)
app.include_router(auth_router)
app.include_router(comercios_router)
app.include_router(empleados_router)
app.include_router(catalogo_router)
app.include_router(clientes_router)
app.include_router(pedidos_router)
app.include_router(conversaciones_router)
app.include_router(whatsapp_router)
app.include_router(pagos_router)
app.include_router(webhooks_router)
app.include_router(n8n_router)
