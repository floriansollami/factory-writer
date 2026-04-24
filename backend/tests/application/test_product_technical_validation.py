from __future__ import annotations

import uuid

from factory_writer.application.ports.product_technical_ingestion import (
    STATUS_WAITING_STYLE_PACK,
    STATUS_WAITING_TECH_FACTS,
    TechnicalDocumentEntity,
    TechnicalFactCandidateInput,
)
from factory_writer.application.services.product_technical_ingestion_service import (
    _entity_to_candidate_input,
    _readiness_waiting_status,
    _validate_technical_candidates,
)
from factory_writer.domain.document_ingestion_types import TechnicalReviewCaseType


def test_validate_technical_candidates_promotes_complete_sourced_facts() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "dimension_width_cm", "120 cm"),
        _candidate(source_id, "dimension_depth_cm", "80 cm"),
        _candidate(source_id, "dimension_height_cm", "72 cm"),
        _candidate(source_id, "assembly_constraints", "Montage à deux personnes"),
        _candidate(source_id, "eco_certifications", "FSC"),
    ]

    result = _validate_technical_candidates(candidates, low_confidence_threshold=0.75)

    assert result.review_cases == []
    assert len(result.promoted_facts) == 7
    assert {fact.field_name for fact in result.promoted_facts} == {
        "product_name",
        "material_primary",
        "dimension_width_cm",
        "dimension_depth_cm",
        "dimension_height_cm",
        "assembly_constraints",
        "eco_certifications",
    }


def test_validate_technical_candidates_blocks_missing_required_fact() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
    ]

    result = _validate_technical_candidates(candidates, low_confidence_threshold=0.75)

    missing_fields = {
        case.field_name
        for case in result.review_cases
        if case.case_type == TechnicalReviewCaseType.MISSING_REQUIRED_FIELD
    }
    assert "dimension_width_cm" in missing_fields
    assert "eco_certifications" in missing_fields


def test_validate_technical_candidates_blocks_contradiction() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "dimension_width_cm", "120 cm"),
        _candidate(source_id, "dimension_width_cm", "140 cm"),
        _candidate(source_id, "dimension_depth_cm", "80 cm"),
        _candidate(source_id, "dimension_height_cm", "72 cm"),
        _candidate(source_id, "assembly_constraints", "Montage à deux personnes"),
        _candidate(source_id, "eco_certifications", "FSC"),
    ]

    result = _validate_technical_candidates(candidates, low_confidence_threshold=0.75)

    assert any(
        case.case_type == TechnicalReviewCaseType.CONTRADICTION
        and case.field_name == "dimension_width_cm"
        for case in result.review_cases
    )
    assert all(fact.field_name != "dimension_width_cm" for fact in result.promoted_facts)


def test_validate_technical_candidates_blocks_low_confidence_fact() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "product_name", "Table Axolotl", confidence=0.4),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "dimension_width_cm", "120 cm"),
        _candidate(source_id, "dimension_depth_cm", "80 cm"),
        _candidate(source_id, "dimension_height_cm", "72 cm"),
        _candidate(source_id, "assembly_constraints", "Montage à deux personnes"),
        _candidate(source_id, "eco_certifications", "FSC"),
    ]

    result = _validate_technical_candidates(candidates, low_confidence_threshold=0.75)

    assert any(
        case.case_type == TechnicalReviewCaseType.LOW_CONFIDENCE
        and case.field_name == "product_name"
        for case in result.review_cases
    )
    assert all(fact.field_name != "product_name" for fact in result.promoted_facts)


def test_readiness_waiting_status_prioritizes_technical_facts() -> None:
    assert (
        _readiness_waiting_status(["style_pack", "commercial_snapshot", "technical_facts"])
        == STATUS_WAITING_TECH_FACTS
    )


def test_readiness_waiting_status_maps_missing_style_pack() -> None:
    assert _readiness_waiting_status(["style_pack"]) == STATUS_WAITING_STYLE_PACK


def _candidate(
    source_id: uuid.UUID,
    field_name: str,
    raw_value: str,
    *,
    confidence: float = 0.95,
) -> TechnicalFactCandidateInput:
    return _entity_to_candidate_input(
        source_id,
        TechnicalDocumentEntity(
            field_name=field_name,
            raw_value=raw_value,
            normalized_value=raw_value,
            unit=None,
            confidence=confidence,
            evidence_text=raw_value,
            page=1,
            bbox_json=None,
            raw_entity_json={"type": field_name, "mentionText": raw_value},
        ),
    )
