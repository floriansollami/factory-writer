"""add canonical readiness rules and fact occurrences

Revision ID: 20260426_0008
Revises: 20260426_0007
Create Date: 2026-04-26 22:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260426_0008"
down_revision: str | None = "20260426_0007"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROFILE_CODE = "mobilier_jardin_table_repas_exterieur_product_sheet_v1"


def _requirement(
    field_name: str,
    level: str,
    *,
    cardinality: str = "SINGLE",
    selection_policy: str = "CANONICAL_SINGLE",
    conflict_policy: str = "BLOCK_ON_CREDIBLE_CONFLICT",
    source_priority: list[str] | None = None,
    target_unit: str | None = None,
    require_unit: bool = False,
    min_confidence: float | None = None,
    bounds: dict[str, float] | None = None,
    condition: str | None = None,
    missing_action: str | None = None,
) -> dict[str, object]:
    payload: dict[str, object] = {
        "field_name": field_name,
        "level": level,
        "cardinality": cardinality,
        "selection_policy": selection_policy,
        "conflict_policy": conflict_policy,
        "conflict_confidence_threshold": 0.70,
    }
    if source_priority is not None:
        payload["source_priority"] = source_priority
    if target_unit is not None:
        payload["target_unit"] = target_unit
        payload["unit"] = target_unit
    if require_unit:
        payload["require_unit"] = True
    if min_confidence is not None:
        payload["min_confidence"] = min_confidence
    if bounds is not None:
        payload["bounds"] = bounds
    if condition is not None:
        payload["condition"] = condition
    if missing_action is not None:
        payload["missing_action"] = missing_action
    return payload


def _requirements_json() -> dict[str, object]:
    return {
        "profile_code": PROFILE_CODE,
        "defaults": {
            "required_min_confidence": 0.75,
            "critical_min_confidence": 0.85,
            "conflict_confidence_threshold": 0.70,
            "optional_missing_action": "IGNORE",
        },
        "requirements": [
            _requirement(
                "sku",
                "REQUIRED",
                min_confidence=0.75,
                source_priority=["TECHNICAL_SHEET", "MATERIAL_SPECIFICATION", "ASSEMBLY_NOTICE"],
            ),
            _requirement("product_name", "REQUIRED", min_confidence=0.75),
            _requirement(
                "dimension_width",
                "REQUIRED",
                target_unit="cm",
                require_unit=True,
                min_confidence=0.85,
                bounds={"min": 120, "max": 360},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "dimension_depth",
                "REQUIRED",
                target_unit="cm",
                require_unit=True,
                min_confidence=0.85,
                bounds={"min": 60, "max": 140},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "dimension_height",
                "REQUIRED",
                target_unit="cm",
                require_unit=True,
                min_confidence=0.85,
                bounds={"min": 60, "max": 90},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "material_primary",
                "REQUIRED",
                min_confidence=0.85,
                source_priority=["MATERIAL_SPECIFICATION", "TECHNICAL_SHEET"],
            ),
            _requirement("finish_primary", "REQUIRED", min_confidence=0.75),
            _requirement(
                "usage_capacity",
                "REQUIRED",
                min_confidence=0.75,
                bounds={"min": 2, "max": 14},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "weight",
                "OPTIONAL",
                target_unit="kg",
                require_unit=True,
                bounds={"min": 15, "max": 140},
            ),
            _requirement(
                "assembly_constraints",
                "CONDITIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                condition="ASSEMBLY_NOTICE_PRESENT",
                min_confidence=0.75,
                source_priority=["ASSEMBLY_NOTICE"],
            ),
            _requirement(
                "required_tool",
                "CONDITIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                condition="ASSEMBLY_NOTICE_PRESENT",
                min_confidence=0.75,
                source_priority=["ASSEMBLY_NOTICE"],
            ),
            _requirement(
                "assembly_people_required",
                "CONDITIONAL",
                condition="ASSEMBLY_NOTICE_PRESENT",
                min_confidence=0.75,
                bounds={"min": 1, "max": 4},
                source_priority=["ASSEMBLY_NOTICE"],
            ),
            _requirement(
                "eco_certifications",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "certification_claim_type",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "covered_component",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "excluded_component",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "unsupported_claims",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                missing_action="DO_NOT_MENTION",
            ),
            _requirement(
                "technical_claim_limits",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                missing_action="DO_NOT_MENTION",
            ),
        ],
    }


def _legacy_requirements_json() -> dict[str, object]:
    return {
        "profile_code": PROFILE_CODE,
        "defaults": {
            "required_min_confidence": 0.75,
            "critical_min_confidence": 0.85,
            "optional_missing_action": "IGNORE",
        },
        "requirements": [
            {"field_name": "sku", "level": "REQUIRED", "min_confidence": 0.75},
            {"field_name": "product_name", "level": "REQUIRED", "min_confidence": 0.75},
            {
                "field_name": "dimension_width",
                "level": "REQUIRED",
                "unit": "cm",
                "min_confidence": 0.85,
                "bounds": {"min": 120, "max": 360},
            },
            {
                "field_name": "dimension_depth",
                "level": "REQUIRED",
                "unit": "cm",
                "min_confidence": 0.85,
                "bounds": {"min": 60, "max": 140},
            },
            {
                "field_name": "dimension_height",
                "level": "REQUIRED",
                "unit": "cm",
                "min_confidence": 0.85,
                "bounds": {"min": 60, "max": 90},
            },
            {"field_name": "material_primary", "level": "REQUIRED", "min_confidence": 0.85},
            {"field_name": "finish_primary", "level": "REQUIRED", "min_confidence": 0.75},
            {
                "field_name": "usage_capacity",
                "level": "REQUIRED",
                "min_confidence": 0.75,
                "bounds": {"min": 2, "max": 14},
            },
            {
                "field_name": "weight",
                "level": "OPTIONAL",
                "unit": "kg",
                "bounds": {"min": 15, "max": 140},
            },
            {
                "field_name": "assembly_constraints",
                "level": "CONDITIONAL",
                "condition": "ASSEMBLY_NOTICE_PRESENT",
            },
            {
                "field_name": "required_tool",
                "level": "CONDITIONAL",
                "condition": "ASSEMBLY_NOTICE_PRESENT",
            },
            {
                "field_name": "assembly_people_required",
                "level": "CONDITIONAL",
                "condition": "ASSEMBLY_NOTICE_PRESENT",
                "bounds": {"min": 1, "max": 4},
            },
            {
                "field_name": "eco_certifications",
                "level": "OPTIONAL",
                "missing_action": "DO_NOT_MENTION",
            },
            {
                "field_name": "certification_claim_type",
                "level": "OPTIONAL",
                "missing_action": "DO_NOT_MENTION",
            },
            {
                "field_name": "covered_component",
                "level": "OPTIONAL",
                "missing_action": "DO_NOT_MENTION",
            },
            {
                "field_name": "excluded_component",
                "level": "OPTIONAL",
                "missing_action": "DO_NOT_MENTION",
            },
            {
                "field_name": "unsupported_claims",
                "level": "OPTIONAL",
                "missing_action": "DO_NOT_MENTION",
            },
            {
                "field_name": "technical_claim_limits",
                "level": "OPTIONAL",
                "missing_action": "DO_NOT_MENTION",
            },
        ],
    }


def upgrade() -> None:
    op.add_column(
        "technical_fact",
        sa.Column("occurrence_index", sa.Integer(), server_default="0", nullable=False),
    )
    op.drop_constraint(
        "uq_technical_fact_product_field_name",
        "technical_fact",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_technical_fact_product_field_occurrence",
        "technical_fact",
        ["product_id", "field_name", "occurrence_index"],
    )
    op.alter_column("technical_fact", "occurrence_index", server_default=None)

    profile = sa.table(
        "generation_readiness_profile",
        sa.column("profile_code", sa.String()),
        sa.column("requirements_json", sa.JSON()),
    )
    op.execute(
        profile.update()
        .where(profile.c.profile_code == PROFILE_CODE)
        .values(requirements_json=_requirements_json())
    )


def downgrade() -> None:
    profile = sa.table(
        "generation_readiness_profile",
        sa.column("profile_code", sa.String()),
        sa.column("requirements_json", sa.JSON()),
    )
    op.execute(
        profile.update()
        .where(profile.c.profile_code == PROFILE_CODE)
        .values(requirements_json=_legacy_requirements_json())
    )
    op.drop_constraint(
        "uq_technical_fact_product_field_occurrence",
        "technical_fact",
        type_="unique",
    )
    op.create_unique_constraint(
        "uq_technical_fact_product_field_name",
        "technical_fact",
        ["product_id", "field_name"],
    )
    op.drop_column("technical_fact", "occurrence_index")
