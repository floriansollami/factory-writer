from __future__ import annotations

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideIngestionInput,
    StyleGuideWorkflowStarterPort,
)
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.style_guide_ingestion.workflow import StyleGuideIngestionWorkflow


class TemporalStyleGuideWorkflowStarter(StyleGuideWorkflowStarterPort):
    def __init__(self, temporal_client: Client):
        self._client = temporal_client

    async def start_style_guide_ingestion(self, payload: StyleGuideIngestionInput) -> str:
        try:
            workflow_id = f"style-guide-ingestion-{payload.source_id}"

            await self._client.start_workflow(
                StyleGuideIngestionWorkflow.run,
                payload,
                id=workflow_id,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer style guide ingestion",
                static_details=f"Style guide source {payload.source_id}",
            )
            return workflow_id

        except Exception as exc:
            raise RuntimeError(f"Impossible de démarrer le workflow Temporal: {str(exc)}") from exc
