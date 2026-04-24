from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.core.config import get_settings
from factory_writer.infrastructure.database.repositories.product_repository import (
    ProductRepository,
)
from factory_writer.infrastructure.database.session import get_session_factory
from factory_writer.infrastructure.gcp.document_ai_client import DocumentAIClient
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.common.worker_runtime import (
    build_deployment_config,
    build_worker_identity,
)
from factory_writer.temporal.sku_lifecycle.activities import ProductLifecycleActivities
from factory_writer.temporal.sku_lifecycle.workflow import ProductLifecycleWorkflow
from factory_writer.temporal.technical_dossier_ingestion.activities import (
    TechnicalDossierActivities,
)
from factory_writer.temporal.technical_dossier_ingestion.workflow import (
    TechnicalDossierIngestionWorkflow,
)

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    deployment_config = build_deployment_config("product-lifecycle")
    session_factory = get_session_factory()
    service = ProductTechnicalIngestionService(
        settings=settings,
        repository=ProductRepository(session_factory),
        document_ai=DocumentAIClient(settings),
    )
    product_activities = ProductLifecycleActivities(service)
    technical_activities = TechnicalDossierActivities(service)

    worker = Worker(
        client,
        task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
        workflows=[ProductLifecycleWorkflow, TechnicalDossierIngestionWorkflow],
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
            technical_activities.check_technical_review_completion,
            technical_activities.mark_technical_ingestion_failed,
        ],
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=build_worker_identity("product-lifecycle"),
    )

    logger.info("Temporal worker started", extra={"worker": "product-lifecycle"})
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
