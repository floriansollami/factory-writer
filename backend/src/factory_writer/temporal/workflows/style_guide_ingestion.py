from __future__ import annotations

from temporalio import workflow

from factory_writer.domain.temporal_models import (
    StyleGuideApprovalSignalInput,
    StyleGuideIngestionInput,
    StyleGuideIngestionOutput,
    StyleGuideWorkflowState,
    WorkflowExecutionStatus,
)
from factory_writer.temporal.activity_options import (
    DB_RETRY_POLICY,
    DOC_AI_RETRY_POLICY,
    HUMAN_APPROVAL_TIMEOUT,
    LLM_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
)
from factory_writer.temporal.task_queues import TaskQueue

with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.activities.style_guide_activities import (
        generate_style_pack_draft_activity,
        mark_style_source_failed_activity,
        mark_style_source_in_progress_activity,
        persist_style_fragments_activity,
        promote_style_pack_activity,
        trigger_style_layout_parse_activity,
    )


@workflow.defn(name="StyleGuideIngestionWorkflow")
class StyleGuideIngestionWorkflow:
    def __init__(self) -> None:
        self.state = StyleGuideWorkflowState()

    @workflow.signal
    def approve_pack(self, payload: StyleGuideApprovalSignalInput) -> None:
        self.state.approved = payload.approved

    @workflow.query
    def get_state(self) -> StyleGuideWorkflowState:
        return self.state

    @workflow.run
    async def run(self, payload: StyleGuideIngestionInput) -> StyleGuideIngestionOutput:
        workflow.logger.info(
            "StyleGuideIngestionWorkflow.started",
            source_id=payload.source_id,
            file_uri=payload.file_uri,
        )

        try:
            await workflow.execute_activity(
                mark_style_source_in_progress_activity,
                payload.source_id,
                task_queue=TaskQueue.STYLE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            layout_result = await workflow.execute_activity(
                trigger_style_layout_parse_activity,
                payload,
                task_queue=TaskQueue.STYLE_INGESTION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DOC_AI_RETRY_POLICY,
            )

            chunk_result = await workflow.execute_activity(
                persist_style_fragments_activity,
                layout_result,
                task_queue=TaskQueue.STYLE_INGESTION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            draft_pack = await workflow.execute_activity(
                generate_style_pack_draft_activity,
                chunk_result,
                task_queue=TaskQueue.STYLE_INGESTION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=LLM_RETRY_POLICY,
            )
            self.state.draft_pack_id = draft_pack.draft_pack_id
            self.state.status = WorkflowExecutionStatus.WAITING_FOR_STYLE_APPROVAL

            await workflow.wait_condition(
                lambda: self.state.approved is not None,
                timeout=HUMAN_APPROVAL_TIMEOUT,
            )

            if self.state.approved is not True:
                self.state.status = WorkflowExecutionStatus.FAILED
                return StyleGuideIngestionOutput(status="rejected", pack_id=None)

            promoted_pack_id = await workflow.execute_activity(
                promote_style_pack_activity,
                draft_pack,
                task_queue=TaskQueue.STYLE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            self.state.status = WorkflowExecutionStatus.PUBLISHED
            return StyleGuideIngestionOutput(status="success", pack_id=promoted_pack_id)

        except Exception:
            self.state.status = WorkflowExecutionStatus.FAILED
            await workflow.execute_activity(
                mark_style_source_failed_activity,
                payload.source_id,
                task_queue=TaskQueue.STYLE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            raise
