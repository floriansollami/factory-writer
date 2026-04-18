import asyncio

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_toolbox import document as documentai_toolbox

from factory_writer.application.ports.style_guide_ingestion import (
    DocumentParserProcessResult,
    StyleGuideFragmentCandidate,
)
from factory_writer.core.config import Settings
from factory_writer.infrastructure.gcp.gcs_uri import parse_gcs_uri


class DocumentAIClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.gcp.project_id:
            raise ValueError("GCP__PROJECT_ID est requis pour Document AI.")
        if not settings.gcp.document_ai_processor_id:
            raise ValueError("GCP__DOCUMENT_AI_PROCESSOR_ID est requis pour Document AI.")

        api_endpoint = f"{settings.gcp.document_ai_location}-documentai.googleapis.com"
        self._document_client = documentai.DocumentProcessorServiceAsyncClient(
            client_options=ClientOptions(api_endpoint=api_endpoint)
        )

    async def start_layout_extraction(
        self,
        input_uri: str,
        output_uri: str,
    ) -> DocumentParserProcessResult:
        processor_name = self._processor_name()

        operation = await self._document_client.batch_process_documents(
            request=documentai.BatchProcessRequest(
                name=processor_name,
                input_documents=documentai.BatchDocumentsInputConfig(
                    gcs_documents=documentai.GcsDocuments(
                        documents=[
                            documentai.GcsDocument(
                                gcs_uri=input_uri,
                                mime_type="application/pdf",
                            )
                        ]
                    )
                ),
                document_output_config=documentai.DocumentOutputConfig(
                    gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                        gcs_uri=output_uri
                    )
                ),
                process_options=documentai.ProcessOptions(
                    layout_config=documentai.ProcessOptions.LayoutConfig(
                        chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                            include_ancestor_headings=True,
                        )
                    )
                ),
            )
        )

        return DocumentParserProcessResult(
            processor_resource_name=processor_name,
            operation_id=operation.operation.name,
            output_uri=output_uri,
        )

    async def check_layout_extraction(
        self,
        operation_id: str,
        output_uri: str,
    ) -> DocumentParserProcessResult | None:
        operation = await self._document_client.transport.operations_client.get_operation(
            name=operation_id
        )

        if not operation.done:
            return None

        if operation.error.code != 0:
            raise RuntimeError(f"Document AI error: {operation.error.message}")

        metadata = documentai.BatchProcessMetadata.deserialize(operation.metadata.value)

        return DocumentParserProcessResult(
            processor_resource_name=self._processor_name(),
            operation_id=operation_id,
            output_uri=_resolve_output_uri(metadata, output_uri),
        )

    async def extract_fragments(self, output_uri: str) -> list[StyleGuideFragmentCandidate]:
        return await asyncio.to_thread(_extract_fragments_sync, output_uri)

    def _processor_name(self) -> str:
        gcp = self._settings.gcp
        if gcp.document_ai_processor_version:
            return self._document_client.processor_version_path(
                gcp.project_id,
                gcp.document_ai_location,
                gcp.document_ai_processor_id,
                gcp.document_ai_processor_version,
            )

        return self._document_client.processor_path(
            gcp.project_id,
            gcp.document_ai_location,
            gcp.document_ai_processor_id,
        )


def _extract_fragments_sync(output_uri: str) -> list[StyleGuideFragmentCandidate]:
    result_uri = parse_gcs_uri(output_uri)

    document = documentai_toolbox.Document.from_gcs(
        gcs_bucket_name=result_uri.bucket_name,
        gcs_prefix=result_uri.object_name,
    )

    return _toolbox_document_to_fragments(document)


def _toolbox_document_to_fragments(
    document: documentai_toolbox.Document,
) -> list[StyleGuideFragmentCandidate]:
    texts = _chunk_texts(document)

    # POC: éviter un fallback paragraphe qui peut couper une règle en plusieurs fragments.
    # Si le Layout Parser ne fournit pas de chunks, on conserve le texte complet.
    if not texts and document.text:
        texts = [str(document.text)]

    cleaned_texts = _texts_to_fragments(texts)

    if not cleaned_texts:
        return []

    return [
        StyleGuideFragmentCandidate(
            index_fragment=index,
            contenu=text,
        )
        for index, text in enumerate(cleaned_texts, start=1)
    ]


def _chunk_texts(document: documentai_toolbox.Document) -> list[str]:
    return [
        text
        for chunk in document.chunks
        if (text := str(getattr(chunk, "content", "") or "").strip())
    ]


def _texts_to_fragments(texts: list[str]) -> list[str]:
    return [text.strip() for text in texts if text.strip()]


def _resolve_output_uri(
    metadata: documentai.BatchProcessMetadata,
    fallback_output_uri: str,
) -> str:
    if metadata.state != documentai.BatchProcessMetadata.State.SUCCEEDED:
        message = metadata.state_message or f"Document AI batch state: {metadata.state.name}"
        raise RuntimeError(message)

    statuses = list(metadata.individual_process_statuses)
    if not statuses:
        return fallback_output_uri

    first_status = statuses[0]
    if first_status.status.code != 0:
        raise RuntimeError(first_status.status.message)

    output_destination = str(first_status.output_gcs_destination or "")
    return output_destination or fallback_output_uri
