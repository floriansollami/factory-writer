from __future__ import annotations

from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.offline_evaluation.contracts import OfflineEvaluationInput
from factory_writer.temporal.offline_evaluation.workflow import OfflineEvaluationWorkflow


def build_workflow_id(scope: str) -> str:
    return f"offline-eval-{scope}"


async def start_workflow(payload: OfflineEvaluationInput) -> str:
    client = await get_temporal_client()
    workflow_id = build_workflow_id(payload.evaluation_scope)
    await client.start_workflow(
        OfflineEvaluationWorkflow.run,
        payload,
        id=workflow_id,
        task_queue=TaskQueue.OFFLINE_EVALUATION.value,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        static_summary="Factory Writer offline evaluation",
        static_details=f"Offline evaluation scope {payload.evaluation_scope}",
    )
    return workflow_id
