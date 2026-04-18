import logging
import sys
from typing import Any

import structlog

from factory_writer.core.config import get_settings

settings = get_settings()


def setup_logging() -> None:
    """
    Configure Structlog en SOTA 2026.
    Intercepte le logger natif (Uvicorn/FastAPI) et injecte le Correlation ID via contextvars.
    """

    # Processeurs partagés entre le JSON (Prod) et la Console (Dév)
    shared_processors: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,  # SOTA 2026: Injecte l'ID asynchrone
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
    ]

    # Rendu dynamique (DEBUG = Console humaine claire, PROD = JSON pur Machine)
    renderer: Any = (
        structlog.dev.ConsoleRenderer(colors=True)
        if settings.debug
        else structlog.processors.JSONRenderer()
    )

    # Cœur de Structlog
    structlog.configure(
        processors=shared_processors
        + [
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Hijacking de la librairie standard (Uvicorn / FastAPI / SQLAlchemy)
    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    # On force le root logger à utiliser notre handler
    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(logging.INFO)

    # On fait taire les logs inintéressants de bases de données ou Uvicorn si besoin
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
