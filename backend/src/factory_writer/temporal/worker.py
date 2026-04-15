from __future__ import annotations

import asyncio
import logging

from temporalio.common import VersioningBehavior
from temporalio.worker import Worker, WorkerDeploymentConfig, WorkerDeploymentVersion

from factory_writer.core.config import get_settings
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.registry import get_worker_registration
from factory_writer.temporal.worker_roles import parse_worker_role

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def _build_deployment_config(role_name: str) -> WorkerDeploymentConfig | None:
    settings = get_settings()
    build_id = settings.temporal.build_id
    deployment_name = settings.temporal.deployment_name

    if build_id is None:
        return None

    return WorkerDeploymentConfig(
        version=WorkerDeploymentVersion(
            deployment_name=f"{deployment_name}-{role_name}",
            build_id=build_id,
        ),
        use_worker_versioning=True,
        default_versioning_behavior=VersioningBehavior.AUTO_UPGRADE,
    )


async def main() -> None:
    settings = get_settings()
    role = parse_worker_role(settings.temporal.worker_role)
    registration = get_worker_registration(role)
    client = await get_temporal_client()
    deployment_config = _build_deployment_config(role.value)

    worker = Worker(
        client,
        task_queue=registration.task_queue.value,
        workflows=list(registration.workflows),
        activities=list(registration.activities),
        build_id=settings.temporal.build_id,
        use_worker_versioning=deployment_config is not None,
        deployment_config=deployment_config,
        identity=f"{settings.temporal.deployment_name}-{role.value}",
    )

    logger.info(
        "Temporal worker started",
        extra={
            "role": role.value,
            "task_queue": registration.task_queue.value,
            "description": registration.description,
        },
    )

    # "Hé, tu as du boulot dans la file XXX ?". (demande en boucle à Temporal)
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
