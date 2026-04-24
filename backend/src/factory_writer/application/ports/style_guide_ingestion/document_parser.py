import uuid
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class StyleGuideLayoutParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_id: uuid.UUID
    document_source_id: uuid.UUID
    ingestion_run_id: uuid.UUID
    output_uri: str


class StyleGuideLayoutJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_id: uuid.UUID
    document_source_id: uuid.UUID
    ingestion_run_id: uuid.UUID
    operation_id: str
    output_uri: str


@dataclass(frozen=True)
class DocumentParserProcessResult:
    processor_resource_name: str
    operation_id: str
    output_uri: str


@dataclass(frozen=True)
class StyleGuideFragmentCandidate:
    index_fragment: int
    titre_section: str
    contenu: str


@dataclass(frozen=True)
class StyleGuideChunkCandidate:
    provider_id: str
    index_chunk: int
    contenu: str
    page_start: int | None
    page_end: int | None
    evidence_json: dict[str, object]


class StyleGuideDocumentParserPort(Protocol):
    async def start_document_layout_parse(
        self,
        input_uri: str,
        output_uri: str,
    ) -> DocumentParserProcessResult: ...

    async def check_document_layout_parse(
        self,
        operation_id: str,
        output_uri: str,
    ) -> DocumentParserProcessResult | None: ...

    async def extract_chunks(self, output_uri: str) -> list[StyleGuideChunkCandidate]: ...
