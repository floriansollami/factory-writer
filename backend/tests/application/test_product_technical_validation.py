from __future__ import annotations

import uuid
from types import SimpleNamespace
from typing import Any, cast

import pytest

from factory_writer.application.ports.product_technical_ingestion import (
    STATUS_WAITING_COMMERCIAL_SNAPSHOT,
    STATUS_WAITING_STYLE_PACK,
    STATUS_WAITING_TECH_FACTS,
    TechnicalClassificationPayload,
    TechnicalDocumentEntity,
    TechnicalDocumentExtractionResult,
    TechnicalDocumentSourceReference,
    TechnicalExtractorRoute,
    TechnicalFactCandidateInput,
)
from factory_writer.application.services.product_sheet_requirement_profile import (
    ProductSheetRequirement as _ReadinessRequirement,
)
from factory_writer.application.services.product_sheet_requirement_profile import (
    ProductSheetRequirementProfile as _ProductSheetRequirementProfile,
)
from factory_writer.application.services.product_technical_ingestion_mappers import (
    _readiness_waiting_status,
)
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
    _post_check_product_sheet_generation,
)
from factory_writer.application.services.technical_classification_validation import (
    classification_review_cases as _classification_review_cases,
)
from factory_writer.application.services.technical_fact_normalization import (
    entity_to_raw_candidate_input as _entity_to_raw_candidate_input,
)
from factory_writer.application.services.technical_fact_validation import (
    _validate_technical_candidates,
)
from factory_writer.core.config import GCPSettings, Settings
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    StatutTechnicalFactCandidate,
    TechnicalReviewCaseType,
    TechnicalReviewResolutionAction,
)


def test_validate_technical_candidates_promotes_complete_sourced_facts() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "sku", "AX-TB-RIV-220-TKGR"),
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "finish_primary", "graphite mat"),
        _candidate(source_id, "dimension_width", "120 cm"),
        _candidate(source_id, "dimension_depth", "80 cm"),
        _candidate(source_id, "dimension_height", "72 cm"),
        _candidate(source_id, "usage_capacity", "8"),
        _candidate(source_id, "assembly_constraints", "Montage à deux personnes"),
        _candidate(source_id, "required_tool", "clé Allen"),
        _candidate(source_id, "assembly_people_required", "2"),
        _candidate(source_id, "eco_certifications", "FSC"),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=_requirement_profile(),
        document_types=("TECHNICAL_SHEET", "ASSEMBLY_NOTICE"),
    )

    assert result.review_cases == []
    assert len(result.promoted_facts) == 12
    assert {fact.field_name for fact in result.promoted_facts} == {
        "sku",
        "product_name",
        "material_primary",
        "finish_primary",
        "dimension_width",
        "dimension_depth",
        "dimension_height",
        "usage_capacity",
        "assembly_constraints",
        "required_tool",
        "assembly_people_required",
        "eco_certifications",
    }
    assert result.product_sheet_readiness["ready"] is True


def test_validate_technical_candidates_blocks_missing_required_fact() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "sku", "AX-TB-RIV-220-TKGR"),
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=_requirement_profile(),
        document_types=("TECHNICAL_SHEET",),
    )

    missing_fields = {
        case.field_name
        for case in result.review_cases
        if case.case_type == TechnicalReviewCaseType.MISSING_REQUIRED_FIELD
    }
    assert "dimension_width" in missing_fields
    assert "finish_primary" in missing_fields
    assert "eco_certifications" not in missing_fields
    assert result.product_sheet_readiness["ready"] is False
    assert "eco_certifications" in result.product_sheet_readiness["do_not_mention"]


def test_validate_technical_candidates_blocks_contradiction() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "sku", "AX-TB-RIV-220-TKGR"),
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "finish_primary", "graphite mat"),
        _candidate(source_id, "dimension_width", "120 cm"),
        _candidate(source_id, "dimension_width", "140 cm"),
        _candidate(source_id, "dimension_depth", "80 cm"),
        _candidate(source_id, "dimension_height", "72 cm"),
        _candidate(source_id, "usage_capacity", "8"),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=_requirement_profile(),
        document_types=("TECHNICAL_SHEET",),
    )

    assert any(
        case.case_type == TechnicalReviewCaseType.CONTRADICTION
        and case.field_name == "dimension_width"
        for case in result.review_cases
    )
    assert all(fact.field_name != "dimension_width" for fact in result.promoted_facts)


def test_validate_technical_candidates_canonicalizes_equivalent_dimensions() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "sku", "AX-TB-RIV-220-TKGR"),
        _candidate(source_id, "product_name", "Table Axolotl"),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "finish_primary", "graphite mat"),
        _candidate(source_id, "dimension_width", "2 200 mm", confidence=0.91),
        _candidate(source_id, "dimension_width", "220 cm", confidence=0.88),
        _candidate(source_id, "dimension_depth", "80 cm"),
        _candidate(source_id, "dimension_height", "72 cm"),
        _candidate(source_id, "usage_capacity", "8"),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=_requirement_profile(),
        document_types=("TECHNICAL_SHEET",),
    )

    width_facts = [fact for fact in result.promoted_facts if fact.field_name == "dimension_width"]
    assert len(width_facts) == 1
    assert width_facts[0].value == "220"
    assert width_facts[0].unit == "cm"
    assert not any(
        case.case_type == TechnicalReviewCaseType.CONTRADICTION for case in result.review_cases
    )


def test_validate_technical_candidates_keeps_usage_capacity_source_text() -> None:
    source_id = uuid.uuid4()
    profile = _ProductSheetRequirementProfile(
        id=uuid.uuid4(),
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        requirements=(
            _requirement(
                "usage_capacity",
                "REQUIRED",
                min_confidence=0.80,
                bounds_min=2,
                bounds_max=14,
                control_type="NUMBER",
            ),
        ),
    )
    candidates = [
        _candidate(source_id, "usage_capacity", "8 couverts"),
        _candidate(source_id, "usage_capacity", "8 places", confidence=0.90),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=profile,
        document_types=("TECHNICAL_SHEET",),
    )

    assert result.review_cases == []
    assert len(result.promoted_facts) == 1
    assert result.promoted_facts[0].value == "8 couverts"
    assert result.product_sheet_readiness["field_checks"][0]["selected_values"] == ["8 couverts"]


def test_validate_technical_candidates_blocks_usage_capacity_numeric_conflict() -> None:
    source_id = uuid.uuid4()
    profile = _ProductSheetRequirementProfile(
        id=uuid.uuid4(),
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        requirements=(
            _requirement(
                "usage_capacity",
                "REQUIRED",
                min_confidence=0.80,
                bounds_min=2,
                bounds_max=14,
                control_type="NUMBER",
            ),
        ),
    )
    candidates = [
        _candidate(source_id, "usage_capacity", "8 couverts"),
        _candidate(source_id, "usage_capacity", "10 places", confidence=0.90),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=profile,
        document_types=("TECHNICAL_SHEET",),
    )

    assert any(
        case.case_type == TechnicalReviewCaseType.CONTRADICTION
        and case.field_name == "usage_capacity"
        and case.detected_value == "10 places, 8 couverts"
        for case in result.review_cases
    )
    assert result.promoted_facts == []


def test_validate_technical_candidates_promotes_optional_multiple_values() -> None:
    source_id = uuid.uuid4()
    profile = _ProductSheetRequirementProfile(
        id=uuid.uuid4(),
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        requirements=(
            _requirement(
                "feature_or_accessory",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
            ),
        ),
    )
    candidates = [
        _candidate(source_id, "feature_or_accessory", "passage parasol"),
        _candidate(source_id, "feature_or_accessory", "patins réglables"),
        _candidate(source_id, "feature_or_accessory", "passage parasol", confidence=0.8),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=profile,
        document_types=("TECHNICAL_SHEET",),
    )

    assert result.review_cases == []
    assert [(fact.value, fact.occurrence_index) for fact in result.promoted_facts] == [
        ("passage parasol", 0),
        ("patins réglables", 1),
    ]


def test_validate_technical_candidates_ignores_low_confidence_optional_value() -> None:
    source_id = uuid.uuid4()
    profile = _ProductSheetRequirementProfile(
        id=uuid.uuid4(),
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        requirements=(
            _requirement(
                "certification_claim_type",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
            ),
        ),
    )
    candidates = [
        _candidate(
            source_id,
            "certification_claim_type",
            "FSC Mix Credit sur composants teck du plateau",
            confidence=0.57,
        ),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=profile,
        document_types=("MATERIAL_SPECIFICATION",),
    )

    assert result.review_cases == []
    assert result.promoted_facts == []
    assert result.product_sheet_readiness["field_checks"][0]["status"] == "SKIPPED"
    assert (
        result.product_sheet_readiness["field_checks"][0]["blocking_reason"]
        == "IGNORED_LOW_CONFIDENCE"
    )


def test_validate_technical_candidates_blocks_low_confidence_fact() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _candidate(source_id, "sku", "AX-TB-RIV-220-TKGR"),
        _candidate(source_id, "product_name", "Table Axolotl", confidence=0.4),
        _candidate(source_id, "material_primary", "aluminium thermolaqué"),
        _candidate(source_id, "finish_primary", "graphite mat"),
        _candidate(source_id, "dimension_width", "120 cm"),
        _candidate(source_id, "dimension_depth", "80 cm"),
        _candidate(source_id, "dimension_height", "72 cm"),
        _candidate(source_id, "usage_capacity", "8"),
    ]

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=_requirement_profile(),
        document_types=("TECHNICAL_SHEET",),
    )

    assert any(
        case.case_type == TechnicalReviewCaseType.LOW_CONFIDENCE
        and case.field_name == "product_name"
        for case in result.review_cases
    )
    assert all(fact.field_name != "product_name" for fact in result.promoted_facts)


def test_classification_review_cases_ignore_reliable_classification() -> None:
    source_id = uuid.uuid4()

    result = _classification_review_cases(
        (
            _classification_payload(
                source_id=source_id,
                document_type="TECHNICAL_SHEET",
                confidence=0.95,
            ),
        ),
        threshold=0.90,
    )

    assert result == []


def test_classification_review_cases_block_uncertain_classification() -> None:
    low_confidence_source_id = uuid.uuid4()
    missing_confidence_source_id = uuid.uuid4()
    unknown_source_id = uuid.uuid4()

    result = _classification_review_cases(
        (
            _classification_payload(
                source_id=low_confidence_source_id,
                document_type="TECHNICAL_SHEET",
                confidence=0.89,
            ),
            _classification_payload(
                source_id=missing_confidence_source_id,
                document_type="ASSEMBLY_NOTICE",
                confidence=None,
            ),
            _classification_payload(
                source_id=unknown_source_id,
                document_type="UNKNOWN",
                confidence=0.99,
            ),
            _classification_payload(
                source_id=uuid.uuid4(),
                document_type="OUT_OF_SCOPE_DOCUMENT",
                confidence=0.99,
            ),
            _classification_payload(
                source_id=uuid.uuid4(),
                document_type="MIXED_TECHNICAL_DOSSIER",
                confidence=0.99,
            ),
        ),
        threshold=0.90,
    )

    assert [case.case_type for case in result] == [
        TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
        TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
        TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
        TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
        TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
    ]
    assert [case.field_name for case in result] == ["document_type"] * 5
    assert result[0].metadata_json == {
        "confidence": 0.89,
        "threshold": 0.90,
        "is_out_of_scope": False,
        "processor_resource_name": "classifier-resource",
        "processor_version": "pretrained-classifier-v1.5",
        "source_id": str(low_confidence_source_id),
    }
    assert cast(dict[str, Any], result[2].metadata_json)["is_out_of_scope"] is True
    assert result[3].title == "Document hors périmètre"


@pytest.mark.anyio
async def test_persist_classification_results_keeps_reliable_classification_moving() -> None:
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()
    repository = _ClassificationRepositoryStub()
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, repository),
    )

    result = await service.persist_classification_results(
        ingestion_run_id=str(run_id),
        classifications=(
            _classification_payload(
                source_id=source_id,
                document_type="TECHNICAL_SHEET",
                confidence=0.95,
            ),
        ),
    )

    assert result.classification_count == 1
    assert result.review_case_count == 0
    assert repository.classification_updates == [
        {
            "source_id": source_id,
            "document_type": "TECHNICAL_SHEET",
            "confidence": 0.95,
        }
    ]
    assert repository.review_cases == []
    assert repository.step_updates == [
        {
            "run_id": run_id,
            "current_step": CurrentStep.FACT_EXTRACTION,
            "step_count": 1,
        }
    ]


@pytest.mark.anyio
async def test_persist_classification_results_blocks_low_confidence_classification() -> None:
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()
    repository = _ClassificationRepositoryStub()
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, repository),
    )

    result = await service.persist_classification_results(
        ingestion_run_id=str(run_id),
        classifications=(
            _classification_payload(
                source_id=source_id,
                document_type="TECHNICAL_SHEET",
                confidence=0.89,
            ),
        ),
    )

    assert result.classification_count == 1
    assert result.review_case_count == 1
    assert repository.step_updates == []
    assert len(repository.review_cases) == 1
    assert repository.review_cases[0].case_type == TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN
    assert repository.review_cases[0].metadata_json == {
        "confidence": 0.89,
        "threshold": 0.90,
        "is_out_of_scope": False,
        "processor_resource_name": "classifier-resource",
        "processor_version": "pretrained-classifier-v1.5",
        "source_id": str(source_id),
    }


@pytest.mark.anyio
async def test_resolve_review_case_signals_remaining_open_review_count() -> None:
    product_id = uuid.uuid4()
    case_id = uuid.uuid4()
    ingestion_run_id = uuid.uuid4()
    repository = _ReviewResolutionRepositoryStub(
        ingestion_run_id=ingestion_run_id,
        open_review_case_count=1,
        review_complete=False,
    )
    workflow_starter = _WorkflowStarterStub()
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, repository),
        workflow_starter=cast(Any, workflow_starter),
    )

    result = await service.resolve_review_case(
        product_id=product_id,
        case_id=case_id,
        action=TechnicalReviewResolutionAction.APPROVE_DETECTED_VALUE,
        resolved_by="admin",
        corrected_value=None,
        corrected_unit=None,
        comment=None,
    )

    assert result["open_review_case_count"] == 1
    assert result["review_complete"] is False
    assert workflow_starter.review_signals == [
        {
            "ingestion_run_id": str(ingestion_run_id),
            "case_id": str(case_id),
            "open_review_case_count": 1,
            "review_complete": False,
        }
    ]


@pytest.mark.anyio
async def test_refresh_technical_classifications_uses_persisted_corrected_type() -> None:
    product_id = uuid.uuid4()
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()
    repository = _ClassificationRefreshRepositoryStub(
        source_id=source_id,
        document_type="ASSEMBLY_NOTICE",
        confidence=0.97,
    )
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, repository),
    )

    result = await service.refresh_technical_classifications(
        product_id=str(product_id),
        ingestion_run_id=str(run_id),
        sources=(
            TechnicalDocumentSourceReference(
                document_source_id=str(source_id),
                storage_uri="gs://bucket/notice.pdf",
                mime_type="application/pdf",
            ),
        ),
        classifications=(
            _classification_payload(
                source_id=source_id,
                document_type="TECHNICAL_SHEET",
                confidence=0.89,
            ),
        ),
    )

    refreshed = result.classifications[0]
    assert refreshed.document_type == "ASSEMBLY_NOTICE"
    assert refreshed.confidence == 0.97
    assert refreshed.extraction_step_json["review_override"] is True
    assert refreshed.quality_metadata_json["review_override"] == {
        "previous_document_type": "TECHNICAL_SHEET",
        "document_type": "ASSEMBLY_NOTICE",
    }
    assert repository.calls == [
        {
            "product_id": product_id,
            "document_source_ids": (source_id,),
            "ingestion_run_id": run_id,
        }
    ]


@pytest.mark.anyio
async def test_resolve_review_case_signals_complete_review() -> None:
    product_id = uuid.uuid4()
    case_id = uuid.uuid4()
    ingestion_run_id = uuid.uuid4()
    repository = _ReviewResolutionRepositoryStub(
        ingestion_run_id=ingestion_run_id,
        open_review_case_count=0,
        review_complete=True,
    )
    workflow_starter = _WorkflowStarterStub()
    service = ProductTechnicalIngestionService(
        settings=Settings(),
        repository=cast(Any, repository),
        workflow_starter=cast(Any, workflow_starter),
    )

    result = await service.resolve_review_case(
        product_id=product_id,
        case_id=case_id,
        action=TechnicalReviewResolutionAction.APPROVE_DETECTED_VALUE,
        resolved_by="admin",
        corrected_value=None,
        corrected_unit=None,
        comment=None,
    )

    assert result["open_review_case_count"] == 0
    assert result["review_complete"] is True
    assert workflow_starter.review_signals[0]["review_complete"] is True


@pytest.mark.anyio
async def test_extract_technical_fact_candidates_trusts_extractor_labels() -> None:
    run_id = uuid.uuid4()
    source_id = uuid.uuid4()
    repository = _ExtractionRepositoryStub()
    document_processor = _DocumentProcessorStub(
        entities=[
            TechnicalDocumentEntity(
                field_name="dimension_width",
                raw_value="220 cm",
                confidence=0.97,
                page=1,
                bbox_json={"vertices": [{"x": 0.1, "y": 0.2}]},
            ),
            TechnicalDocumentEntity(
                field_name="unknown_field",
                raw_value="ignored",
                confidence=0.99,
                page=1,
                bbox_json=None,
            ),
        ]
    )
    service = ProductTechnicalIngestionService(
        settings=Settings(
            gcp=GCPSettings(
                document_ai_technical_sheet_extractor_processor_id="51d79fcf170d4db5",
            )
        ),
        repository=cast(Any, repository),
        document_processor=cast(Any, document_processor),
    )

    result = await service.extract_technical_fact_candidates(
        ingestion_run_id=str(run_id),
        sources=(
            TechnicalDocumentSourceReference(
                document_source_id=str(source_id),
                storage_uri="gs://bucket/source.pdf",
                mime_type="application/pdf",
            ),
        ),
        classifications=(
            _classification_payload(
                source_id=source_id,
                document_type="TECHNICAL_SHEET",
                confidence=0.99,
            ),
        ),
    )

    assert document_processor.calls == [
        {
            "input_uri": "gs://bucket/source.pdf",
            "document_type": "TECHNICAL_SHEET",
            "extractor_route": TechnicalExtractorRoute(
                document_type="TECHNICAL_SHEET",
                processor_id="51d79fcf170d4db5",
                processor_version=None,
                extractor_name="fw-technical-sheet-extractor",
            ),
            "mime_type": "application/pdf",
        }
    ]
    assert len(result.candidates) == 2
    assert result.candidates[0].field_name == "dimension_width"
    assert result.candidates[0].normalized_value is None
    assert result.candidates[0].unit is None
    assert result.candidates[0].validation_status == StatutTechnicalFactCandidate.EXTRACTED
    assert result.candidates[1].field_name == "unknown_field"
    assert result.candidates[1].normalized_value is None
    assert result.candidates[1].validation_status == StatutTechnicalFactCandidate.EXTRACTED
    assert result.extraction_steps_json["total_elapsed_seconds"] >= 0
    assert [step["step"] for step in result.extraction_steps_json["steps"]] == [
        "classification",
        "extraction",
    ]
    assert repository.step_updates == [
        {
            "run_id": run_id,
            "current_step": CurrentStep.FACT_EXTRACTION,
            "step_count": 2,
        }
    ]


def test_validate_technical_candidates_uses_dimension_set_unit_context() -> None:
    source_id = uuid.uuid4()
    candidates = [
        _entity_to_raw_candidate_input(
            source_id,
            TechnicalDocumentEntity(
                field_name="dimension_set_raw",
                raw_value="Dimensions L/P/H (mm) : 2 200 / 950 / 740",
                confidence=0.98,
                page=1,
                bbox_json=None,
            ),
        ),
        _entity_to_raw_candidate_input(
            source_id,
            TechnicalDocumentEntity(
                field_name="dimension_width",
                raw_value="2 200",
                confidence=0.97,
                page=1,
                bbox_json=None,
            ),
        ),
    ]
    profile = _ProductSheetRequirementProfile(
        id=uuid.uuid4(),
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        requirements=(_requirement("dimension_width", "REQUIRED", unit="cm", min_confidence=0.90),),
    )

    result = _validate_technical_candidates(
        candidates,
        low_confidence_threshold=0.75,
        profile=profile,
        document_types=("TECHNICAL_SHEET",),
        source_document_types={str(source_id): "TECHNICAL_SHEET"},
    )

    assert result.review_cases == []
    assert result.promoted_facts[0].field_name == "dimension_width"
    assert result.promoted_facts[0].value == "220"
    assert result.promoted_facts[0].unit == "cm"


def test_readiness_waiting_status_prioritizes_technical_facts() -> None:
    assert (
        _readiness_waiting_status(["style_pack", "commercial_snapshot", "technical_facts"])
        == STATUS_WAITING_TECH_FACTS
    )


def test_readiness_waiting_status_maps_missing_style_pack() -> None:
    assert _readiness_waiting_status(["style_pack"]) == STATUS_WAITING_STYLE_PACK


def test_readiness_waiting_status_maps_missing_commercial_snapshot() -> None:
    assert _readiness_waiting_status(["commercial_snapshot"]) == STATUS_WAITING_COMMERCIAL_SNAPSHOT


def test_product_sheet_post_check_ignores_blocked_claims_control_field() -> None:
    status, self_check = _post_check_product_sheet_generation(
        sheet_json={
            "title": "Table Rivage 220",
            "subtitle": "Table de repas extérieure en teck",
            "short_description": "Une table généreuse pour les repas d'été.",
            "long_description": "Le teck et la ligne sobre structurent l'espace extérieur.",
            "benefit_bullets": ["8 couverts", "Plateau en teck", "Finition huilée"],
            "technical_specs": [
                {
                    "label": "Largeur",
                    "value": "220 cm",
                    "source_fact_field": "dimension_width",
                },
                {
                    "label": "Matière",
                    "value": "teck",
                    "source_fact_field": "material_primary",
                },
            ],
            "care_and_use": ["Nettoyer avec un chiffon doux."],
            "blocked_claims": ["incassable", "sans entretien pour toujours"],
            "proof_ledger": [
                {
                    "section": "Claims bloqués",
                    "source_fact_fields": ["unsupported_claims"],
                    "evidence": "sans entretien pour toujours",
                }
            ],
            "requires_human_review": False,
            "human_review_reasons": [],
        },
        self_check_json={"requires_human_review": False, "human_review_reasons": []},
        context_payload={"technical_facts": _critical_generation_facts()},
    )

    assert status == "TERMINE"
    assert self_check["post_checks"]["forbidden_claim_hits"] == []


def test_product_sheet_post_check_flags_forbidden_claims_in_publishable_text() -> None:
    status, self_check = _post_check_product_sheet_generation(
        sheet_json={
            "title": "Table Rivage 220 incassable",
            "subtitle": "Table de repas extérieure en teck",
            "short_description": "Une table généreuse pour les repas d'été.",
            "long_description": "Le teck et la ligne sobre structurent l'espace extérieur.",
            "benefit_bullets": ["8 couverts", "Plateau en teck", "Finition huilée"],
            "technical_specs": [
                {
                    "label": "Largeur",
                    "value": "220 cm",
                    "source_fact_field": "dimension_width",
                }
            ],
            "care_and_use": ["Nettoyer avec un chiffon doux."],
            "blocked_claims": [],
            "requires_human_review": False,
            "human_review_reasons": [],
        },
        self_check_json={"requires_human_review": False, "human_review_reasons": []},
        context_payload={"technical_facts": _critical_generation_facts()},
    )

    assert status == "A_VALIDER"
    assert self_check["post_checks"]["forbidden_claim_hits"] == ["incassable"]


def _critical_generation_facts() -> list[dict[str, str]]:
    return [
        {"field_name": "sku"},
        {"field_name": "product_name"},
        {"field_name": "dimension_width"},
        {"field_name": "dimension_depth"},
        {"field_name": "dimension_height"},
        {"field_name": "material_primary"},
        {"field_name": "finish_primary"},
        {"field_name": "usage_capacity"},
    ]


def _candidate(
    source_id: uuid.UUID,
    field_name: str,
    raw_value: str,
    *,
    confidence: float = 0.95,
) -> TechnicalFactCandidateInput:
    return _entity_to_raw_candidate_input(
        source_id,
        TechnicalDocumentEntity(
            field_name=field_name,
            raw_value=raw_value,
            confidence=confidence,
            page=1,
            bbox_json=None,
        ),
    )


def _requirement_profile() -> _ProductSheetRequirementProfile:
    requirements = (
        _requirement("sku", "REQUIRED", min_confidence=0.85),
        _requirement("product_name", "REQUIRED", min_confidence=0.85),
        _requirement("dimension_width", "REQUIRED", unit="cm", min_confidence=0.90),
        _requirement("dimension_depth", "REQUIRED", unit="cm", min_confidence=0.90),
        _requirement("dimension_height", "REQUIRED", unit="cm", min_confidence=0.90),
        _requirement("material_primary", "REQUIRED", min_confidence=0.90),
        _requirement("finish_primary", "REQUIRED", min_confidence=0.80),
        _requirement(
            "usage_capacity",
            "REQUIRED",
            min_confidence=0.80,
            bounds_min=2,
            bounds_max=14,
            control_type="NUMBER",
        ),
        _requirement(
            "assembly_constraints",
            "CONDITIONAL",
            condition="ASSEMBLY_NOTICE_PRESENT",
            min_confidence=0.80,
        ),
        _requirement(
            "required_tool",
            "CONDITIONAL",
            condition="ASSEMBLY_NOTICE_PRESENT",
            min_confidence=0.80,
        ),
        _requirement(
            "assembly_people_required",
            "CONDITIONAL",
            condition="ASSEMBLY_NOTICE_PRESENT",
            min_confidence=0.80,
            bounds_min=1,
            bounds_max=4,
        ),
        _requirement("eco_certifications", "OPTIONAL", missing_action="DO_NOT_MENTION"),
    )
    return _ProductSheetRequirementProfile(
        id=uuid.uuid4(),
        famille_code="mobilier_jardin",
        sous_famille_code="table_repas_exterieur",
        requirements=requirements,
    )


def _requirement(
    field_name: str,
    level: str,
    *,
    unit: str | None = None,
    min_confidence: float | None = None,
    bounds_min: float | None = None,
    bounds_max: float | None = None,
    condition: str | None = None,
    missing_action: str | None = None,
    cardinality: str = "SINGLE",
    selection_policy: str = "CANONICAL_SINGLE",
    control_type: str | None = None,
) -> _ReadinessRequirement:
    return _ReadinessRequirement(
        field_name=field_name,
        level=level,
        target_unit=unit,
        require_unit=unit is not None,
        min_confidence=min_confidence,
        conflict_confidence_threshold=0.70,
        bounds_min=bounds_min,
        bounds_max=bounds_max,
        condition=condition,
        missing_action=missing_action,
        cardinality=cardinality,
        selection_policy=selection_policy,
        conflict_policy="BLOCK_ON_CREDIBLE_CONFLICT",
        source_priority=(),
        control_type=control_type,
    )


def _classification_payload(
    *,
    source_id: uuid.UUID,
    document_type: str,
    confidence: float | None,
) -> TechnicalClassificationPayload:
    return TechnicalClassificationPayload(
        document_source_id=str(source_id),
        document_type=document_type,
        confidence=confidence,
        quality_metadata_json={
            "classifier": {
                "processor_resource_name": "classifier-resource",
                "processor_version": "pretrained-classifier-v1.5",
            }
        },
        extraction_step_json={"step": "classification"},
    )


class _ClassificationRepositoryStub:
    def __init__(self) -> None:
        self.classification_updates: list[dict[str, Any]] = []
        self.review_cases: list[Any] = []
        self.step_updates: list[dict[str, Any]] = []

    async def update_source_classification(
        self,
        *,
        source_id: uuid.UUID,
        document_type: str,
        confidence: float | None,
        quality_metadata_json: Any | None,
    ) -> None:
        _ = quality_metadata_json
        self.classification_updates.append(
            {
                "source_id": source_id,
                "document_type": document_type,
                "confidence": confidence,
            }
        )

    async def create_classification_review_cases(
        self,
        *,
        run_id: uuid.UUID,
        review_cases: list[Any],
        extraction_steps_json: Any,
    ) -> int:
        _ = run_id, extraction_steps_json
        self.review_cases = review_cases
        return len(review_cases)

    async def update_ingestion_run_step(
        self,
        *,
        run_id: uuid.UUID,
        current_step: CurrentStep,
        statut: Any | None = None,
        extraction_steps_json: Any | None = None,
    ) -> None:
        _ = statut
        self.step_updates.append(
            {
                "run_id": run_id,
                "current_step": current_step,
                "step_count": len((extraction_steps_json or {}).get("steps") or []),
            }
        )


class _ReviewResolutionRepositoryStub:
    def __init__(
        self,
        *,
        ingestion_run_id: uuid.UUID,
        open_review_case_count: int,
        review_complete: bool,
    ) -> None:
        self.ingestion_run_id = ingestion_run_id
        self.open_review_case_count = open_review_case_count
        self.review_complete = review_complete

    async def resolve_review_case(
        self,
        *,
        product_id: uuid.UUID,
        case_id: uuid.UUID,
        action: TechnicalReviewResolutionAction,
        resolved_by: str,
        corrected_value: str | None,
        corrected_unit: str | None,
        selected_candidate_id: uuid.UUID | None,
        comment: str | None,
    ) -> dict[str, Any]:
        _ = (
            product_id,
            action,
            resolved_by,
            corrected_value,
            corrected_unit,
            selected_candidate_id,
            comment,
        )
        return {
            "case_id": str(case_id),
            "status": "APPROUVE",
            "ingestion_run_id": str(self.ingestion_run_id),
            "open_review_case_count": self.open_review_case_count,
            "review_complete": self.review_complete,
        }


class _ClassificationRefreshRepositoryStub:
    def __init__(
        self,
        *,
        source_id: uuid.UUID,
        document_type: str,
        confidence: float | None,
    ) -> None:
        self.source_id = source_id
        self.document_type = document_type
        self.confidence = confidence
        self.calls: list[dict[str, Any]] = []

    async def get_technical_ingestion_context(
        self,
        *,
        product_id: uuid.UUID,
        document_source_ids: tuple[uuid.UUID, ...],
        ingestion_run_id: uuid.UUID,
    ) -> dict[str, Any]:
        self.calls.append(
            {
                "product_id": product_id,
                "document_source_ids": document_source_ids,
                "ingestion_run_id": ingestion_run_id,
            }
        )
        return {
            "sources": [
                SimpleNamespace(
                    id=self.source_id,
                    document_type=self.document_type,
                    classification_confidence=self.confidence,
                )
            ]
        }


class _ExtractionRepositoryStub:
    def __init__(self) -> None:
        self.step_updates: list[dict[str, Any]] = []

    async def update_ingestion_run_step(
        self,
        *,
        run_id: uuid.UUID,
        current_step: CurrentStep,
        statut: Any | None = None,
        extraction_steps_json: Any | None = None,
    ) -> None:
        _ = statut
        self.step_updates.append(
            {
                "run_id": run_id,
                "current_step": current_step,
                "step_count": len((extraction_steps_json or {}).get("steps") or []),
            }
        )


class _DocumentProcessorStub:
    def __init__(self, *, entities: list[TechnicalDocumentEntity]) -> None:
        self.entities = entities
        self.calls: list[dict[str, Any]] = []

    async def extract_technical_facts(
        self,
        *,
        input_uri: str,
        document_type: str,
        extractor_route: TechnicalExtractorRoute,
        mime_type: str = "application/pdf",
    ) -> TechnicalDocumentExtractionResult:
        self.calls.append(
            {
                "input_uri": input_uri,
                "document_type": document_type,
                "extractor_route": extractor_route,
                "mime_type": mime_type,
            }
        )
        return TechnicalDocumentExtractionResult(
            processor_resource_name="extractor-resource",
            processor_version="extractor-v1",
            latency_ms=123,
            request_config_snapshot={"processor_kind": "custom_extractor_foundation_model"},
            entities=self.entities,
        )


class _WorkflowStarterStub:
    def __init__(self) -> None:
        self.review_signals: list[dict[str, Any]] = []

    async def signal_technical_review_case_resolved(
        self,
        *,
        ingestion_run_id: str,
        case_id: str,
        open_review_case_count: int,
        review_complete: bool,
    ) -> None:
        self.review_signals.append(
            {
                "ingestion_run_id": ingestion_run_id,
                "case_id": case_id,
                "open_review_case_count": open_review_case_count,
                "review_complete": review_complete,
            }
        )
