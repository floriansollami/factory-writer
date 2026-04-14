from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from api.routes.eventarc_router import router as eventarc_router
from core.config import get_settings
from core.logger import setup_logging
from infrastructure.database.session import engine

settings = get_settings()

# Interception globale stdlib -> Structlog
setup_logging()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    S'exécute autour de la durée de vie globale du serveur pour gérer les connexions partagées.
    """
    logger.info(
        "🚀 Démarrage de Factory Writer : Initialisation des ressources globales SOTA 2026..."
    )
    yield  # met la fonction en pause
    logger.info("🛑 Extinction du serveur : Coupure propre du Pool asynchrone PostgreSQL...")
    await engine.dispose()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Moteur Central Factory Writer.",
    lifespan=lifespan,
)

# Ajout du Middleware ASGI ContextVars (Crée un Request-ID sécurisé en asynchrone)
app.add_middleware(CorrelationIdMiddleware)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """
    Vérifie la santé de l'API. Utilisé par Cloud Run / Kubernetes.
    """
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


# Inclusion du routeur dédié au webhooks eventarc SOTA 2026
app.include_router(eventarc_router, prefix="/webhooks/eventarc", tags=["Webhooks", "Eventarc"])


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """
    SOTA 2026: Filtre global des paniques BDD.
    Protège les données et force Eventarc (webhook) à réessayer (HTTP 500).
    """
    logger.error(
        "DB_PANIC : Erreur critique SQLAlchemy (Corrompue ou MultipleResults?)", exc_info=exc
    )
    return JSONResponse(status_code=500, content={"error": "Database error. Retrying later."})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """
    SOTA 2026: Le filet de sécurité final. Masque les infos de stack-trace en prod.
    """
    logger.critical("SERVER_CRASH : Exception inattendue non gérée", exc_info=exc)
    return JSONResponse(status_code=500, content={"error": "Internal Server Error"})
