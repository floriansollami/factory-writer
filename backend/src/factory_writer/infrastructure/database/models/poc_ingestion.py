from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    JSON,
    BigInteger,
    Boolean,
    CheckConstraint,
    Float,
    ForeignKey,
    Index,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from factory_writer.domain.document_ingestion_types import (
    CollectionKind,
    CurrentStep,
    DecisionEditorialeStyleRule,
    DocumentType,
    ExtractionMethod,
    OrigineStyleRule,
    StatutDocumentCollection,
    StatutDocumentIngestionRun,
    StatutStylePack,
    StatutTechnicalFactCandidate,
    TechnicalFactValidationSource,
    TechnicalReviewCaseType,
    TechnicalReviewResolutionAction,
    TechnicalReviewSeverity,
    TechnicalReviewStatus,
    TechnicalReviewTriggerSource,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle
from factory_writer.infrastructure.database.models.base import BaseModel


class Product(BaseModel):
    __tablename__ = "product"
    __table_args__ = {"comment": "Produit/SKU du POC ingestion documentaire."}

    sku: Mapped[str] = mapped_column(String, unique=True, index=True)
    name: Mapped[str] = mapped_column(String)
    taxonomie_produit_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("taxonomie_produit.id"), index=True
    )
    sous_famille_code: Mapped[str | None] = mapped_column(String, nullable=True)
    season_code: Mapped[str | None] = mapped_column(String, nullable=True)
    segment_prix_code: Mapped[str | None] = mapped_column(String, nullable=True)
    langue_principale: Mapped[str] = mapped_column(String, default="fr-FR")

    taxonomie_produit = relationship("TaxonomieProduit", back_populates="products")
    document_collections = relationship("DocumentCollection", back_populates="product")
    technical_facts = relationship("TechnicalFact", back_populates="product")
    context_snapshots = relationship("ProductContextSnapshot", back_populates="product")


class CommercialSignalSnapshot(BaseModel):
    __tablename__ = "commercial_signal_snapshot"
    __table_args__ = (
        UniqueConstraint("cohort_key", name="uq_commercial_signal_snapshot_cohort_key"),
        {"comment": "Snapshot seedé des historiques de ventes et retours clients du POC."},
    )

    snapshot_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    cohort_key: Mapped[str] = mapped_column(String, index=True)
    famille_code: Mapped[str] = mapped_column(String, index=True)
    segment_prix_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    season_code: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    sales_signals_json: Mapped[Any] = mapped_column(JSON)
    feedback_signals_json: Mapped[Any] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column()
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    product_context_snapshots = relationship(
        "ProductContextSnapshot", back_populates="commercial_signal_snapshot"
    )


class DocumentCollection(BaseModel):
    __tablename__ = "document_collection"
    __table_args__ = (
        CheckConstraint(
            "(collection_kind = 'STYLE_GUIDE' AND product_id IS NULL) "
            "OR (collection_kind = 'TECHNICAL_DOSSIER' AND product_id IS NOT NULL)",
            name="ck_document_collection_kind_product",
        ),
        {"comment": "Dossier metier POC: style guide global ou dossier technique produit."},
    )

    collection_kind: Mapped[CollectionKind] = mapped_column(index=True)
    product_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("product.id"), nullable=True, index=True
    )
    statut: Mapped[StatutDocumentCollection] = mapped_column(
        default=StatutDocumentCollection.EN_ATTENTE
    )
    replaced_by_collection_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_collection.id", ondelete="SET NULL"), nullable=True
    )
    dernier_message_erreur: Mapped[str | None] = mapped_column(Text, nullable=True)

    product = relationship("Product", back_populates="document_collections")
    document_sources = relationship(
        "DocumentSource", back_populates="collection", cascade="all, delete-orphan"
    )
    ingestion_runs = relationship(
        "DocumentIngestionRun", back_populates="collection", cascade="all, delete-orphan"
    )


class DocumentSource(BaseModel):
    __tablename__ = "document_source"
    __table_args__ = (
        UniqueConstraint(
            "storage_bucket",
            "storage_object_name",
            "storage_generation",
            name="uq_document_source_storage_version",
        ),
        {"comment": "Fichier source d'un guide de style ou d'un dossier technique."},
    )

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_collection.id", ondelete="CASCADE"), index=True
    )
    original_file_name: Mapped[str] = mapped_column(String)
    storage_uri: Mapped[str] = mapped_column(String, index=True)
    storage_bucket: Mapped[str] = mapped_column(String)
    storage_object_name: Mapped[str] = mapped_column(String)
    storage_generation: Mapped[str] = mapped_column(String)
    storage_metageneration: Mapped[str] = mapped_column(String)
    storage_content_type: Mapped[str] = mapped_column(String)
    storage_size_bytes: Mapped[int] = mapped_column(BigInteger)
    document_type: Mapped[DocumentType] = mapped_column(default=DocumentType.UNKNOWN, index=True)
    classification_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_score_avg: Mapped[float | None] = mapped_column(Float, nullable=True)
    quality_metadata_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    statut: Mapped[StatutSource] = mapped_column(default=StatutSource.EN_ATTENTE)
    replaced_by_source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_source.id", ondelete="SET NULL"), nullable=True
    )
    dernier_message_erreur: Mapped[str | None] = mapped_column(Text, nullable=True)

    collection = relationship("DocumentCollection", back_populates="document_sources")
    technical_fact_candidates = relationship(
        "TechnicalFactCandidate", back_populates="source", cascade="all, delete-orphan"
    )
    technical_review_cases = relationship("TechnicalReviewCase", back_populates="source")


class DocumentIngestionRun(BaseModel):
    __tablename__ = "document_ingestion_run"
    __table_args__ = {"comment": "Run d'ingestion pilote par Temporal pour le POC documentaire."}

    collection_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_collection.id", ondelete="CASCADE"), index=True
    )
    pipeline_kind: Mapped[str] = mapped_column(String)
    statut: Mapped[StatutDocumentIngestionRun] = mapped_column(
        default=StatutDocumentIngestionRun.EN_ATTENTE
    )
    current_step: Mapped[CurrentStep] = mapped_column(default=CurrentStep.UPLOAD)
    temporal_workflow_id: Mapped[str] = mapped_column(String, unique=True, index=True)
    temporal_run_id: Mapped[str | None] = mapped_column(String, nullable=True)
    extraction_steps_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    validation_summary_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    started_at: Mapped[datetime | None] = mapped_column(nullable=True)
    completed_at: Mapped[datetime | None] = mapped_column(nullable=True)

    collection = relationship("DocumentCollection", back_populates="ingestion_runs")
    style_packs = relationship("StylePack", back_populates="ingestion_run")
    technical_fact_candidates = relationship(
        "TechnicalFactCandidate", back_populates="ingestion_run"
    )
    technical_review_cases = relationship("TechnicalReviewCase", back_populates="ingestion_run")
    product_context_snapshots = relationship(
        "ProductContextSnapshot", back_populates="technical_ingestion_run"
    )


class StylePack(BaseModel):
    __tablename__ = "style_pack"
    __table_args__ = (
        Index(
            "uq_style_pack_est_actif_true",
            "est_actif",
            unique=True,
            postgresql_where=text("est_actif = true"),
        ),
        {"comment": "Pack de style POC genere depuis un run d'ingestion."},
    )

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_ingestion_run.id", ondelete="CASCADE"), index=True
    )
    statut: Mapped[StatutStylePack] = mapped_column(default=StatutStylePack.BROUILLON)
    est_actif: Mapped[bool] = mapped_column(Boolean, default=False)
    prompt_registry_provider: Mapped[str] = mapped_column(String)
    prompt_name: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String)
    llm_model: Mapped[str] = mapped_column(String)
    llm_temperature: Mapped[float] = mapped_column(Float)
    llm_max_tokens: Mapped[int] = mapped_column()
    llm_response_format_name: Mapped[str] = mapped_column(String)
    rendered_system_prompt_hash: Mapped[str] = mapped_column(String)
    rendered_user_prompt_hash: Mapped[str] = mapped_column(String)
    validation_summary_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    approuve_le: Mapped[datetime | None] = mapped_column(nullable=True)

    ingestion_run = relationship("DocumentIngestionRun", back_populates="style_packs")
    style_rules = relationship("StyleRule", back_populates="pack", cascade="all, delete-orphan")
    product_context_snapshots = relationship("ProductContextSnapshot", back_populates="style_pack")


class StyleRule(BaseModel):
    __tablename__ = "style_rule"
    __table_args__ = {"comment": "Regle de style POC avec preuve principale denormalisee."}

    pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("style_pack.id", ondelete="CASCADE"), index=True
    )
    taxonomie_produit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomie_produit.id", ondelete="SET NULL"), nullable=True, index=True
    )
    type_regle: Mapped[TypeRegle] = mapped_column()
    niveau_contrainte: Mapped[NiveauContrainte] = mapped_column()
    texte_regle_original: Mapped[str | None] = mapped_column(Text, nullable=True)
    texte_regle: Mapped[str] = mapped_column(Text)
    decision_editoriale: Mapped[DecisionEditorialeStyleRule] = mapped_column(
        default=DecisionEditorialeStyleRule.A_VALIDER
    )
    est_actif: Mapped[bool] = mapped_column(Boolean, default=False)
    origine: Mapped[OrigineStyleRule] = mapped_column(default=OrigineStyleRule.LLM)
    source_evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence_provider_id: Mapped[str | None] = mapped_column(String, nullable=True)
    source_evidence_page_start: Mapped[int | None] = mapped_column(nullable=True)
    source_evidence_page_end: Mapped[int | None] = mapped_column(nullable=True)
    source_evidence_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    commentaire_review: Mapped[str | None] = mapped_column(Text, nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String, nullable=True)

    pack = relationship("StylePack", back_populates="style_rules")
    taxonomie_produit = relationship("TaxonomieProduit", back_populates="style_rules")


class TechnicalFactCandidate(BaseModel):
    __tablename__ = "technical_fact_candidate"
    __table_args__ = {"comment": "Fact technique candidat extrait avant validation finale."}

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_ingestion_run.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_source.id", ondelete="CASCADE"), index=True
    )
    field_name: Mapped[str] = mapped_column(String, index=True)
    raw_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    normalized_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    extractor_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    extraction_method: Mapped[ExtractionMethod | None] = mapped_column(nullable=True)
    validation_status: Mapped[StatutTechnicalFactCandidate] = mapped_column(
        default=StatutTechnicalFactCandidate.NEEDS_REVIEW
    )
    review_required: Mapped[bool] = mapped_column(Boolean, default=False)
    review_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_evidence_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    source_page: Mapped[int | None] = mapped_column(nullable=True)
    source_bbox_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)
    raw_entity_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    ingestion_run = relationship("DocumentIngestionRun", back_populates="technical_fact_candidates")
    source = relationship("DocumentSource", back_populates="technical_fact_candidates")
    review_cases = relationship("TechnicalReviewCase", back_populates="fact_candidate")
    technical_fact = relationship("TechnicalFact", back_populates="source_candidate", uselist=False)


class TechnicalReviewCase(BaseModel):
    __tablename__ = "technical_review_case"
    __table_args__ = {"comment": "Exception technique a resoudre humainement dans le POC."}

    ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_ingestion_run.id", ondelete="CASCADE"), index=True
    )
    source_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("document_source.id", ondelete="SET NULL"), nullable=True, index=True
    )
    fact_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("technical_fact_candidate.id", ondelete="SET NULL"), nullable=True, index=True
    )
    case_type: Mapped[TechnicalReviewCaseType] = mapped_column(index=True)
    trigger_source: Mapped[TechnicalReviewTriggerSource] = mapped_column()
    severity: Mapped[TechnicalReviewSeverity] = mapped_column()
    status: Mapped[TechnicalReviewStatus] = mapped_column(default=TechnicalReviewStatus.A_TRAITER)
    field_name: Mapped[str | None] = mapped_column(String, nullable=True)
    title: Mapped[str] = mapped_column(String)
    description: Mapped[str] = mapped_column(Text)
    detected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    detected_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    suggested_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    suggested_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    corrected_value: Mapped[str | None] = mapped_column(Text, nullable=True)
    corrected_unit: Mapped[str | None] = mapped_column(String, nullable=True)
    resolution_action: Mapped[TechnicalReviewResolutionAction | None] = mapped_column(nullable=True)
    resolution_comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    resolved_fact_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("technical_fact.id", ondelete="SET NULL"), nullable=True
    )
    resolved_by: Mapped[str | None] = mapped_column(String, nullable=True)
    resolved_at: Mapped[datetime | None] = mapped_column(nullable=True)
    metadata_json: Mapped[Any | None] = mapped_column(JSON, nullable=True)

    ingestion_run = relationship("DocumentIngestionRun", back_populates="technical_review_cases")
    source = relationship("DocumentSource", back_populates="technical_review_cases")
    fact_candidate = relationship("TechnicalFactCandidate", back_populates="review_cases")
    resolved_fact = relationship("TechnicalFact", back_populates="resolved_from_review_case")


class TechnicalFact(BaseModel):
    __tablename__ = "technical_fact"
    __table_args__ = (
        UniqueConstraint("product_id", "field_name", name="uq_technical_fact_product_field_name"),
        UniqueConstraint("source_candidate_id", name="uq_technical_fact_source_candidate_id"),
        {"comment": "Fact technique valide et publiable pour le runtime produit."},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product.id"), index=True)
    source_candidate_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("technical_fact_candidate.id", ondelete="SET NULL"), nullable=True, index=True
    )
    field_name: Mapped[str] = mapped_column(String)
    value: Mapped[str] = mapped_column(Text)
    unit: Mapped[str | None] = mapped_column(String, nullable=True)
    validation_source: Mapped[TechnicalFactValidationSource] = mapped_column()
    validated_at: Mapped[datetime] = mapped_column()
    validated_by: Mapped[str] = mapped_column(String)

    product = relationship("Product", back_populates="technical_facts")
    source_candidate = relationship("TechnicalFactCandidate", back_populates="technical_fact")
    resolved_from_review_case = relationship(
        "TechnicalReviewCase", back_populates="resolved_fact", uselist=False
    )


class ProductContextSnapshot(BaseModel):
    __tablename__ = "product_context_snapshot"
    __table_args__ = (
        UniqueConstraint(
            "product_id",
            "technical_ingestion_run_id",
            name="uq_product_context_snapshot_product_run",
        ),
        {"comment": "Contexte immutable figé avant génération d'une fiche produit."},
    )

    product_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("product.id"), index=True)
    technical_ingestion_run_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("document_ingestion_run.id"), index=True
    )
    style_pack_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("style_pack.id"), index=True)
    commercial_signal_snapshot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("commercial_signal_snapshot.id"), index=True
    )
    technical_fact_ids: Mapped[Any] = mapped_column(JSON)
    snapshot_json: Mapped[Any] = mapped_column(JSON)

    product = relationship("Product", back_populates="context_snapshots")
    technical_ingestion_run = relationship(
        "DocumentIngestionRun", back_populates="product_context_snapshots"
    )
    style_pack = relationship("StylePack", back_populates="product_context_snapshots")
    commercial_signal_snapshot = relationship(
        "CommercialSignalSnapshot", back_populates="product_context_snapshots"
    )
