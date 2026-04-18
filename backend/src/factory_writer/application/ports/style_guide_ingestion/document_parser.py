import uuid
from dataclasses import dataclass
from typing import Protocol

from pydantic import BaseModel, ConfigDict


class StyleGuideLayoutParseResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: uuid.UUID
    output_uri: str


class StyleGuideLayoutJobResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: uuid.UUID
    operation_id: str
    output_uri: str


class StyleGuideChunkPersistResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: uuid.UUID
    fragment_ids: list[str]


@dataclass(frozen=True)
class DocumentParserProcessResult:
    processor_resource_name: str
    operation_id: str
    output_uri: str


@dataclass(frozen=True)
class StyleGuideFragmentCandidate:
    index_fragment: int
    contenu: str


class StyleGuideDocumentParserPort(Protocol):
    async def start_layout_extraction(
        self,
        input_uri: str,
        output_uri: str,
    ) -> DocumentParserProcessResult: ...

    async def check_layout_extraction(
        self,
        operation_id: str,
        output_uri: str,
    ) -> DocumentParserProcessResult | None: ...

    async def extract_fragments(self, output_uri: str) -> list[StyleGuideFragmentCandidate]: ...
