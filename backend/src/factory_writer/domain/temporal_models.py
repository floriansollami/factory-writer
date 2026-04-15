from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict, Field


class TemporalPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowExecutionStatus(StrEnum):
    WAITING_FOR_TECHNICAL_ARCHIVE = "waiting_for_technical_archive"
    EXTRACTING_FACTS = "extracting_facts"
    BUILDING_CONTEXT = "building_context"
    GENERATING_COPY = "generating_copy"
    WAITING_FOR_STYLE_APPROVAL = "waiting_for_style_approval"
    RUNNING_OFFLINE_EVAL = "running_offline_eval"
    PENDING_EDITOR_REVIEW = "pending_editor_review"
    PUBLISHED = "published"
    FAILED = "failed"


class PublicationDecision(StrEnum):
    READY_TO_PUBLISH = "ready_to_publish"
    PENDING_EDITOR_REVIEW = "pending_editor_review"


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


class StyleGuideIngestionInput(TemporalPayloadModel):
    source_id: str = Field(..., description="UUID du document source en base")
    file_uri: str = Field(..., description="URI GCS du PDF du style guide")


class StyleGuideApprovalSignalInput(TemporalPayloadModel):
    approved: bool
    reviewer_id: str | None = None
    comment: str | None = None


class StyleGuideWorkflowState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.WAITING_FOR_STYLE_APPROVAL
    draft_pack_id: str | None = None
    approved: bool | None = None


class StyleGuideLayoutParseResult(TemporalPayloadModel):
    layout_operation_id: str
    output_uri: str


class StyleGuideChunkPersistResult(TemporalPayloadModel):
    fragment_ids: list[str]


class StylePackDraftResult(TemporalPayloadModel):
    draft_pack_id: str
    draft_version_label: str


class StyleGuideIngestionOutput(TemporalPayloadModel):
    status: str
    pack_id: str | None = None


class OfflineEvaluationInput(TemporalPayloadModel):
    evaluation_scope: str = "full"
    trigger_source: str = "cron"
    candidate_prompt_package_id: str | None = None
    dry_run: bool = False


class OfflineEvaluationState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.RUNNING_OFFLINE_EVAL
    batch_id: str | None = None
    candidate_prompt_package_id: str | None = None
    promoted_prompt_package_id: str | None = None


class OfflineEvaluationBatch(TemporalPayloadModel):
    batch_id: str
    source_dataset: str
    case_count: int


class PromptPackageCandidateResult(TemporalPayloadModel):
    prompt_package_id: str
    version_label: str
    source: str


class OfflineEvaluationOutput(TemporalPayloadModel):
    status: str
    candidate_prompt_package_id: str | None = None
    promoted_prompt_package_id: str | None = None
