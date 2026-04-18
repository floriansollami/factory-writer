import uuid
from dataclasses import dataclass
from typing import Protocol

from factory_writer.application.prompts.style_guide_extract_rules.v1.output_schema import (
    DraftStylePackExtractionV1,
)

from .prompt_registry import PreparedPrompt


@dataclass(frozen=True)
class StyleGuideFragmentSnapshot:
    id: uuid.UUID
    source_id: uuid.UUID
    index_fragment: int
    contenu: str


@dataclass(frozen=True)
class StyleGuideTaxonomySnapshot:
    id: uuid.UUID
    famille_code: str
    libelle_fr: str


@dataclass(frozen=True)
class StyleGuideDraftPackGenerationMetadata:
    prompt_registry_provider: str
    prompt_name: str
    prompt_version: str
    llm_model: str
    llm_temperature: float
    llm_max_tokens: int
    llm_response_format: str
    system_prompt_hash: str
    user_prompt_hash: str


@dataclass(frozen=True)
class StyleGuideDraftPackGenerationResult:
    candidate: DraftStylePackExtractionV1
    metadata: StyleGuideDraftPackGenerationMetadata


@dataclass(frozen=True)
class StyleGuideDraftPackSnapshot:
    draft_pack_id: str


class StyleGuideDraftPackGeneratorPort(Protocol):
    async def generate_draft_pack(
        self,
        prompt: PreparedPrompt,
    ) -> StyleGuideDraftPackGenerationResult: ...
