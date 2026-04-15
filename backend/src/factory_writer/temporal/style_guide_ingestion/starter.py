from __future__ import annotations

from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.application.ports.style_guide_ingestion import StyleGuideWorkflowStarterPort
from factory_writer.domain.exceptions import WorkflowStartError
from factory_writer.temporal.client import get_temporal_client
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.style_guide_ingestion.contracts import StyleGuideIngestionInput
from factory_writer.temporal.style_guide_ingestion.workflow import StyleGuideIngestionWorkflow


def build_workflow_id(source_id: str) -> str:
    return f"style-guide-ingestion-{source_id}"


async def start_workflow(payload: StyleGuideIngestionInput) -> str:
    client = await get_temporal_client()
    workflow_id = build_workflow_id(payload.source_id)
    await client.start_workflow(
        StyleGuideIngestionWorkflow.run,
        payload,
        id=workflow_id,
        task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
        id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
        static_summary="Factory Writer style guide ingestion",
        static_details=f"Style guide source {payload.source_id}",
    )
    return workflow_id


class TemporalStyleGuideWorkflowStarter(StyleGuideWorkflowStarterPort):
    async def start_style_guide_ingestion(self, payload: StyleGuideIngestionInput) -> str:
        try:
            return await start_workflow(payload)
        except Exception as exc:
            raise WorkflowStartError(str(exc)) from exc
