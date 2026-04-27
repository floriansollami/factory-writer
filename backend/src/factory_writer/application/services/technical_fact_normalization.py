from __future__ import annotations

import re
import uuid
from dataclasses import replace

from factory_writer.application.ports.product_technical_ingestion import (
    TechnicalDocumentEntity,
    TechnicalFactCandidateInput,
)
from factory_writer.domain.document_ingestion_types import StatutTechnicalFactCandidate

_DIMENSION_FIELDS = {"dimension_width", "dimension_depth", "dimension_height"}
_DIMENSION_CONTEXT_FIELD = "dimension_set_raw"
_FIELD_NAME_ALIASES = {
    "dimension_width_cm": "dimension_width",
    "dimension_depth_cm": "dimension_depth",
    "dimension_height_cm": "dimension_height",
    "weight_kg": "weight",
    "assembly_time_minutes": "assembly_time",
    "max_torque_nm": "max_torque",
}
_NUMBER_TOKEN = r"\d+(?:[ \u00a0]\d{3})*(?:[,.]\d+)?|\d+(?:[,.]\d+)?"
_NUMBER_PATTERN = re.compile(rf"(?P<number>{_NUMBER_TOKEN})")
_DIMENSION_PATTERN = re.compile(
    rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>mm|cm|m)?\b",
    re.I,
)
_DIMENSION_UNIT_PATTERN = re.compile(r"(?<![a-zA-Z])(mm|cm|m)(?![a-zA-Z])", re.I)
_WEIGHT_PATTERN = re.compile(rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>kg|g|t)?\b", re.I)


def entity_to_raw_candidate_input(
    source_id: uuid.UUID,
    entity: TechnicalDocumentEntity,
) -> TechnicalFactCandidateInput:
    return TechnicalFactCandidateInput(
        source_id=source_id,
        field_name=canonical_field_name(entity.field_name),
        raw_value=entity.raw_value,
        normalized_value=None,
        unit=None,
        extractor_confidence=entity.confidence,
        validation_status=StatutTechnicalFactCandidate.EXTRACTED,
        source_page=entity.page,
    )


def normalize_candidates(
    candidates: list[TechnicalFactCandidateInput],
) -> list[TechnicalFactCandidateInput]:
    normalized = [
        replace(candidate, normalized_value=value, unit=unit)
        for candidate in candidates
        for value, unit in [_normalize_value(candidate.field_name, candidate.raw_value)]
    ]
    dimension_unit_context = _dimension_unit_context(normalized)
    if dimension_unit_context is None:
        return normalized

    return [
        _normalize_dimension_with_context(candidate, dimension_unit_context)
        if candidate.field_name in _DIMENSION_FIELDS and candidate.unit is None
        else candidate
        for candidate in normalized
    ]


def candidate_numeric_value(candidate: TechnicalFactCandidateInput) -> float | None:
    match = _NUMBER_PATTERN.search(candidate.normalized_value or candidate.raw_value or "")
    return _parse_number(match.group("number")) if match else None


def candidate_value_key(candidate: TechnicalFactCandidateInput) -> str:
    value = candidate.normalized_value or candidate.raw_value or ""
    return " ".join(value.strip().lower().split())


def canonical_field_name(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return _FIELD_NAME_ALIASES.get(normalized, normalized)


def _normalize_value(field_name: str, raw_value: str | None) -> tuple[str | None, str | None]:
    if not raw_value:
        return None, None
    if field_name in _DIMENSION_FIELDS:
        return _normalize_dimension_cm(raw_value)
    if field_name == "weight":
        return _normalize_weight_kg(raw_value)
    if field_name == "assembly_people_required":
        return _normalize_number(raw_value)
    return " ".join(raw_value.split()), None


def _normalize_dimension_with_context(
    candidate: TechnicalFactCandidateInput,
    unit_context: str,
) -> TechnicalFactCandidateInput:
    raw_value = candidate.normalized_value or candidate.raw_value
    if raw_value is None:
        return candidate
    value, unit = _normalize_dimension_cm(raw_value, unit_context=unit_context)
    return replace(candidate, normalized_value=value, unit=unit) if unit else candidate


def _dimension_unit_context(candidates: list[TechnicalFactCandidateInput]) -> str | None:
    for candidate in candidates:
        if candidate.field_name == _DIMENSION_CONTEXT_FIELD:
            match = _DIMENSION_UNIT_PATTERN.search(candidate.raw_value or "")
            if match:
                return match.group(1).lower()
    return None


def _normalize_dimension_cm(
    value: str,
    *,
    unit_context: str | None = None,
) -> tuple[str | None, str | None]:
    match = _DIMENSION_PATTERN.search(value)
    if match is None:
        return None, None
    number = _parse_number(match.group("number"))
    if number is None:
        return None, None

    unit = (match.group("unit") or unit_context or "").lower() or None
    if unit == "mm":
        number = number / 10
    elif unit == "m":
        number = number * 100
    elif unit != "cm":
        return _format_number(number), None
    return _format_number(number), "cm"


def _normalize_weight_kg(value: str) -> tuple[str | None, str | None]:
    match = _WEIGHT_PATTERN.search(value)
    if match is None:
        return None, None
    number = _parse_number(match.group("number"))
    if number is None:
        return None, None

    unit = (match.group("unit") or "").lower() or None
    if unit == "g":
        number = number / 1000
    elif unit == "t":
        number = number * 1000
    elif unit != "kg":
        return _format_number(number), None
    return _format_number(number), "kg"


def _normalize_number(value: str) -> tuple[str | None, str | None]:
    match = _NUMBER_PATTERN.search(value)
    if match is None:
        return None, None
    number = _parse_number(match.group("number"))
    return _format_number(number) if number is not None else None, None


def _parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    try:
        return float(value.replace("\u00a0", " ").replace(" ", "").replace(",", "."))
    except ValueError:
        return None


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")
