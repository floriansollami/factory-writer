"""add poc ingestion schema

Revision ID: 20260421_0002
Revises: 20260415_0001
Create Date: 2026-04-21 09:10:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260421_0002"
down_revision: str | None = "20260415_0001"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


collection_kind_enum = sa.Enum(
    "STYLE_GUIDE",
    "TECHNICAL_DOSSIER",
    name="collectionkind",
)
document_type_enum = sa.Enum(
    "STYLE_GUIDE",
    "TECHNICAL_SHEET",
    "BLUEPRINT",
    "ECO_CERTIFICATE",
    "ASSEMBLY_NOTICE",
    "MATERIAL_SPECIFICATION",
    "UNKNOWN",
    name="documenttype",
)
document_collection_statut_enum = sa.Enum(
    "EN_ATTENTE",
    "EN_COURS",
    "A_VALIDER",
    "TERMINE",
    "ERREUR",
    name="statutdocumentcollection",
)
document_ingestion_run_statut_enum = sa.Enum(
    "EN_ATTENTE",
    "EN_COURS",
    "A_VALIDER",
    "TERMINE",
    "ERREUR",
    "ANNULE",
    name="statutdocumentingestionrun",
)
current_step_enum = sa.Enum(
    "UPLOAD",
    "DOCUMENT_CLASSIFICATION",
    "OCR_PROOF",
    "LAYOUT_PARSE",
    "FACT_EXTRACTION",
    "DETERMINISTIC_VALIDATION",
    "LLM_DRAFT_PACK",
    "HUMAN_REVIEW",
    "PROMOTION",
    "DONE",
    name="currentstep",
)
style_pack_statut_enum = sa.Enum(
    "BROUILLON",
    "ACTIF",
    "ARCHIVE",
    name="statutstylepack",
)
decision_editoriale_enum = sa.Enum(
    "A_VALIDER",
    "APPROUVEE",
    "DESACTIVEE",
    name="decisioneditorialestylerule",
)
origine_style_rule_enum = sa.Enum(
    "LLM",
    "HUMAIN",
    "MODIFIEE",
    name="originestylerule",
)
extraction_method_enum = sa.Enum(
    "EXTRACT",
    "DERIVE",
    name="extractionmethod",
)
technical_fact_candidate_statut_enum = sa.Enum(
    "AUTO_VALIDATED",
    "NEEDS_REVIEW",
    "REJECTED",
    "PROMOTED",
    name="statuttechnicalfactcandidate",
)
technical_review_case_type_enum = sa.Enum(
    "CLASSIFICATION_UNCERTAIN",
    "LOW_OCR_QUALITY",
    "DOCUMENT_UNREADABLE",
    "MISSING_REQUIRED_FIELD",
    "LOW_CONFIDENCE",
    "VALUE_OUT_OF_RANGE",
    "EXACT_MATCH_FAILED",
    "CONTRADICTION",
    "LLM_SELF_CHECK_FLAG",
    name="technicalreviewcasetype",
)
technical_review_trigger_source_enum = sa.Enum(
    "CLASSIFIER",
    "OCR",
    "CUSTOM_EXTRACTOR",
    "PYTHON_VALIDATOR",
    "LLM_SELF_CHECK",
    name="technicalreviewtriggersource",
)
technical_review_severity_enum = sa.Enum(
    "BLOCKING",
    "WARNING",
    name="technicalreviewseverity",
)
technical_review_status_enum = sa.Enum(
    "A_TRAITER",
    "APPROUVE",
    "CORRIGE",
    "REJETE",
    "DOCUMENT_A_REMPLACER",
    name="technicalreviewstatus",
)
technical_review_resolution_action_enum = sa.Enum(
    "APPROVE_DETECTED_VALUE",
    "CORRECT_VALUE",
    "REJECT_VALUE",
    "REQUEST_NEW_DOCUMENT",
    name="technicalreviewresolutionaction",
)
technical_fact_validation_source_enum = sa.Enum(
    "SYSTEM",
    "HUMAN",
    name="technicalfactvalidationsource",
)

# Enums existants re-utilises par les nouvelles tables
statut_source_enum = sa.Enum(
    "EN_ATTENTE",
    "EN_COURS",
    "TERMINE",
    "ERREUR",
    name="statutsource",
    create_type=False,
)
type_regle_enum = sa.Enum(
    "VOIX",
    "TON",
    "FORMATAGE",
    "PROMESSE_INTERDITE",
    name="typeregle",
    create_type=False,
)
niveau_contrainte_enum = sa.Enum(
    "HARD",
    "SOFT",
    name="niveaucontrainte",
    create_type=False,
)


def upgrade() -> None:
    op.create_table(
        "product",
        sa.Column("sku", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("taxonomie_produit_id", sa.Uuid(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["taxonomie_produit_id"], ["taxonomie_produit.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="Produit/SKU du POC ingestion documentaire.",
    )
    op.create_index(op.f("ix_product_sku"), "product", ["sku"], unique=True)
    op.create_index(
        op.f("ix_product_taxonomie_produit_id"), "product", ["taxonomie_produit_id"], unique=False
    )

    op.create_table(
        "document_collection",
        sa.Column("collection_kind", collection_kind_enum, nullable=False),
        sa.Column("product_id", sa.Uuid(), nullable=True),
        sa.Column(
            "statut",
            document_collection_statut_enum,
            nullable=False,
            server_default="EN_ATTENTE",
        ),
        sa.Column("replaced_by_collection_id", sa.Uuid(), nullable=True),
        sa.Column("dernier_message_erreur", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.CheckConstraint(
            "(collection_kind = 'STYLE_GUIDE' AND product_id IS NULL) "
            "OR (collection_kind = 'TECHNICAL_DOSSIER' AND product_id IS NOT NULL)",
            name="ck_document_collection_kind_product",
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(
            ["replaced_by_collection_id"],
            ["document_collection.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Dossier metier POC: style guide global ou dossier technique produit.",
    )
    op.create_index(
        op.f("ix_document_collection_collection_kind"),
        "document_collection",
        ["collection_kind"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_collection_product_id"),
        "document_collection",
        ["product_id"],
        unique=False,
    )

    op.create_table(
        "document_source",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("original_file_name", sa.String(), nullable=False),
        sa.Column("storage_uri", sa.String(), nullable=False),
        sa.Column("storage_bucket", sa.String(), nullable=False),
        sa.Column("storage_object_name", sa.String(), nullable=False),
        sa.Column("storage_generation", sa.String(), nullable=False),
        sa.Column("storage_metageneration", sa.String(), nullable=False),
        sa.Column("storage_content_type", sa.String(), nullable=False),
        sa.Column("storage_size_bytes", sa.BigInteger(), nullable=False),
        sa.Column(
            "document_type",
            document_type_enum,
            nullable=False,
            server_default="UNKNOWN",
        ),
        sa.Column("classification_confidence", sa.Float(), nullable=True),
        sa.Column("quality_score_min", sa.Float(), nullable=True),
        sa.Column("quality_score_avg", sa.Float(), nullable=True),
        sa.Column("quality_metadata_json", sa.JSON(), nullable=True),
        sa.Column("statut", statut_source_enum, nullable=False, server_default="EN_ATTENTE"),
        sa.Column("replaced_by_source_id", sa.Uuid(), nullable=True),
        sa.Column("dernier_message_erreur", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["document_collection.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["replaced_by_source_id"],
            ["document_source.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "storage_bucket",
            "storage_object_name",
            "storage_generation",
            name="uq_document_source_storage_version",
        ),
        comment="Fichier source d'un guide de style ou d'un dossier technique.",
    )
    op.create_index(
        op.f("ix_document_source_collection_id"), "document_source", ["collection_id"], unique=False
    )
    op.create_index(
        op.f("ix_document_source_document_type"), "document_source", ["document_type"], unique=False
    )
    op.create_index(
        op.f("ix_document_source_storage_uri"), "document_source", ["storage_uri"], unique=False
    )

    op.create_table(
        "document_ingestion_run",
        sa.Column("collection_id", sa.Uuid(), nullable=False),
        sa.Column("pipeline_kind", sa.String(), nullable=False),
        sa.Column(
            "statut",
            document_ingestion_run_statut_enum,
            nullable=False,
            server_default="EN_ATTENTE",
        ),
        sa.Column("current_step", current_step_enum, nullable=False, server_default="UPLOAD"),
        sa.Column("temporal_workflow_id", sa.String(), nullable=False),
        sa.Column("temporal_run_id", sa.String(), nullable=True),
        sa.Column("extraction_steps_json", sa.JSON(), nullable=True),
        sa.Column("validation_summary_json", sa.JSON(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(), nullable=True),
        sa.Column("completed_at", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["collection_id"],
            ["document_collection.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Run d'ingestion pilote par Temporal pour le POC documentaire.",
    )
    op.create_index(
        op.f("ix_document_ingestion_run_collection_id"),
        "document_ingestion_run",
        ["collection_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_document_ingestion_run_temporal_workflow_id"),
        "document_ingestion_run",
        ["temporal_workflow_id"],
        unique=True,
    )

    op.create_table(
        "style_pack",
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column(
            "statut",
            style_pack_statut_enum,
            nullable=False,
            server_default="BROUILLON",
        ),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("prompt_registry_provider", sa.String(), nullable=False),
        sa.Column("prompt_name", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("llm_model", sa.String(), nullable=False),
        sa.Column("llm_temperature", sa.Float(), nullable=False),
        sa.Column("llm_max_tokens", sa.Integer(), nullable=False),
        sa.Column("llm_response_format_name", sa.String(), nullable=False),
        sa.Column("rendered_system_prompt_hash", sa.String(), nullable=False),
        sa.Column("rendered_user_prompt_hash", sa.String(), nullable=False),
        sa.Column("validation_summary_json", sa.JSON(), nullable=True),
        sa.Column("approuve_le", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["document_ingestion_run.id"],
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Pack de style POC genere depuis un run d'ingestion.",
    )
    op.create_index(
        op.f("ix_style_pack_ingestion_run_id"), "style_pack", ["ingestion_run_id"], unique=False
    )
    op.create_index(
        "uq_style_pack_est_actif_true",
        "style_pack",
        ["est_actif"],
        unique=True,
        postgresql_where=sa.text("est_actif = true"),
    )

    op.create_table(
        "style_rule",
        sa.Column("pack_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomie_produit_id", sa.Uuid(), nullable=True),
        sa.Column("type_regle", type_regle_enum, nullable=False),
        sa.Column("niveau_contrainte", niveau_contrainte_enum, nullable=False),
        sa.Column("texte_regle_original", sa.Text(), nullable=True),
        sa.Column("texte_regle", sa.Text(), nullable=False),
        sa.Column(
            "decision_editoriale",
            decision_editoriale_enum,
            nullable=False,
            server_default="A_VALIDER",
        ),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("origine", origine_style_rule_enum, nullable=False, server_default="LLM"),
        sa.Column("source_evidence_text", sa.Text(), nullable=True),
        sa.Column("source_evidence_provider_id", sa.String(), nullable=True),
        sa.Column("source_evidence_page_start", sa.Integer(), nullable=True),
        sa.Column("source_evidence_page_end", sa.Integer(), nullable=True),
        sa.Column("source_evidence_json", sa.JSON(), nullable=True),
        sa.Column("commentaire_review", sa.Text(), nullable=True),
        sa.Column("reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("reviewed_by", sa.String(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["pack_id"], ["style_pack.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["taxonomie_produit_id"],
            ["taxonomie_produit.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        comment="Regle de style POC avec preuve principale denormalisee.",
    )
    op.create_index(op.f("ix_style_rule_pack_id"), "style_rule", ["pack_id"], unique=False)
    op.create_index(
        op.f("ix_style_rule_taxonomie_produit_id"),
        "style_rule",
        ["taxonomie_produit_id"],
        unique=False,
    )

    op.create_table(
        "technical_fact_candidate",
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("raw_value", sa.Text(), nullable=True),
        sa.Column("normalized_value", sa.Text(), nullable=True),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("extractor_confidence", sa.Float(), nullable=True),
        sa.Column("extraction_method", extraction_method_enum, nullable=True),
        sa.Column(
            "validation_status",
            technical_fact_candidate_statut_enum,
            nullable=False,
            server_default="NEEDS_REVIEW",
        ),
        sa.Column("review_required", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("review_reason", sa.Text(), nullable=True),
        sa.Column("source_evidence_text", sa.Text(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_bbox_json", sa.JSON(), nullable=True),
        sa.Column("raw_entity_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["document_ingestion_run.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["document_source.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        comment="Fact technique candidat extrait avant validation finale.",
    )
    op.create_index(
        op.f("ix_technical_fact_candidate_field_name"),
        "technical_fact_candidate",
        ["field_name"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_fact_candidate_ingestion_run_id"),
        "technical_fact_candidate",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_fact_candidate_source_id"),
        "technical_fact_candidate",
        ["source_id"],
        unique=False,
    )

    op.create_table(
        "technical_fact",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("source_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("field_name", sa.String(), nullable=False),
        sa.Column("value", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(), nullable=True),
        sa.Column("validation_source", technical_fact_validation_source_enum, nullable=False),
        sa.Column("validated_at", sa.DateTime(), nullable=False),
        sa.Column("validated_by", sa.String(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(
            ["source_candidate_id"],
            ["technical_fact_candidate.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id", "field_name", name="uq_technical_fact_product_field_name"
        ),
        sa.UniqueConstraint("source_candidate_id", name="uq_technical_fact_source_candidate_id"),
        comment="Fact technique valide et publiable pour le runtime produit.",
    )
    op.create_index(
        op.f("ix_technical_fact_product_id"), "technical_fact", ["product_id"], unique=False
    )
    op.create_index(
        op.f("ix_technical_fact_source_candidate_id"),
        "technical_fact",
        ["source_candidate_id"],
        unique=False,
    )

    op.create_table(
        "technical_review_case",
        sa.Column("ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("source_id", sa.Uuid(), nullable=True),
        sa.Column("fact_candidate_id", sa.Uuid(), nullable=True),
        sa.Column("case_type", technical_review_case_type_enum, nullable=False),
        sa.Column("trigger_source", technical_review_trigger_source_enum, nullable=False),
        sa.Column("severity", technical_review_severity_enum, nullable=False),
        sa.Column(
            "status",
            technical_review_status_enum,
            nullable=False,
            server_default="A_TRAITER",
        ),
        sa.Column("field_name", sa.String(), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("detected_value", sa.Text(), nullable=True),
        sa.Column("detected_unit", sa.String(), nullable=True),
        sa.Column("suggested_value", sa.Text(), nullable=True),
        sa.Column("suggested_unit", sa.String(), nullable=True),
        sa.Column("corrected_value", sa.Text(), nullable=True),
        sa.Column("corrected_unit", sa.String(), nullable=True),
        sa.Column("resolution_action", technical_review_resolution_action_enum, nullable=True),
        sa.Column("resolution_comment", sa.Text(), nullable=True),
        sa.Column("resolved_fact_id", sa.Uuid(), nullable=True),
        sa.Column("resolved_by", sa.String(), nullable=True),
        sa.Column("resolved_at", sa.DateTime(), nullable=True),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["fact_candidate_id"],
            ["technical_fact_candidate.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(
            ["ingestion_run_id"],
            ["document_ingestion_run.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["resolved_fact_id"],
            ["technical_fact.id"],
            ondelete="SET NULL",
        ),
        sa.ForeignKeyConstraint(["source_id"], ["document_source.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        comment="Exception technique a resoudre humainement dans le POC.",
    )
    op.create_index(
        op.f("ix_technical_review_case_case_type"),
        "technical_review_case",
        ["case_type"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_review_case_fact_candidate_id"),
        "technical_review_case",
        ["fact_candidate_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_review_case_ingestion_run_id"),
        "technical_review_case",
        ["ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_technical_review_case_source_id"),
        "technical_review_case",
        ["source_id"],
        unique=False,
    )

    op.execute(
        "COMMENT ON TABLE source_guide_style IS "
        "'DEPRECATED: ancien schema style guide, remplace par document_collection/document_source.'"
    )
    op.execute(
        "COMMENT ON TABLE fragment_style IS "
        "'DEPRECATED: ancien schema fragment_style, remplace par style_rule.source_evidence_*.'"
    )
    op.execute(
        "COMMENT ON TABLE pack_style IS "
        "'DEPRECATED: ancien schema pack_style, remplace par style_pack.'"
    )
    op.execute(
        "COMMENT ON TABLE regle_style IS "
        "'DEPRECATED: ancien schema regle_style, remplace par style_rule.'"
    )


def downgrade() -> None:
    op.execute("COMMENT ON TABLE regle_style IS NULL")
    op.execute("COMMENT ON TABLE pack_style IS NULL")
    op.execute("COMMENT ON TABLE fragment_style IS NULL")
    op.execute("COMMENT ON TABLE source_guide_style IS NULL")

    op.drop_index(op.f("ix_technical_review_case_source_id"), table_name="technical_review_case")
    op.drop_index(
        op.f("ix_technical_review_case_ingestion_run_id"), table_name="technical_review_case"
    )
    op.drop_index(
        op.f("ix_technical_review_case_fact_candidate_id"), table_name="technical_review_case"
    )
    op.drop_index(op.f("ix_technical_review_case_case_type"), table_name="technical_review_case")
    op.drop_table("technical_review_case")

    op.drop_index(op.f("ix_technical_fact_source_candidate_id"), table_name="technical_fact")
    op.drop_index(op.f("ix_technical_fact_product_id"), table_name="technical_fact")
    op.drop_table("technical_fact")

    op.drop_index(
        op.f("ix_technical_fact_candidate_source_id"), table_name="technical_fact_candidate"
    )
    op.drop_index(
        op.f("ix_technical_fact_candidate_ingestion_run_id"),
        table_name="technical_fact_candidate",
    )
    op.drop_index(
        op.f("ix_technical_fact_candidate_field_name"),
        table_name="technical_fact_candidate",
    )
    op.drop_table("technical_fact_candidate")

    op.drop_index(op.f("ix_style_rule_taxonomie_produit_id"), table_name="style_rule")
    op.drop_index(op.f("ix_style_rule_pack_id"), table_name="style_rule")
    op.drop_table("style_rule")

    op.drop_index("uq_style_pack_est_actif_true", table_name="style_pack")
    op.drop_index(op.f("ix_style_pack_ingestion_run_id"), table_name="style_pack")
    op.drop_table("style_pack")

    op.drop_index(
        op.f("ix_document_ingestion_run_temporal_workflow_id"),
        table_name="document_ingestion_run",
    )
    op.drop_index(
        op.f("ix_document_ingestion_run_collection_id"),
        table_name="document_ingestion_run",
    )
    op.drop_table("document_ingestion_run")

    op.drop_index(op.f("ix_document_source_storage_uri"), table_name="document_source")
    op.drop_index(op.f("ix_document_source_document_type"), table_name="document_source")
    op.drop_index(op.f("ix_document_source_collection_id"), table_name="document_source")
    op.drop_table("document_source")

    op.drop_index(op.f("ix_document_collection_product_id"), table_name="document_collection")
    op.drop_index(op.f("ix_document_collection_collection_kind"), table_name="document_collection")
    op.drop_table("document_collection")

    op.drop_index(op.f("ix_product_taxonomie_produit_id"), table_name="product")
    op.drop_index(op.f("ix_product_sku"), table_name="product")
    op.drop_table("product")

    bind = op.get_bind()
    technical_fact_validation_source_enum.drop(bind, checkfirst=True)
    technical_review_resolution_action_enum.drop(bind, checkfirst=True)
    technical_review_status_enum.drop(bind, checkfirst=True)
    technical_review_severity_enum.drop(bind, checkfirst=True)
    technical_review_trigger_source_enum.drop(bind, checkfirst=True)
    technical_review_case_type_enum.drop(bind, checkfirst=True)
    technical_fact_candidate_statut_enum.drop(bind, checkfirst=True)
    extraction_method_enum.drop(bind, checkfirst=True)
    origine_style_rule_enum.drop(bind, checkfirst=True)
    decision_editoriale_enum.drop(bind, checkfirst=True)
    style_pack_statut_enum.drop(bind, checkfirst=True)
    current_step_enum.drop(bind, checkfirst=True)
    document_ingestion_run_statut_enum.drop(bind, checkfirst=True)
    document_collection_statut_enum.drop(bind, checkfirst=True)
    document_type_enum.drop(bind, checkfirst=True)
    collection_kind_enum.drop(bind, checkfirst=True)
