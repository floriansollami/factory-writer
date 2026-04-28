from __future__ import annotations

import uuid
from dataclasses import asdict
from typing import Any

from factory_writer.application.ports.product_technical_ingestion import (
    STATUS_WAITING_COMMERCIAL_SNAPSHOT,
    STATUS_WAITING_STYLE_PACK,
    STATUS_WAITING_TECH_FACTS,
    DocumentSourceSnapshot,
    IngestionRunSnapshot,
    ProductContextReference,
    ProductSnapshot,
    ProductTaxonomySnapshot,
    PromotedTechnicalFactInput,
    PromotedTechnicalFactPayload,
    TechnicalDocumentSourceReference,
    TechnicalFactCandidateInput,
    TechnicalFactCandidatePayload,
    TechnicalFactSnapshot,
    TechnicalReviewCaseInput,
    TechnicalReviewCasePayload,
)
from factory_writer.domain.document_ingestion_types import (
    StatutTechnicalFactCandidate,
    TechnicalReviewCaseType,
    TechnicalReviewSeverity,
    TechnicalReviewTriggerSource,
)


def _source_snapshot_to_ref(source: DocumentSourceSnapshot) -> TechnicalDocumentSourceReference:
    return TechnicalDocumentSourceReference(
        document_source_id=str(source.id),
        storage_uri=source.storage_uri,
        mime_type=source.storage_content_type,
    )


def _candidate_input_to_payload(
    candidate: TechnicalFactCandidateInput,
) -> TechnicalFactCandidatePayload:
    return TechnicalFactCandidatePayload(
        source_id=str(candidate.source_id),
        field_name=candidate.field_name,
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        unit=candidate.unit,
        extractor_confidence=candidate.extractor_confidence,
        validation_status=candidate.validation_status.value,
        source_page=candidate.source_page,
    )


def _candidate_payload_to_input(
    candidate: TechnicalFactCandidatePayload,
) -> TechnicalFactCandidateInput:
    return TechnicalFactCandidateInput(
        source_id=uuid.UUID(candidate.source_id),
        field_name=candidate.field_name,
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        unit=candidate.unit,
        extractor_confidence=candidate.extractor_confidence,
        validation_status=StatutTechnicalFactCandidate(candidate.validation_status),
        source_page=candidate.source_page,
    )


def _review_case_input_to_payload(
    review_case: TechnicalReviewCaseInput,
) -> TechnicalReviewCasePayload:
    return TechnicalReviewCasePayload(
        source_id=str(review_case.source_id) if review_case.source_id is not None else None,
        candidate_index=review_case.candidate_index,
        case_type=review_case.case_type.value,
        trigger_source=review_case.trigger_source.value,
        severity=review_case.severity.value,
        field_name=review_case.field_name,
        title=review_case.title,
        description=review_case.description,
        detected_value=review_case.detected_value,
        detected_unit=review_case.detected_unit,
        suggested_value=review_case.suggested_value,
        suggested_unit=review_case.suggested_unit,
        metadata_json=review_case.metadata_json,
    )


def _review_case_payload_to_input(
    review_case: TechnicalReviewCasePayload,
) -> TechnicalReviewCaseInput:
    return TechnicalReviewCaseInput(
        source_id=uuid.UUID(review_case.source_id) if review_case.source_id is not None else None,
        candidate_index=review_case.candidate_index,
        case_type=TechnicalReviewCaseType(review_case.case_type),
        trigger_source=TechnicalReviewTriggerSource(review_case.trigger_source),
        severity=TechnicalReviewSeverity(review_case.severity),
        field_name=review_case.field_name,
        title=review_case.title,
        description=review_case.description,
        detected_value=review_case.detected_value,
        detected_unit=review_case.detected_unit,
        suggested_value=review_case.suggested_value,
        suggested_unit=review_case.suggested_unit,
        metadata_json=review_case.metadata_json,
    )


def _promoted_fact_input_to_payload(
    promoted_fact: PromotedTechnicalFactInput,
) -> PromotedTechnicalFactPayload:
    return PromotedTechnicalFactPayload(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        occurrence_index=promoted_fact.occurrence_index,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _promoted_fact_payload_to_input(
    promoted_fact: PromotedTechnicalFactPayload,
) -> PromotedTechnicalFactInput:
    return PromotedTechnicalFactInput(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        occurrence_index=promoted_fact.occurrence_index,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _technical_fact_snapshot_to_dict(fact: TechnicalFactSnapshot) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "field_name": fact.field_name,
        "occurrence_index": fact.occurrence_index,
        "value": fact.value,
        "unit": fact.unit,
    }


def _readiness_waiting_status(missing: list[str]) -> str | None:
    if "technical_facts" in missing:
        return STATUS_WAITING_TECH_FACTS

    if "style_pack" in missing:
        return STATUS_WAITING_STYLE_PACK

    if "commercial_snapshot" in missing:
        return STATUS_WAITING_COMMERCIAL_SNAPSHOT

    return None


def _payload_product_to_snapshot(product: ProductContextReference) -> ProductSnapshot:
    if product.product_id is None:
        raise RuntimeError("product_id est requis pour charger le snapshot commercial.")

    return ProductSnapshot(
        id=uuid.UUID(product.product_id),
        sku=product.sku,
        name=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _product_to_context_reference(product: ProductSnapshot) -> ProductContextReference:
    return ProductContextReference(
        product_id=str(product.id),
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code or "",
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _product_snapshot_to_dict(product: ProductSnapshot) -> dict[str, Any]:
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


def _product_snapshot_to_list_item(
    product: ProductSnapshot,
    *,
    readiness_status: str,
    style_guide_ready: bool,
    commercial_signals_ready: bool,
) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "familleCode": product.famille_code,
        "sousFamilleCode": product.sous_famille_code,
        "seasonCode": product.season_code,
        "segmentPrixCode": product.segment_prix_code,
        "languePrincipale": product.langue_principale,
        "readinessStatus": readiness_status,
        "styleGuideReady": style_guide_ready,
        "commercialSignalsReady": commercial_signals_ready,
        "createdAt": product.created_at.isoformat() if product.created_at is not None else None,
    }


def _product_readiness_status_from_overview(overview: dict[str, Any]) -> str:
    run = overview.get("run")
    sources = overview.get("sources") or []
    review_cases = overview.get("review_cases") or []
    product_sheet_generation = overview.get("product_sheet_generation")

    if isinstance(product_sheet_generation, dict):
        generation_status = product_sheet_generation.get("status")
        if generation_status == "EN_COURS":
            return "GENERATION_RUNNING"
        if generation_status in {"TERMINE", "A_VALIDER"}:
            return "PRODUCT_SHEET_READY"

    if overview.get("product_context_snapshot") is not None:
        return "CONTEXT_READY"

    if isinstance(run, dict):
        run_status = run.get("statut")
        if run_status == "ERREUR":
            return "FAILED"

        if any(
            case.get("status") in {"A_TRAITER", "DOCUMENT_A_REMPLACER"}
            for case in review_cases
            if isinstance(case, dict)
        ):
            return "PENDING_TECH_REVIEW"

        return "INGESTION_RUNNING"

    if len(sources) > 0:
        return "TECHNICAL_SOURCES_UPLOADED"

    return "PRODUCT_CREATED"


def _product_taxonomy_to_dict(taxonomy: ProductTaxonomySnapshot) -> dict[str, Any]:
    return {
        "id": str(taxonomy.id),
        "code": taxonomy.code,
        "libelleFr": taxonomy.libelle_fr,
        "parentId": str(taxonomy.parent_id) if taxonomy.parent_id is not None else None,
    }


def _source_snapshot_to_dict(source: DocumentSourceSnapshot) -> dict[str, Any]:
    payload = asdict(source)

    return {
        key: str(value) if isinstance(value, uuid.UUID) else value for key, value in payload.items()
    }


def _run_snapshot_to_dict(run: IngestionRunSnapshot) -> dict[str, Any]:
    payload = asdict(run)

    return {
        key: str(value) if isinstance(value, uuid.UUID) else value for key, value in payload.items()
    }
