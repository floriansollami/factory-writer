from __future__ import annotations

from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.domain.temporal_models import (
    OfflineEvaluationInput,
    ProductContextRef,
    SkuLifecycleInput,
    StyleGuideIngestionInput,
    TechnicalArchiveSignalInput,
)
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.task_queues import TaskQueue
from factory_writer.temporal.workflows.offline_evaluation import OfflineEvaluationWorkflow
from factory_writer.temporal.workflows.sku_lifecycle import SkuLifecycleWorkflow
from factory_writer.temporal.workflows.style_guide_ingestion import StyleGuideIngestionWorkflow


def build_sku_workflow_id(sku: str) -> str:
    return f"sku-lifecycle-{sku}"


def build_style_guide_workflow_id(source_id: str) -> str:
    return f"style-guide-ingestion-{source_id}"


def build_offline_eval_workflow_id(scope: str) -> str:
    return f"offline-eval-{scope}"


async def start_sku_lifecycle_workflow(product: ProductContextRef) -> str:
    client = await get_temporal_client()
    workflow_id = build_sku_workflow_id(product.sku)
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
    handle = client.get_workflow_handle(build_sku_workflow_id(sku))
    await handle.signal(SkuLifecycleWorkflow.technical_archive_received, payload)


async def start_style_guide_ingestion_workflow(payload: StyleGuideIngestionInput) -> str:
    client = await get_temporal_client()

    workflow_id = build_style_guide_workflow_id(payload.source_id)

    # "Mets un post-it dans la file d'attente STYLE_INGESTION qui dit
    # 'Il faut lancer le programme StyleGuideIngestionWorkflow avec la source 123'"

    await client.start_workflow(
        StyleGuideIngestionWorkflow.run,
        payload,  # le payload qu'a besoin le workflow
        id=workflow_id,
        task_queue=TaskQueue.STYLE_INGESTION.value,  # Le nom de la "file d'attente" où cette tâche va être déposée
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,  # si on appelle le workflow alors qu'il est actif, ne fait rien et renvoie l'ID de celui en cours
        static_summary="Factory Writer style guide ingestion",  # UI temporal
        static_details=f"Style guide source {payload.source_id}",  # UI temporal
    )
    return workflow_id


async def start_offline_evaluation_workflow(payload: OfflineEvaluationInput) -> str:
    client = await get_temporal_client()
    workflow_id = build_offline_eval_workflow_id(payload.evaluation_scope)
    await client.start_workflow(
        OfflineEvaluationWorkflow.run,
        payload,
        id=workflow_id,
        task_queue=TaskQueue.OFFLINE_EVAL.value,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        static_summary="Factory Writer offline evaluation",
        static_details=f"Offline evaluation scope {payload.evaluation_scope}",
    )
    return workflow_id
