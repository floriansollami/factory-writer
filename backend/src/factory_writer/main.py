from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

import structlog
from asgi_correlation_id import CorrelationIdMiddleware
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from factory_writer.api.routes.products import router as products_router
from factory_writer.api.routes.style_guide import router as style_guide_router
from factory_writer.core.config import get_settings
from factory_writer.core.logger import setup_logging
from factory_writer.infrastructure.database.session import dispose_engine

settings = get_settings()

setup_logging()

logger = structlog.get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """Gère les ressources partagées de l'application."""
    logger.info("factory_writer.startup")
    yield
    logger.info("factory_writer.shutdown")
    await dispose_engine()


app = FastAPI(
    title=settings.app_name,
    version=settings.version,
    description="Moteur Central Factory Writer.",
    lifespan=lifespan,
)

app.add_middleware(CorrelationIdMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["Health"])
async def health_check() -> dict[str, str]:
    """Endpoint de santé pour Cloud Run."""
    return {"status": "ok", "app": settings.app_name, "version": settings.version}


app.include_router(style_guide_router, prefix="/api/style-guide", tags=["Style Guide Admin"])
app.include_router(products_router, prefix="/api/products", tags=["Products"])


@app.exception_handler(SQLAlchemyError)
async def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError) -> JSONResponse:
    """Transforme les erreurs SQLAlchemy en réponse HTTP générique."""
    logger.error("database_error", path=request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Database error. Retrying later.", "code": "DATABASE_ERROR"},
    )


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Dernier filet de sécurité pour les erreurs non gérées."""
    logger.critical("unhandled_server_error", path=request.url.path, exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"error": "Internal Server Error", "code": "INTERNAL_SERVER_ERROR"},
    )
