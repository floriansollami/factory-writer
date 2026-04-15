from __future__ import annotations

from pydantic import Field

from factory_writer.temporal.common.contracts import (
    PublicationDecision,
    TemporalPayloadModel,
    WorkflowExecutionStatus,
)


class ProductContextRef(TemporalPayloadModel):
    product_id: str | None = Field(default=None, description="Identifiant interne du produit")
    sku: str = Field(..., description="SKU métier principal")
    famille_code: str = Field(..., description="Famille produit")
    sous_famille_code: str = Field(..., description="Sous-famille produit")
    season_code: str | None = Field(default=None, description="Saison commerciale")
    segment_prix_code: str | None = Field(default=None, description="Segment prix")
    langue_principale: str = Field(default="fr-FR", description="Langue de génération")


class TechnicalArchiveSignalInput(TemporalPayloadModel):
    archive_uri: str = Field(..., description="URI GCS du zip technique scellé")
    checksum: str | None = Field(default=None, description="Checksum optionnel du zip")
    source_event_id: str | None = Field(default=None, description="Idempotence côté Eventarc")


class SkuLifecycleState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.WAITING_FOR_TECHNICAL_ARCHIVE
    technical_archive_received: bool = False
    technical_archive_uri: str | None = None
    facts_snapshot_id: str | None = None
    signal_snapshot_id: str | None = None
    style_pack_id: str | None = None
    prompt_package_id: str | None = None
    publication_decision: PublicationDecision | None = None
    published_content_id: str | None = None


class SkuLifecycleInput(TemporalPayloadModel):
    product: ProductContextRef
    resume_state: SkuLifecycleState | None = Field(
        default=None,
        description="État réinjecté en cas de Continue-As-New",
    )


class SkuLifecycleOutput(TemporalPayloadModel):
    status: WorkflowExecutionStatus
    publication_decision: PublicationDecision
    published_content_id: str | None = None


class TechnicalFactsExtractionInput(TemporalPayloadModel):
    product: ProductContextRef
    archive_signal: TechnicalArchiveSignalInput


class TechnicalFactsExtractionResult(TemporalPayloadModel):
    facts_snapshot_id: str
    evidence_bundle_id: str
    validation_status: str


class SignalSnapshotLoadInput(TemporalPayloadModel):
    product: ProductContextRef


class SignalSnapshotResult(TemporalPayloadModel):
    signal_snapshot_id: str
    cohort_key_used: str
    snapshot_status: str


class StylePackLoadInput(TemporalPayloadModel):
    product: ProductContextRef


class StylePackResult(TemporalPayloadModel):
    style_pack_id: str
    version_label: str


class PromptPackageLoadInput(TemporalPayloadModel):
    product: ProductContextRef


class PromptPackageResult(TemporalPayloadModel):
    prompt_package_id: str
    version_label: str


class ContextSnapshot(TemporalPayloadModel):
    product: ProductContextRef
    facts: TechnicalFactsExtractionResult
    signals: SignalSnapshotResult
    style_pack: StylePackResult
    prompt_package: PromptPackageResult


class GenerationStepInput(TemporalPayloadModel):
    context_snapshot: ContextSnapshot
    upstream_artifact_id: str | None = None


class GeneratedArtifactRef(TemporalPayloadModel):
    artifact_id: str
    artifact_kind: str
    status: str


class PublishGateInput(TemporalPayloadModel):
    context_snapshot: ContextSnapshot
    review_artifact: GeneratedArtifactRef


class PublishGateDecision(TemporalPayloadModel):
    decision: PublicationDecision
    reason: str


class PublishContentInput(TemporalPayloadModel):
    context_snapshot: ContextSnapshot
    review_artifact: GeneratedArtifactRef


class PublishContentResult(TemporalPayloadModel):
    published_content_id: str
    target_system: str
