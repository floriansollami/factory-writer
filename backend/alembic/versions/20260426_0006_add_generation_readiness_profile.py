"""add generation readiness profile

Revision ID: 20260426_0006
Revises: 20260424_0005
Create Date: 2026-04-26 16:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260426_0006"
down_revision: str | None = "20260424_0005"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROFILE_ID = UUID("00000000-0000-0000-0000-000000000201")
PROFILE_CODE = "mobilier_jardin_table_repas_exterieur_product_sheet_v1"
_NOW = datetime(2026, 4, 26, 16, 30, tzinfo=UTC)

REQUIREMENTS_JSON = {
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


def upgrade() -> None:
    op.create_table(
        "generation_readiness_profile",
        sa.Column("profile_code", sa.String(), nullable=False),
        sa.Column("famille_code", sa.String(), nullable=False),
        sa.Column("sous_famille_code", sa.String(), nullable=True),
        sa.Column("channel_code", sa.String(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("requirements_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_code", name="uq_generation_readiness_profile_code"),
        comment="Profil POC des facts requis avant generation fiche produit.",
    )
    op.create_index(
        op.f("ix_generation_readiness_profile_famille_code"),
        "generation_readiness_profile",
        ["famille_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generation_readiness_profile_sous_famille_code"),
        "generation_readiness_profile",
        ["sous_famille_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generation_readiness_profile_channel_code"),
        "generation_readiness_profile",
        ["channel_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_generation_readiness_profile_is_active"),
        "generation_readiness_profile",
        ["is_active"],
        unique=False,
    )

    table = sa.table(
        "generation_readiness_profile",
        sa.column("id", sa.Uuid()),
        sa.column("profile_code", sa.String()),
        sa.column("famille_code", sa.String()),
        sa.column("sous_famille_code", sa.String()),
        sa.column("channel_code", sa.String()),
        sa.column("is_active", sa.Boolean()),
        sa.column("requirements_json", sa.JSON()),
        sa.column("created_at", sa.DateTime()),
        sa.column("updated_at", sa.DateTime()),
    )
    op.bulk_insert(
        table,
        [
            {
                "id": PROFILE_ID,
                "profile_code": PROFILE_CODE,
                "famille_code": "mobilier_jardin",
                "sous_famille_code": "table_repas_exterieur",
                "channel_code": "product_sheet",
                "is_active": True,
                "requirements_json": REQUIREMENTS_JSON,
                "created_at": _NOW,
                "updated_at": _NOW,
            }
        ],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_generation_readiness_profile_is_active"),
        table_name="generation_readiness_profile",
    )
    op.drop_index(
        op.f("ix_generation_readiness_profile_channel_code"),
        table_name="generation_readiness_profile",
    )
    op.drop_index(
        op.f("ix_generation_readiness_profile_sous_famille_code"),
        table_name="generation_readiness_profile",
    )
    op.drop_index(
        op.f("ix_generation_readiness_profile_famille_code"),
        table_name="generation_readiness_profile",
    )
    op.drop_table("generation_readiness_profile")
