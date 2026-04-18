from __future__ import annotations

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.sku_lifecycle.contracts import (
    ProductContextRef,
    SkuLifecycleInput,
    TechnicalArchiveSignalInput,
)
from factory_writer.temporal.sku_lifecycle.workflow import SkuLifecycleWorkflow


class TemporalSkuLifecycleWorkflowStarter:
    def __init__(self, temporal_client: Client):
        self._client = temporal_client

    async def start_sku_lifecycle(self, product: ProductContextRef) -> str:
        try:
            workflow_id = f"sku-lifecycle-{product.sku}"
            await self._client.start_workflow(
                SkuLifecycleWorkflow.run,
                SkuLifecycleInput(product=product),
                id=workflow_id,
                task_queue=TaskQueue.SKU_LIFECYCLE.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer SKU lifecycle",
                static_details=f"Lifecycle orchestration for SKU {product.sku}",
            )
            return workflow_id
        except Exception as exc:
            raise RuntimeError(
                f"Impossible de démarrer le workflow Temporal SKU Lifecycle: {str(exc)}"
            ) from exc

    async def signal_technical_archive_received(
        self,
        sku: str,
        payload: TechnicalArchiveSignalInput,
    ) -> None:
        try:
            handle = self._client.get_workflow_handle(f"sku-lifecycle-{sku}")
            await handle.signal(SkuLifecycleWorkflow.technical_archive_received, payload)
        except Exception as exc:
            raise RuntimeError(f"Impossible d'envoyer le signal au workflow: {str(exc)}") from exc
