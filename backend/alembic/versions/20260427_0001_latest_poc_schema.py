"""latest poc schema

Revision ID: 20260427_0001
Revises:
Create Date: 2026-04-27 08:30:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa

from alembic import op
from factory_writer.infrastructure.database.models import Base

revision: str = "20260427_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None

PROFILE_ID = UUID("00000000-0000-0000-0000-000000000201")
_NOW = datetime(2026, 4, 27, 8, 30, tzinfo=UTC)


commercial_signal_snapshot = sa.table(
    "commercial_signal_snapshot",
    sa.column("id", sa.Uuid()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
    sa.column("snapshot_id", sa.String()),
    sa.column("cohort_key", sa.String()),
    sa.column("famille_code", sa.String()),
    sa.column("segment_prix_code", sa.String()),
    sa.column("season_code", sa.String()),
    sa.column("sales_signals_json", sa.JSON()),
    sa.column("feedback_signals_json", sa.JSON()),
    sa.column("generated_at", sa.DateTime()),
    sa.column("is_active", sa.Boolean()),
)

product_sheet_requirement_profile = sa.table(
    "product_sheet_requirement_profile",
    sa.column("id", sa.Uuid()),
    sa.column("created_at", sa.DateTime()),
    sa.column("updated_at", sa.DateTime()),
    sa.column("famille_code", sa.String()),
    sa.column("sous_famille_code", sa.String()),
    sa.column("is_active", sa.Boolean()),
    sa.column("requirements_json", sa.JSON()),
)


def upgrade() -> None:
    Base.metadata.create_all(bind=op.get_bind())
    _seed_poc_data()


def downgrade() -> None:
    Base.metadata.drop_all(bind=op.get_bind())


def _seed_poc_data() -> None:
    op.bulk_insert(
        commercial_signal_snapshot,
        [
            {
                "id": UUID("00000000-0000-0000-0000-000000000101"),
                "created_at": _NOW,
                "updated_at": _NOW,
                "snapshot_id": "sig_mobilier_jardin_premium_ss26",
                "cohort_key": "mobilier_jardin.premium.printemps_ete",
                "famille_code": "mobilier_jardin",
                "segment_prix_code": "premium",
                "season_code": "printemps_ete",
                "sales_signals_json": {
                    "top_performing_arguments": [
                        "matières durables perçues comme premium",
                        "confort d'usage en terrasse",
                        "cohérence esthétique avec un jardin architecturé",
                    ],
                    "conversion_notes": [
                        "les produits avec scènes de vie extérieure performent mieux",
                        "les dimensions rassurent quand elles sont visibles tôt",
                    ],
                },
                "feedback_signals_json": {
                    "perceived_strengths": [
                        "ligne sobre",
                        "stabilité",
                        "qualité des finitions",
                    ],
                    "customer_questions": [
                        "entretien en extérieur",
                        "compatibilité avec petits espaces",
                    ],
                },
                "generated_at": _NOW,
                "is_active": True,
            },
            {
                "id": UUID("00000000-0000-0000-0000-000000000102"),
                "created_at": _NOW,
                "updated_at": _NOW,
                "snapshot_id": "sig_outils_jardin_premium_ss26",
                "cohort_key": "outils_jardin.premium.printemps_ete",
                "famille_code": "outils_jardin",
                "segment_prix_code": "premium",
                "season_code": "printemps_ete",
                "sales_signals_json": {
                    "top_performing_arguments": [
                        "prise en main confortable",
                        "précision du geste",
                        "réduction de la fatigue sur usage répété",
                    ],
                    "conversion_notes": [
                        "les preuves d'ergonomie doivent rester factuelles",
                        "les usages saisonniers clarifient le bénéfice",
                    ],
                },
                "feedback_signals_json": {
                    "perceived_strengths": [
                        "équilibre",
                        "robustesse",
                        "simplicité d'utilisation",
                    ],
                    "customer_questions": [
                        "poids en main",
                        "compatibilité avec différents sols",
                    ],
                },
                "generated_at": _NOW,
                "is_active": True,
            },
        ],
    )

    op.bulk_insert(
        product_sheet_requirement_profile,
        [
            {
                "id": PROFILE_ID,
                "created_at": _NOW,
                "updated_at": _NOW,
                "famille_code": "mobilier_jardin",
                "sous_famille_code": "table_repas_exterieur",
                "is_active": True,
                "requirements_json": _requirements_json(),
            }
        ],
    )


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
    control_type: str | None = None,
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
    if require_unit:
        payload["require_unit"] = True
    if min_confidence is not None:
        payload["min_confidence"] = min_confidence
    if bounds is not None:
        payload["bounds"] = bounds
    if control_type is not None:
        payload["control_type"] = control_type
    if condition is not None:
        payload["condition"] = condition
    if missing_action is not None:
        payload["missing_action"] = missing_action
    return payload


def _requirements_json() -> dict[str, object]:
    return {
        "defaults": {
            "conflict_confidence_threshold": 0.70,
        },
        "requirements": [
            _requirement(
                "sku",
                "REQUIRED",
                min_confidence=0.85,
                source_priority=["TECHNICAL_SHEET", "MATERIAL_SPECIFICATION", "ASSEMBLY_NOTICE"],
            ),
            _requirement("product_name", "REQUIRED", min_confidence=0.85),
            _requirement(
                "dimension_width",
                "REQUIRED",
                target_unit="cm",
                require_unit=True,
                min_confidence=0.90,
                bounds={"min": 120, "max": 360},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "dimension_depth",
                "REQUIRED",
                target_unit="cm",
                require_unit=True,
                min_confidence=0.90,
                bounds={"min": 60, "max": 140},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "dimension_height",
                "REQUIRED",
                target_unit="cm",
                require_unit=True,
                min_confidence=0.90,
                bounds={"min": 60, "max": 90},
                source_priority=["TECHNICAL_SHEET"],
            ),
            _requirement(
                "material_primary",
                "REQUIRED",
                min_confidence=0.90,
                source_priority=["MATERIAL_SPECIFICATION", "TECHNICAL_SHEET"],
            ),
            _requirement("finish_primary", "REQUIRED", min_confidence=0.80),
            _requirement(
                "usage_capacity",
                "REQUIRED",
                min_confidence=0.80,
                bounds={"min": 2, "max": 14},
                control_type="NUMBER",
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
                min_confidence=0.80,
                source_priority=["ASSEMBLY_NOTICE"],
            ),
            _requirement(
                "required_tool",
                "CONDITIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                condition="ASSEMBLY_NOTICE_PRESENT",
                min_confidence=0.80,
                source_priority=["ASSEMBLY_NOTICE"],
            ),
            _requirement(
                "assembly_people_required",
                "CONDITIONAL",
                condition="ASSEMBLY_NOTICE_PRESENT",
                min_confidence=0.80,
                bounds={"min": 1, "max": 4},
                control_type="NUMBER",
                source_priority=["ASSEMBLY_NOTICE"],
            ),
            _requirement(
                "eco_certifications",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "certification_claim_type",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "covered_component",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "excluded_component",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
                missing_action="DO_NOT_MENTION",
                source_priority=["MATERIAL_SPECIFICATION"],
            ),
            _requirement(
                "unsupported_claims",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
                missing_action="DO_NOT_MENTION",
            ),
            _requirement(
                "technical_claim_limits",
                "OPTIONAL",
                cardinality="MULTIPLE",
                selection_policy="KEEP_ALL_VALID",
                min_confidence=0.80,
                missing_action="DO_NOT_MENTION",
            ),
        ],
    }
