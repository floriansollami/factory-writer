from __future__ import annotations

from temporalio import workflow

from factory_writer.temporal.common.config import (
    DB_RETRY_POLICY,
    DOC_AI_RETRY_POLICY,
    LONG_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.technical_dossier_ingestion.contracts import (
    ClassifyTechnicalSourcesInput,
    ExtractTechnicalFactCandidatesInput,
    FinalizeTechnicalReviewInput,
    MarkTechnicalIngestionFailedInput,
    PersistClassificationInput,
    PersistTechnicalFactCandidatesInput,
    PrepareTechnicalIngestionInput,
    PromoteTechnicalFactsInput,
    RefreshTechnicalClassificationsInput,
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
            self.state.open_review_case_count = payload.open_review_case_count
            workflow.logger.info(
                "Technical dossier | review case résolu signalé | "
                f"ingestion_run_id={payload.ingestion_run_id} "
                f"case_id={payload.case_id} "
                f"open_review_case_count={payload.open_review_case_count} "
                f"review_complete={payload.review_complete}"
            )

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
        workflow.logger.info(
            "Technical dossier | workflow démarré | "
            f"product_id={payload.product.product_id} "
            f"sku={payload.product.sku} "
            f"ingestion_run_id={payload.sources_signal.ingestion_run_id} "
            f"document_source_ids={payload.sources_signal.document_source_ids}"
        )

        try:
            result = await self._run_ingestion(payload)
            workflow.logger.info(
                "Technical dossier | workflow terminé | "
                f"product_id={payload.product.product_id} "
                f"sku={payload.product.sku} "
                f"ingestion_run_id={result.ingestion_run_id} "
                f"status={result.status} "
                f"review_case_count={result.review_case_count} "
                f"promoted_fact_count={result.promoted_fact_count}"
            )
            return result
        except Exception as exc:
            self.state.status = WorkflowExecutionStatus.FAILED
            workflow.logger.error(
                "Technical dossier | workflow échoué | "
                f"product_id={payload.product.product_id} "
                f"sku={payload.product.sku} "
                f"ingestion_run_id={payload.sources_signal.ingestion_run_id} "
                f"error={exc}"
            )
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
        product_id = payload.product.product_id

        if product_id is None:
            raise RuntimeError("product_id est requis pour préparer l'ingestion technique.")

        workflow.logger.info(
            "Technical dossier | préparation du run | "
            f"product_id={product_id} "
            f"ingestion_run_id={payload.sources_signal.ingestion_run_id} "
            f"document_source_count={len(payload.sources_signal.document_source_ids)}"
        )
        prepared = await workflow.execute_activity_method(
            TechnicalDossierActivities.prepare_technical_ingestion_run,
            PrepareTechnicalIngestionInput(
                product_id=product_id,
                ingestion_run_id=payload.sources_signal.ingestion_run_id,
                document_source_ids=payload.sources_signal.document_source_ids,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )
        workflow.logger.info(
            "Technical dossier | préparation terminée | "
            f"product_id={product_id} "
            f"collection_id={prepared.collection_id} "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"source_count={len(prepared.sources)}"
        )

        workflow.logger.info(
            "Technical dossier | classification démarrée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"source_count={len(prepared.sources)}"
        )

        classifications = await workflow.execute_activity_method(
            TechnicalDossierActivities.classify_technical_sources,
            ClassifyTechnicalSourcesInput(sources=prepared.sources),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
            retry_policy=DOC_AI_RETRY_POLICY,
        )

        workflow.logger.info(
            "Technical dossier | classification terminée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"classification_count={len(classifications.classifications)} "
            f"document_types={tuple(c.document_type for c in classifications.classifications)}"
        )

        workflow.logger.info(
            "Technical dossier | persistance classification démarrée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"classification_count={len(classifications.classifications)}"
        )

        persisted_classification = await workflow.execute_activity_method(
            TechnicalDossierActivities.persist_classification_results,
            PersistClassificationInput(
                ingestion_run_id=prepared.ingestion_run_id,
                classifications=classifications.classifications,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        workflow.logger.info(
            "Technical dossier | persistance classification terminée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"review_case_count={persisted_classification.review_case_count}"
        )

        self.state.review_case_count = persisted_classification.review_case_count
        self.state.open_review_case_count = persisted_classification.review_case_count

        if persisted_classification.review_case_count > 0:
            self.state.status = WorkflowExecutionStatus.PENDING_TECH_REVIEW

            workflow.logger.info(
                "Technical dossier | classification à valider | "
                f"ingestion_run_id={prepared.ingestion_run_id} "
                f"review_case_count={persisted_classification.review_case_count}"
            )

            await workflow.wait_condition(lambda: self.state.open_review_case_count == 0)

            workflow.logger.info(
                "Technical dossier | classification validée | "
                f"ingestion_run_id={prepared.ingestion_run_id}"
            )

            classifications = await workflow.execute_activity_method(
                TechnicalDossierActivities.refresh_technical_classifications,
                RefreshTechnicalClassificationsInput(
                    product_id=product_id,
                    ingestion_run_id=prepared.ingestion_run_id,
                    sources=prepared.sources,
                    classifications=classifications.classifications,
                ),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )

        self.state.status = WorkflowExecutionStatus.EXTRACTING_FACTS

        workflow.logger.info(
            "Technical dossier | extraction des faits démarrée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"source_count={len(prepared.sources)}"
        )

        extraction = await workflow.execute_activity_method(
            TechnicalDossierActivities.extract_technical_fact_candidates,
            ExtractTechnicalFactCandidatesInput(
                ingestion_run_id=prepared.ingestion_run_id,
                sources=prepared.sources,
                classifications=classifications.classifications,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
            retry_policy=DOC_AI_RETRY_POLICY,
        )

        workflow.logger.info(
            "Technical dossier | extraction des faits terminée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"candidate_count={len(extraction.candidates)} "
            f"total_elapsed_seconds={extraction.extraction_steps_json.get('total_elapsed_seconds')}"
        )

        workflow.logger.info(
            "Technical dossier | persistance candidats démarrée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"candidate_count={len(extraction.candidates)}"
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

        workflow.logger.info(
            "Technical dossier | persistance candidats terminée | "
            f"ingestion_run_id={prepared.ingestion_run_id}"
        )

        workflow.logger.info(
            "Technical dossier | validation déterministe démarrée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"candidate_count={len(extraction.candidates)}"
        )

        # ici
        validation = await workflow.execute_activity_method(
            TechnicalDossierActivities.validate_technical_facts,
            ValidateTechnicalFactsInput(
                product=payload.product,
                candidates=extraction.candidates,
                document_types=tuple(
                    classification.document_type
                    for classification in classifications.classifications
                ),
                source_document_types={
                    classification.document_source_id: classification.document_type
                    for classification in classifications.classifications
                },
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        workflow.logger.info(
            "Technical dossier | validation déterministe terminée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"review_case_count={len(validation.review_cases)} "
            f"promoted_fact_count={len(validation.promoted_facts)} "
            f"generation_ready={validation.generation_readiness.get('ready')}"
        )

        workflow.logger.info(
            "Technical dossier | promotion des faits démarrée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"review_case_count={len(validation.review_cases)} "
            f"promoted_fact_count={len(validation.promoted_facts)}"
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
                generation_readiness=validation.generation_readiness,
            ),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        workflow.logger.info(
            "Technical dossier | promotion des faits terminée | "
            f"ingestion_run_id={prepared.ingestion_run_id} "
            f"status={promotion.status} "
            f"review_case_count={promotion.review_case_count} "
            f"promoted_fact_count={promotion.promoted_fact_count}"
        )

        self.state.review_case_count = promotion.review_case_count
        self.state.open_review_case_count = promotion.review_case_count
        self.state.promoted_fact_count = promotion.promoted_fact_count

        if promotion.status == WorkflowExecutionStatus.PENDING_TECH_REVIEW:
            self.state.status = WorkflowExecutionStatus.PENDING_TECH_REVIEW
            workflow.logger.info(
                "Technical dossier | en attente de review technique | "
                f"ingestion_run_id={prepared.ingestion_run_id} "
                f"review_case_count={promotion.review_case_count}"
            )
            await workflow.wait_condition(lambda: self.state.open_review_case_count == 0)
            workflow.logger.info(
                "Technical dossier | review technique terminée | "
                f"ingestion_run_id={prepared.ingestion_run_id}"
            )
            finalized = await workflow.execute_activity_method(
                TechnicalDossierActivities.finalize_technical_review,
                FinalizeTechnicalReviewInput(
                    product=payload.product,
                    ingestion_run_id=prepared.ingestion_run_id,
                ),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            self.state.promoted_fact_count = finalized.promoted_fact_count

        self.state.status = WorkflowExecutionStatus.TECHNICAL_FACTS_READY

        return TechnicalDossierIngestionOutput(
            status=self.state.status,
            ingestion_run_id=prepared.ingestion_run_id,
            review_case_count=self.state.review_case_count,
            promoted_fact_count=self.state.promoted_fact_count,
        )
