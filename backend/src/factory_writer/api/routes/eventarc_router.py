import structlog
from fastapi import APIRouter, Depends, Header, Response
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client

from factory_writer.api.routes.schemas.eventarc_payload import StorageObjectData
from factory_writer.application.ports.style_guide_ingestion import StyleGuideIngestionConfigPort
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.style_guide_repository import (
    StyleGuideRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.starter import TemporalStyleGuideWorkflowStarter

router = APIRouter()
logger = structlog.get_logger(__name__)
settings = get_settings()


async def get_style_guide_ingestion_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
    temporal_client: Client = Depends(get_temporal_client),
) -> StyleGuideIngestionService:
    repo = StyleGuideRepository(session_factory)
    starter = TemporalStyleGuideWorkflowStarter(temporal_client)

    return StyleGuideIngestionService(
        config=StyleGuideIngestionConfigPort(
            bucket_name=settings.gcp.style_guide_bucket_name,
            draft_pack_prompt_name=settings.llm.style_guide_prompt_name,
            active_prompt_version=settings.llm.style_guide_prompt_version,
        ),
        repository=repo,
        workflow_starter=starter,
    )


@router.post("/style-guide", status_code=200)
async def handle_style_guide_eventarc(
    payload: StorageObjectData,
    ce_type: str = Header(...),
    service: StyleGuideIngestionService = Depends(get_style_guide_ingestion_service),
) -> Response:
    if ce_type != "google.cloud.storage.object.v1.finalized":
        return Response(status_code=200)

    target_uri = f"gs://{payload.bucket}/{payload.name}"

    try:
        await service.start_from_storage_event(
            bucket_name=payload.bucket,
            file_name=payload.name,
            target_uri=target_uri,
        )
    except ValueError as exc:
        logger.info(
            "style_guide_event_ignored",
            reason=str(exc),
            bucket=payload.bucket,
            file_name=payload.name,
        )
    except RuntimeError as exc:
        if "already ingested or in progress" not in str(exc):
            raise
        logger.info(
            "style_guide_event_duplicate_ignored",
            reason=str(exc),
            bucket=payload.bucket,
            file_name=payload.name,
        )

    return Response(status_code=200)
