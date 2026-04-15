from __future__ import annotations

from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.sku_lifecycle.contracts import (
    ProductContextRef,
    SkuLifecycleInput,
    TechnicalArchiveSignalInput,
)
from factory_writer.temporal.sku_lifecycle.workflow import SkuLifecycleWorkflow


def build_workflow_id(sku: str) -> str:
    return f"sku-lifecycle-{sku}"


async def start_workflow(product: ProductContextRef) -> str:
    client = await get_temporal_client()
    workflow_id = build_workflow_id(product.sku)
    await client.start_workflow(
        SkuLifecycleWorkflow.run,
        SkuLifecycleInput(product=product),
        id=workflow_id,
        task_queue=TaskQueue.SKU_LIFECYCLE.value,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        static_summary="Factory Writer SKU lifecycle",
        static_details=f"Lifecycle orchestration for SKU {product.sku}",
    )
    return workflow_id


async def signal_technical_archive_received(
    sku: str,
    payload: TechnicalArchiveSignalInput,
) -> None:
    client = await get_temporal_client()
    handle = client.get_workflow_handle(build_workflow_id(sku))
    await handle.signal(SkuLifecycleWorkflow.technical_archive_received, payload)
