import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StyleGuideDocumentSourceFile:
    storage_uri: str
    storage_bucket: str
    storage_object_name: str
    generation: str
    metageneration: str


@dataclass(frozen=True)
class UploadedStyleGuideDocumentSourceFile:
    storage_uri: str
    storage_bucket: str
    storage_object_name: str
    generation: str
    metageneration: str


class StyleGuideStoragePort(Protocol):
    async def upload_document_source_pdf(
        self,
        *,
        document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedStyleGuideDocumentSourceFile: ...

    async def get_document_source_file(
        self, storage_uri: str
    ) -> StyleGuideDocumentSourceFile | None: ...

    async def has_parser_result(self, result_uri: str) -> bool: ...

    def build_parser_result_uri(
        self,
        input_uri: str,
        extraction_type: str,
        document_source_id: uuid.UUID,
        generation: str,
    ) -> str: ...
