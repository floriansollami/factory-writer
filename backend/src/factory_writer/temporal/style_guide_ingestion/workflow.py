from __future__ import annotations

from temporalio import workflow
from temporalio.exceptions import ActivityError

from factory_writer.temporal.common.config import (
    DB_RETRY_POLICY,
    DOC_AI_RETRY_POLICY,
    HUMAN_APPROVAL_TIMEOUT,
    LLM_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StyleGuideApprovalSignalInput,
    StyleGuideChunkPersistResult,
    StyleGuideIngestionInput,
    StyleGuideIngestionOutput,
    StyleGuideLayoutParseResult,
    StyleGuideWorkflowState,
    StylePackDraftResult,
)

# On utilise imports_passed_through pour empêcher la Sandbox Temporal d'analyser le code des Activités.
# (Les activités importent SQLAlchemy, Google Cloud, etc. qui feraient crasher la sandbox déterministe).
with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.style_guide_ingestion.activities import StyleGuideActivities


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
            await workflow.execute_activity_method(
                StyleGuideActivities.mark_source_in_progress,
                payload.source_id,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            layout_result: StyleGuideLayoutParseResult = await workflow.execute_activity_method(
                StyleGuideActivities.parse_layout,
                payload,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                heartbeat_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DOC_AI_RETRY_POLICY,
            )

            chunk_result: StyleGuideChunkPersistResult = await workflow.execute_activity_method(
                StyleGuideActivities.persist_fragments,
                layout_result,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            draft_pack: StylePackDraftResult = await workflow.execute_activity_method(
                StyleGuideActivities.generate_draft_pack,
                chunk_result,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
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

            promoted_pack_id: str = await workflow.execute_activity_method(
                StyleGuideActivities.promote_pack,
                draft_pack,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            self.state.status = WorkflowExecutionStatus.PUBLISHED
            return StyleGuideIngestionOutput(status="success", pack_id=promoted_pack_id)

        except ActivityError:
            self.state.status = WorkflowExecutionStatus.FAILED
            await workflow.execute_activity_method(
                StyleGuideActivities.mark_source_failed,
                payload.source_id,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            raise
