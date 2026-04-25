from __future__ import annotations

import asyncio

import structlog
from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from factory_writer.application.ports.style_guide_ingestion import StyleGuideIngestionConfigPort
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.product_repository import (
    ProductRepository,
)
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
from factory_writer.temporal.sku_lifecycle.starter import TemporalProductLifecycleWorkflowStarter
from factory_writer.temporal.style_guide_ingestion.activities import StyleGuideActivities
from factory_writer.temporal.style_guide_ingestion.workflow import StyleGuideIngestionWorkflow

logger = structlog.get_logger(__name__)

_WORKFLOW_SANDBOX_RESTRICTIONS = SandboxRestrictions.default.with_passthrough_modules(
    "pydantic",
    "pydantic_core",
    "factory_writer.application.ports.style_guide_ingestion",
    "factory_writer.temporal.common.contracts",
    "factory_writer.temporal.style_guide_ingestion.contracts",
)


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
    product_notification_service = ProductTechnicalIngestionService(
        settings=settings,
        repository=ProductRepository(session_factory),
        workflow_starter=TemporalProductLifecycleWorkflowStarter(client),
    )
    activities = StyleGuideActivities(service, product_notification_service)

    worker = Worker(
        client,
        task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
        workflows=[StyleGuideIngestionWorkflow],
        activities=[
            activities.mark_ingestion_failed,
            activities.parse_docai_document,
            activities.generate_draft_pack,
            activities.finalize_style_pack_approval,
            activities.notify_style_pack_activated,
            activities.finalize_style_pack_rejection,
        ],
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=build_worker_identity("style-guide-ingestion"),
        interceptors=[DomainErrorInterceptor()],
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=_WORKFLOW_SANDBOX_RESTRICTIONS,
        ),
    )

    logger.info(
        "temporal.worker.started",
        worker="style-guide-ingestion",
        task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
    )
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
