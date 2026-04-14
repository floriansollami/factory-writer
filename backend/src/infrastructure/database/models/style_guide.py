import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from infrastructure.database.models.base import BaseModel


class StatutSource(enum.StrEnum):
    EN_ATTENTE = "EN_ATTENTE"
    EN_COURS = "EN_COURS"
    TERMINE = "TERMINE"
    ERREUR = "ERREUR"


class StatutPack(enum.StrEnum):
    BROUILLON = "BROUILLON"
    APPROUVE = "APPROUVE"
    ACTIF = "ACTIF"


class TypeRegle(enum.StrEnum):
    VOIX = "VOIX"
    TON = "TON"
    FORMATAGE = "FORMATAGE"
    PROMESSE_INTERDITE = "PROMESSE_INTERDITE"


class NiveauContrainte(enum.StrEnum):
    HARD = "HARD"
    SOFT = "SOFT"


class SourceGuideStyle(BaseModel):
    __tablename__ = "source_guide_style"

    uri_fichier: Mapped[str] = mapped_column(String, unique=True, index=True)
    statut: Mapped[StatutSource] = mapped_column(default=StatutSource.EN_ATTENTE)

    # Relationships
    fragments = relationship("FragmentStyle", back_populates="source", cascade="all, delete-orphan")
    packs = relationship("PackStyle", back_populates="source", cascade="all, delete-orphan")


class FragmentStyle(BaseModel):
    __tablename__ = "fragment_style"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_guide_style.id", ondelete="CASCADE"), index=True
    )
    index_fragment: Mapped[int] = mapped_column()
    titre_section: Mapped[str] = mapped_column(String)
    contenu: Mapped[str] = mapped_column(Text)

    # Relationships
    source = relationship("SourceGuideStyle", back_populates="fragments")
    regles = relationship(
        "RegleStyle", back_populates="fragment_source", cascade="all, delete-orphan"
    )


class PackStyle(BaseModel):
    __tablename__ = "pack_style"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_guide_style.id", ondelete="CASCADE"), index=True
    )
    label_version: Mapped[str] = mapped_column(String)
    statut: Mapped[StatutPack] = mapped_column(default=StatutPack.BROUILLON)
    est_actif: Mapped[bool] = mapped_column(Boolean, default=False)
    approuve_le: Mapped[datetime | None] = mapped_column(nullable=True)
    # Relationships
    source = relationship("SourceGuideStyle", back_populates="packs")
    regles = relationship("RegleStyle", back_populates="pack", cascade="all, delete-orphan")


class TaxonomieProduit(BaseModel):
    __tablename__ = "taxonomie_produit"

    code_famille: Mapped[str] = mapped_column(String, unique=True, index=True)
    libelle_fr: Mapped[str] = mapped_column(String)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomie_produit.id", ondelete="SET NULL"), nullable=True
    )

    # Relationships
    regles = relationship("RegleStyle", back_populates="taxonomie_produit")


class RegleStyle(BaseModel):
    __tablename__ = "regle_style"

    pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pack_style.id", ondelete="CASCADE"), index=True
    )
    fragment_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fragment_style.id", ondelete="RESTRICT"), index=True
    )
    # Règle de métier : NULL = global (VOICE), NOT NULL = spécifique (TON)
    taxonomie_produit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomie_produit.id", ondelete="SET NULL"), nullable=True, index=True
    )

    type_regle: Mapped[TypeRegle] = mapped_column()
    niveau_contrainte: Mapped[NiveauContrainte] = mapped_column()
    texte_regle: Mapped[str] = mapped_column(Text)
    est_actif: Mapped[bool] = mapped_column(Boolean, default=True)

    # Relationships
    pack = relationship("PackStyle", back_populates="regles")
    fragment_source = relationship("FragmentStyle", back_populates="regles")
    taxonomie_produit = relationship("TaxonomieProduit", back_populates="regles")
