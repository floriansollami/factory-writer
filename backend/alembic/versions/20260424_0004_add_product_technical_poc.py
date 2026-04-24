"""add product technical ingestion poc

Revision ID: 20260424_0004
Revises: 20260421_0003
Create Date: 2026-04-24 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime
from uuid import UUID

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_0004"
down_revision: str | None = "20260421_0003"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


_NOW = datetime(2026, 4, 24, 10, 0, tzinfo=UTC)


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


def upgrade() -> None:
    op.add_column("product", sa.Column("sous_famille_code", sa.String(), nullable=True))
    op.add_column("product", sa.Column("season_code", sa.String(), nullable=True))
    op.add_column("product", sa.Column("segment_prix_code", sa.String(), nullable=True))
    op.add_column(
        "product",
        sa.Column("langue_principale", sa.String(), nullable=False, server_default="fr-FR"),
    )
    op.alter_column("product", "langue_principale", server_default=None)

    op.create_table(
        "commercial_signal_snapshot",
        sa.Column("snapshot_id", sa.String(), nullable=False),
        sa.Column("cohort_key", sa.String(), nullable=False),
        sa.Column("famille_code", sa.String(), nullable=False),
        sa.Column("segment_prix_code", sa.String(), nullable=True),
        sa.Column("season_code", sa.String(), nullable=True),
        sa.Column("sales_signals_json", sa.JSON(), nullable=False),
        sa.Column("feedback_signals_json", sa.JSON(), nullable=False),
        sa.Column("generated_at", sa.DateTime(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("cohort_key", name="uq_commercial_signal_snapshot_cohort_key"),
        comment="Snapshot seedé des historiques de ventes et retours clients du POC.",
    )
    op.create_index(
        op.f("ix_commercial_signal_snapshot_snapshot_id"),
        "commercial_signal_snapshot",
        ["snapshot_id"],
        unique=True,
    )
    op.create_index(
        op.f("ix_commercial_signal_snapshot_cohort_key"),
        "commercial_signal_snapshot",
        ["cohort_key"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_signal_snapshot_famille_code"),
        "commercial_signal_snapshot",
        ["famille_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_signal_snapshot_segment_prix_code"),
        "commercial_signal_snapshot",
        ["segment_prix_code"],
        unique=False,
    )
    op.create_index(
        op.f("ix_commercial_signal_snapshot_season_code"),
        "commercial_signal_snapshot",
        ["season_code"],
        unique=False,
    )

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


def downgrade() -> None:
    op.drop_index(
        op.f("ix_commercial_signal_snapshot_season_code"), table_name="commercial_signal_snapshot"
    )
    op.drop_index(
        op.f("ix_commercial_signal_snapshot_segment_prix_code"),
        table_name="commercial_signal_snapshot",
    )
    op.drop_index(
        op.f("ix_commercial_signal_snapshot_famille_code"), table_name="commercial_signal_snapshot"
    )
    op.drop_index(
        op.f("ix_commercial_signal_snapshot_cohort_key"), table_name="commercial_signal_snapshot"
    )
    op.drop_index(
        op.f("ix_commercial_signal_snapshot_snapshot_id"), table_name="commercial_signal_snapshot"
    )
    op.drop_table("commercial_signal_snapshot")

    op.drop_column("product", "langue_principale")
    op.drop_column("product", "segment_prix_code")
    op.drop_column("product", "season_code")
    op.drop_column("product", "sous_famille_code")
