import asyncio
import uuid

from google.cloud.storage import Client as GcsClient  # type: ignore[import-untyped]

from factory_writer.application.ports.style_guide_ingestion import StyleGuideSourceFile
from factory_writer.core.config import Settings
from factory_writer.infrastructure.gcp.gcs_uri import as_directory_prefix, parse_gcs_uri

_INTERNAL_DERIVED_DOCUMENT_AI_PREFIX = "_factory_writer/derived/document-ai"


class StorageClient:
    def __init__(self, settings: Settings) -> None:
        # Client GCS instancie une seule fois pour reutiliser les connexions HTTP.
        self._client = GcsClient(project=settings.gcp.project_id or None)

    async def get_source_file(self, file_uri: str) -> StyleGuideSourceFile | None:
        # Le SDK GCS est synchrone: on le deplace dans un thread pour ne pas bloquer
        # la boucle async du worker Temporal.
        return await asyncio.to_thread(self._get_source_file_sync, file_uri)

    async def has_parser_result(self, result_uri: str) -> bool:
        # Meme logique que get_source_file: list_blobs est une I/O bloquante.
        return await asyncio.to_thread(self._has_parser_result_sync, result_uri)

    def build_parser_result_uri(
        self,
        input_uri: str,
        extraction_type: str,
        source_id: uuid.UUID,
        generation: str,
    ) -> str:
        # Le resultat Document AI est un artefact technique derive, pas une source métier.
        # On le separe donc sous _factory_writer/derived/document-ai.
        source_uri = parse_gcs_uri(input_uri)
        return (
            f"gs://{source_uri.bucket_name}/"
            f"{_INTERNAL_DERIVED_DOCUMENT_AI_PREFIX}/"
            f"{extraction_type}/source_id={source_id}/gcs_generation={generation}/"
        )

    def _get_source_file_sync(self, file_uri: str) -> StyleGuideSourceFile | None:
        # On recupere les metadonnees GCS du fichier source sans telecharger le PDF.
        # generation/metageneration permettent de tracer la version exacte du PDF.
        source_uri = parse_gcs_uri(file_uri)
        blob = self._client.bucket(source_uri.bucket_name).get_blob(source_uri.object_name)
        if blob is None:
            return None
        if blob.generation is None or blob.metageneration is None:
            raise RuntimeError(f"Metadata GCS incomplète pour {file_uri}")

        return StyleGuideSourceFile(
            uri=f"gs://{source_uri.bucket_name}/{blob.name}",
            generation=str(blob.generation),
            metageneration=str(blob.metageneration),
        )

    def _has_parser_result_sync(self, dir_uri: str) -> bool:
        # GCS n'a pas de vrais dossiers: un "dossier" est juste un prefixe d'objet.
        # as_directory_prefix ajoute le slash final pour eviter les faux positifs.
        result_uri = parse_gcs_uri(dir_uri, require_object=False)
        prefix = as_directory_prefix(result_uri.object_name)
        # max_results=1 suffit: on veut seulement savoir si au moins un JSON existe.
        blobs = self._client.list_blobs(result_uri.bucket_name, prefix=prefix, max_results=1)
        return any(blobs)
