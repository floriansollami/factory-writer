import uuid
from datetime import datetime
from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field

from factory_writer.domain.style_guide_types import (
    NiveauContrainte,
    StatutPack,
    TypeRegle,
)

# --- COMPOSANTS DE BASE ---


class RegleStyleBase(BaseModel):
    # SOTA 2026 : Strict Mode pour empêcher le LLM d'inventer des clés non prévues ou de casser les types.
    model_config = ConfigDict(strict=True, extra="forbid")

    type_regle: Annotated[TypeRegle, Field(description="La catégorie de la règle de style.")]
    niveau_contrainte: Annotated[
        NiveauContrainte, Field(description="Niveau d'obligation: HARD ou SOFT.")
    ]
    texte_regle: Annotated[
        str, Field(min_length=5, description="La règle textuelle exacte extraite.")
    ]

    taxonomie_produit_id: Annotated[
        uuid.UUID | None,
        Field(
            default=None,
            description="NULL si c'est la VOICE globale, UUID de la catégorie si c'est un TONE ciblé.",
        ),
    ]


# --- SCHÉMAS D'EXTRACTION LLM ---


class RegleStyleCreate(RegleStyleBase):
    """
    DTO généré par le LLM (Structured Output).
    On force le LLM à lier la règle au fragment source !
    """

    fragment_source_id: Annotated[
        uuid.UUID, Field(description="UUID du fragment PDF qui justifie cette règle.")
    ]


class ExtractionResultLLM(BaseModel):
    """
    Schéma racine poussé au LLM pour le Structured Output SOTA 2026.
    Il wrappe un array de règles pour être facilement parsable.
    """

    model_config = ConfigDict(strict=True, extra="forbid")

    regles_extraites: Annotated[
        list[RegleStyleCreate],
        Field(description="La liste complète des règles identifiées dans les fragments fournis."),
    ]


# --- SCHÉMAS DE RÉPONSE API (READ) ---


class RegleStyleResponse(RegleStyleBase):
    """
    DTO envoyé vers l'interface Frontend.
    """

    id: uuid.UUID
    pack_id: uuid.UUID
    est_actif: bool

    model_config = ConfigDict(from_attributes=True)


class PackStyleResponse(BaseModel):
    id: uuid.UUID
    source_id: uuid.UUID
    label_version: str
    statut: StatutPack
    est_actif: bool
    approuve_le: datetime | None = None
    regles: list[RegleStyleResponse] = []

    model_config = ConfigDict(from_attributes=True)
