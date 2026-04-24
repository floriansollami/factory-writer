from __future__ import annotations

from typing import Any

from pydantic import Field

from factory_writer.temporal.common.contracts import (
    TemporalPayloadModel,
    WorkflowExecutionStatus,
)


class ProductContextRef(TemporalPayloadModel):
    product_id: str | None = Field(default=None, description="Identifiant interne du produit")
    sku: str = Field(..., description="SKU métier principal")
    famille_code: str = Field(..., description="Famille produit")
    sous_famille_code: str | None = Field(default=None, description="Sous-famille produit")
    season_code: str | None = Field(default=None, description="Saison commerciale")
    segment_prix_code: str | None = Field(default=None, description="Segment prix")
    langue_principale: str = Field(default="fr-FR", description="Langue de génération")


class TechnicalSourcesUploadedSignal(TemporalPayloadModel):
    document_source_ids: tuple[str, ...] = Field(
        default_factory=tuple,
        description="Sources PDF techniques uploadées pour ce run",
    )
    ingestion_run_id: str = Field(..., description="Run technique préparé en base")
    source_event_id: str | None = Field(default=None, description="Idempotence côté event source")


class ReviewCaseResolvedSignal(TemporalPayloadModel):
    ingestion_run_id: str
    case_id: str


class StylePackActivatedSignal(TemporalPayloadModel):
    style_pack_id: str


class CommercialSnapshotAvailableSignal(TemporalPayloadModel):
    snapshot_id: str


class ProductLifecycleState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.WAITING_TECHNICAL_SOURCES
    product_loaded: bool = False
    technical_sources_uploaded: bool = False
    technical_ingestion_run_id: str | None = None
    technical_document_source_ids: tuple[str, ...] = Field(default_factory=tuple)
    technical_facts_ready: bool = False
    product_context_snapshot_id: str | None = None
    style_pack_id: str | None = None
    commercial_signal_snapshot_id: str | None = None
    readiness_event_count: int = 0
    waiting_reason: str | None = None


class ProductLifecycleInput(TemporalPayloadModel):
    product: ProductContextRef
    resume_state: ProductLifecycleState | None = Field(
        default=None,
        description="État réinjecté en cas de Continue-As-New",
    )


class ProductLifecycleOutput(TemporalPayloadModel):
    status: WorkflowExecutionStatus
    product_context_snapshot_id: str | None = None


class LoadCanonicalProductInput(TemporalPayloadModel):
    product: ProductContextRef


class LoadCanonicalProductResult(TemporalPayloadModel):
    product: ProductContextRef


class ContextReadinessCheckInput(TemporalPayloadModel):
    product: ProductContextRef
    technical_ingestion_run_id: str


class ProductContextReadinessResult(TemporalPayloadModel):
    ready: bool
    missing_prerequisites: tuple[str, ...] = Field(default_factory=tuple)
    waiting_status: WorkflowExecutionStatus | None = None
    style_pack_id: str | None = None
    style_pack_version_label: str | None = None
    commercial_signal_snapshot_id: str | None = None
    commercial_snapshot_id: str | None = None
    commercial_cohort_key: str | None = None
    commercial_selection_reason: str | None = None
    commercial_matched_fields: dict[str, str | None] = Field(default_factory=dict)
    technical_fact_ids: tuple[str, ...] = Field(default_factory=tuple)
    technical_facts: tuple[dict[str, Any], ...] = Field(default_factory=tuple)


class CreateProductContextSnapshotInput(TemporalPayloadModel):
    product: ProductContextRef
    technical_ingestion_run_id: str
    readiness: ProductContextReadinessResult


class ProductContextSnapshotResult(TemporalPayloadModel):
    product_context_snapshot_id: str
