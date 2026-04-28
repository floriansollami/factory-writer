from __future__ import annotations

import structlog
from temporalio import activity

from factory_writer.application.ports import product_technical_ingestion as app_contracts
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.sku_lifecycle.contracts import ProductContextRef
from factory_writer.temporal.technical_dossier_ingestion.contracts import (
    ClassifyTechnicalSourcesInput,
    ClassifyTechnicalSourcesResult,
    ExtractTechnicalFactCandidatesInput,
    ExtractTechnicalFactCandidatesResult,
    FinalizeTechnicalReviewInput,
    FinalizeTechnicalReviewResult,
    MarkTechnicalIngestionFailedInput,
    NotifyTechnicalFactsReadyInput,
    NotifyTechnicalFactsReadyResult,
    PersistClassificationInput,
    PersistClassificationResult,
    PersistTechnicalFactCandidatesInput,
    PersistTechnicalFactCandidatesResult,
    PrepareTechnicalIngestionInput,
    PrepareTechnicalIngestionResult,
    PromotedTechnicalFactPayload,
    PromoteTechnicalFactsInput,
    PromoteTechnicalFactsResult,
    RefreshTechnicalClassificationsInput,
    TechnicalClassificationPayload,
    TechnicalDocumentSourceRef,
    TechnicalFactCandidatePayload,
    TechnicalReviewCasePayload,
    ValidateTechnicalFactsInput,
    ValidateTechnicalFactsResult,
)

logger = structlog.get_logger(__name__)


class TechnicalDossierActivities:
    def __init__(self, service: ProductTechnicalIngestionService) -> None:
        self._service = service

    @activity.defn
    async def prepare_technical_ingestion_run(
        self,
        payload: PrepareTechnicalIngestionInput,
    ) -> PrepareTechnicalIngestionResult:
        logger.info(
            "Technical dossier | run preparation",
            product_id=payload.product_id,
            ingestion_run_id=payload.ingestion_run_id,
        )

        result = await self._service.prepare_technical_ingestion_run(
            product_id=payload.product_id,
            ingestion_run_id=payload.ingestion_run_id,
            document_source_ids=payload.document_source_ids,
        )

        logger.info(
            "Technical dossier | run preparation completed",
            product_id=payload.product_id,
            ingestion_run_id=result.ingestion_run_id,
            collection_id=result.collection_id,
            source_count=len(result.sources),
        )

        return PrepareTechnicalIngestionResult(
            product=_to_temporal_product_ref(result.product),
            ingestion_run_id=result.ingestion_run_id,
            collection_id=result.collection_id,
            sources=tuple(_to_temporal_source_ref(source) for source in result.sources),
        )

    @activity.defn
    async def classify_technical_sources(
        self,
        payload: ClassifyTechnicalSourcesInput,
    ) -> ClassifyTechnicalSourcesResult:
        logger.info("Technical dossier | classification started", source_count=len(payload.sources))

        result = await self._service.classify_technical_sources(
            tuple(_to_app_source_ref(source) for source in payload.sources)
        )

        classifications = tuple(
            _to_temporal_classification(classification) for classification in result.classifications
        )

        logger.info(
            "Technical dossier | classification completed",
            classification_count=len(classifications),
            document_types=tuple(
                classification.document_type for classification in classifications
            ),
        )

        return ClassifyTechnicalSourcesResult(classifications=classifications)

    @activity.defn
    async def persist_classification_results(
        self,
        payload: PersistClassificationInput,
    ) -> PersistClassificationResult:
        logger.info(
            "Technical dossier | classification persistence",
            ingestion_run_id=payload.ingestion_run_id,
            classification_count=len(payload.classifications),
        )

        result = await self._service.persist_classification_results(
            ingestion_run_id=payload.ingestion_run_id,
            classifications=tuple(
                _to_app_classification(classification) for classification in payload.classifications
            ),
        )

        logger.info(
            "Technical dossier | classification persistence completed",
            ingestion_run_id=payload.ingestion_run_id,
            classification_count=result.classification_count,
            review_case_count=result.review_case_count,
        )

        return PersistClassificationResult(
            classification_count=result.classification_count,
            review_case_count=result.review_case_count,
        )

    @activity.defn
    async def refresh_technical_classifications(
        self,
        payload: RefreshTechnicalClassificationsInput,
    ) -> ClassifyTechnicalSourcesResult:
        logger.info(
            "Technical dossier | classification refresh",
            product_id=payload.product_id,
            ingestion_run_id=payload.ingestion_run_id,
            source_count=len(payload.sources),
        )

        result = await self._service.refresh_technical_classifications(
            product_id=payload.product_id,
            ingestion_run_id=payload.ingestion_run_id,
            sources=tuple(_to_app_source_ref(source) for source in payload.sources),
            classifications=tuple(
                _to_app_classification(classification) for classification in payload.classifications
            ),
        )

        classifications = tuple(
            _to_temporal_classification(classification) for classification in result.classifications
        )

        logger.info(
            "Technical dossier | classification refresh completed",
            product_id=payload.product_id,
            ingestion_run_id=payload.ingestion_run_id,
            classification_count=len(classifications),
            document_types=tuple(
                classification.document_type for classification in classifications
            ),
        )

        return ClassifyTechnicalSourcesResult(classifications=classifications)

    @activity.defn
    async def extract_technical_fact_candidates(
        self,
        payload: ExtractTechnicalFactCandidatesInput,
    ) -> ExtractTechnicalFactCandidatesResult:
        logger.info("Technical dossier | extraction started", source_count=len(payload.sources))

        result = await self._service.extract_technical_fact_candidates(
            ingestion_run_id=payload.ingestion_run_id,
            sources=tuple(_to_app_source_ref(source) for source in payload.sources),
            classifications=tuple(
                _to_app_classification(classification) for classification in payload.classifications
            ),
        )

        candidates = tuple(_to_temporal_candidate(candidate) for candidate in result.candidates)

        logger.info(
            "Technical dossier | extraction completed",
            source_count=len(payload.sources),
            candidate_count=len(candidates),
            total_elapsed_seconds=result.extraction_steps_json.get("total_elapsed_seconds"),
        )

        return ExtractTechnicalFactCandidatesResult(
            candidates=candidates,
            extraction_steps_json=result.extraction_steps_json,
        )

    @activity.defn
    async def persist_technical_fact_candidates(
        self,
        payload: PersistTechnicalFactCandidatesInput,
    ) -> PersistTechnicalFactCandidatesResult:
        logger.info(
            "Technical dossier | candidate persistence",
            ingestion_run_id=payload.ingestion_run_id,
            candidate_count=len(payload.candidates),
        )
        result = await self._service.persist_technical_fact_candidates(
            product=_to_app_product_ref(payload.product),
            ingestion_run_id=payload.ingestion_run_id,
            candidates=tuple(_to_app_candidate(candidate) for candidate in payload.candidates),
            extraction_steps_json=payload.extraction_steps_json,
        )
        logger.info(
            "Technical dossier | candidate persistence completed",
            ingestion_run_id=payload.ingestion_run_id,
            candidate_count=result.candidate_count,
        )
        return PersistTechnicalFactCandidatesResult(candidate_count=result.candidate_count)

    @activity.defn
    async def validate_technical_facts(
        self,
        payload: ValidateTechnicalFactsInput,
    ) -> ValidateTechnicalFactsResult:
        logger.info(
            "Technical dossier | deterministic validation",
            candidate_count=len(payload.candidates),
            document_types=payload.document_types,
        )

        result = await self._service.validate_technical_facts(
            product=_to_app_product_ref(payload.product),
            candidates=tuple(_to_app_candidate(candidate) for candidate in payload.candidates),
            document_types=payload.document_types,
            source_document_types=payload.source_document_types,
        )

        logger.info(
            "Technical dossier | deterministic validation completed",
            candidate_count=len(result.candidates),
            review_case_count=len(result.review_cases),
            promoted_fact_count=len(result.promoted_facts),
        )

        return ValidateTechnicalFactsResult(
            candidates=tuple(_to_temporal_candidate(candidate) for candidate in result.candidates),
            review_cases=tuple(_to_temporal_review_case(case) for case in result.review_cases),
            promoted_facts=tuple(
                _to_temporal_promoted_fact(promoted_fact) for promoted_fact in result.promoted_facts
            ),
            product_sheet_readiness=result.product_sheet_readiness,
        )

    @activity.defn
    async def promote_technical_facts(
        self,
        payload: PromoteTechnicalFactsInput,
    ) -> PromoteTechnicalFactsResult:
        logger.info(
            "Technical dossier | fact promotion",
            ingestion_run_id=payload.ingestion_run_id,
            review_case_count=len(payload.review_cases),
            promoted_fact_count=len(payload.promoted_facts),
        )
        result = await self._service.promote_technical_facts(
            product=_to_app_product_ref(payload.product),
            ingestion_run_id=payload.ingestion_run_id,
            candidates=tuple(_to_app_candidate(candidate) for candidate in payload.candidates),
            review_cases=tuple(_to_app_review_case(case) for case in payload.review_cases),
            promoted_facts=tuple(
                _to_app_promoted_fact(promoted_fact) for promoted_fact in payload.promoted_facts
            ),
            extraction_steps_json=payload.extraction_steps_json,
            product_sheet_readiness=payload.product_sheet_readiness,
        )
        logger.info(
            "Technical dossier | fact promotion completed",
            ingestion_run_id=payload.ingestion_run_id,
            status=result.status,
            review_case_count=result.review_case_count,
            promoted_fact_count=result.promoted_fact_count,
        )
        return PromoteTechnicalFactsResult(
            status=_to_temporal_workflow_status(result.status),
            review_case_count=result.review_case_count,
            promoted_fact_count=result.promoted_fact_count,
        )

    @activity.defn
    async def finalize_technical_review(
        self,
        payload: FinalizeTechnicalReviewInput,
    ) -> FinalizeTechnicalReviewResult:
        logger.info(
            "Technical dossier | review finalization",
            ingestion_run_id=payload.ingestion_run_id,
        )
        result = await self._service.finalize_technical_review(
            product=_to_app_product_ref(payload.product),
            ingestion_run_id=payload.ingestion_run_id,
        )
        logger.info(
            "Technical dossier | review finalization completed",
            ingestion_run_id=payload.ingestion_run_id,
            promoted_fact_count=result.promoted_fact_count,
        )
        return FinalizeTechnicalReviewResult(promoted_fact_count=result.promoted_fact_count)

    @activity.defn
    async def notify_technical_facts_ready(
        self,
        payload: NotifyTechnicalFactsReadyInput,
    ) -> NotifyTechnicalFactsReadyResult:
        logger.info(
            "Technical dossier | notifying technical facts ready",
            product_id=payload.product.product_id,
            sku=payload.product.sku,
            ingestion_run_id=payload.ingestion_run_id,
            promoted_fact_count=payload.promoted_fact_count,
        )
        await self._service.notify_technical_facts_ready(
            product=_to_app_product_ref(payload.product),
            technical_ingestion_run_id=payload.ingestion_run_id,
            promoted_fact_count=payload.promoted_fact_count,
        )
        logger.info(
            "Technical dossier | technical facts ready notified",
            product_id=payload.product.product_id,
            sku=payload.product.sku,
            ingestion_run_id=payload.ingestion_run_id,
            promoted_fact_count=payload.promoted_fact_count,
        )
        return NotifyTechnicalFactsReadyResult(notified=True)

    @activity.defn
    async def mark_technical_ingestion_failed(
        self,
        payload: MarkTechnicalIngestionFailedInput,
    ) -> None:
        logger.error(
            "Technical dossier | ingestion failed",
            product_id=payload.product.product_id,
            sku=payload.product.sku,
            error_message=payload.error_message,
        )
        await self._service.mark_technical_ingestion_failed(
            product=_to_app_product_ref(payload.product),
            error_message=payload.error_message,
        )


def _to_app_product_ref(product: ProductContextRef) -> app_contracts.ProductContextReference:
    return app_contracts.ProductContextReference(
        product_id=product.product_id,
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _to_temporal_product_ref(product: app_contracts.ProductContextReference) -> ProductContextRef:
    return ProductContextRef(
        product_id=product.product_id,
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _to_app_source_ref(
    source: TechnicalDocumentSourceRef,
) -> app_contracts.TechnicalDocumentSourceReference:
    return app_contracts.TechnicalDocumentSourceReference(
        document_source_id=source.document_source_id,
        storage_uri=source.storage_uri,
        mime_type=source.mime_type,
    )


def _to_temporal_source_ref(
    source: app_contracts.TechnicalDocumentSourceReference,
) -> TechnicalDocumentSourceRef:
    return TechnicalDocumentSourceRef(
        document_source_id=source.document_source_id,
        storage_uri=source.storage_uri,
        mime_type=source.mime_type,
    )


def _to_app_classification(
    classification: TechnicalClassificationPayload,
) -> app_contracts.TechnicalClassificationPayload:
    return app_contracts.TechnicalClassificationPayload(
        document_source_id=classification.document_source_id,
        document_type=classification.document_type,
        confidence=classification.confidence,
        quality_metadata_json=classification.quality_metadata_json,
        extraction_step_json=classification.extraction_step_json,
    )


def _to_temporal_classification(
    classification: app_contracts.TechnicalClassificationPayload,
) -> TechnicalClassificationPayload:
    return TechnicalClassificationPayload(
        document_source_id=classification.document_source_id,
        document_type=classification.document_type,
        confidence=classification.confidence,
        quality_metadata_json=classification.quality_metadata_json,
        extraction_step_json=classification.extraction_step_json,
    )


def _to_app_candidate(
    candidate: TechnicalFactCandidatePayload,
) -> app_contracts.TechnicalFactCandidatePayload:
    return app_contracts.TechnicalFactCandidatePayload(
        source_id=candidate.source_id,
        field_name=candidate.field_name,
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        unit=candidate.unit,
        extractor_confidence=candidate.extractor_confidence,
        validation_status=candidate.validation_status,
        source_page=candidate.source_page,
    )


def _to_temporal_candidate(
    candidate: app_contracts.TechnicalFactCandidatePayload,
) -> TechnicalFactCandidatePayload:
    return TechnicalFactCandidatePayload(
        source_id=candidate.source_id,
        field_name=candidate.field_name,
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        unit=candidate.unit,
        extractor_confidence=candidate.extractor_confidence,
        validation_status=candidate.validation_status,
        source_page=candidate.source_page,
    )


def _to_app_review_case(
    review_case: TechnicalReviewCasePayload,
) -> app_contracts.TechnicalReviewCasePayload:
    return app_contracts.TechnicalReviewCasePayload(
        source_id=review_case.source_id,
        candidate_index=review_case.candidate_index,
        case_type=review_case.case_type,
        trigger_source=review_case.trigger_source,
        severity=review_case.severity,
        field_name=review_case.field_name,
        title=review_case.title,
        description=review_case.description,
        detected_value=review_case.detected_value,
        detected_unit=review_case.detected_unit,
        suggested_value=review_case.suggested_value,
        suggested_unit=review_case.suggested_unit,
        metadata_json=review_case.metadata_json,
    )


def _to_temporal_review_case(
    review_case: app_contracts.TechnicalReviewCasePayload,
) -> TechnicalReviewCasePayload:
    return TechnicalReviewCasePayload(
        source_id=review_case.source_id,
        candidate_index=review_case.candidate_index,
        case_type=review_case.case_type,
        trigger_source=review_case.trigger_source,
        severity=review_case.severity,
        field_name=review_case.field_name,
        title=review_case.title,
        description=review_case.description,
        detected_value=review_case.detected_value,
        detected_unit=review_case.detected_unit,
        suggested_value=review_case.suggested_value,
        suggested_unit=review_case.suggested_unit,
        metadata_json=review_case.metadata_json,
    )


def _to_app_promoted_fact(
    promoted_fact: PromotedTechnicalFactPayload,
) -> app_contracts.PromotedTechnicalFactPayload:
    return app_contracts.PromotedTechnicalFactPayload(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        occurrence_index=promoted_fact.occurrence_index,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _to_temporal_promoted_fact(
    promoted_fact: app_contracts.PromotedTechnicalFactPayload,
) -> PromotedTechnicalFactPayload:
    return PromotedTechnicalFactPayload(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        occurrence_index=promoted_fact.occurrence_index,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _to_temporal_workflow_status(status: str) -> WorkflowExecutionStatus:
    if status == app_contracts.STATUS_PENDING_TECH_REVIEW:
        return WorkflowExecutionStatus.PENDING_TECH_REVIEW
    if status == app_contracts.STATUS_TECHNICAL_FACTS_READY:
        return WorkflowExecutionStatus.TECHNICAL_FACTS_READY
    return WorkflowExecutionStatus(status)
