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
from factory_writer.temporal.offline_evaluation.activities import (
    load_evaluation_batch,
    promote_generation_recipe_candidate,
    run_vertex_prompt_evaluation,
)
from factory_writer.temporal.offline_evaluation.workflow import OfflineEvaluationWorkflow

logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    client = await get_temporal_client()
    deployment_config = build_deployment_config("offline-evaluation")

    worker = Worker(
        client,
        task_queue=TaskQueue.OFFLINE_EVALUATION.value,
        workflows=[OfflineEvaluationWorkflow],
        activities=[
            load_evaluation_batch,
            run_vertex_prompt_evaluation,
            promote_generation_recipe_candidate,
        ],
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=build_worker_identity("offline-evaluation"),
    )

    logger.info("Temporal worker started", extra={"worker": "offline-evaluation"})
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
