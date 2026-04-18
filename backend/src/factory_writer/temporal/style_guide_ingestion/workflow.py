from __future__ import annotations

import asyncio
import uuid

from temporalio import workflow

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideChunkPersistResult,
    StyleGuideIngestionInput,
    StyleGuideLayoutJobResult,
    StyleGuideLayoutParseResult,
)
from factory_writer.temporal.common.config import (
    DB_ACTIVITY_TIMEOUT,
    DB_RETRY_POLICY,
    DOC_AI_POLL_INTERVAL,
    DOC_AI_RETRY_POLICY,
    DOC_AI_START_RETRY_POLICY,
    HUMAN_APPROVAL_TIMEOUT,
    LLM_RETRY_POLICY,
    LONG_ACTIVITY_TIMEOUT,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StyleGuideApprovalSignalInput,
    StyleGuideIngestionOutput,
    StyleGuideWorkflowState,
    StylePackDraftResult,
)

# On utilise imports_passed_through pour empêcher la Sandbox Temporal d'analyser le code des Activités.
# (Les activités importent SQLAlchemy, Google Cloud, etc. qui feraient crasher la sandbox déterministe).
with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.style_guide_ingestion.activities import StyleGuideActivities


_APPROVAL_TIMEOUT_MESSAGE = "Validation humaine du guide de style expirée."
_APPROVAL_REJECTED_MESSAGE = "Guide de style rejeté lors de la validation humaine."
_WORKFLOW_FAILURE_MESSAGE = (
    "Ingestion du guide de style interrompue. Voir l'historique Temporal pour le détail."
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
            await workflow.execute_activity_method(
                StyleGuideActivities.mark_source_in_progress,
                payload.source_id,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                # le temps maximum autorisé pour qu'un Worker exécute l'activité de bout en bout
                start_to_close_timeout=DB_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            layout_job: StyleGuideLayoutJobResult = await workflow.execute_activity_method(
                StyleGuideActivities.start_docai_job,
                payload,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DOC_AI_START_RETRY_POLICY,
            )

            layout_result = await self._wait_for_docai_result(layout_job)

            chunk_result: StyleGuideChunkPersistResult = await workflow.execute_activity_method(
                StyleGuideActivities.persist_fragments,
                layout_result,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=DB_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            draft_pack: StylePackDraftResult = await workflow.execute_activity_method(
                StyleGuideActivities.generate_draft_pack,
                chunk_result,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                schedule_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=LLM_RETRY_POLICY,
            )
            self.state.draft_pack_id = draft_pack.draft_pack_id
            self.state.status = WorkflowExecutionStatus.WAITING_FOR_STYLE_APPROVAL

            approval_timed_out = False
            try:
                await workflow.wait_condition(
                    lambda: self.state.approved is not None,
                    timeout=HUMAN_APPROVAL_TIMEOUT,
                )
            except TimeoutError:
                approval_timed_out = True
                self.state.approved = False

            if self.state.approved is not True:
                self.state.status = WorkflowExecutionStatus.FAILED
                message = (
                    _APPROVAL_TIMEOUT_MESSAGE if approval_timed_out else _APPROVAL_REJECTED_MESSAGE
                )
                await self._mark_source_failed(payload.source_id, message)
                return StyleGuideIngestionOutput(
                    status="approval_timeout" if approval_timed_out else "rejected",
                    pack_id=None,
                )

            promoted_pack_id: str = await workflow.execute_activity_method(
                StyleGuideActivities.promote_pack,
                draft_pack,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=DB_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            self.state.status = WorkflowExecutionStatus.PUBLISHED
            return StyleGuideIngestionOutput(status="success", pack_id=promoted_pack_id)

        except asyncio.CancelledError:
            self.state.status = WorkflowExecutionStatus.FAILED
            await self._mark_source_failed(payload.source_id, _WORKFLOW_FAILURE_MESSAGE)
            raise
        except Exception:
            self.state.status = WorkflowExecutionStatus.FAILED
            await self._mark_source_failed(payload.source_id, _WORKFLOW_FAILURE_MESSAGE)
            raise

    async def _wait_for_docai_result(
        self,
        layout_job: StyleGuideLayoutJobResult,
    ) -> StyleGuideLayoutParseResult:
        while True:
            layout_result: (
                StyleGuideLayoutParseResult | None
            ) = await workflow.execute_activity_method(
                StyleGuideActivities.check_docai_job,
                layout_job,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DOC_AI_RETRY_POLICY,
            )
            if layout_result is not None:
                return layout_result

            await workflow.sleep(DOC_AI_POLL_INTERVAL)

    async def _mark_source_failed(
        self,
        source_id: uuid.UUID,
        message: str,
    ) -> None:
        try:
            await workflow.execute_activity_method(
                StyleGuideActivities.mark_source_failed,
                args=[source_id, message],
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=DB_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
        except Exception as cleanup_error:
            workflow.logger.error(
                "StyleGuideIngestionWorkflow.cleanup_failed",
                cleanup_error_type=type(cleanup_error).__name__,
            )
