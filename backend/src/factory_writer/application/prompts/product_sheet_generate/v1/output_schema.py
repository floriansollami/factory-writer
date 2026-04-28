from typing import Annotated

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, field_validator

StrippedNonEmptyString = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class ProductSheetTechnicalSpecV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    label: StrippedNonEmptyString
    value: StrippedNonEmptyString
    source_fact_field: StrippedNonEmptyString


class ProductSheetProofV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    section: StrippedNonEmptyString
    source_fact_fields: list[StrippedNonEmptyString] = Field(min_length=1)
    evidence: StrippedNonEmptyString


class ProductSheetCandidateV1(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: StrippedNonEmptyString
    subtitle: StrippedNonEmptyString
    short_description: StrippedNonEmptyString
    long_description: StrippedNonEmptyString
    benefit_bullets: list[StrippedNonEmptyString] = Field(min_length=3, max_length=6)
    technical_specs: list[ProductSheetTechnicalSpecV1] = Field(min_length=5)
    care_and_use: list[StrippedNonEmptyString] = Field(min_length=1, max_length=6)
    proof_ledger: list[ProductSheetProofV1] = Field(min_length=1)
    blocked_claims: list[StrippedNonEmptyString] = Field(default_factory=list)
    requires_human_review: bool
    human_review_reasons: list[StrippedNonEmptyString] = Field(default_factory=list)

    @field_validator("human_review_reasons")
    @classmethod
    def _review_reasons_required_if_flagged(
        cls,
        value: list[str],
        info: object,
    ) -> list[str]:
        data = getattr(info, "data", {})
        if data.get("requires_human_review") is True and not value:
            raise ValueError("human_review_reasons requis si requires_human_review=true.")
        return value


PRODUCT_SHEET_CANDIDATE_RESPONSE_FORMAT = {
    "type": "json_schema",
    "json_schema": {
        "name": "product_sheet_candidate_v1",
        "schema": ProductSheetCandidateV1.model_json_schema(),
        "strict": True,
    },
}
