import uuid
from dataclasses import dataclass
from typing import Protocol

from factory_writer.application.prompts.style_guide_extract_rules.v1.output_schema import (
    DraftStylePackExtractionV1,
)
from factory_writer.domain.style_guide_types import StatutSource

from .document_parser import StyleGuideChunkPersistResult, StyleGuideFragmentCandidate
from .draft_pack_generator import (
    StyleGuideDraftPackGenerationMetadata,
    StyleGuideDraftPackSnapshot,
    StyleGuideFragmentSnapshot,
    StyleGuideTaxonomySnapshot,
)


@dataclass(frozen=True)
class StyleGuideSourceSnapshot:
    id: uuid.UUID
    uri_fichier: str
    statut: StatutSource
    storage_generation: str | None = None
    parser_operation_id: str | None = None
    parser_output_uri: str | None = None


class StyleGuideRepositoryPort(Protocol):
    async def get_by_uri(self, uri: str) -> StyleGuideSourceSnapshot | None: ...

    async def create_source(self, uri: str) -> StyleGuideSourceSnapshot: ...

    async def update_source_status(
        self,
        source_id: uuid.UUID,
        statut: StatutSource,
        error_message: str | None = None,
        only_if_not_terminal: bool = False,
    ) -> StyleGuideSourceSnapshot: ...

    async def update_storage_metadata(
        self,
        source_id: uuid.UUID,
        uri: str,
        generation: str,
        metageneration: str,
    ) -> StyleGuideSourceSnapshot: ...

    async def update_parser_output(
        self,
        source_id: uuid.UUID,
        parser_resource_id: str,
        operation_id: str,
        output_uri: str,
    ) -> StyleGuideSourceSnapshot: ...

    async def replace_fragments(
        self,
        source_id: uuid.UUID,
        fragments: list[StyleGuideFragmentCandidate],
    ) -> StyleGuideChunkPersistResult: ...

    async def get_fragments_by_ids(
        self,
        fragment_ids: list[str],
    ) -> list[StyleGuideFragmentSnapshot]: ...

    async def list_taxonomies(self) -> list[StyleGuideTaxonomySnapshot]: ...

    async def replace_draft_pack(
        self,
        source_id: uuid.UUID,
        candidate: DraftStylePackExtractionV1,
        metadata: StyleGuideDraftPackGenerationMetadata,
    ) -> StyleGuideDraftPackSnapshot: ...

    async def promote_pack(self, draft_pack_id: str) -> str: ...
