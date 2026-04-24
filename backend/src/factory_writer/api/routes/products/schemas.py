from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

from factory_writer.domain.document_ingestion_types import TechnicalReviewResolutionAction


class ProductCreateRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    sku: str = Field(..., min_length=1)
    name: str = Field(..., min_length=1)
    famille_code: str = Field(..., alias="familleCode", min_length=1)
    sous_famille_code: str | None = Field(default=None, alias="sousFamilleCode")
    season_code: str | None = Field(default=None, alias="seasonCode")
    segment_prix_code: str | None = Field(default=None, alias="segmentPrixCode")
    langue_principale: str = Field(default="fr-FR", alias="languePrincipale")


class TechnicalReviewCaseResolveRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    action: TechnicalReviewResolutionAction
    resolved_by: str = Field(default="admin", alias="resolvedBy")
    corrected_value: str | None = Field(default=None, alias="correctedValue")
    corrected_unit: str | None = Field(default=None, alias="correctedUnit")
    comment: str | None = None
