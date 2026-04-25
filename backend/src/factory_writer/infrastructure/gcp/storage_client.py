import asyncio

from google.api_core.exceptions import PreconditionFailed
from google.cloud.storage import Client as GcsClient  # type: ignore[import-untyped]

from factory_writer.application.ports.object_storage import (
    StoredObjectFile,
    UploadedObjectFile,
)
from factory_writer.core.config import Settings
from factory_writer.infrastructure.gcp.gcs_uri import as_directory_prefix, parse_gcs_uri

_PDF_CONTENT_TYPE = "application/pdf"


class StorageClient:
    def __init__(self, settings: Settings) -> None:
        self._client = _build_gcs_client(settings)

    async def upload_pdf_object(
        self,
        *,
        bucket_name: str,
        object_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedObjectFile:
        return await asyncio.to_thread(
            self._upload_pdf_object_sync,
            bucket_name,
            object_name,
            content,
            content_type,
        )

    async def get_object_file(self, storage_uri: str) -> StoredObjectFile | None:
        return await asyncio.to_thread(self._get_object_file_sync, storage_uri)

    async def has_objects(self, result_uri: str) -> bool:
        return await asyncio.to_thread(self._has_objects_sync, result_uri)

    def _upload_pdf_object_sync(
        self,
        bucket_name: str,
        object_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedObjectFile:
        if not bucket_name:
            raise RuntimeError("GCP bucket non configuré.")

        if not object_name.strip():
            raise RuntimeError("GCS object_name non configuré.")

        blob = self._client.bucket(bucket_name).blob(object_name)

        try:
            blob.upload_from_string(
                content,
                content_type=_normalize_pdf_content_type(content_type),
                if_generation_match=0,
            )
        except PreconditionFailed:
            blob.reload()

        if blob.generation is None or blob.metageneration is None:
            raise RuntimeError(f"Metadata GCS incomplète après upload: {object_name}")

        return UploadedObjectFile(
            storage_uri=f"gs://{bucket_name}/{object_name}",
            storage_bucket=bucket_name,
            storage_object_name=object_name,
            generation=str(blob.generation),
            metageneration=str(blob.metageneration),
        )

    def _get_object_file_sync(self, storage_uri: str) -> StoredObjectFile | None:
        parsed_storage_uri = parse_gcs_uri(storage_uri)
        blob = self._client.bucket(parsed_storage_uri.bucket_name).get_blob(
            parsed_storage_uri.object_name
        )
        if blob is None:
            return None
        if blob.generation is None or blob.metageneration is None:
            raise RuntimeError(f"Metadata GCS incomplète pour {storage_uri}")

        return StoredObjectFile(
            storage_uri=f"gs://{parsed_storage_uri.bucket_name}/{blob.name}",
            storage_bucket=parsed_storage_uri.bucket_name,
            storage_object_name=blob.name,
            generation=str(blob.generation),
            metageneration=str(blob.metageneration),
        )

    def _has_objects_sync(self, dir_uri: str) -> bool:
        result_uri = parse_gcs_uri(dir_uri, require_object=False)
        prefix = as_directory_prefix(result_uri.object_name)
        blobs = self._client.list_blobs(result_uri.bucket_name, prefix=prefix, max_results=1)
        return any(blobs)


def _normalize_pdf_content_type(content_type: str) -> str:
    return _PDF_CONTENT_TYPE


def _build_gcs_client(settings: Settings) -> GcsClient:
    emulator_host = settings.gcp.storage_emulator_host.strip()
    if emulator_host:
        # En test local on cible explicitement l'émulateur GCS et on désactive l'auth.
        return GcsClient(
            project=settings.gcp.project_id or "local-dev",
            client_options={"api_endpoint": _normalize_storage_emulator_host(emulator_host)},
            use_auth_w_custom_endpoint=False,
        )

    # En environnement réel, on laisse le client utiliser la config standard GCP/ADC.
    return GcsClient(project=settings.gcp.project_id or None)


def _normalize_storage_emulator_host(storage_emulator_host: str) -> str:
    if "://" in storage_emulator_host:
        return storage_emulator_host
    return f"http://{storage_emulator_host}"
