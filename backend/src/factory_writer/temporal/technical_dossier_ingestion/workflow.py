from __future__ import annotations

from contextlib import suppress

from temporalio import workflow

from factory_writer.temporal.common.config import (
    DB_RETRY_POLICY,
    DOC_AI_RETRY_POLICY,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.technical_dossier_ingestion.contracts import (
    CheckTechnicalReviewCompletionInput,
    ClassifyTechnicalSourcesInput,
    ExtractTechnicalFactCandidatesInput,
    MarkTechnicalIngestionFailedInput,
    PersistClassificationInput,
    PersistTechnicalFactCandidatesInput,
    PrepareTechnicalIngestionInput,
    PromoteTechnicalFactsInput,
    ReviewCaseResolvedSignal,
    TechnicalDossierIngestionInput,
    TechnicalDossierIngestionOutput,
    TechnicalDossierIngestionState,
    ValidateTechnicalFactsInput,
)

with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.technical_dossier_ingestion.activities import (
        TechnicalDossierActivities,
    )


@workflow.defn(name="TechnicalDossierIngestionWorkflow")
class TechnicalDossierIngestionWorkflow:
    def __init__(self) -> None:
        self.state = TechnicalDossierIngestionState()

    @workflow.signal
    def review_case_resolved(self, payload: ReviewCaseResolvedSignal) -> None:
        if self.state.ingestion_run_id == payload.ingestion_run_id:
            self.state.review_event_count += 1

    @workflow.query
    def get_state(self) -> TechnicalDossierIngestionState:
        return self.state

    @workflow.run
    async def run(
        self,
        payload: TechnicalDossierIngestionInput,
    ) -> TechnicalDossierIngestionOutput:
        self.state.ingestion_run_id = payload.sources_signal.ingestion_run_id
        self.state.status = WorkflowExecutionStatus.EXTRACTING_FACTS

        try:
            return await self._run_ingestion(payload)
        except Exception as exc:
            self.state.status = WorkflowExecutionStatus.FAILED
            await workflow.execute_activity_method(
                TechnicalDossierActivities.mark_technical_ingestion_failed,
                MarkTechnicalIngestionFailedInput(
                    product=payload.product,
                    error_message=str(exc),
                ),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            raise

    async def _run_ingestion(
        self,
        payload: TechnicalDossierIngestionInput,
    ) -> TechnicalDossierIngestionOutput:
        prepared = await workflow.execute_activity_method(
            TechnicalDossierActivities.prepare_technical_ingestion_run,
            PrepareTechnicalIngestionInput(
                product=payload.product,
                ingestion_run_id=payload.sources_signal.ingestion_run_id,
                document_source_ids=payload.sources_signal.document_source_ids,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        classifications = await workflow.execute_activity_method(
            TechnicalDossierActivities.classify_technical_sources,
            ClassifyTechnicalSourcesInput(sources=prepared.sources),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=DOC_AI_RETRY_POLICY,
        )

        await workflow.execute_activity_method(
            TechnicalDossierActivities.persist_classification_results,
            PersistClassificationInput(
                ingestion_run_id=prepared.ingestion_run_id,
                classifications=classifications.classifications,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        extraction = await workflow.execute_activity_method(
            TechnicalDossierActivities.extract_technical_fact_candidates,
            ExtractTechnicalFactCandidatesInput(
                sources=prepared.sources,
                classifications=classifications.classifications,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=DOC_AI_RETRY_POLICY,
        )

        await workflow.execute_activity_method(
            TechnicalDossierActivities.persist_technical_fact_candidates,
            PersistTechnicalFactCandidatesInput(
                product=payload.product,
                ingestion_run_id=prepared.ingestion_run_id,
                candidates=extraction.candidates,
                extraction_steps_json=extraction.extraction_steps_json,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        validation = await workflow.execute_activity_method(
            TechnicalDossierActivities.validate_technical_facts,
            ValidateTechnicalFactsInput(candidates=extraction.candidates),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        promotion = await workflow.execute_activity_method(
            TechnicalDossierActivities.promote_technical_facts,
            PromoteTechnicalFactsInput(
                product=payload.product,
                ingestion_run_id=prepared.ingestion_run_id,
                candidates=validation.candidates,
                review_cases=validation.review_cases,
                promoted_facts=validation.promoted_facts,
                extraction_steps_json=extraction.extraction_steps_json,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        self.state.review_case_count = promotion.review_case_count
        self.state.promoted_fact_count = promotion.promoted_fact_count
        if promotion.status == WorkflowExecutionStatus.PENDING_TECH_REVIEW:
            self.state.status = WorkflowExecutionStatus.PENDING_TECH_REVIEW
            await self._wait_until_review_complete(prepared.ingestion_run_id)

        self.state.status = WorkflowExecutionStatus.TECHNICAL_FACTS_READY
        return TechnicalDossierIngestionOutput(
            status=self.state.status,
            ingestion_run_id=prepared.ingestion_run_id,
            review_case_count=self.state.review_case_count,
            promoted_fact_count=self.state.promoted_fact_count,
        )

    async def _wait_until_review_complete(self, ingestion_run_id: str) -> None:
        while True:
            completion = await workflow.execute_activity_method(
                TechnicalDossierActivities.check_technical_review_completion,
                CheckTechnicalReviewCompletionInput(ingestion_run_id=ingestion_run_id),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            if completion.complete:
                return

            current_count = self.state.review_event_count

            def review_event_received(previous_count: int = current_count) -> bool:
                return self.state.review_event_count > previous_count

            with suppress(TimeoutError):
                await workflow.wait_condition(
                    review_event_received,
                    timeout=SHORT_ACTIVITY_TIMEOUT,
                )
