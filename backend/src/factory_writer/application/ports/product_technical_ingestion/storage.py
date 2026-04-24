import uuid
from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class UploadedTechnicalDocumentSourceFile:
    storage_uri: str
    storage_bucket: str
    storage_object_name: str
    generation: str
    metageneration: str


class TechnicalSourceStoragePort(Protocol):
    async def upload_technical_document_source_pdf(
        self,
        *,
        product_id: uuid.UUID,
        document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedTechnicalDocumentSourceFile: ...
