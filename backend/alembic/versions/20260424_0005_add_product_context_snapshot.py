"""add product context snapshot

Revision ID: 20260424_0005
Revises: 20260424_0004
Create Date: 2026-04-24 12:45:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260424_0005"
down_revision: str | None = "20260424_0004"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_context_snapshot",
        sa.Column("product_id", sa.Uuid(), nullable=False),
        sa.Column("technical_ingestion_run_id", sa.Uuid(), nullable=False),
        sa.Column("style_pack_id", sa.Uuid(), nullable=False),
        sa.Column("commercial_signal_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("technical_fact_ids", sa.JSON(), nullable=False),
        sa.Column("snapshot_json", sa.JSON(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["commercial_signal_snapshot_id"], ["commercial_signal_snapshot.id"]
        ),
        sa.ForeignKeyConstraint(["product_id"], ["product.id"]),
        sa.ForeignKeyConstraint(["style_pack_id"], ["style_pack.id"]),
        sa.ForeignKeyConstraint(["technical_ingestion_run_id"], ["document_ingestion_run.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "product_id",
            "technical_ingestion_run_id",
            name="uq_product_context_snapshot_product_run",
        ),
        comment="Contexte immutable figé avant génération d'une fiche produit.",
    )
    op.create_index(
        op.f("ix_product_context_snapshot_product_id"),
        "product_context_snapshot",
        ["product_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_context_snapshot_technical_ingestion_run_id"),
        "product_context_snapshot",
        ["technical_ingestion_run_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_context_snapshot_style_pack_id"),
        "product_context_snapshot",
        ["style_pack_id"],
        unique=False,
    )
    op.create_index(
        op.f("ix_product_context_snapshot_commercial_signal_snapshot_id"),
        "product_context_snapshot",
        ["commercial_signal_snapshot_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f("ix_product_context_snapshot_commercial_signal_snapshot_id"),
        table_name="product_context_snapshot",
    )
    op.drop_index(
        op.f("ix_product_context_snapshot_style_pack_id"),
        table_name="product_context_snapshot",
    )
    op.drop_index(
        op.f("ix_product_context_snapshot_technical_ingestion_run_id"),
        table_name="product_context_snapshot",
    )
    op.drop_index(
        op.f("ix_product_context_snapshot_product_id"),
        table_name="product_context_snapshot",
    )
    op.drop_table("product_context_snapshot")
