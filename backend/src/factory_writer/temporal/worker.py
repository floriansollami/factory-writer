from __future__ import annotations

import asyncio

import structlog

from factory_writer.core.config import get_settings
from factory_writer.core.logger import setup_logging
from factory_writer.temporal.common.worker_roles import WorkerRole, parse_worker_role
from factory_writer.temporal.sku_lifecycle.worker import (
    main as run_product_lifecycle_worker,
)
from factory_writer.temporal.style_guide_ingestion.worker import (
    main as run_style_guide_ingestion_worker,
)

setup_logging()
logger = structlog.get_logger(__name__)


async def main() -> None:
    settings = get_settings()
    role = parse_worker_role(settings.temporal.worker_role)

    logger.info(
        "temporal.worker.dispatcher.starting",
        role=role.value,
    )

    match role:
        case WorkerRole.PRODUCT_LIFECYCLE:
            await run_product_lifecycle_worker()
        case WorkerRole.STYLE_GUIDE_INGESTION:
            await run_style_guide_ingestion_worker()


if __name__ == "__main__":
    asyncio.run(main())
