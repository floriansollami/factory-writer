from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

from factory_writer.domain.style_guide_types import NiveauContrainte, TypeRegle

StrippedNonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
FamilleCode = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class DraftStyleRuleV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_evidence_provider_id: StrippedNonEmptyString = Field(
        description=(
            "Identifiant exact d'un chunk de preuve fourni en entree. Ne jamais inventer d'identifiant."
        )
    )
    citation_source: StrippedNonEmptyString = Field(
        description=(
            "Court extrait copie depuis le chunk reference, justifiant la regle. "
            "Si aucun extrait direct ne justifie la regle, ne pas produire cette regle."
        )
    )
    type_regle: TypeRegle = Field(
        description=(
            "VOIX pour une regle globale de marque, TON pour une regle liee a une "
            "famille produit, FORMATAGE pour une contrainte de structure, "
            "PROMESSE_INTERDITE pour une formulation ou claim interdit."
        )
    )
    niveau_contrainte: NiveauContrainte = Field(
        description="HARD pour une contrainte bloquante, SOFT pour une preference editoriale."
    )
    texte_regle: StrippedNonEmptyString = Field(
        description=(
            "Regle atomique reformulee comme une contrainte exploitable par le pipeline. "
            "Une regle = une idee. Ne pas ajouter d'information absente du fragment."
        )
    )
    famille_code: FamilleCode | None = Field(
        description=(
            "Code de famille autorise si la regle cible explicitement une famille produit. "
            "null si la regle est globale. Ne jamais inventer de code."
        ),
    )

    @field_validator("famille_code", mode="before")
    @classmethod
    def _empty_famille_code_as_none(_cls, value: object) -> object:
        if isinstance(value, str):
            value = value.strip()
            return value or None
        return value


class DraftStylePackExtractionV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    regles: list[DraftStyleRuleV1] = Field(
        min_length=1,
        description="Liste des regles explicitement justifiees par les chunks fournis.",
    )


STYLE_PACK_CANDIDATE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "style_pack_candidate_v1",
        "schema": DraftStylePackExtractionV1.model_json_schema(),
        "strict": True,
    },
}
