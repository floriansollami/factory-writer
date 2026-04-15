from __future__ import annotations

import asyncio
import logging

from factory_writer.core.config import get_settings
from factory_writer.temporal.common.worker_roles import WorkerRole, parse_worker_role
from factory_writer.temporal.offline_evaluation.worker import (
    main as run_offline_evaluation_worker,
)
from factory_writer.temporal.sku_lifecycle.worker import (
    main as run_sku_lifecycle_worker,
)
from factory_writer.temporal.style_guide_ingestion.worker import (
    main as run_style_guide_ingestion_worker,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def main() -> None:
    settings = get_settings()
    role = parse_worker_role(settings.temporal.worker_role)

    logger.info("Temporal worker dispatcher starting", extra={"role": role.value})

    if role == WorkerRole.SKU_LIFECYCLE:
        await run_sku_lifecycle_worker()
        return

    if role == WorkerRole.STYLE_GUIDE_INGESTION:
        await run_style_guide_ingestion_worker()
        return

    if role == WorkerRole.OFFLINE_EVALUATION:
        await run_offline_evaluation_worker()
        return

    msg = f"Unsupported worker role after parsing: {role.value}"
    raise RuntimeError(msg)


if __name__ == "__main__":
    asyncio.run(main())
