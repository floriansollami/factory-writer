from __future__ import annotations

import uuid
from collections.abc import Callable

import structlog

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideDocumentParserPort,
    StyleGuideIngestionStartResult,
    StyleGuideRepositoryPort,
    StyleGuideStartStatus,
    StyleGuideStoragePort,
    StyleGuideWorkflowStarterPort,
)
from factory_writer.domain.exceptions import (
    ConfigurationError,
    DocumentAIOutputMissingError,
    FactoryWriterError,
    InvalidGcsUriError,
    InvalidStyleGuideSourceIdError,
    StyleGuideObjectNotFoundError,
    WorkflowStartError,
)
from factory_writer.domain.style_guide_types import StatutSource
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StyleGuideIngestionInput,
    StyleGuideLayoutParseResult,
)

logger = structlog.get_logger(__name__)

_DOC_AI_OUTPUT_PREFIX = "_factory_writer/style-guide-layout"
_GENERIC_WORKFLOW_FAILURE_MESSAGE = "Le workflow a échoué. Voir l'historique Temporal pour le détail."


def _parse_uuid(raw_value: str) -> uuid.UUID:
    try:
        return uuid.UUID(raw_value)
    except ValueError as exc:
        raise InvalidStyleGuideSourceIdError(raw_value) from exc


def _parse_gcs_uri(uri: str) -> tuple[str, str]:
    if not uri.startswith("gs://"):
        raise InvalidGcsUriError(uri)

    path = uri.removeprefix("gs://")
    bucket_name, separator, object_name = path.partition("/")
    if not bucket_name or not separator or not object_name:
        raise InvalidGcsUriError(uri)

    return bucket_name, object_name


def _build_docai_output_uri(bucket_name: str, source_id: str, generation: str) -> str:
    return f"gs://{bucket_name}/{_DOC_AI_OUTPUT_PREFIX}/{source_id}/{generation}/"


class StyleGuideIngestionService:
    def __init__(
        self,
        repository: StyleGuideRepositoryPort,
        *,
        style_guide_bucket_name: str | None = None,
        workflow_starter: StyleGuideWorkflowStarterPort | None = None,
        storage: StyleGuideStoragePort | None = None,
        document_parser: StyleGuideDocumentParserPort | None = None,
    ) -> None:
        self._repository = repository
        self._style_guide_bucket_name = style_guide_bucket_name
        self._workflow_starter = workflow_starter
        self._storage = storage
        self._document_parser = document_parser

    async def start_from_storage_event(
        self,
        *,
        bucket_name: str,
        file_name: str,
    ) -> StyleGuideIngestionStartResult:
        expected_bucket_name = self._require_style_guide_bucket_name()

        if bucket_name != expected_bucket_name:
            return StyleGuideIngestionStartResult(
                status=StyleGuideStartStatus.IGNORED,
                reason="wrong_bucket",
            )

        if not file_name.lower().endswith(".pdf"):
            return StyleGuideIngestionStartResult(
                status=StyleGuideStartStatus.IGNORED,
                reason="not_pdf",
            )

        target_uri = f"gs://{bucket_name}/{file_name}"
        existing_source = await self._repository.get_by_uri(target_uri)

        if existing_source is not None and existing_source.statut != StatutSource.ERREUR:
            return StyleGuideIngestionStartResult(
                status=StyleGuideStartStatus.IGNORED,
                reason="already_ingested",
                source_id=str(existing_source.id),
            )

        if existing_source is None:
            source = await self._repository.create_source(target_uri, StatutSource.EN_ATTENTE)
        else:
            source = await self._repository.update_source_status(
                existing_source.id,
                StatutSource.EN_ATTENTE,
                error_message=None,
            )

        workflow_payload = StyleGuideIngestionInput(
            source_id=str(source.id),
            file_uri=source.uri_fichier,
        )

        try:
            workflow_id = await self._require_workflow_starter().start_style_guide_ingestion(
                workflow_payload
            )
        except FactoryWriterError as exc:
            await self._repository.update_source_status(
                source.id,
                StatutSource.ERREUR,
                error_message=exc.message,
            )
            raise

        logger.info(
            "style_guide_ingestion.started",
            source_id=str(source.id),
            file_uri=source.uri_fichier,
            workflow_id=workflow_id,
        )
        return StyleGuideIngestionStartResult(
            status=StyleGuideStartStatus.STARTED,
            source_id=str(source.id),
            workflow_id=workflow_id,
        )

    async def mark_source_in_progress(self, source_id: str) -> None:
        source_uuid = _parse_uuid(source_id)
        await self._repository.update_source_status(
            source_id=source_uuid,
            statut=StatutSource.EN_COURS,
            only_if_not_terminal=True,
        )

    async def mark_source_failed(self, source_id: str) -> None:
        source_uuid = _parse_uuid(source_id)
        await self._repository.update_source_status(
            source_id=source_uuid,
            statut=StatutSource.ERREUR,
            error_message=_GENERIC_WORKFLOW_FAILURE_MESSAGE,
        )

    async def parse_style_guide_with_docai(
        self,
        payload: StyleGuideIngestionInput,
        heartbeat: Callable[[dict[str, str]], None],
    ) -> StyleGuideLayoutParseResult:
        source_uuid = _parse_uuid(payload.source_id)
        bucket_name, object_name = _parse_gcs_uri(payload.file_uri)

        try:
            storage = self._require_storage()
            document_parser = self._require_document_parser()

            metadata = await storage.get_blob_metadata(bucket_name, object_name)
            if metadata is None:
                raise StyleGuideObjectNotFoundError(payload.file_uri)

            output_uri = _build_docai_output_uri(
                bucket_name=metadata.bucket_name,
                source_id=payload.source_id,
                generation=metadata.generation,
            )

            heartbeat(
                {
                    "stage": "gcs_metadata_loaded",
                    "source_id": payload.source_id,
                    "generation": metadata.generation,
                }
            )

            source = await self._repository.update_gcs_metadata(
                source_id=source_uuid,
                bucket_name=metadata.bucket_name,
                object_name=metadata.object_name,
                generation=metadata.generation,
                metageneration=metadata.metageneration,
            )

            if (
                source.uri_sortie_docai == output_uri
                and source.operation_docai_id is not None
                and source.generation_gcs == metadata.generation
            ):
                output_prefix = output_uri.removeprefix(f"gs://{bucket_name}/")
                output_exists = await storage.has_blobs_with_prefix(bucket_name, output_prefix)
                if output_exists:
                    return StyleGuideLayoutParseResult(
                        source_id=payload.source_id,
                        source_generation=metadata.generation,
                        layout_operation_id=source.operation_docai_id,
                        output_uri=output_uri,
                    )

            parse_result = await document_parser.process_document_lro(
                input_uri=payload.file_uri,
                output_uri=output_uri,
                heartbeat_callback=heartbeat,
            )

            resolved_bucket_name, resolved_prefix = _parse_gcs_uri(parse_result.output_uri)
            output_exists = await storage.has_blobs_with_prefix(
                resolved_bucket_name,
                resolved_prefix,
            )
            if not output_exists:
                raise DocumentAIOutputMissingError(parse_result.output_uri)

            await self._repository.update_docai_output(
                source_id=source_uuid,
                docai_resource=parse_result.processor_resource_name,
                operation_id=parse_result.operation_id,
                output_uri=parse_result.output_uri,
            )

            return StyleGuideLayoutParseResult(
                source_id=payload.source_id,
                source_generation=metadata.generation,
                layout_operation_id=parse_result.operation_id,
                output_uri=parse_result.output_uri,
            )
        except FactoryWriterError as exc:
            await self._repository.update_error_message(source_uuid, exc.message)
            raise

    def _require_style_guide_bucket_name(self) -> str:
        if not self._style_guide_bucket_name:
            raise ConfigurationError(
                "GCP__STYLE_GUIDE_BUCKET_NAME is required to ingest a style guide.",
                code="MISSING_STYLE_GUIDE_BUCKET",
            )
        return self._style_guide_bucket_name

    def _require_workflow_starter(self) -> StyleGuideWorkflowStarterPort:
        if self._workflow_starter is None:
            raise WorkflowStartError("workflow starter non configuré")
        return self._workflow_starter

    def _require_storage(self) -> StyleGuideStoragePort:
        if self._storage is None:
            raise ConfigurationError(
                "Style guide storage adapter is required for Document AI parsing.",
                code="MISSING_STYLE_GUIDE_STORAGE",
            )
        return self._storage

    def _require_document_parser(self) -> StyleGuideDocumentParserPort:
        if self._document_parser is None:
            raise ConfigurationError(
                "Style guide document parser adapter is required for Document AI parsing.",
                code="MISSING_STYLE_GUIDE_DOCUMENT_PARSER",
            )
        return self._document_parser
