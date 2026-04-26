"""update readiness profile to unitless extractor labels

Revision ID: 20260426_0007
Revises: 20260426_0006
Create Date: 2026-04-26 20:15:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.sql.selectable import TableClause

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260426_0007"
down_revision: str | None = "20260426_0006"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROFILE_CODE = "mobilier_jardin_table_repas_exterieur_product_sheet_v1"


def _requirements_json(*, legacy: bool = False) -> dict[str, object]:
    width = "dimension_width_cm" if legacy else "dimension_width"
    depth = "dimension_depth_cm" if legacy else "dimension_depth"
    height = "dimension_height_cm" if legacy else "dimension_height"
    weight = "weight_kg" if legacy else "weight"

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
                "field_name": width,
                "level": "REQUIRED",
                "unit": "cm",
                "min_confidence": 0.85,
                "bounds": {"min": 120, "max": 360},
            },
            {
                "field_name": depth,
                "level": "REQUIRED",
                "unit": "cm",
                "min_confidence": 0.85,
                "bounds": {"min": 60, "max": 140},
            },
            {
                "field_name": height,
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
                "field_name": weight,
                "level": "OPTIONAL",
                "unit": "kg",
                "bounds": {"min": 15, "max": 140},
            },
            {
                "field_name": "assembly_constraints",
                "level": "CONDITIONAL",
                "condition": "ASSEMBLY_NOTICE_PRESENT",
                "min_confidence": 0.75,
            },
            {
                "field_name": "required_tool",
                "level": "CONDITIONAL",
                "condition": "ASSEMBLY_NOTICE_PRESENT",
                "min_confidence": 0.75,
            },
            {
                "field_name": "assembly_people_required",
                "level": "CONDITIONAL",
                "condition": "ASSEMBLY_NOTICE_PRESENT",
                "min_confidence": 0.75,
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


def _profile_table() -> TableClause:
    return sa.table(
        "generation_readiness_profile",
        sa.column("profile_code", sa.String()),
        sa.column("requirements_json", sa.JSON()),
    )


def upgrade() -> None:
    table = _profile_table()
    op.get_bind().execute(
        sa.update(table)
        .where(table.c.profile_code == PROFILE_CODE)
        .values(requirements_json=_requirements_json())
    )


def downgrade() -> None:
    table = _profile_table()
    op.get_bind().execute(
        sa.update(table)
        .where(table.c.profile_code == PROFILE_CODE)
        .values(requirements_json=_requirements_json(legacy=True))
    )
