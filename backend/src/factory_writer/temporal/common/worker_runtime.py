from __future__ import annotations

from temporalio.common import VersioningBehavior
from temporalio.worker import WorkerDeploymentConfig, WorkerDeploymentVersion

from factory_writer.core.config import get_settings


def build_deployment_config(worker_name: str) -> WorkerDeploymentConfig | None:
    settings = get_settings()
    if settings.temporal.build_id is None:
        return None

    return WorkerDeploymentConfig(
        version=WorkerDeploymentVersion(
            deployment_name=f"{settings.temporal.deployment_name}-{worker_name}",
            build_id=settings.temporal.build_id,
        ),
        use_worker_versioning=True,
        default_versioning_behavior=VersioningBehavior.AUTO_UPGRADE,
    )


def build_worker_identity(worker_name: str) -> str:
    settings = get_settings()
    return f"{settings.temporal.deployment_name}-{worker_name}"
