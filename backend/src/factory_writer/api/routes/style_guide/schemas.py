from pydantic import BaseModel, ConfigDict

from factory_writer.domain.document_ingestion_types import DecisionEditorialeStyleRule
from factory_writer.domain.style_guide_types import NiveauContrainte, TypeRegle


class StyleGuideRulePatchRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    texteRegle: str | None = None
    typeRegle: TypeRegle | None = None
    niveauContrainte: NiveauContrainte | None = None
    taxonomieCode: str | None = None
    decisionEditoriale: DecisionEditorialeStyleRule | None = None
    estActif: bool | None = None
    commentaire: str | None = None
