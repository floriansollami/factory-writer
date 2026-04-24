from fastapi import APIRouter

from factory_writer.api.routes.style_guide.document_source_router import (
    router as document_source_router,
)
from factory_writer.api.routes.style_guide.ingestion_router import (
    router as ingestion_router,
)
from factory_writer.api.routes.style_guide.overview_router import router as overview_router
from factory_writer.api.routes.style_guide.review_router import router as review_router

router = APIRouter()
router.include_router(overview_router)
router.include_router(document_source_router)
router.include_router(ingestion_router)
router.include_router(review_router)

__all__ = ["router"]
