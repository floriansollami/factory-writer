import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    StatutDocumentIngestionRun,
    StatutTechnicalFactCandidate,
    TechnicalReviewCaseType,
    TechnicalReviewResolutionAction,
    TechnicalReviewSeverity,
    TechnicalReviewTriggerSource,
)


@dataclass(frozen=True)
class ProductSnapshot:
    id: uuid.UUID
    sku: str
    name: str
    famille_code: str
    sous_famille_code: str | None
    season_code: str | None
    segment_prix_code: str | None
    langue_principale: str
    created_at: datetime | None = None


@dataclass(frozen=True)
class ProductTaxonomySnapshot:
    id: uuid.UUID
    code: str
    libelle_fr: str
    parent_id: uuid.UUID | None


@dataclass(frozen=True)
class UploadedTechnicalSourceData:
    document_source_id: uuid.UUID
    original_file_name: str
    storage_uri: str
    storage_bucket: str
    storage_object_name: str
    storage_generation: str
    storage_metageneration: str
    storage_content_type: str
    storage_size_bytes: int


@dataclass(frozen=True)
class DocumentSourceSnapshot:
    id: uuid.UUID
    collection_id: uuid.UUID
    original_file_name: str
    storage_uri: str
    storage_generation: str
    storage_metageneration: str
    storage_content_type: str
    storage_size_bytes: int
    document_type: str
    classification_confidence: float | None
    statut: str
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class IngestionRunSnapshot:
    id: uuid.UUID
    collection_id: uuid.UUID
    workflow_id: str
    statut: str
    current_step: str
    validation_summary_json: Any | None
    extraction_steps_json: Any | None
    created_at: datetime | None = None
    updated_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None


@dataclass(frozen=True)
class TechnicalIngestionStartPreparation:
    product: ProductSnapshot
    collection_id: uuid.UUID
    run: IngestionRunSnapshot
    sources: tuple[DocumentSourceSnapshot, ...]
    reused_existing_run: bool


@dataclass(frozen=True)
class TechnicalSourcesLotReplacementResult:
    sources: tuple[DocumentSourceSnapshot, ...]
    replaced_ingestion_run_id: uuid.UUID | None = None


@dataclass(frozen=True)
class CommercialSignalSnapshotSelection:
    id: uuid.UUID
    snapshot_id: str
    cohort_key: str
    famille_code: str
    segment_prix_code: str | None
    season_code: str | None
    sales_signals_json: Any
    feedback_signals_json: Any
    selection_reason: str
    matched_fields: dict[str, str | None]


@dataclass(frozen=True)
class ProductSheetRequirementProfileSnapshot:
    id: uuid.UUID
    famille_code: str
    sous_famille_code: str | None
    requirements_json: Any


@dataclass(frozen=True)
class StylePackRuntimeSnapshot:
    style_pack_id: str
    version_label: str


@dataclass(frozen=True)
class TechnicalFactSnapshot:
    id: uuid.UUID
    field_name: str
    occurrence_index: int
    value: str
    unit: str | None


@dataclass(frozen=True)
class ProductContextSnapshotResult:
    id: uuid.UUID
    product_id: uuid.UUID
    technical_ingestion_run_id: uuid.UUID
    style_pack_id: uuid.UUID
    commercial_signal_snapshot_id: uuid.UUID
    technical_fact_ids: tuple[uuid.UUID, ...]


@dataclass(frozen=True)
class ProductSheetGenerationSnapshot:
    id: uuid.UUID
    product_id: uuid.UUID
    product_context_snapshot_id: uuid.UUID
    status: str
    workflow_id: str | None
    prompt_registry_provider: str | None
    prompt_name: str | None
    prompt_version: str | None
    llm_model: str | None
    llm_temperature: float | None
    llm_max_tokens: int | None
    llm_response_format_name: str | None
    rendered_system_prompt_hash: str | None
    rendered_user_prompt_hash: str | None
    sheet_json: Any | None
    self_check_json: Any | None
    error_message: str | None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class ProductSheetGenerationContext:
    generation: ProductSheetGenerationSnapshot
    product: ProductSnapshot
    product_context_snapshot_id: uuid.UUID
    product_context_snapshot_json: Any
    technical_facts: tuple[TechnicalFactSnapshot, ...]
    style_rules_json: tuple[dict[str, Any], ...]
    commercial_signals_json: dict[str, Any]


@dataclass(frozen=True)
class TechnicalFactCandidateInput:
    source_id: uuid.UUID
    field_name: str
    raw_value: str | None
    normalized_value: str | None
    unit: str | None
    extractor_confidence: float | None
    validation_status: StatutTechnicalFactCandidate
    source_page: int | None


@dataclass(frozen=True)
class TechnicalReviewCaseInput:
    source_id: uuid.UUID | None
    candidate_index: int | None
    case_type: TechnicalReviewCaseType
    trigger_source: TechnicalReviewTriggerSource
    severity: TechnicalReviewSeverity
    field_name: str | None
    title: str
    description: str
    detected_value: str | None = None
    detected_unit: str | None = None
    suggested_value: str | None = None
    suggested_unit: str | None = None
    metadata_json: Any | None = None


@dataclass(frozen=True)
class PromotedTechnicalFactInput:
    candidate_index: int
    field_name: str
    occurrence_index: int
    value: str
    unit: str | None


class ProductTechnicalRepositoryPort(Protocol):
    async def create_product(
        self,
        *,
        sku: str,
        name: str,
        famille_code: str,
        sous_famille_code: str | None,
        season_code: str | None,
        segment_prix_code: str | None,
        langue_principale: str,
    ) -> ProductSnapshot: ...

    async def get_product(self, product_id: uuid.UUID) -> ProductSnapshot | None: ...

    async def list_products(self, *, limit: int = 50) -> tuple[ProductSnapshot, ...]: ...

    async def list_product_taxonomies(self) -> tuple[ProductTaxonomySnapshot, ...]: ...

    async def create_technical_sources(
        self,
        *,
        product_id: uuid.UUID,
        sources: list[UploadedTechnicalSourceData],
    ) -> tuple[DocumentSourceSnapshot, ...]: ...

    async def replace_technical_sources_lot(
        self,
        *,
        product_id: uuid.UUID,
        sources: list[UploadedTechnicalSourceData],
    ) -> TechnicalSourcesLotReplacementResult: ...

    async def prepare_technical_ingestion_start(
        self,
        *,
        product_id: uuid.UUID,
    ) -> TechnicalIngestionStartPreparation: ...

    async def get_technical_ingestion_context(
        self,
        *,
        product_id: uuid.UUID,
        document_source_ids: tuple[uuid.UUID, ...],
        ingestion_run_id: uuid.UUID | None = None,
    ) -> dict[str, Any]: ...

    async def select_commercial_signal_snapshot(
        self,
        *,
        product: ProductSnapshot,
    ) -> CommercialSignalSnapshotSelection: ...

    async def load_product_sheet_requirement_profile(
        self,
        *,
        product: ProductSnapshot,
    ) -> ProductSheetRequirementProfileSnapshot: ...

    async def load_active_style_pack(self) -> StylePackRuntimeSnapshot: ...

    async def update_ingestion_run_step(
        self,
        *,
        run_id: uuid.UUID,
        current_step: CurrentStep,
        statut: StatutDocumentIngestionRun | None = None,
        extraction_steps_json: Any | None = None,
    ) -> IngestionRunSnapshot: ...

    async def update_source_classification(
        self,
        *,
        source_id: uuid.UUID,
        document_type: str,
        confidence: float | None,
        quality_metadata_json: Any | None,
    ) -> None: ...

    async def create_classification_review_cases(
        self,
        *,
        run_id: uuid.UUID,
        review_cases: list[TechnicalReviewCaseInput],
        extraction_steps_json: Any,
    ) -> int: ...

    async def persist_technical_fact_candidates(
        self,
        *,
        product_id: uuid.UUID,
        run_id: uuid.UUID,
        candidates: list[TechnicalFactCandidateInput],
        extraction_steps_json: Any,
    ) -> IngestionRunSnapshot: ...

    async def complete_technical_ingestion(
        self,
        *,
        product_id: uuid.UUID,
        run_id: uuid.UUID,
        candidates: list[TechnicalFactCandidateInput],
        review_cases: list[TechnicalReviewCaseInput],
        promoted_facts: list[PromotedTechnicalFactInput],
        extraction_steps_json: Any,
        validation_summary_json: Any,
        requires_review: bool,
    ) -> IngestionRunSnapshot: ...

    async def list_technical_facts(
        self,
        *,
        product_id: uuid.UUID,
    ) -> tuple[TechnicalFactSnapshot, ...]: ...

    async def create_product_context_snapshot(
        self,
        *,
        product_id: uuid.UUID,
        technical_ingestion_run_id: uuid.UUID,
        style_pack_id: uuid.UUID,
        commercial_signal_snapshot_id: uuid.UUID,
        technical_fact_ids: tuple[uuid.UUID, ...],
        snapshot_json: Any,
    ) -> ProductContextSnapshotResult: ...

    async def prepare_product_sheet_generation(
        self,
        *,
        product_id: uuid.UUID,
    ) -> ProductSheetGenerationSnapshot: ...

    async def mark_product_sheet_generation_started(
        self,
        *,
        generation_id: uuid.UUID,
        workflow_id: str,
    ) -> ProductSheetGenerationSnapshot: ...

    async def load_product_sheet_generation_context(
        self,
        *,
        generation_id: uuid.UUID,
    ) -> ProductSheetGenerationContext: ...

    async def complete_product_sheet_generation(
        self,
        *,
        generation_id: uuid.UUID,
        status: str,
        prompt_registry_provider: str,
        prompt_name: str,
        prompt_version: str,
        llm_model: str,
        llm_temperature: float,
        llm_max_tokens: int,
        llm_response_format_name: str,
        rendered_system_prompt_hash: str,
        rendered_user_prompt_hash: str,
        sheet_json: Any,
        self_check_json: Any,
    ) -> ProductSheetGenerationSnapshot: ...

    async def mark_product_sheet_generation_failed(
        self,
        *,
        generation_id: uuid.UUID,
        error_message: str,
    ) -> ProductSheetGenerationSnapshot: ...

    async def list_products_for_style_pack_activation(
        self,
        *,
        max_results: int = 250,
    ) -> tuple[ProductSnapshot, ...]: ...

    async def mark_technical_ingestion_failed(
        self,
        *,
        product_id: uuid.UUID,
        error_message: str,
    ) -> None: ...

    async def resolve_review_case(
        self,
        *,
        product_id: uuid.UUID,
        case_id: uuid.UUID,
        action: TechnicalReviewResolutionAction,
        resolved_by: str,
        corrected_value: str | None,
        corrected_unit: str | None,
        selected_candidate_id: uuid.UUID | None,
        comment: str | None,
    ) -> dict[str, Any]: ...

    async def get_product_overview(self, product_id: uuid.UUID) -> dict[str, Any]: ...
