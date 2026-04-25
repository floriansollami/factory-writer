import uuid
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict, Field


class StyleGuideChunkCandidate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_id: str
    index_chunk: int
    contenu: str
    page_start: int | None
    page_end: int | None
    evidence_json: dict[str, object] = Field(default_factory=dict)


class StyleGuideLayoutParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_id: uuid.UUID
    document_source_id: uuid.UUID
    ingestion_run_id: uuid.UUID
    chunks: tuple[StyleGuideChunkCandidate, ...]


@dataclass(frozen=True)
class DocumentParserProcessResult:
    processor_resource_name: str
    chunks: list[StyleGuideChunkCandidate]
    latency_ms: int


@dataclass(frozen=True)
class StyleGuideFragmentCandidate:
    index_fragment: int
    titre_section: str
    contenu: str


class StyleGuideDocumentParserPort(Protocol):
    async def parse_document_layout(
        self,
        input_uri: str,
    ) -> DocumentParserProcessResult: ...
