from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from temporalio.client import Client

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideIngestionConfigPort,
)
from factory_writer.application.services.style_guide_admin_service import (
    StyleGuideAdminService,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.core.config import Settings, get_settings
from factory_writer.infrastructure.database.repositories.style_guide_repository import (
    StyleGuideRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.infrastructure.gcp.storage_client import StorageClient
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.style_guide_ingestion.controller import (
    TemporalStyleGuideWorkflowController,
)
from factory_writer.temporal.style_guide_ingestion.starter import TemporalStyleGuideWorkflowStarter

STYLE_GUIDE_TAG = "Style Guide Admin"
MAX_STYLE_GUIDE_PDF_BYTES = 25 * 1024 * 1024


def _style_guide_config(settings: Settings) -> StyleGuideIngestionConfigPort:
    return StyleGuideIngestionConfigPort(
        bucket_name=settings.gcp.style_guide_bucket_name,
        draft_pack_prompt_name=settings.llm.style_guide_prompt_name,
        active_prompt_version=settings.llm.style_guide_prompt_version,
    )


async def get_style_guide_upload_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> StyleGuideIngestionService:
    settings = get_settings()
    return StyleGuideIngestionService(
        config=_style_guide_config(settings),
        repository=StyleGuideRepository(session_factory),
        storage=StorageClient(settings),
    )


async def get_style_guide_ingestion_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
    temporal_client: Client = Depends(get_temporal_client),
) -> StyleGuideIngestionService:
    settings = get_settings()
    return StyleGuideIngestionService(
        config=_style_guide_config(settings),
        repository=StyleGuideRepository(session_factory),
        workflow_starter=TemporalStyleGuideWorkflowStarter(temporal_client),
    )


async def get_style_guide_admin_read_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
) -> StyleGuideAdminService:
    return StyleGuideAdminService(
        repository=StyleGuideRepository(session_factory),
    )


async def get_style_guide_admin_action_service(
    session_factory: async_sessionmaker[AsyncSession] = Depends(get_session_factory),
    temporal_client: Client = Depends(get_temporal_client),
) -> StyleGuideAdminService:
    return StyleGuideAdminService(
        repository=StyleGuideRepository(session_factory),
        workflow_controller=TemporalStyleGuideWorkflowController(temporal_client),
    )
