"""initial style guide schema

Revision ID: 20260415_0001
Revises:
Create Date: 2026-04-15 10:00:00.000000
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260415_0001"
down_revision: str | None = None
branch_labels: Sequence[str] | None = None
depends_on: Sequence[str] | None = None


statut_source_enum = sa.Enum(
    "EN_ATTENTE",
    "EN_COURS",
    "TERMINE",
    "ERREUR",
    name="statutsource",
)
statut_pack_enum = sa.Enum(
    "BROUILLON",
    "APPROUVE",
    "ACTIF",
    name="statutpack",
)
type_regle_enum = sa.Enum(
    "VOIX",
    "TON",
    "FORMATAGE",
    "PROMESSE_INTERDITE",
    name="typeregle",
)
niveau_contrainte_enum = sa.Enum(
    "HARD",
    "SOFT",
    name="niveaucontrainte",
)


def upgrade() -> None:
    bind = op.get_bind()
    statut_source_enum.create(bind, checkfirst=True)
    statut_pack_enum.create(bind, checkfirst=True)
    type_regle_enum.create(bind, checkfirst=True)
    niveau_contrainte_enum.create(bind, checkfirst=True)

    op.create_table(
        "source_guide_style",
        sa.Column("uri_fichier", sa.String(), nullable=False),
        sa.Column("statut", statut_source_enum, nullable=False, server_default="EN_ATTENTE"),
        sa.Column("bucket_gcs", sa.String(), nullable=True),
        sa.Column("objet_gcs", sa.String(), nullable=True),
        sa.Column("generation_gcs", sa.String(), nullable=True),
        sa.Column("metageneration_gcs", sa.String(), nullable=True),
        sa.Column("ressource_processeur_docai", sa.String(), nullable=True),
        sa.Column("operation_docai_id", sa.String(), nullable=True),
        sa.Column("uri_sortie_docai", sa.String(), nullable=True),
        sa.Column("dernier_message_erreur", sa.Text(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_source_guide_style_uri_fichier"),
        "source_guide_style",
        ["uri_fichier"],
        unique=True,
    )

    op.create_table(
        "taxonomie_produit",
        sa.Column("code_famille", sa.String(), nullable=False),
        sa.Column("libelle_fr", sa.String(), nullable=False),
        sa.Column("parent_id", sa.Uuid(), nullable=True),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["parent_id"], ["taxonomie_produit.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        op.f("ix_taxonomie_produit_code_famille"),
        "taxonomie_produit",
        ["code_famille"],
        unique=True,
    )

    op.create_table(
        "fragment_style",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("index_fragment", sa.Integer(), nullable=False),
        sa.Column("titre_section", sa.String(), nullable=False),
        sa.Column("contenu", sa.Text(), nullable=False),
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["source_id"], ["source_guide_style.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_fragment_style_source_id"), "fragment_style", ["source_id"], unique=False)

    op.create_table(
        "pack_style",
        sa.Column("source_id", sa.Uuid(), nullable=False),
        sa.Column("label_version", sa.String(), nullable=False),
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
        sa.ForeignKeyConstraint(["fragment_source_id"], ["fragment_style.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["pack_id"], ["pack_style.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["taxonomie_produit_id"],
            ["taxonomie_produit.id"],
            ondelete="SET NULL",
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_regle_style_fragment_source_id"), "regle_style", ["fragment_source_id"], unique=False)
    op.create_index(op.f("ix_regle_style_pack_id"), "regle_style", ["pack_id"], unique=False)
    op.create_index(
        op.f("ix_regle_style_taxonomie_produit_id"),
        "regle_style",
        ["taxonomie_produit_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_regle_style_taxonomie_produit_id"), table_name="regle_style")
    op.drop_index(op.f("ix_regle_style_pack_id"), table_name="regle_style")
    op.drop_index(op.f("ix_regle_style_fragment_source_id"), table_name="regle_style")
    op.drop_table("regle_style")

    op.drop_index(op.f("ix_pack_style_source_id"), table_name="pack_style")
    op.drop_table("pack_style")

    op.drop_index(op.f("ix_fragment_style_source_id"), table_name="fragment_style")
    op.drop_table("fragment_style")

    op.drop_index(op.f("ix_taxonomie_produit_code_famille"), table_name="taxonomie_produit")
    op.drop_table("taxonomie_produit")

    op.drop_index(op.f("ix_source_guide_style_uri_fichier"), table_name="source_guide_style")
    op.drop_table("source_guide_style")

    bind = op.get_bind()
    niveau_contrainte_enum.drop(bind, checkfirst=True)
    type_regle_enum.drop(bind, checkfirst=True)
    statut_pack_enum.drop(bind, checkfirst=True)
    statut_source_enum.drop(bind, checkfirst=True)
