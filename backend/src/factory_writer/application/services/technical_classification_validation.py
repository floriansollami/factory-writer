from __future__ import annotations

import uuid

from factory_writer.application.ports.product_technical_ingestion import (
    TechnicalClassificationPayload,
    TechnicalReviewCaseInput,
)
from factory_writer.domain.document_ingestion_types import (
    DocumentType,
    TechnicalReviewCaseType,
    TechnicalReviewSeverity,
    TechnicalReviewTriggerSource,
)

_ROUTABLE_TECHNICAL_DOCUMENT_TYPES = {
    DocumentType.TECHNICAL_SHEET.value,
    DocumentType.ASSEMBLY_NOTICE.value,
    DocumentType.MATERIAL_SPECIFICATION.value,
}


def classification_review_cases(
    classifications: tuple[TechnicalClassificationPayload, ...],
    *,
    threshold: float,
) -> list[TechnicalReviewCaseInput]:
    return [
        _classification_review_case(classification, threshold)
        for classification in classifications
        if classification.document_type not in _ROUTABLE_TECHNICAL_DOCUMENT_TYPES
        or classification.confidence is None
        or classification.confidence < threshold
    ]


def _classification_review_case(
    classification: TechnicalClassificationPayload,
    threshold: float,
) -> TechnicalReviewCaseInput:
    document_type = classification.document_type
    is_out_of_scope = document_type not in _ROUTABLE_TECHNICAL_DOCUMENT_TYPES
    classifier_metadata = classification.quality_metadata_json.get("classifier", {})

    return TechnicalReviewCaseInput(
        source_id=uuid.UUID(classification.document_source_id),
        candidate_index=None,
        case_type=TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
        trigger_source=TechnicalReviewTriggerSource.CLASSIFIER,
        severity=TechnicalReviewSeverity.BLOCKING,
        field_name="document_type",
        title="Document hors périmètre" if is_out_of_scope else "Type de document à confirmer",
        description=(
            "Ce PDF ne correspond pas à un dossier technique produit exploitable."
            if is_out_of_scope
            else (
                "Le classifier Document AI n'a pas assez de confiance pour router ce "
                "PDF vers le bon extracteur."
            )
        ),
        detected_value=document_type,
        metadata_json={
            "confidence": classification.confidence,
            "threshold": threshold,
            "is_out_of_scope": is_out_of_scope,
            "processor_resource_name": classifier_metadata.get("processor_resource_name"),
            "processor_version": classifier_metadata.get("processor_version"),
            "source_id": classification.document_source_id,
        },
    )
