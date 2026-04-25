from __future__ import annotations

import uuid

from temporalio import workflow

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideIngestionInput,
    StyleGuideLayoutParseResult,
)
from factory_writer.temporal.common.config import (
    DB_ACTIVITY_TIMEOUT,
    DB_RETRY_POLICY,
    DOC_AI_RETRY_POLICY,
    LLM_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StyleGuideDraftStylePackResult,
    StyleGuideFinalDecision,
    StyleGuideIngestionOutput,
    StyleGuideWorkflowState,
)

# On utilise imports_passed_through pour empêcher la Sandbox Temporal d'analyser le code des Activités.
# (Les activités importent SQLAlchemy, Google Cloud, etc. qui feraient crasher la sandbox déterministe).
with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.style_guide_ingestion.activities import StyleGuideActivities


_WORKFLOW_FAILURE_MESSAGE = (
    "Ingestion du guide de style interrompue. Voir l'historique Temporal pour le détail."
)


@workflow.defn(name="StyleGuideIngestionWorkflow")
class StyleGuideIngestionWorkflow:
    def __init__(self) -> None:
        self.state = StyleGuideWorkflowState()

    @workflow.query
    def get_state(self) -> StyleGuideWorkflowState:
        return self.state

    @workflow.update
    def approve_style_pack(self, style_pack_id: str) -> None:
        self._record_final_decision(
            expected_style_pack_id=style_pack_id,
            decision=StyleGuideFinalDecision.APPROVE,
        )

    @workflow.update
    def reject_style_pack(self, style_pack_id: str) -> None:
        self._record_final_decision(
            expected_style_pack_id=style_pack_id,
            decision=StyleGuideFinalDecision.REJECT,
        )

    @workflow.run
    async def run(self, payload: StyleGuideIngestionInput) -> StyleGuideIngestionOutput:
        self.state.ingestion_run_id = str(payload.ingestion_run_id)

        # Temporal permet d'interroger (Query) l'état interne d'un workflow pendant qu'il tourne.
        self.state.status = WorkflowExecutionStatus.BUILDING_CONTEXT

        try:
            layout_result: StyleGuideLayoutParseResult = await workflow.execute_activity_method(
                StyleGuideActivities.parse_docai_document,
                payload,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DOC_AI_RETRY_POLICY,
            )

            draft_style_pack: StyleGuideDraftStylePackResult = (
                await workflow.execute_activity_method(
                    StyleGuideActivities.generate_draft_pack,
                    layout_result,
                    task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                    start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                    retry_policy=LLM_RETRY_POLICY,
                )
            )

            self.state.draft_style_pack_id = draft_style_pack.draft_style_pack_id
            self.state.status = WorkflowExecutionStatus.PENDING_EDITOR_REVIEW

            await workflow.wait_condition(lambda: self.state.final_decision is not None)

            final_decision = self.state.final_decision

            if final_decision == StyleGuideFinalDecision.APPROVE:
                await workflow.execute_activity_method(
                    StyleGuideActivities.finalize_style_pack_approval,
                    draft_style_pack.draft_style_pack_id,
                    task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                    start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                    retry_policy=DB_RETRY_POLICY,
                )
                await workflow.execute_activity_method(
                    StyleGuideActivities.notify_style_pack_activated,
                    draft_style_pack.draft_style_pack_id,
                    task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                    start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                    retry_policy=DB_RETRY_POLICY,
                )
                self.state.status = WorkflowExecutionStatus.PUBLISHED
                return StyleGuideIngestionOutput(
                    status="completed",
                    style_pack_id=draft_style_pack.draft_style_pack_id,
                )

            await workflow.execute_activity_method(
                StyleGuideActivities.finalize_style_pack_rejection,
                draft_style_pack.draft_style_pack_id,
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

            return StyleGuideIngestionOutput(
                status="rejected",
                style_pack_id=draft_style_pack.draft_style_pack_id,
            )
        except Exception:
            self.state.status = WorkflowExecutionStatus.FAILED
            await self._mark_ingestion_failed(payload.ingestion_run_id, _WORKFLOW_FAILURE_MESSAGE)
            raise

    def _record_final_decision(
        self,
        *,
        expected_style_pack_id: str,
        decision: StyleGuideFinalDecision,
    ) -> None:
        if self.state.status != WorkflowExecutionStatus.PENDING_EDITOR_REVIEW:
            raise RuntimeError("Le workflow n'est pas en attente de validation éditoriale.")
        if self.state.draft_style_pack_id is None:
            raise RuntimeError("Aucun pack candidat n'est associé à ce workflow.")
        if expected_style_pack_id != self.state.draft_style_pack_id:
            raise RuntimeError("Le pack ciblé ne correspond pas au draft courant du workflow.")
        if self.state.final_decision is not None:
            raise RuntimeError("Une décision finale a déjà été enregistrée pour ce workflow.")

        self.state.final_decision = decision
        self.state.decision_received_at = workflow.now().isoformat()

    async def _mark_ingestion_failed(
        self,
        ingestion_run_id: uuid.UUID,
        message: str,
    ) -> None:
        try:
            await workflow.execute_activity_method(
                StyleGuideActivities.mark_ingestion_failed,
                args=[ingestion_run_id, message],
                task_queue=TaskQueue.STYLE_GUIDE_INGESTION.value,
                start_to_close_timeout=DB_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
        except Exception as cleanup_error:
            workflow.logger.error(
                "StyleGuideIngestionWorkflow.cleanup_failed cleanup_error_type=%s",
                type(cleanup_error).__name__,
            )
