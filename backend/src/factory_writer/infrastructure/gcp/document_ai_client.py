import asyncio
from collections.abc import Callable

from google.api_core.client_options import ClientOptions
from google.api_core.exceptions import GoogleAPICallError, NotFound
from google.cloud import documentai_v1 as documentai

from factory_writer.application.ports.style_guide_ingestion import DocumentAIProcessResult
from factory_writer.core.config import Settings
from factory_writer.domain.exceptions import (
    ConfigurationError,
    StyleGuideDocumentAIProcessingError,
    StyleGuideDocumentAIResourceNotFoundError,
    StyleGuideDocumentAITransientError,
)


class DocumentAIClient:
    def __init__(self, settings: Settings):
        self._settings = settings
        if not self._settings.gcp.project_id:
            raise ConfigurationError(
                "GCP__PROJECT_ID is required for Document AI.",
                code="MISSING_GCP_PROJECT_ID",
            )
        if not self._settings.gcp.document_ai_processor_id:
            raise ConfigurationError(
                "GCP__DOCUMENT_AI_PROCESSOR_ID is required for Document AI.",
                code="MISSING_DOCUMENT_AI_PROCESSOR_ID",
            )

        api_endpoint = f"{self._settings.gcp.document_ai_location}-documentai.googleapis.com"
        self._client = documentai.DocumentProcessorServiceAsyncClient(
            client_options=ClientOptions(api_endpoint=api_endpoint)
        )

    def _build_processor_name(self) -> str:
        processor_version = self._settings.gcp.document_ai_processor_version
        if processor_version:
            return self._client.processor_version_path(
                self._settings.gcp.project_id,
                self._settings.gcp.document_ai_location,
                self._settings.gcp.document_ai_processor_id,
                processor_version,
            )

        return self._client.processor_path(
            self._settings.gcp.project_id,
            self._settings.gcp.document_ai_location,
            self._settings.gcp.document_ai_processor_id,
        )

    async def process_document_lro(
        self,
        input_uri: str,
        output_uri: str,
        heartbeat_callback: Callable[[dict[str, str]], None] | None = None,
    ) -> DocumentAIProcessResult:
        """
        Starts a Document AI batch process, polls with a heartbeat callback, 
        and returns the resolved Document AI batch processing result.
        """
        try:
            processor_name = self._build_processor_name()

            input_documents = documentai.BatchDocumentsInputConfig(
                gcs_documents=documentai.GcsDocuments(
                    documents=[
                        documentai.GcsDocument(
                            gcs_uri=input_uri,
                            mime_type="application/pdf",
                        )
                    ]
                )
            )
            document_output_config = documentai.DocumentOutputConfig(
                gcs_output_config=documentai.DocumentOutputConfig.GcsOutputConfig(
                    gcs_uri=output_uri
                )
            )
            request = documentai.BatchProcessRequest(
                name=processor_name,
                input_documents=input_documents,
                document_output_config=document_output_config,
                skip_human_review=True,
            )

            operation = await self._client.batch_process_documents(request=request)
            operation_id = operation.operation.name

            if heartbeat_callback:
                heartbeat_callback(
                    {
                        "stage": "docai_operation_started",
                        "operation_id": operation_id,
                    }
                )

            # SOTA Polling with heartbeat
            while not await operation.done():  # type: ignore[no-untyped-call]
                await asyncio.sleep(5)
                if heartbeat_callback:
                    heartbeat_callback(
                        {
                            "stage": "docai_operation_polling",
                            "operation_id": operation_id,
                        }
                    )

            await operation.result()  # type: ignore[no-untyped-call]

            # Determine actual output bucket destination
            metadata_response = operation.metadata
            resolved_output_uri = output_uri

            statuses = getattr(metadata_response, "individual_process_statuses", [])
            if statuses:
                first_status = statuses[0]
                raw_status = getattr(first_status, "status", None)
                if raw_status is not None and getattr(raw_status, "code", 0) != 0:
                    raise StyleGuideDocumentAIProcessingError(
                        f"{input_uri}: {raw_status.message}"
                    )

                output_destination = getattr(first_status, "output_gcs_destination", "")
                if output_destination:
                    resolved_output_uri = str(output_destination)

            return DocumentAIProcessResult(
                processor_resource_name=processor_name,
                operation_id=operation_id,
                output_uri=resolved_output_uri,
            )
        except NotFound as exc:
            raise StyleGuideDocumentAIResourceNotFoundError(str(exc)) from exc
        except GoogleAPICallError as exc:
            raise StyleGuideDocumentAITransientError(str(exc)) from exc
