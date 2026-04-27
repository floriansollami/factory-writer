from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Any

from factory_writer.application.ports.product_technical_ingestion import (
    PromotedTechnicalFactInput,
    TechnicalFactCandidateInput,
    TechnicalReviewCaseInput,
)
from factory_writer.application.services.product_sheet_requirement_profile import (
    ProductSheetRequirement as _ReadinessRequirement,
)
from factory_writer.application.services.product_sheet_requirement_profile import (
    ProductSheetRequirementProfile as _ProductSheetRequirementProfile,
)
from factory_writer.application.services.technical_fact_normalization import (
    candidate_numeric_value as _candidate_numeric_value,
)
from factory_writer.application.services.technical_fact_normalization import (
    candidate_value_key as _candidate_value_key,
)
from factory_writer.application.services.technical_fact_normalization import (
    normalize_candidates as _normalize_candidates,
)
from factory_writer.domain.document_ingestion_types import (
    DocumentType,
    StatutTechnicalFactCandidate,
    TechnicalReviewCaseType,
    TechnicalReviewSeverity,
    TechnicalReviewTriggerSource,
)

_CandidateRef = tuple[int, TechnicalFactCandidateInput]


@dataclass(frozen=True)
class _ValidationResult:
    review_cases: list[TechnicalReviewCaseInput]
    promoted_facts: list[PromotedTechnicalFactInput]
    generation_readiness: dict[str, Any]


def _validate_technical_candidates(
    candidates: list[TechnicalFactCandidateInput],
    *,
    low_confidence_threshold: float,
    profile: _ProductSheetRequirementProfile,
    document_types: tuple[str, ...],
    source_document_types: dict[str, str] | None = None,
) -> _ValidationResult:
    source_document_types = source_document_types or {}
    candidates_by_field = _group_candidates_by_field(_normalize_candidates(candidates))
    readiness = _build_readiness_summary(profile, document_types)
    review_cases: list[TechnicalReviewCaseInput] = []
    promoted_facts: list[PromotedTechnicalFactInput] = []

    for requirement in profile.requirements:
        field_candidates = candidates_by_field.get(requirement.field_name, [])
        is_blocking = _requirement_blocks(requirement, document_types)

        if is_blocking:
            readiness["required_fields"].append(requirement.field_name)

        if not field_candidates:
            _record_missing_requirement(requirement, is_blocking, readiness, review_cases)
            continue

        field_reviews, field_facts, field_check = _validate_one_requirement(
            requirement,
            field_candidates,
            low_confidence_threshold=low_confidence_threshold,
            is_blocking=is_blocking,
            source_document_types=source_document_types,
        )
        review_cases.extend(field_reviews)
        promoted_facts.extend(field_facts)
        readiness["field_checks"].append(field_check)

        for review_case in field_reviews:
            _record_review_case(readiness, review_case)

    readiness["ready"] = not review_cases
    readiness["blocking_count"] = len(review_cases)
    return _ValidationResult(review_cases, promoted_facts, readiness)


def _validate_one_requirement(
    requirement: _ReadinessRequirement,
    candidates: list[_CandidateRef],
    *,
    low_confidence_threshold: float,
    is_blocking: bool,
    source_document_types: dict[str, str],
) -> tuple[list[TechnicalReviewCaseInput], list[PromotedTechnicalFactInput], dict[str, Any]]:
    valid_candidates: list[_CandidateRef] = []
    candidate_issues: list[TechnicalReviewCaseInput] = []
    optional_warning: str | None = None

    for candidate_ref in candidates:
        issue = _candidate_blocking_issue(
            candidate_ref,
            requirement=requirement,
            low_confidence_threshold=low_confidence_threshold,
            is_blocking=is_blocking,
            source_document_types=source_document_types,
        )
        if issue is None:
            valid_candidates.append(candidate_ref)
        elif is_blocking:
            candidate_issues.append(issue)
        else:
            optional_warning = issue.case_type.value

    if not valid_candidates:
        if optional_warning:
            return (
                [],
                [],
                _field_check(
                    requirement,
                    status="SKIPPED",
                    alternatives=candidates,
                    blocking_reason=f"IGNORED_{optional_warning}",
                    source_document_types=source_document_types,
                ),
            )

        return (
            candidate_issues,
            [],
            _field_check(
                requirement,
                status="BLOCKED",
                alternatives=candidates,
                blocking_reason="NO_VALID_CANDIDATE",
                source_document_types=source_document_types,
            ),
        )

    selected, conflicts = _select_values(
        requirement,
        valid_candidates,
        source_document_types,
    )
    if conflicts and requirement.conflict_policy == "BLOCK_ON_CREDIBLE_CONFLICT":
        review_case = _contradiction_review_case(
            requirement,
            selected=selected[0],
            conflicts=conflicts,
            source_document_types=source_document_types,
        )
        return (
            [review_case],
            [],
            _field_check(
                requirement,
                status="BLOCKED",
                selected_candidates=selected,
                alternatives=[*selected, *conflicts],
                blocking_reason=review_case.case_type.value,
                source_document_types=source_document_types,
            ),
        )

    return (
        [],
        _promoted_facts(requirement, selected),
        _field_check(
            requirement,
            status="WARNING" if conflicts else "PASSED",
            selected_candidates=selected,
            alternatives=conflicts,
            blocking_reason="PREFERRED_BEST_WITH_WARNING" if conflicts else None,
            source_document_types=source_document_types,
        ),
    )


def _candidate_blocking_issue(
    candidate_ref: _CandidateRef,
    *,
    requirement: _ReadinessRequirement,
    low_confidence_threshold: float,
    is_blocking: bool,
    source_document_types: dict[str, str],
) -> TechnicalReviewCaseInput | None:
    index, candidate = candidate_ref
    metadata = _candidate_metadata(index, candidate, source_document_types)

    if is_blocking and not candidate.raw_value:
        return _candidate_review_case(
            candidate_ref,
            TechnicalReviewCaseType.EXACT_MATCH_FAILED,
            f"Preuve source manquante pour {candidate.field_name}",
            "Chaque fact critique doit être rattaché à une preuve source.",
            metadata,
        )

    confidence_threshold = requirement.min_confidence
    if confidence_threshold is None and is_blocking:
        confidence_threshold = low_confidence_threshold
    if confidence_threshold is not None and (
        candidate.extractor_confidence is None
        or candidate.extractor_confidence < confidence_threshold
    ):
        return _candidate_review_case(
            candidate_ref,
            TechnicalReviewCaseType.LOW_CONFIDENCE,
            f"Confiance faible pour {candidate.field_name}",
            "Le modèle a extrait une valeur sous le seuil de confiance.",
            {
                **metadata,
                "extractor_confidence": candidate.extractor_confidence,
                "threshold": confidence_threshold,
            },
            trigger_source=TechnicalReviewTriggerSource.CUSTOM_EXTRACTOR,
        )

    if requirement.target_unit and (
        candidate.unit != requirement.target_unit
        if requirement.require_unit
        else candidate.unit is not None and candidate.unit != requirement.target_unit
    ):
        return _candidate_review_case(
            candidate_ref,
            TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
            f"Unité invalide pour {candidate.field_name}",
            f"Le champ doit être exprimé en {requirement.target_unit}.",
            {**metadata, "expected_unit": requirement.target_unit},
        )

    if requirement.bounds_min is not None or requirement.bounds_max is not None:
        numeric_value = _candidate_numeric_value(candidate)
        bounds = {"min": requirement.bounds_min, "max": requirement.bounds_max}
        if numeric_value is None:
            return _candidate_review_case(
                candidate_ref,
                TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
                f"Valeur numérique invalide pour {candidate.field_name}",
                "La valeur doit être numérique pour être contrôlée.",
                {**metadata, "bounds": bounds},
            )
        below_min = requirement.bounds_min is not None and numeric_value < requirement.bounds_min
        above_max = requirement.bounds_max is not None and numeric_value > requirement.bounds_max
        if below_min or above_max:
            return _candidate_review_case(
                candidate_ref,
                TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
                f"Valeur hors borne pour {candidate.field_name}",
                "La valeur extraite sort des bornes réalistes du profil de prérequis fiche produit.",
                {**metadata, "value": numeric_value, "bounds": bounds},
                detected_value=candidate.normalized_value or candidate.raw_value,
            )

    if is_blocking and not (candidate.normalized_value or candidate.raw_value):
        return _candidate_review_case(
            candidate_ref,
            TechnicalReviewCaseType.MISSING_REQUIRED_FIELD,
            f"Valeur vide pour {candidate.field_name}",
            "Le champ requis doit contenir une valeur exploitable.",
            metadata,
        )

    return None


def _select_values(
    requirement: _ReadinessRequirement,
    candidates: list[_CandidateRef],
    source_document_types: dict[str, str],
) -> tuple[list[_CandidateRef], list[_CandidateRef]]:
    if requirement.cardinality == "MULTIPLE" or requirement.selection_policy == "KEEP_ALL_VALID":
        return _best_candidate_per_distinct_value(
            candidates,
            requirement,
            source_document_types,
        ), []

    selected = _best_candidate(candidates, requirement, source_document_types)
    selected_key = _candidate_comparison_key(selected[1], requirement)
    conflicts = [
        candidate_ref
        for candidate_ref in candidates
        if _candidate_comparison_key(candidate_ref[1], requirement) != selected_key
        and (candidate_ref[1].extractor_confidence or 0.0)
        >= requirement.conflict_confidence_threshold
    ]
    return [selected], conflicts


def _build_readiness_summary(
    profile: _ProductSheetRequirementProfile,
    document_types: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "profile_id": str(profile.id),
        "famille_code": profile.famille_code,
        "sous_famille_code": profile.sous_famille_code,
        "document_types": list(document_types),
        "ready": False,
        "blocking_count": 0,
        "required_fields": [],
        "required_missing": [],
        "low_confidence": [],
        "out_of_bounds": [],
        "contradictions": [],
        "do_not_mention": [],
        "field_checks": [],
    }


def _record_missing_requirement(
    requirement: _ReadinessRequirement,
    is_blocking: bool,
    readiness: dict[str, Any],
    review_cases: list[TechnicalReviewCaseInput],
) -> None:
    if is_blocking:
        review_case = _missing_required_field_review_case(requirement)
        review_cases.append(review_case)
        readiness["required_missing"].append(requirement.field_name)
        readiness["field_checks"].append(
            _field_check(
                requirement,
                status="BLOCKED",
                blocking_reason=review_case.case_type.value,
            )
        )
    elif requirement.missing_action == "DO_NOT_MENTION":
        readiness["do_not_mention"].append(requirement.field_name)
        readiness["field_checks"].append(
            _field_check(requirement, status="SKIPPED", blocking_reason="DO_NOT_MENTION")
        )


def _record_review_case(readiness: dict[str, Any], review_case: TechnicalReviewCaseInput) -> None:
    field_name = review_case.field_name or "unknown"
    metadata = review_case.metadata_json if isinstance(review_case.metadata_json, dict) else {}

    if review_case.case_type == TechnicalReviewCaseType.LOW_CONFIDENCE:
        readiness["low_confidence"].append(
            {
                "field_name": field_name,
                "confidence": metadata.get("extractor_confidence"),
                "threshold": metadata.get("threshold"),
            }
        )
    elif review_case.case_type == TechnicalReviewCaseType.VALUE_OUT_OF_RANGE:
        readiness["out_of_bounds"].append(
            {
                "field_name": field_name,
                "value": metadata.get("value", review_case.detected_value),
                "unit": review_case.detected_unit,
                "bounds": metadata.get("bounds"),
                "expected_unit": metadata.get("expected_unit"),
            }
        )
    elif review_case.case_type == TechnicalReviewCaseType.CONTRADICTION:
        readiness["contradictions"].append(
            {"field_name": field_name, "distinct_values": metadata.get("distinct_values")}
        )


def _best_candidate_per_distinct_value(
    candidates: list[_CandidateRef],
    requirement: _ReadinessRequirement,
    source_document_types: dict[str, str],
) -> list[_CandidateRef]:
    candidates_by_value: dict[str, list[_CandidateRef]] = {}
    for candidate_ref in candidates:
        candidates_by_value.setdefault(
            _candidate_comparison_key(candidate_ref[1], requirement),
            [],
        ).append(candidate_ref)

    selected = [
        _best_candidate(group, requirement, source_document_types)
        for group in candidates_by_value.values()
    ]
    return sorted(
        selected,
        key=lambda candidate_ref: _candidate_sort_key(
            candidate_ref,
            requirement,
            source_document_types,
        ),
    )


def _best_candidate(
    candidates: list[_CandidateRef],
    requirement: _ReadinessRequirement,
    source_document_types: dict[str, str],
) -> _CandidateRef:
    return min(
        candidates,
        key=lambda candidate_ref: _candidate_sort_key(
            candidate_ref,
            requirement,
            source_document_types,
        ),
    )


def _candidate_sort_key(
    candidate_ref: _CandidateRef,
    requirement: _ReadinessRequirement,
    source_document_types: dict[str, str],
) -> tuple[int, int, int, float, int, int]:
    index, candidate = candidate_ref
    document_type = source_document_types.get(str(candidate.source_id))
    source_rank = (
        requirement.source_priority.index(document_type)
        if document_type in requirement.source_priority
        else len(requirement.source_priority)
    )
    unexpected_unit_rank = int(
        requirement.target_unit is not None and candidate.unit != requirement.target_unit
    )
    missing_raw_value_rank = int(not candidate.raw_value)
    confidence_rank = -(candidate.extractor_confidence or 0.0)
    page_rank = candidate.source_page if candidate.source_page is not None else 9999
    return (
        source_rank,
        unexpected_unit_rank,
        missing_raw_value_rank,
        confidence_rank,
        page_rank,
        index,
    )


def _candidate_review_case(
    candidate_ref: _CandidateRef,
    case_type: TechnicalReviewCaseType,
    title: str,
    description: str,
    metadata_json: dict[str, Any],
    *,
    trigger_source: TechnicalReviewTriggerSource = TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
    detected_value: str | None = None,
) -> TechnicalReviewCaseInput:
    index, candidate = candidate_ref
    return TechnicalReviewCaseInput(
        source_id=candidate.source_id,
        candidate_index=index,
        case_type=case_type,
        trigger_source=trigger_source,
        severity=TechnicalReviewSeverity.BLOCKING,
        field_name=candidate.field_name,
        title=title,
        description=description,
        detected_value=detected_value if detected_value is not None else candidate.raw_value,
        detected_unit=candidate.unit,
        metadata_json=metadata_json,
    )


def _contradiction_review_case(
    requirement: _ReadinessRequirement,
    *,
    selected: _CandidateRef,
    conflicts: list[_CandidateRef],
    source_document_types: dict[str, str],
) -> TechnicalReviewCaseInput:
    selected_index, selected_candidate = selected
    conflicting_candidates = [selected, *conflicts]
    distinct_values = sorted(
        {
            _candidate_display_value(candidate)
            for _, candidate in conflicting_candidates
            if _candidate_display_value(candidate)
        }
    )
    return TechnicalReviewCaseInput(
        source_id=selected_candidate.source_id,
        candidate_index=selected_index,
        case_type=TechnicalReviewCaseType.CONTRADICTION,
        trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
        severity=TechnicalReviewSeverity.BLOCKING,
        field_name=requirement.field_name,
        title=f"Contradiction détectée sur {requirement.field_name}",
        description="Plusieurs valeurs incompatibles ont été extraites avec un score crédible.",
        detected_value=", ".join(distinct_values),
        detected_unit=selected_candidate.unit,
        metadata_json={
            "candidate_index": selected_index,
            "distinct_values": distinct_values,
            "threshold": requirement.conflict_confidence_threshold,
            "candidates": [
                _candidate_metadata(index, candidate, source_document_types)
                for index, candidate in conflicting_candidates
            ],
        },
    )


def _promoted_facts(
    requirement: _ReadinessRequirement,
    candidates: list[_CandidateRef],
) -> list[PromotedTechnicalFactInput]:
    facts: list[PromotedTechnicalFactInput] = []
    for occurrence_index, (candidate_index, candidate) in enumerate(candidates):
        value = candidate.normalized_value or candidate.raw_value
        if value:
            facts.append(
                PromotedTechnicalFactInput(
                    candidate_index=candidate_index,
                    field_name=requirement.field_name,
                    occurrence_index=occurrence_index,
                    value=value,
                    unit=candidate.unit,
                )
            )
    return facts


def _mark_review_candidates(
    candidates: list[TechnicalFactCandidateInput],
    review_cases: list[TechnicalReviewCaseInput],
) -> list[TechnicalFactCandidateInput]:
    review_indexes = {
        review_case.candidate_index
        for review_case in review_cases
        if review_case.candidate_index is not None
    }
    return [
        replace(candidate, validation_status=StatutTechnicalFactCandidate.NEEDS_REVIEW)
        if index in review_indexes
        else candidate
        for index, candidate in enumerate(candidates)
    ]


def _field_check(
    requirement: _ReadinessRequirement,
    *,
    status: str,
    selected_candidates: list[_CandidateRef] | None = None,
    alternatives: list[_CandidateRef] | None = None,
    blocking_reason: str | None = None,
    source_document_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_document_types = source_document_types or {}
    selected_candidates = selected_candidates or []
    alternatives = alternatives or []
    confidences = [
        candidate.extractor_confidence
        for _, candidate in selected_candidates
        if candidate.extractor_confidence is not None
    ]
    return {
        "field_name": requirement.field_name,
        "level": requirement.level,
        "cardinality": requirement.cardinality,
        "control_type": requirement.control_type,
        "status": status,
        "selected_values": [
            candidate.normalized_value or candidate.raw_value
            for _, candidate in selected_candidates
            if candidate.normalized_value or candidate.raw_value
        ],
        "selected_candidate_indexes": [index for index, _ in selected_candidates],
        "selected_sources": [
            _candidate_metadata(index, candidate, source_document_types)
            for index, candidate in selected_candidates
        ],
        "confidence": max(confidences) if confidences else None,
        "threshold": requirement.min_confidence,
        "alternatives": [
            _candidate_metadata(index, candidate, source_document_types)
            for index, candidate in alternatives
        ],
        "blocking_reason": blocking_reason,
    }


def _candidate_metadata(
    index: int,
    candidate: TechnicalFactCandidateInput,
    source_document_types: dict[str, str],
) -> dict[str, Any]:
    return {
        "candidate_index": index,
        "source_id": str(candidate.source_id),
        "source_document_type": source_document_types.get(str(candidate.source_id)),
        "field_name": candidate.field_name,
        "raw_value": candidate.raw_value,
        "normalized_value": candidate.normalized_value,
        "unit": candidate.unit,
        "confidence": candidate.extractor_confidence,
        "page": candidate.source_page,
        "value_key": _candidate_value_key(candidate),
    }


def _candidate_comparison_key(
    candidate: TechnicalFactCandidateInput,
    requirement: _ReadinessRequirement,
) -> str:
    if requirement.control_type == "NUMBER":
        numeric_value = _candidate_numeric_value(candidate)
        if numeric_value is not None:
            return f"number:{numeric_value:g}"
    return _candidate_value_key(candidate)


def _candidate_display_value(candidate: TechnicalFactCandidateInput) -> str:
    return candidate.normalized_value or candidate.raw_value or ""


def _missing_required_field_review_case(
    requirement: _ReadinessRequirement,
) -> TechnicalReviewCaseInput:
    return TechnicalReviewCaseInput(
        source_id=None,
        candidate_index=None,
        case_type=TechnicalReviewCaseType.MISSING_REQUIRED_FIELD,
        trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
        severity=TechnicalReviewSeverity.BLOCKING,
        field_name=requirement.field_name,
        title=f"Champ requis manquant: {requirement.field_name}",
        description=f"Aucune preuve exploitable trouvée pour {requirement.field_name}.",
        metadata_json={"level": requirement.level, "condition": requirement.condition},
    )


def _requirement_blocks(
    requirement: _ReadinessRequirement,
    document_types: tuple[str, ...],
) -> bool:
    if requirement.level == "REQUIRED":
        return True
    return (
        requirement.level == "CONDITIONAL"
        and requirement.condition == "ASSEMBLY_NOTICE_PRESENT"
        and DocumentType.ASSEMBLY_NOTICE.value in set(document_types)
    )


def _group_candidates_by_field(
    candidates: list[TechnicalFactCandidateInput],
) -> dict[str, list[_CandidateRef]]:
    grouped: dict[str, list[_CandidateRef]] = {}
    for index, candidate in enumerate(candidates):
        grouped.setdefault(candidate.field_name, []).append((index, candidate))
    return grouped
