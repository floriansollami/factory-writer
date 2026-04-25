from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True)
class StoredObjectFile:
    storage_uri: str
    storage_bucket: str
    storage_object_name: str
    generation: str
    metageneration: str


@dataclass(frozen=True)
class UploadedObjectFile:
    storage_uri: str
    storage_bucket: str
    storage_object_name: str
    generation: str
    metageneration: str


class ObjectStoragePort(Protocol):
    async def upload_pdf_object(
        self,
        *,
        bucket_name: str,
        object_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedObjectFile: ...
