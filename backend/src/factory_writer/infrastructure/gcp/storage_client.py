import asyncio

from google.cloud.storage import Client as GcsClient  # type: ignore[import-untyped]

from factory_writer.application.ports.style_guide_ingestion import GcsObjectMetadata
from factory_writer.core.config import Settings


class StorageClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        project_id = self._settings.gcp.project_id or None
        self._client = GcsClient(project=project_id)

    def _fetch_blob_metadata_sync(self, bucket_name: str, object_name: str) -> GcsObjectMetadata | None:
        blob = self._client.bucket(bucket_name).get_blob(object_name)
        if blob is None:
            return None
        
        generation = getattr(blob, "generation", None)
        metageneration = getattr(blob, "metageneration", None)
        if generation is None or metageneration is None:
            return None

        return GcsObjectMetadata(
            bucket_name=bucket_name,
            object_name=object_name,
            generation=str(generation),
            metageneration=str(metageneration),
        )

    def _list_blobs_sync(self, bucket_name: str, prefix: str) -> bool:
        blobs = self._client.list_blobs(bucket_name, prefix=prefix, max_results=1)
        return any(True for _ in blobs)

    async def get_blob_metadata(self, bucket_name: str, object_name: str) -> GcsObjectMetadata | None:
        return await asyncio.to_thread(self._fetch_blob_metadata_sync, bucket_name, object_name)

    async def has_blobs_with_prefix(self, bucket_name: str, prefix: str) -> bool:
        return await asyncio.to_thread(self._list_blobs_sync, bucket_name, prefix)
