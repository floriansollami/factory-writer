from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI

from api.core.config import settings
from api.core.logger import setup_logging
from api.infrastructure.database.session import engine

# Interception globale stdlib -> Structlog
setup_logging()

logger = structlog.get_logger(__name__)


# Dans les anciens langages, on devait créer deux fonctions séparées (onStartup() et onShutdown()).
# L'immense avantage du yield en Python, c'est que la phase d'allumage et la phase d'extinction partagent la même fonction.
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    L'équivalent du OnApplicationShutdown de NestJS.
    S'exécute autour de la durée de vie globale du serveur.
    """
    logger.info(
        "🚀 Démarrage de Factory Writer : Initialisation des ressources globales SOTA 2026..."
    )
    yield  # met la fonction en pause
    logger.info("🛑 Extinction du serveur : Coupure propre du Pool asynchrone PostgreSQL...")
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.VERSION,
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
    return {"status": "ok", "app": settings.APP_NAME, "version": settings.VERSION}


# Les routeurs des bounded contexts (presentation) seront inclus ici.
# ex: app.include_router(style_guide_router, prefix="/api/v1/style-guide", tags=["Style Guide"])
