from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker
from temporalio.worker.workflow_sandbox import SandboxedWorkflowRunner, SandboxRestrictions

from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.product_repository import (
    ProductRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.infrastructure.gcp.document_ai_client import DocumentAIClient
from factory_writer.infrastructure.llm.litellm_gateway import LiteLLMGateway
from factory_writer.infrastructure.llm.product_sheet_generator import LiteLLMProductSheetGenerator
from factory_writer.infrastructure.prompts.local_prompt_registry import LocalPromptRegistry
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.common.worker_runtime import (
    build_deployment_config,
    build_worker_identity,
)
from factory_writer.temporal.product_sheet_generation.activities import (
    ProductSheetGenerationActivities,
)
from factory_writer.temporal.product_sheet_generation.workflow import (
    ProductSheetGenerationWorkflow,
)
from factory_writer.temporal.sku_lifecycle.activities import ProductLifecycleActivities
from factory_writer.temporal.sku_lifecycle.starter import TemporalProductLifecycleWorkflowStarter
from factory_writer.temporal.sku_lifecycle.workflow import ProductLifecycleWorkflow
from factory_writer.temporal.technical_dossier_ingestion.activities import (
    TechnicalDossierActivities,
)
from factory_writer.temporal.technical_dossier_ingestion.workflow import (
    TechnicalDossierIngestionWorkflow,
)

logger = logging.getLogger(__name__)

_WORKFLOW_SANDBOX_RESTRICTIONS = SandboxRestrictions.default.with_passthrough_modules(
    "pydantic",
    "pydantic_core",
    "factory_writer.temporal.common.contracts",
    "factory_writer.temporal.sku_lifecycle.contracts",
    "factory_writer.temporal.technical_dossier_ingestion.contracts",
    "factory_writer.temporal.product_sheet_generation.contracts",
)


async def main() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    deployment_config = build_deployment_config("product-lifecycle")
    session_factory = get_session_factory()
    service = ProductTechnicalIngestionService(
        settings=settings,
        repository=ProductRepository(session_factory),
        workflow_starter=TemporalProductLifecycleWorkflowStarter(client),
        document_processor=DocumentAIClient(settings),
        prompt_registry=LocalPromptRegistry(),
        product_sheet_generator=LiteLLMProductSheetGenerator(
            settings,
            LiteLLMGateway(settings),
        ),
    )
    product_activities = ProductLifecycleActivities(service)
    technical_activities = TechnicalDossierActivities(service)
    product_sheet_activities = ProductSheetGenerationActivities(service)

    worker = Worker(
        client,
        task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
        workflows=[
            ProductLifecycleWorkflow,
            TechnicalDossierIngestionWorkflow,
            ProductSheetGenerationWorkflow,
        ],
        activities=[
            product_activities.load_canonical_product,
            product_activities.check_product_context_readiness,
            product_activities.create_product_context_snapshot,
            technical_activities.prepare_technical_ingestion_run,
            technical_activities.classify_technical_sources,
            technical_activities.persist_classification_results,
            technical_activities.extract_technical_fact_candidates,
            technical_activities.persist_technical_fact_candidates,
            technical_activities.validate_technical_facts,
            technical_activities.promote_technical_facts,
            technical_activities.finalize_technical_review,
            technical_activities.notify_technical_facts_ready,
            technical_activities.mark_technical_ingestion_failed,
            product_sheet_activities.generate_product_sheet_candidate,
            product_sheet_activities.persist_product_sheet_generation_result,
            product_sheet_activities.mark_product_sheet_generation_failed,
        ],
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=build_worker_identity("product-lifecycle"),
        workflow_runner=SandboxedWorkflowRunner(
            restrictions=_WORKFLOW_SANDBOX_RESTRICTIONS,
        ),
    )

    logger.info("Temporal worker started", extra={"worker": "product-lifecycle"})
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
