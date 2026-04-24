import asyncio
import re
import uuid
from pathlib import Path

from google.api_core.exceptions import PreconditionFailed
from google.cloud.storage import Client as GcsClient  # type: ignore[import-untyped]

from factory_writer.application.ports.product_technical_ingestion import (
    UploadedTechnicalDocumentSourceFile,
)
from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideDocumentSourceFile,
    UploadedStyleGuideDocumentSourceFile,
)
from factory_writer.core.config import Settings
from factory_writer.infrastructure.gcp.gcs_uri import as_directory_prefix, parse_gcs_uri

_INTERNAL_DERIVED_DOCUMENT_AI_PREFIX = "_factory_writer/derived/document-ai"
_SOURCE_STYLE_GUIDE_PREFIX = "sources/style-guides"
_SOURCE_TECHNICAL_DOSSIER_PREFIX = "sources/technical-dossiers"
_PDF_CONTENT_TYPE = "application/pdf"
_MAX_SAFE_FILENAME_LENGTH = 120
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


class StorageClient:
    def __init__(self, settings: Settings) -> None:
        self._style_guide_bucket_name = settings.gcp.style_guide_bucket_name
        self._technical_dossier_bucket_name = settings.gcp.technical_dossier_bucket_name
        self._client = _build_gcs_client(settings)

    async def upload_document_source_pdf(
        self,
        *,
        document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedStyleGuideDocumentSourceFile:
        return await asyncio.to_thread(
            self._upload_document_source_pdf_sync,
            document_source_id,
            file_name,
            content,
            content_type,
        )

    async def get_document_source_file(
        self, storage_uri: str
    ) -> StyleGuideDocumentSourceFile | None:
        return await asyncio.to_thread(self._get_document_source_file_sync, storage_uri)

    async def upload_technical_document_source_pdf(
        self,
        *,
        product_id: uuid.UUID,
        document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedTechnicalDocumentSourceFile:
        return await asyncio.to_thread(
            self._upload_technical_document_source_pdf_sync,
            product_id,
            document_source_id,
            file_name,
            content,
            content_type,
        )

    async def has_parser_result(self, result_uri: str) -> bool:
        return await asyncio.to_thread(self._has_parser_result_sync, result_uri)

    def build_parser_result_uri(
        self,
        input_uri: str,
        extraction_type: str,
        document_source_id: uuid.UUID,
        generation: str,
    ) -> str:
        # Les artefacts Document AI sont des sorties techniques dérivées du PDF source.
        # On les range donc sous un préfixe interne séparé des documents métier.
        parsed_input_uri = parse_gcs_uri(input_uri)
        return (
            f"gs://{parsed_input_uri.bucket_name}/"
            f"{_INTERNAL_DERIVED_DOCUMENT_AI_PREFIX}/"
            f"{extraction_type}/document_source_id={document_source_id}/gcs_generation={generation}/"
        )

    def _upload_document_source_pdf_sync(
        self,
        document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedStyleGuideDocumentSourceFile:
        if not self._style_guide_bucket_name:
            raise RuntimeError("GCP style guide bucket non configuré.")

        # On garde un nom de fichier lisible, mais maîtrisé :
        # extension .pdf obligatoire, caractères spéciaux neutralisés, longueur bornée.
        safe_file_name = _safe_pdf_filename(file_name)

        # Le chemin GCS est déterministe par document_source_id.
        # Ça évite les collisions et permet de recoller exactement l'objet GCS
        # au document_source SQL correspondant.
        object_name = f"{_SOURCE_STYLE_GUIDE_PREFIX}/{document_source_id}/{safe_file_name}"

        # Le SDK GCS manipule un Blob, c'est l'objet fichier côté bucket.
        blob = self._client.bucket(self._style_guide_bucket_name).blob(object_name)

        try:
            blob.upload_from_string(
                content,
                # Le routeur a déjà validé qu'on traite un PDF.
                content_type=_normalize_pdf_content_type(content_type),
                # if_generation_match=0 rend l'écriture idempotente :
                # on crée l'objet uniquement s'il n'existe pas encore.
                if_generation_match=0,
            )
        except PreconditionFailed:
            # Si Temporal ou le client rejoue après un upload déjà réussi,
            # GCS renvoie 412. On recharge alors les métadonnées de l'objet existant.
            blob.reload()

        if blob.generation is None or blob.metageneration is None:
            raise RuntimeError(f"Metadata GCS incomplète après upload: {object_name}")

        return UploadedStyleGuideDocumentSourceFile(
            # URI canonique que l'on stocke en base et que l'on passe au reste du pipeline.
            storage_uri=f"gs://{self._style_guide_bucket_name}/{object_name}",
            # On renvoie aussi la séparation bucket/object_name pour éviter de reparser l'URI
            # plus bas dans le repository.
            storage_bucket=self._style_guide_bucket_name,
            storage_object_name=object_name,
            # generation = version du contenu, metageneration = version des métadonnées.
            generation=str(blob.generation),
            metageneration=str(blob.metageneration),
        )

    def _upload_technical_document_source_pdf_sync(
        self,
        product_id: uuid.UUID,
        document_source_id: uuid.UUID,
        file_name: str,
        content: bytes,
        content_type: str,
    ) -> UploadedTechnicalDocumentSourceFile:
        if not self._technical_dossier_bucket_name:
            raise RuntimeError("GCP technical dossier bucket non configuré.")

        safe_file_name = _safe_pdf_filename(file_name, fallback_stem="technical-document")
        object_name = (
            f"{_SOURCE_TECHNICAL_DOSSIER_PREFIX}/{product_id}/{document_source_id}/{safe_file_name}"
        )

        blob = self._client.bucket(self._technical_dossier_bucket_name).blob(object_name)

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

        return UploadedTechnicalDocumentSourceFile(
            storage_uri=f"gs://{self._technical_dossier_bucket_name}/{object_name}",
            storage_bucket=self._technical_dossier_bucket_name,
            storage_object_name=object_name,
            generation=str(blob.generation),
            metageneration=str(blob.metageneration),
        )

    def _get_document_source_file_sync(
        self, storage_uri: str
    ) -> StyleGuideDocumentSourceFile | None:
        # Ici on repart d'une URI persistée en base pour relire l'objet GCS exact.
        parsed_storage_uri = parse_gcs_uri(storage_uri)
        blob = self._client.bucket(parsed_storage_uri.bucket_name).get_blob(
            parsed_storage_uri.object_name
        )
        if blob is None:
            return None
        if blob.generation is None or blob.metageneration is None:
            raise RuntimeError(f"Metadata GCS incomplète pour {storage_uri}")

        return StyleGuideDocumentSourceFile(
            storage_uri=f"gs://{parsed_storage_uri.bucket_name}/{blob.name}",
            storage_bucket=parsed_storage_uri.bucket_name,
            storage_object_name=blob.name,
            generation=str(blob.generation),
            metageneration=str(blob.metageneration),
        )

    def _has_parser_result_sync(self, dir_uri: str) -> bool:
        # GCS n'a pas de vrais répertoires : on vérifie juste qu'au moins un objet existe
        # sous le préfixe de sortie Document AI.
        result_uri = parse_gcs_uri(dir_uri, require_object=False)
        prefix = as_directory_prefix(result_uri.object_name)
        blobs = self._client.list_blobs(result_uri.bucket_name, prefix=prefix, max_results=1)
        return any(blobs)


def _safe_pdf_filename(file_name: str, fallback_stem: str = "style-guide") -> str:
    path = Path(file_name.strip())
    # pathlib évite les manipulations fragiles de suffixe à la main.
    if path.suffix.lower() != ".pdf":
        raise ValueError(f"File must be a PDF: {file_name}")

    safe_stem = _SAFE_FILENAME_PATTERN.sub("-", path.stem).strip("-_.")
    safe_stem = (safe_stem or fallback_stem)[: _MAX_SAFE_FILENAME_LENGTH - 4]
    return f"{safe_stem}.pdf"


def _normalize_pdf_content_type(content_type: str) -> str:
    # On force le content type canonique, même si le navigateur a envoyé
    # application/octet-stream ou une variante équivalente.
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
