from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import selectinload

from factory_writer.application.ports.product_technical_ingestion import (
    DocumentSourceSnapshot,
    IngestionRunSnapshot,
    ProductContextSnapshotResult,
    ProductSheetRequirementProfileSnapshot,
    ProductSnapshot,
)
from factory_writer.domain.document_ingestion_types import (
    DocumentType,
    TechnicalReviewCaseType,
    TechnicalReviewStatus,
)
from factory_writer.infrastructure.database.models.poc_ingestion import (
    CommercialSignalSnapshot,
    DocumentCollection,
    DocumentIngestionRun,
    DocumentSource,
    Product,
    ProductContextSnapshot,
    ProductSheetRequirementProfile,
    TechnicalFact,
    TechnicalFactCandidate,
    TechnicalReviewCase,
)
from factory_writer.infrastructure.database.models.taxonomy import TaxonomieProduit


def _choose_commercial_snapshot(
    product: ProductSnapshot,
    snapshots: list[CommercialSignalSnapshot],
) -> tuple[CommercialSignalSnapshot, str]:
    for snapshot in snapshots:
        if _commercial_snapshot_matches_product(product=product, snapshot=snapshot):
            return snapshot, "matched_family_segment_season"

    raise RuntimeError(_commercial_snapshot_missing_message(product))


def _product_sheet_requirement_profile_specificity(
    *,
    product: ProductSnapshot,
    profile: ProductSheetRequirementProfile,
) -> tuple[int, int]:
    family_score = 2 if profile.famille_code == product.famille_code else 0
    subfamily_score = (
        2
        if profile.sous_famille_code == product.sous_famille_code
        else 1
        if profile.sous_famille_code in {None, "*"}
        else 0
    )
    return family_score, subfamily_score


def _to_product_sheet_requirement_profile_snapshot(
    profile: ProductSheetRequirementProfile,
) -> ProductSheetRequirementProfileSnapshot:
    return ProductSheetRequirementProfileSnapshot(
        id=profile.id,
        famille_code=profile.famille_code,
        sous_famille_code=profile.sous_famille_code,
        requirements_json=profile.requirements_json,
    )


def _commercial_snapshot_matches_product(
    *,
    product: ProductSnapshot,
    snapshot: CommercialSignalSnapshot,
) -> bool:
    return (
        snapshot.famille_code == product.famille_code
        and snapshot.segment_prix_code == product.segment_prix_code
        and snapshot.season_code == product.season_code
    )


def _commercial_snapshot_missing_message(product: ProductSnapshot) -> str:
    return (
        "Aucun snapshot commercial actif compatible "
        f"pour famille={product.famille_code}, "
        f"saison={product.season_code}, "
        f"segment={product.segment_prix_code}."
    )


def _active_current_sources(sources: list[DocumentSource]) -> tuple[DocumentSource, ...]:
    sources_by_file_name: dict[str, DocumentSource] = {}
    for source in sources:
        if source.replaced_by_source_id is not None:
            continue

        current_source = sources_by_file_name.get(source.original_file_name)
        if current_source is None or source.created_at > current_source.created_at:
            sources_by_file_name[source.original_file_name] = source

    return tuple(
        sorted(
            sources_by_file_name.values(),
            key=lambda source: (source.created_at, source.original_file_name),
        )
    )


def _product_taxonomy_load_option() -> Any:
    return selectinload(Product.taxonomie_produit).selectinload(TaxonomieProduit.parent)


def _to_document_type(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError:
        return DocumentType.UNKNOWN


def _is_routable_technical_document_type(value: str | None) -> bool:
    return value in {
        DocumentType.TECHNICAL_SHEET.value,
        DocumentType.ASSEMBLY_NOTICE.value,
        DocumentType.MATERIAL_SPECIFICATION.value,
    }


def _to_product_context_snapshot_result(
    snapshot: ProductContextSnapshot,
) -> ProductContextSnapshotResult:
    return ProductContextSnapshotResult(
        id=snapshot.id,
        product_id=snapshot.product_id,
        technical_ingestion_run_id=snapshot.technical_ingestion_run_id,
        style_pack_id=snapshot.style_pack_id,
        commercial_signal_snapshot_id=snapshot.commercial_signal_snapshot_id,
        technical_fact_ids=tuple(uuid.UUID(value) for value in snapshot.technical_fact_ids),
    )


def _product_to_dict(product: ProductSnapshot) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "famille_code": product.famille_code,
        "sous_famille_code": product.sous_famille_code,
        "season_code": product.season_code,
        "segment_prix_code": product.segment_prix_code,
        "langue_principale": product.langue_principale,
    }


def _collection_to_dict(collection: DocumentCollection) -> dict[str, Any]:
    return {
        "id": str(collection.id),
        "kind": collection.collection_kind.value,
        "statut": collection.statut.value,
    }


def _source_to_dict(source: DocumentSourceSnapshot) -> dict[str, Any]:
    return {
        "id": str(source.id),
        "collection_id": str(source.collection_id),
        "original_file_name": source.original_file_name,
        "storage_uri": source.storage_uri,
        "storage_generation": source.storage_generation,
        "storage_metageneration": source.storage_metageneration,
        "storage_content_type": source.storage_content_type,
        "storage_size_bytes": source.storage_size_bytes,
        "document_type": source.document_type,
        "classification_confidence": source.classification_confidence,
        "statut": source.statut,
        "created_at": source.created_at.isoformat() if source.created_at is not None else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at is not None else None,
    }


def _run_to_dict(run: IngestionRunSnapshot) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "collection_id": str(run.collection_id),
        "workflow_id": run.workflow_id,
        "statut": run.statut,
        "current_step": run.current_step,
        "validation_summary_json": run.validation_summary_json,
        "extraction_steps_json": run.extraction_steps_json,
        "created_at": run.created_at.isoformat() if run.created_at is not None else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at is not None else None,
        "started_at": run.started_at.isoformat() if run.started_at is not None else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at is not None else None,
    }


def _technical_fact_to_dict(fact: TechnicalFact) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "field_name": fact.field_name,
        "occurrence_index": fact.occurrence_index,
        "value": fact.value,
        "unit": fact.unit,
        "validation_source": fact.validation_source.value,
        "validated_at": fact.validated_at.isoformat(),
    }


def _candidate_to_dict(candidate: TechnicalFactCandidate) -> dict[str, Any]:
    return {
        "id": str(candidate.id),
        "source_id": str(candidate.source_id),
        "field_name": candidate.field_name,
        "raw_value": candidate.raw_value,
        "normalized_value": candidate.normalized_value,
        "unit": candidate.unit,
        "extractor_confidence": candidate.extractor_confidence,
        "validation_status": candidate.validation_status.value,
        "source_page": candidate.source_page,
    }


def _technical_classifications_to_dict(
    *,
    sources: list[DocumentSource],
    run: DocumentIngestionRun | None,
    review_cases: list[TechnicalReviewCase],
) -> list[dict[str, Any]]:
    classification_steps_by_source_id = _classification_steps_by_source_id(run)
    blocking_cases_by_source_id = _blocking_classification_cases_by_source_id(review_cases)
    results: list[dict[str, Any]] = []

    for source in sources:
        source_id = str(source.id)
        step = classification_steps_by_source_id.get(source_id, {})
        blocking_case = blocking_cases_by_source_id.get(source_id)
        has_classification_result = (
            bool(step)
            or source.classification_confidence is not None
            or source.document_type != DocumentType.UNKNOWN
            or blocking_case is not None
        )
        if not has_classification_result:
            continue

        document_type = _optional_string(step.get("document_type")) or source.document_type.value
        confidence = _optional_float(step.get("confidence"))
        if confidence is None:
            confidence = source.classification_confidence

        blocking_reason = _classification_blocking_reason(
            document_type=document_type,
            confidence=confidence,
            blocking_case=blocking_case,
        )

        results.append(
            {
                "source_id": source_id,
                "file_name": source.original_file_name,
                "document_type": document_type,
                "confidence": confidence,
                "is_blocking": blocking_reason is not None,
                "blocking_reason": blocking_reason,
            }
        )

    return results


def _classification_steps_by_source_id(
    run: DocumentIngestionRun | None,
) -> dict[str, dict[str, Any]]:
    extraction_steps_json = run.extraction_steps_json if run is not None else None
    if not isinstance(extraction_steps_json, dict):
        return {}

    steps = extraction_steps_json.get("steps")
    if not isinstance(steps, list):
        return {}

    indexed_steps: dict[str, dict[str, Any]] = {}
    for step in steps:
        if not isinstance(step, dict) or step.get("step") != "classification":
            continue

        source_id = _optional_string(step.get("source_id"))
        if source_id is not None:
            indexed_steps[source_id] = step

    return indexed_steps


def _blocking_classification_cases_by_source_id(
    review_cases: list[TechnicalReviewCase],
) -> dict[str, TechnicalReviewCase]:
    blocking_cases: dict[str, TechnicalReviewCase] = {}

    for review_case in review_cases:
        if (
            review_case.case_type != TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN
            or review_case.source_id is None
            or review_case.status
            not in {
                TechnicalReviewStatus.A_TRAITER,
                TechnicalReviewStatus.DOCUMENT_A_REMPLACER,
            }
        ):
            continue

        blocking_cases[str(review_case.source_id)] = review_case

    return blocking_cases


def _classification_blocking_reason(
    *,
    document_type: str,
    confidence: float | None,
    blocking_case: TechnicalReviewCase | None,
) -> str | None:
    if blocking_case is None:
        return None

    metadata_json = blocking_case.metadata_json
    is_out_of_scope = (
        isinstance(metadata_json, dict) and metadata_json.get("is_out_of_scope") is True
    )
    if is_out_of_scope or not _is_routable_technical_document_type(document_type):
        return "OUT_OF_SCOPE"

    if confidence is None:
        return "MISSING_CONFIDENCE"

    return "LOW_CONFIDENCE"


def _review_case_to_dict(review_case: TechnicalReviewCase) -> dict[str, Any]:
    return {
        "id": str(review_case.id),
        "source_id": str(review_case.source_id) if review_case.source_id else None,
        "case_type": review_case.case_type.value,
        "severity": review_case.severity.value,
        "status": review_case.status.value,
        "field_name": review_case.field_name,
        "title": review_case.title,
        "description": review_case.description,
        "detected_value": review_case.detected_value,
        "detected_unit": review_case.detected_unit,
        "suggested_value": review_case.suggested_value,
        "suggested_unit": review_case.suggested_unit,
        "corrected_value": review_case.corrected_value,
        "corrected_unit": review_case.corrected_unit,
        "resolution_action": (
            review_case.resolution_action.value if review_case.resolution_action else None
        ),
        "resolution_comment": review_case.resolution_comment,
        "metadata_json": review_case.metadata_json,
    }


def _review_case_occurrence_index(review_case: TechnicalReviewCase) -> int:
    metadata = review_case.metadata_json if isinstance(review_case.metadata_json, dict) else {}
    raw_value = metadata.get("occurrence_index")
    return raw_value if isinstance(raw_value, int) and raw_value >= 0 else 0


def _review_case_metadata_with_candidate_ids(
    metadata_json: Any | None,
    persisted_candidates: list[TechnicalFactCandidate],
) -> Any | None:
    if not isinstance(metadata_json, dict):
        return metadata_json

    metadata = dict(metadata_json)
    candidate_index = metadata.get("candidate_index")
    if isinstance(candidate_index, int) and 0 <= candidate_index < len(persisted_candidates):
        metadata["candidate_id"] = str(persisted_candidates[candidate_index].id)

    candidates = metadata.get("candidates")
    if isinstance(candidates, list):
        enriched_candidates: list[Any] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                enriched_candidates.append(candidate)
                continue
            enriched = dict(candidate)
            nested_candidate_index = enriched.get("candidate_index")
            if isinstance(nested_candidate_index, int) and 0 <= nested_candidate_index < len(
                persisted_candidates
            ):
                enriched["candidate_id"] = str(persisted_candidates[nested_candidate_index].id)
            enriched_candidates.append(enriched)
        metadata["candidates"] = enriched_candidates

    return metadata


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
