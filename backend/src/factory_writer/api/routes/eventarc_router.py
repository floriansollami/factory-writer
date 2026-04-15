import structlog
from fastapi import APIRouter, Header, Response

from factory_writer.api.routes.schemas.eventarc_payload import StorageObjectData
from factory_writer.application.ports.style_guide_ingestion import StyleGuideStartStatus
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.style_guide_repository import (
    StyleGuideRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.temporal.starter import TemporalStyleGuideWorkflowStarter

router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()


@router.post("/style-guide", status_code=200)
async def handle_style_guide_eventarc(
    payload: StorageObjectData,
    ce_type: str = Header(
        ...,
        description="Type d'évènement CloudEvent (ex: google.cloud.storage.object.v1.finalized)",
    ),
) -> Response:
    """Point d'entrée Eventarc pour l'upload des guides de style."""
    if ce_type != "google.cloud.storage.object.v1.finalized":
        return Response(status_code=200)

    session_factory = get_session_factory()
    repo = StyleGuideRepository(session_factory)
    service = StyleGuideIngestionService(
        repo,
        style_guide_bucket_name=settings.gcp.style_guide_bucket_name,
        workflow_starter=TemporalStyleGuideWorkflowStarter(),
    )

    result = await service.start_from_storage_event(
        bucket_name=payload.bucket,
        file_name=payload.name,
    )
    if result.status is StyleGuideStartStatus.IGNORED:
        logger.info(
            "Style guide event ignored",
            reason=result.reason,
            bucket=payload.bucket,
            file_name=payload.name,
        )
    return Response(status_code=200)
