from __future__ import annotations

import asyncio
import logging

from temporalio.worker import Worker

from factory_writer.core.config import get_settings
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.common.worker_runtime import (
    build_deployment_config,
    build_worker_identity,
)
from factory_writer.temporal.sku_lifecycle.activities import (
    evaluate_publish_gate,
    extract_archive_and_facts,
    generate_claim_plan,
    generate_final_draft,
    generate_redaction_plan,
    load_prompt_package,
    load_signal_snapshot,
    load_style_pack,
    publish_generated_content,
    review_and_rewrite,
)
from factory_writer.temporal.sku_lifecycle.workflow import SkuLifecycleWorkflow

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    deployment_config = build_deployment_config("sku-lifecycle")

    worker = Worker(
        client,
        task_queue=TaskQueue.SKU_LIFECYCLE.value,
        workflows=[SkuLifecycleWorkflow],
        activities=[
            extract_archive_and_facts,
            load_signal_snapshot,
            load_style_pack,
            load_prompt_package,
            generate_claim_plan,
            generate_redaction_plan,
            generate_final_draft,
            review_and_rewrite,
            evaluate_publish_gate,
            publish_generated_content,
        ],
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=build_worker_identity("sku-lifecycle"),
    )

    logger.info("Temporal worker started", extra={"worker": "sku-lifecycle"})
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
