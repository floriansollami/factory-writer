from __future__ import annotations

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.offline_evaluation.contracts import OfflineEvaluationInput
from factory_writer.temporal.offline_evaluation.workflow import OfflineEvaluationWorkflow


class TemporalOfflineEvaluationWorkflowStarter:
    def __init__(self, temporal_client: Client):
        self._client = temporal_client

    async def start_offline_evaluation(self, payload: OfflineEvaluationInput) -> str:
        try:
            workflow_id = f"offline-eval-{payload.evaluation_scope}"

            await self._client.start_workflow(
                OfflineEvaluationWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=TaskQueue.OFFLINE_EVALUATION.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer offline evaluation",
                static_details=f"Offline evaluation scope {payload.evaluation_scope}",
            )
            return workflow_id
        except Exception as exc:
            raise RuntimeError(
                f"Impossible de démarrer le workflow Temporal Offline Evaluation: {str(exc)}"
            ) from exc
