from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from factory_writer.application.ports.style_guide_ingestion import StyleGuideIngestionConfigPort
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.style_guide_repository import (
    StyleGuideRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.infrastructure.gcp.document_ai_client import DocumentAIClient
from factory_writer.infrastructure.gcp.storage_client import StorageClient
from factory_writer.infrastructure.llm import LiteLLMGateway, LiteLLMStyleGuideDraftPackGenerator
from factory_writer.infrastructure.prompts.local_prompt_registry import (
    LocalStyleGuidePromptRegistry,
)
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.common.interceptors import DomainErrorInterceptor
from factory_writer.temporal.common.worker_runtime import (
    build_deployment_config,
    build_worker_identity,
)
from factory_writer.temporal.style_guide_ingestion.activities import StyleGuideActivities
from factory_writer.temporal.style_guide_ingestion.workflow import StyleGuideIngestionWorkflow

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    deployment_config = build_deployment_config("style-guide-ingestion")

    session_factory = get_session_factory()
    llm_gateway = LiteLLMGateway(settings)
    service = StyleGuideIngestionService(
        config=StyleGuideIngestionConfigPort(
            bucket_name=settings.gcp.style_guide_bucket_name,
            draft_pack_prompt_name=settings.llm.style_guide_prompt_name,
            active_prompt_version=settings.llm.style_guide_prompt_version,
        ),
        repository=StyleGuideRepository(session_factory),
        storage=StorageClient(settings),
        document_parser=DocumentAIClient(settings),
        prompt_registry=LocalStyleGuidePromptRegistry(),
        draft_pack_generator=LiteLLMStyleGuideDraftPackGenerator(settings, llm_gateway),
    )
    activities = StyleGuideActivities(service)

    worker = Worker(
        client,
        task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
        workflows=[StyleGuideIngestionWorkflow],
        activities=[
            activities.mark_source_in_progress,
            activities.mark_source_failed,
            activities.start_docai_job,
            activities.check_docai_job,
            activities.persist_fragments,
            activities.generate_draft_pack,
            activities.promote_pack,
        ],
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=build_worker_identity("style-guide-ingestion"),
        interceptors=[DomainErrorInterceptor()],
    )

    logger.info("Temporal worker started", extra={"worker": "style-guide-ingestion"})
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
