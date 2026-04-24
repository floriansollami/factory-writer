import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Protocol

from factory_writer.application.prompts.style_guide_extract_rules.v1.output_schema import (
    DraftStylePackExtractionV1,
)
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    DecisionEditorialeStyleRule,
    DocumentType,
    OrigineStyleRule,
    StatutDocumentCollection,
    StatutDocumentIngestionRun,
    StatutStylePack,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle

from .document_parser import StyleGuideChunkCandidate
from .draft_pack_generator import (
    StyleGuideDraftPackGenerationMetadata,
    StyleGuideDraftPackSnapshot,
    StyleGuideTaxonomySnapshot,
)


@dataclass(frozen=True)
class StyleGuideDocumentSourceSnapshot:
    id: uuid.UUID
    collection_id: uuid.UUID
    storage_uri: str
    statut: StatutSource
    collection_statut: StatutDocumentCollection
    document_type: DocumentType
    original_file_name: str
    dernier_message_erreur: str | None
    replaced_by_source_id: uuid.UUID | None = None
    replaced_by_collection_id: uuid.UUID | None = None
    storage_generation: str | None = None
    storage_metageneration: str | None = None
    storage_content_type: str | None = None
    storage_size_bytes: int | None = None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class StyleGuideIngestionRunSnapshot:
    id: uuid.UUID
    collection_id: uuid.UUID
    pipeline_kind: str
    statut: StatutDocumentIngestionRun
    current_step: CurrentStep
    temporal_workflow_id: str
    temporal_run_id: str | None
    extraction_steps_json: Any | None
    validation_summary_json: Any | None
    error_message: str | None
    started_at: datetime | None
    completed_at: datetime | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class StyleGuideIngestionStartPreparation:
    document_source: StyleGuideDocumentSourceSnapshot
    run: StyleGuideIngestionRunSnapshot
    reused_existing_run: bool


@dataclass(frozen=True)
class StyleGuidePackSnapshot:
    id: uuid.UUID
    ingestion_run_id: uuid.UUID
    collection_id: uuid.UUID
    document_source_id: uuid.UUID
    original_file_name: str
    statut: StatutStylePack
    est_actif: bool
    approuve_le: datetime | None
    temporal_workflow_id: str
    run_statut: StatutDocumentIngestionRun
    run_current_step: CurrentStep
    rules_count: int
    approved_rules_count: int
    disabled_rules_count: int
    hard_rules_count: int
    soft_rules_count: int
    scopes: list[str]
    validation_summary_json: Any | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


@dataclass(frozen=True)
class StyleGuideRuleSnapshot:
    id: uuid.UUID
    pack_id: uuid.UUID
    type_regle: TypeRegle
    niveau_contrainte: NiveauContrainte
    texte_regle: str
    taxonomie_code: str | None
    est_actif: bool
    decision_editoriale: DecisionEditorialeStyleRule
    origine: OrigineStyleRule
    source_evidence_text: str | None
    source_evidence_provider_id: str | None
    source_evidence_page_start: int | None
    source_evidence_page_end: int | None
    source_evidence_json: Any | None
    commentaire_review: str | None
    reviewed_at: datetime | None
    reviewed_by: str | None
    created_at: datetime | None = None
    updated_at: datetime | None = None


class StyleGuideRepositoryPort(Protocol):
    async def get_current_document_source(self) -> StyleGuideDocumentSourceSnapshot | None: ...

    async def get_document_source_by_id(
        self, document_source_id: uuid.UUID
    ) -> StyleGuideDocumentSourceSnapshot | None: ...

    async def get_latest_ingestion_run_for_document_source(
        self,
        document_source_id: uuid.UUID,
    ) -> StyleGuideIngestionRunSnapshot | None: ...

    async def prepare_ingestion_start(
        self,
        *,
        document_source_id: uuid.UUID,
        pipeline_kind: str,
    ) -> StyleGuideIngestionStartPreparation: ...

    async def create_document_source(
        self,
        *,
        document_source_id: uuid.UUID,
        storage_uri: str,
        storage_bucket: str,
        storage_object_name: str,
        original_file_name: str,
        storage_content_type: str,
        storage_size_bytes: int,
        storage_generation: str,
        storage_metageneration: str,
    ) -> StyleGuideDocumentSourceSnapshot: ...

    async def create_reuploaded_document_source(
        self,
        *,
        replaced_document_source_id: uuid.UUID,
        document_source_id: uuid.UUID,
        storage_uri: str,
        storage_bucket: str,
        storage_object_name: str,
        original_file_name: str,
        storage_content_type: str,
        storage_size_bytes: int,
        storage_generation: str,
        storage_metageneration: str,
    ) -> StyleGuideDocumentSourceSnapshot: ...

    async def create_ingestion_run(
        self,
        *,
        document_source_id: uuid.UUID,
        pipeline_kind: str,
        temporal_workflow_id: str | None = None,
        temporal_run_id: str | None = None,
        statut: StatutDocumentIngestionRun = StatutDocumentIngestionRun.EN_COURS,
        current_step: CurrentStep = CurrentStep.UPLOAD,
    ) -> StyleGuideIngestionRunSnapshot: ...

    async def update_document_source_status(
        self,
        document_source_id: uuid.UUID,
        statut: StatutSource,
        error_message: str | None = None,
        only_if_not_terminal: bool = False,
    ) -> StyleGuideDocumentSourceSnapshot: ...

    async def update_ingestion_run_status(
        self,
        run_id: uuid.UUID,
        *,
        statut: StatutDocumentIngestionRun,
        current_step: CurrentStep | None = None,
        temporal_run_id: str | None = None,
        validation_summary_json: Any | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> StyleGuideIngestionRunSnapshot: ...

    async def record_layout_parse_result(
        self,
        *,
        run_id: uuid.UUID,
        parser_resource_id: str,
        operation_id: str,
        output_uri: str,
    ) -> StyleGuideIngestionRunSnapshot: ...

    async def get_latest_draft_pack(self) -> StyleGuidePackSnapshot | None: ...

    async def get_latest_active_pack(self) -> StyleGuidePackSnapshot | None: ...

    async def list_recent_packs(self, *, limit: int = 5) -> list[StyleGuidePackSnapshot]: ...

    async def get_pack_by_id(
        self,
        style_pack_id: uuid.UUID,
    ) -> StyleGuidePackSnapshot | None: ...

    async def list_rules_for_pack(
        self,
        style_pack_id: uuid.UUID,
    ) -> list[StyleGuideRuleSnapshot]: ...

    async def update_style_rule(
        self,
        *,
        style_pack_id: uuid.UUID,
        rule_id: uuid.UUID,
        texte_regle: str | None = None,
        type_regle: TypeRegle | None = None,
        niveau_contrainte: NiveauContrainte | None = None,
        taxonomie_code: str | None = None,
        decision_editoriale: DecisionEditorialeStyleRule | None = None,
        est_actif: bool | None = None,
        commentaire_review: str | None = None,
        reviewed_by: str,
    ) -> StyleGuideRuleSnapshot: ...

    async def list_taxonomies(self) -> list[StyleGuideTaxonomySnapshot]: ...

    async def replace_draft_style_pack(
        self,
        *,
        document_source_id: uuid.UUID,
        ingestion_run_id: uuid.UUID,
        chunks: list[StyleGuideChunkCandidate],
        candidate: DraftStylePackExtractionV1,
        metadata: StyleGuideDraftPackGenerationMetadata,
    ) -> StyleGuideDraftPackSnapshot: ...

    async def finalize_style_pack_approval(
        self,
        *,
        style_pack_id: uuid.UUID,
    ) -> StyleGuidePackSnapshot: ...

    async def finalize_style_pack_rejection(
        self,
        *,
        style_pack_id: uuid.UUID,
    ) -> StyleGuidePackSnapshot: ...
