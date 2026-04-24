from __future__ import annotations

from typing import Any

from factory_writer.temporal.common.contracts import TemporalPayloadModel, WorkflowExecutionStatus
from factory_writer.temporal.sku_lifecycle.contracts import (
    ProductContextRef,
    ReviewCaseResolvedSignal,
    TechnicalSourcesUploadedSignal,
)


class TechnicalDocumentSourceRef(TemporalPayloadModel):
    document_source_id: str
    storage_uri: str
    mime_type: str


class TechnicalDossierIngestionInput(TemporalPayloadModel):
    product: ProductContextRef
    sources_signal: TechnicalSourcesUploadedSignal


class TechnicalDossierIngestionState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.EXTRACTING_FACTS
    ingestion_run_id: str | None = None
    review_case_count: int = 0
    promoted_fact_count: int = 0
    review_event_count: int = 0


class TechnicalDossierIngestionOutput(TemporalPayloadModel):
    status: WorkflowExecutionStatus
    ingestion_run_id: str
    review_case_count: int = 0
    promoted_fact_count: int = 0


class PrepareTechnicalIngestionInput(TemporalPayloadModel):
    product: ProductContextRef
    ingestion_run_id: str
    document_source_ids: tuple[str, ...]


class PrepareTechnicalIngestionResult(TemporalPayloadModel):
    product: ProductContextRef
    ingestion_run_id: str
    collection_id: str
    sources: tuple[TechnicalDocumentSourceRef, ...]


class TechnicalClassificationPayload(TemporalPayloadModel):
    document_source_id: str
    document_type: str
    confidence: float | None = None
    quality_metadata_json: dict[str, Any]
    extraction_step_json: dict[str, Any]


class ClassifyTechnicalSourcesInput(TemporalPayloadModel):
    sources: tuple[TechnicalDocumentSourceRef, ...]


class ClassifyTechnicalSourcesResult(TemporalPayloadModel):
    classifications: tuple[TechnicalClassificationPayload, ...]


class PersistClassificationInput(TemporalPayloadModel):
    ingestion_run_id: str
    classifications: tuple[TechnicalClassificationPayload, ...]


class PersistClassificationResult(TemporalPayloadModel):
    classification_count: int


class TechnicalFactCandidatePayload(TemporalPayloadModel):
    source_id: str
    field_name: str
    raw_value: str | None = None
    normalized_value: str | None = None
    unit: str | None = None
    extractor_confidence: float | None = None
    validation_status: str
    review_required: bool
    review_reason: str | None = None
    source_evidence_text: str | None = None
    source_page: int | None = None
    source_bbox_json: Any | None = None
    raw_entity_json: Any | None = None


class ExtractTechnicalFactCandidatesInput(TemporalPayloadModel):
    sources: tuple[TechnicalDocumentSourceRef, ...]
    classifications: tuple[TechnicalClassificationPayload, ...]


class ExtractTechnicalFactCandidatesResult(TemporalPayloadModel):
    candidates: tuple[TechnicalFactCandidatePayload, ...]
    extraction_steps_json: dict[str, Any]


class PersistTechnicalFactCandidatesInput(TemporalPayloadModel):
    product: ProductContextRef
    ingestion_run_id: str
    candidates: tuple[TechnicalFactCandidatePayload, ...]
    extraction_steps_json: dict[str, Any]


class PersistTechnicalFactCandidatesResult(TemporalPayloadModel):
    candidate_count: int


class TechnicalReviewCasePayload(TemporalPayloadModel):
    source_id: str | None = None
    candidate_index: int | None = None
    case_type: str
    trigger_source: str
    severity: str
    field_name: str | None = None
    title: str
    description: str
    detected_value: str | None = None
    detected_unit: str | None = None
    suggested_value: str | None = None
    suggested_unit: str | None = None
    metadata_json: Any | None = None


class PromotedTechnicalFactPayload(TemporalPayloadModel):
    candidate_index: int
    field_name: str
    value: str
    unit: str | None = None


class ValidateTechnicalFactsInput(TemporalPayloadModel):
    candidates: tuple[TechnicalFactCandidatePayload, ...]


class ValidateTechnicalFactsResult(TemporalPayloadModel):
    candidates: tuple[TechnicalFactCandidatePayload, ...]
    review_cases: tuple[TechnicalReviewCasePayload, ...]
    promoted_facts: tuple[PromotedTechnicalFactPayload, ...]


class PromoteTechnicalFactsInput(TemporalPayloadModel):
    product: ProductContextRef
    ingestion_run_id: str
    candidates: tuple[TechnicalFactCandidatePayload, ...]
    review_cases: tuple[TechnicalReviewCasePayload, ...]
    promoted_facts: tuple[PromotedTechnicalFactPayload, ...]
    extraction_steps_json: dict[str, Any]


class PromoteTechnicalFactsResult(TemporalPayloadModel):
    status: WorkflowExecutionStatus
    review_case_count: int
    promoted_fact_count: int


class CheckTechnicalReviewCompletionInput(TemporalPayloadModel):
    ingestion_run_id: str


class CheckTechnicalReviewCompletionResult(TemporalPayloadModel):
    complete: bool


class MarkTechnicalIngestionFailedInput(TemporalPayloadModel):
    product: ProductContextRef
    error_message: str


__all__ = [
    "CheckTechnicalReviewCompletionInput",
    "CheckTechnicalReviewCompletionResult",
    "ClassifyTechnicalSourcesInput",
    "ClassifyTechnicalSourcesResult",
    "ExtractTechnicalFactCandidatesInput",
    "ExtractTechnicalFactCandidatesResult",
    "MarkTechnicalIngestionFailedInput",
    "PersistClassificationInput",
    "PersistClassificationResult",
    "PersistTechnicalFactCandidatesInput",
    "PersistTechnicalFactCandidatesResult",
    "PrepareTechnicalIngestionInput",
    "PrepareTechnicalIngestionResult",
    "PromoteTechnicalFactsInput",
    "PromoteTechnicalFactsResult",
    "ReviewCaseResolvedSignal",
    "TechnicalDossierIngestionInput",
    "TechnicalDossierIngestionOutput",
    "TechnicalDossierIngestionState",
    "TechnicalDocumentSourceRef",
    "TechnicalFactCandidatePayload",
    "TechnicalReviewCasePayload",
    "ValidateTechnicalFactsInput",
    "ValidateTechnicalFactsResult",
]
