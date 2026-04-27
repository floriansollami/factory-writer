from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from factory_writer.application.ports.product_technical_ingestion import (
    ProductSheetRequirementProfileSnapshot,
)


@dataclass(frozen=True)
class ProductSheetRequirement:
    field_name: str
    level: str
    target_unit: str | None
    require_unit: bool
    min_confidence: float | None
    conflict_confidence_threshold: float
    bounds_min: float | None
    bounds_max: float | None
    condition: str | None
    missing_action: str | None
    cardinality: str
    selection_policy: str
    conflict_policy: str
    source_priority: tuple[str, ...]
    control_type: str | None


@dataclass(frozen=True)
class ProductSheetRequirementProfile:
    id: uuid.UUID
    famille_code: str
    sous_famille_code: str | None
    requirements: tuple[ProductSheetRequirement, ...]


def parse_product_sheet_requirement_profile(
    snapshot: ProductSheetRequirementProfileSnapshot,
) -> ProductSheetRequirementProfile:
    raw = snapshot.requirements_json or {}
    if not isinstance(raw, dict):
        raise RuntimeError(
            f"Profil de prérequis fiche produit invalide: {snapshot.id} requirements_json doit être un objet."
        )

    raw_defaults = raw.get("defaults")
    defaults: dict[str, Any] = raw_defaults if isinstance(raw_defaults, dict) else {}
    requirements = [
        _parse_requirement(item, defaults, snapshot.id)
        for item in raw.get("requirements", [])
        if isinstance(item, dict)
    ]
    if not requirements:
        raise RuntimeError(f"Profil de prérequis fiche produit vide: {snapshot.id}")

    return ProductSheetRequirementProfile(
        id=snapshot.id,
        famille_code=snapshot.famille_code,
        sous_famille_code=snapshot.sous_famille_code,
        requirements=tuple(requirements),
    )


def _parse_requirement(
    item: dict[str, Any],
    defaults: dict[str, Any],
    profile_id: uuid.UUID,
) -> ProductSheetRequirement:
    field_name = str(item.get("field_name") or "").strip()
    level = str(item.get("level") or "").strip().upper()
    if not field_name or level not in {"REQUIRED", "CONDITIONAL", "OPTIONAL"}:
        raise RuntimeError(f"Requirement fiche produit invalide dans {profile_id}: {item!r}")

    raw_bounds = item.get("bounds")
    bounds: dict[str, Any] = raw_bounds if isinstance(raw_bounds, dict) else {}
    source_priority = item.get("source_priority")
    target_unit = item.get("target_unit") or item.get("unit")

    return ProductSheetRequirement(
        field_name=field_name,
        level=level,
        target_unit=str(target_unit) if target_unit else None,
        require_unit=bool(item.get("require_unit")),
        min_confidence=_to_float(item.get("min_confidence")),
        conflict_confidence_threshold=(
            _to_float(item.get("conflict_confidence_threshold"))
            or _to_float(defaults.get("conflict_confidence_threshold"))
            or 0.70
        ),
        bounds_min=_to_float(bounds.get("min")),
        bounds_max=_to_float(bounds.get("max")),
        condition=str(item["condition"]) if item.get("condition") else None,
        missing_action=str(item["missing_action"]).upper() if item.get("missing_action") else None,
        cardinality=str(item.get("cardinality") or "SINGLE").upper(),
        selection_policy=str(item.get("selection_policy") or "CANONICAL_SINGLE").upper(),
        conflict_policy=str(item.get("conflict_policy") or "BLOCK_ON_CREDIBLE_CONFLICT").upper(),
        source_priority=(
            tuple(str(value) for value in source_priority if value)
            if isinstance(source_priority, list)
            else ()
        ),
        control_type=str(item["control_type"]).upper() if item.get("control_type") else None,
    )


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
