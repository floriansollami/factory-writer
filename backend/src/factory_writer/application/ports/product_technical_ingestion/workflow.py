from dataclasses import dataclass, field
from typing import Any, Protocol

STATUS_PENDING_TECH_REVIEW = "PENDING_TECH_REVIEW"
STATUS_TECHNICAL_FACTS_READY = "TECHNICAL_FACTS_READY"
STATUS_WAITING_TECH_FACTS = "WAITING_TECH_FACTS"
STATUS_WAITING_STYLE_PACK = "WAITING_STYLE_PACK"
STATUS_WAITING_COMMERCIAL_SNAPSHOT = "WAITING_COMMERCIAL_SNAPSHOT"


@dataclass(frozen=True)
class ProductContextReference:
    product_id: str | None
    sku: str
    famille_code: str
    sous_famille_code: str | None = None
    season_code: str | None = None
    segment_prix_code: str | None = None
    langue_principale: str = "fr-FR"


@dataclass(frozen=True)
class TechnicalSourcesUploaded:
    ingestion_run_id: str
    document_source_ids: tuple[str, ...] = field(default_factory=tuple)
    source_event_id: str | None = None


@dataclass(frozen=True)
class LoadCanonicalProductResult:
    product: ProductContextReference


@dataclass(frozen=True)
class TechnicalDocumentSourceReference:
    document_source_id: str
    storage_uri: str
    mime_type: str


@dataclass(frozen=True)
class PrepareTechnicalIngestionResult:
    product: ProductContextReference
    ingestion_run_id: str
    collection_id: str
    sources: tuple[TechnicalDocumentSourceReference, ...]


@dataclass(frozen=True)
class TechnicalClassificationPayload:
    document_source_id: str
    document_type: str
    confidence: float | None = None
    quality_metadata_json: dict[str, Any] = field(default_factory=dict)
    extraction_step_json: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ClassifyTechnicalSourcesResult:
    classifications: tuple[TechnicalClassificationPayload, ...]


@dataclass(frozen=True)
class PersistClassificationResult:
    classification_count: int
    review_case_count: int = 0


@dataclass(frozen=True)
class TechnicalFactCandidatePayload:
    source_id: str
    field_name: str
    validation_status: str
    raw_value: str | None = None
    normalized_value: str | None = None
    unit: str | None = None
    extractor_confidence: float | None = None
    source_page: int | None = None


@dataclass(frozen=True)
class ExtractTechnicalFactCandidatesResult:
    candidates: tuple[TechnicalFactCandidatePayload, ...]
    extraction_steps_json: dict[str, Any]


@dataclass(frozen=True)
class PersistTechnicalFactCandidatesResult:
    candidate_count: int


@dataclass(frozen=True)
class TechnicalReviewCasePayload:
    case_type: str
    trigger_source: str
    severity: str
    title: str
    description: str
    source_id: str | None = None
    candidate_index: int | None = None
    field_name: str | None = None
    detected_value: str | None = None
    detected_unit: str | None = None
    suggested_value: str | None = None
    suggested_unit: str | None = None
    metadata_json: Any | None = None


@dataclass(frozen=True)
class PromotedTechnicalFactPayload:
    candidate_index: int
    field_name: str
    occurrence_index: int
    value: str
    unit: str | None = None


@dataclass(frozen=True)
class ValidateTechnicalFactsResult:
    candidates: tuple[TechnicalFactCandidatePayload, ...]
    review_cases: tuple[TechnicalReviewCasePayload, ...]
    promoted_facts: tuple[PromotedTechnicalFactPayload, ...]
    generation_readiness: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class PromoteTechnicalFactsResult:
    status: str
    review_case_count: int
    promoted_fact_count: int


@dataclass(frozen=True)
class FinalizeTechnicalReviewResult:
    promoted_fact_count: int


@dataclass(frozen=True)
class ProductContextReadiness:
    ready: bool
    missing_prerequisites: tuple[str, ...] = field(default_factory=tuple)
    waiting_status: str | None = None
    style_pack_id: str | None = None
    style_pack_version_label: str | None = None
    commercial_signal_snapshot_id: str | None = None
    commercial_snapshot_id: str | None = None
    commercial_cohort_key: str | None = None
    commercial_selection_reason: str | None = None
    commercial_matched_fields: dict[str, str | None] = field(default_factory=dict)
    technical_fact_ids: tuple[str, ...] = field(default_factory=tuple)
    technical_facts: tuple[dict[str, Any], ...] = field(default_factory=tuple)
    generation_readiness: dict[str, Any] | None = None


@dataclass(frozen=True)
class CreateProductContextSnapshotResult:
    product_context_snapshot_id: str


class ProductLifecycleWorkflowPort(Protocol):
    async def start_product_lifecycle(self, product: ProductContextReference) -> str: ...

    async def start_technical_dossier_ingestion(
        self,
        product: ProductContextReference,
        payload: TechnicalSourcesUploaded,
    ) -> str: ...

    async def signal_technical_sources_uploaded(
        self,
        sku: str,
        payload: TechnicalSourcesUploaded,
    ) -> None: ...

    async def signal_technical_review_case_resolved(
        self,
        *,
        ingestion_run_id: str,
        case_id: str,
        open_review_case_count: int,
        review_complete: bool,
    ) -> None: ...

    async def terminate_technical_dossier_ingestion(
        self,
        *,
        ingestion_run_id: str,
        reason: str,
    ) -> None: ...

    async def signal_style_pack_activated(self, *, sku: str, style_pack_id: str) -> None: ...

    async def signal_commercial_snapshot_available(self, *, sku: str, snapshot_id: str) -> None: ...
