"""drop legacy style guide schema

Revision ID: 20260421_0003
Revises: 20260421_0002
Create Date: 2026-04-21 18:20:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260421_0003"
down_revision: str | None = "20260421_0002"
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


statut_pack_enum = sa.Enum(
    "BROUILLON",
    "APPROUVE",
    "ACTIF",
    name="statutpack",
)

statut_source_enum = sa.Enum(
    "EN_ATTENTE",
    "EN_COURS",
    "TERMINE",
    "ERREUR",
    name="statutsource",
    create_type=False,
)
type_regle_enum = sa.Enum(
    "VOIX",
    "TON",
    "FORMATAGE",
    "PROMESSE_INTERDITE",
    name="typeregle",
    create_type=False,
)
niveau_contrainte_enum = sa.Enum(
    "HARD",
    "SOFT",
    name="niveaucontrainte",
    create_type=False,
)


def upgrade() -> None:
    op.drop_index(op.f("ix_regle_style_taxonomie_produit_id"), table_name="regle_style")
    op.drop_index(op.f("ix_regle_style_pack_id"), table_name="regle_style")
    op.drop_index(op.f("ix_regle_style_fragment_source_id"), table_name="regle_style")
    op.drop_table("regle_style")

    op.drop_index(op.f("ix_pack_style_source_id"), table_name="pack_style")
    op.drop_table("pack_style")

    op.drop_index(op.f("ix_fragment_style_source_id"), table_name="fragment_style")
    op.drop_table("fragment_style")

    op.drop_index(op.f("ix_source_guide_style_storage_uri"), table_name="source_guide_style")
    op.drop_table("source_guide_style")

    bind = op.get_bind()
    statut_pack_enum.drop(bind, checkfirst=True)


def downgrade() -> None:
    bind = op.get_bind()
    statut_pack_enum.create(bind, checkfirst=True)

    op.create_table(
        "source_guide_style",
        sa.Column("storage_uri", sa.String(), nullable=False),
        sa.Column("statut", statut_source_enum, nullable=False, server_default="EN_ATTENTE"),
        sa.Column("storage_generation", sa.String(), nullable=True),
        sa.Column("storage_metageneration", sa.String(), nullable=True),
        sa.Column("parser_resource_id", sa.String(), nullable=True),
        sa.Column("parser_operation_id", sa.String(), nullable=True),
        sa.Column("parser_output_uri", sa.String(), nullable=True),
        sa.Column("dernier_message_erreur", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_guide_style_storage_uri"),
        "source_guide_style",
        ["storage_uri"],
        unique=True,
    )

    op.create_table(
        "fragment_style",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("index_fragment", sa.Integer(), nullable=False),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_guide_style.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_fragment_style_source_id"), "fragment_style", ["source_id"], unique=False
    )

    op.create_table(
        "pack_style",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("prompt_registry_provider", sa.String(), nullable=False),
        sa.Column("prompt_name", sa.String(), nullable=False),
        sa.Column("prompt_version", sa.String(), nullable=False),
        sa.Column("llm_model", sa.String(), nullable=False),
        sa.Column("llm_temperature", sa.Float(), nullable=False),
        sa.Column("llm_max_tokens", sa.Integer(), nullable=False),
        sa.Column("llm_response_format", sa.String(), nullable=False),
        sa.Column("system_prompt_hash", sa.String(), nullable=False),
        sa.Column("user_prompt_hash", sa.String(), nullable=False),
        sa.Column("statut", statut_pack_enum, nullable=False, server_default="BROUILLON"),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("approuve_le", sa.DateTime(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_guide_style.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_pack_style_source_id"), "pack_style", ["source_id"], unique=False)

    op.create_table(
        "regle_style",
        sa.Column("pack_id", sa.Uuid(), nullable=False),
        sa.Column("fragment_source_id", sa.Uuid(), nullable=False),
        sa.Column("taxonomie_produit_id", sa.Uuid(), nullable=True),
        sa.Column("type_regle", type_regle_enum, nullable=False),
        sa.Column("niveau_contrainte", niveau_contrainte_enum, nullable=False),
        sa.Column("texte_regle", sa.Text(), nullable=False),
        sa.Column("est_actif", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["fragment_source_id"], ["fragment_style.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["pack_id"], ["pack_style.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["taxonomie_produit_id"],
            ["taxonomie_produit.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_regle_style_fragment_source_id"),
        "regle_style",
        ["fragment_source_id"],
        unique=False,
    )
    op.create_index(op.f("ix_regle_style_pack_id"), "regle_style", ["pack_id"], unique=False)
    op.create_index(
        op.f("ix_regle_style_taxonomie_produit_id"),
        "regle_style",
        ["taxonomie_produit_id"],
        unique=False,
    )
