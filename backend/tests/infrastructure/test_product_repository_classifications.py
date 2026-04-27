from __future__ import annotations

import uuid

from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    DocumentType,
    StatutDocumentIngestionRun,
    TechnicalReviewCaseType,
    TechnicalReviewSeverity,
    TechnicalReviewStatus,
    TechnicalReviewTriggerSource,
)
from factory_writer.domain.style_guide_types import StatutSource
from factory_writer.infrastructure.database.models.poc_ingestion import (
    DocumentIngestionRun,
    DocumentSource,
    TechnicalReviewCase,
)
from factory_writer.infrastructure.database.repositories.product_repository_mappers import (
    _technical_classifications_to_dict,
)


def test_technical_classifications_expose_label_confidence_and_blocking_reason() -> None:
    ok_source_id = uuid.uuid4()
    bad_source_id = uuid.uuid4()
    run_id = uuid.uuid4()

    run = DocumentIngestionRun(
        id=run_id,
        collection_id=uuid.uuid4(),
        pipeline_kind="TECHNICAL_DOSSIER_EXTRACTION",
        statut=StatutDocumentIngestionRun.A_VALIDER,
        current_step=CurrentStep.HUMAN_REVIEW,
        temporal_workflow_id=f"technical-dossier-{run_id}",
        extraction_steps_json={
            "steps": [
                {
                    "step": "classification",
                    "source_id": str(ok_source_id),
                    "document_type": "TECHNICAL_SHEET",
                    "confidence": 0.996,
                },
                {
                    "step": "classification",
                    "source_id": str(bad_source_id),
                    "document_type": "OUT_OF_SCOPE_DOCUMENT",
                    "confidence": 0.991,
                },
            ],
        },
    )

    results = _technical_classifications_to_dict(
        sources=[
            _source(ok_source_id, "fiche.pdf", DocumentType.TECHNICAL_SHEET, 0.996),
            _source(bad_source_id, "cv.pdf", DocumentType.UNKNOWN, 0.991),
        ],
        run=run,
        review_cases=[
            TechnicalReviewCase(
                ingestion_run_id=run_id,
                source_id=bad_source_id,
                case_type=TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
                trigger_source=TechnicalReviewTriggerSource.CLASSIFIER,
                severity=TechnicalReviewSeverity.BLOCKING,
                status=TechnicalReviewStatus.A_TRAITER,
                field_name="document_type",
                title="Document hors périmètre",
                description="Ce PDF ne correspond pas à un dossier technique produit exploitable.",
                detected_value="OUT_OF_SCOPE_DOCUMENT",
                metadata_json={"is_out_of_scope": True},
            )
        ],
    )

    assert results == [
        {
            "source_id": str(ok_source_id),
            "file_name": "fiche.pdf",
            "document_type": "TECHNICAL_SHEET",
            "confidence": 0.996,
            "is_blocking": False,
            "blocking_reason": None,
        },
        {
            "source_id": str(bad_source_id),
            "file_name": "cv.pdf",
            "document_type": "OUT_OF_SCOPE_DOCUMENT",
            "confidence": 0.991,
            "is_blocking": True,
            "blocking_reason": "OUT_OF_SCOPE",
        },
    ]


def test_technical_classifications_skip_sources_without_classifier_result() -> None:
    source_id = uuid.uuid4()

    results = _technical_classifications_to_dict(
        sources=[_source(source_id, "notice.pdf", DocumentType.UNKNOWN, None)],
        run=None,
        review_cases=[],
    )

    assert results == []


def _source(
    source_id: uuid.UUID,
    file_name: str,
    document_type: DocumentType,
    confidence: float | None,
) -> DocumentSource:
    return DocumentSource(
        id=source_id,
        collection_id=uuid.uuid4(),
        original_file_name=file_name,
        storage_uri=f"gs://bucket/{file_name}",
        storage_bucket="bucket",
        storage_object_name=file_name,
        storage_generation="1",
        storage_metageneration="1",
        storage_content_type="application/pdf",
        storage_size_bytes=42,
        document_type=document_type,
        classification_confidence=confidence,
        statut=StatutSource.EN_COURS,
    )
