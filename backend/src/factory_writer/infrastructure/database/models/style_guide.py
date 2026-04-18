import uuid
from datetime import datetime

from sqlalchemy import Boolean, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from factory_writer.domain.style_guide_types import (
    NiveauContrainte,
    StatutPack,
    StatutSource,
    TypeRegle,
)
from factory_writer.infrastructure.database.models.base import BaseModel


class SourceGuideStyle(BaseModel):
    __tablename__ = "source_guide_style"

    uri_fichier: Mapped[str] = mapped_column(String, unique=True, index=True)
    statut: Mapped[StatutSource] = mapped_column(default=StatutSource.EN_ATTENTE)
    storage_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_generation: Mapped[str | None] = mapped_column(String, nullable=True)
    storage_metageneration: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_resource_id: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_operation_id: Mapped[str | None] = mapped_column(String, nullable=True)
    parser_output_uri: Mapped[str | None] = mapped_column(String, nullable=True)
    dernier_message_erreur: Mapped[str | None] = mapped_column(Text, nullable=True)

    fragments = relationship("FragmentStyle", back_populates="source", cascade="all, delete-orphan")
    packs = relationship("PackStyle", back_populates="source", cascade="all, delete-orphan")


class FragmentStyle(BaseModel):
    __tablename__ = "fragment_style"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_guide_style.id", ondelete="CASCADE"), index=True
    )
    index_fragment: Mapped[int] = mapped_column()
    contenu: Mapped[str] = mapped_column(Text)

    source = relationship("SourceGuideStyle", back_populates="fragments")
    regles = relationship(
        "RegleStyle", back_populates="fragment_source", cascade="all, delete-orphan"
    )


class PackStyle(BaseModel):
    __tablename__ = "pack_style"

    source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("source_guide_style.id", ondelete="CASCADE"), index=True
    )
    prompt_registry_provider: Mapped[str] = mapped_column(String)
    prompt_name: Mapped[str] = mapped_column(String)
    prompt_version: Mapped[str] = mapped_column(String)
    llm_model: Mapped[str] = mapped_column(String)
    llm_temperature: Mapped[float] = mapped_column(Float)
    llm_max_tokens: Mapped[int] = mapped_column()
    llm_response_format: Mapped[str] = mapped_column(String)
    system_prompt_hash: Mapped[str] = mapped_column(String)
    user_prompt_hash: Mapped[str] = mapped_column(String)
    statut: Mapped[StatutPack] = mapped_column(default=StatutPack.BROUILLON)
    est_actif: Mapped[bool] = mapped_column(Boolean, default=False)
    approuve_le: Mapped[datetime | None] = mapped_column(nullable=True)

    source = relationship("SourceGuideStyle", back_populates="packs")
    regles = relationship("RegleStyle", back_populates="pack", cascade="all, delete-orphan")


class TaxonomieProduit(BaseModel):
    __tablename__ = "taxonomie_produit"

    famille_code: Mapped[str] = mapped_column(String, unique=True, index=True)
    libelle_fr: Mapped[str] = mapped_column(String)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomie_produit.id", ondelete="SET NULL"), nullable=True
    )

    regles = relationship("RegleStyle", back_populates="taxonomie_produit")


class RegleStyle(BaseModel):
    __tablename__ = "regle_style"

    pack_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("pack_style.id", ondelete="CASCADE"), index=True
    )
    fragment_source_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("fragment_style.id", ondelete="CASCADE"), index=True
    )
    # Règle de métier : NULL = global (VOICE), NOT NULL = spécifique (TON)
    taxonomie_produit_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("taxonomie_produit.id", ondelete="SET NULL"), nullable=True, index=True
    )

    type_regle: Mapped[TypeRegle] = mapped_column()
    niveau_contrainte: Mapped[NiveauContrainte] = mapped_column()
    texte_regle: Mapped[str] = mapped_column(Text)
    est_actif: Mapped[bool] = mapped_column(Boolean, default=True)

    pack = relationship("PackStyle", back_populates="regles")
    fragment_source = relationship("FragmentStyle", back_populates="regles")
    taxonomie_produit = relationship("TaxonomieProduit", back_populates="regles")
