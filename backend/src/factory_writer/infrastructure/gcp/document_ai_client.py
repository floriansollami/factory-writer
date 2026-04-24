import asyncio
from time import perf_counter
from typing import Any, cast

from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_toolbox import document as documentai_toolbox
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

from factory_writer.application.ports.product_technical_ingestion import (
    TechnicalDocumentClassificationResult,
    TechnicalDocumentEntity,
    TechnicalDocumentExtractionResult,
)
from factory_writer.application.ports.style_guide_ingestion import (
    DocumentParserProcessResult,
    StyleGuideChunkCandidate,
)
from factory_writer.core.config import Settings
from factory_writer.infrastructure.gcp.gcs_uri import parse_gcs_uri

_STYLE_GUIDE_CHUNK_SIZE_TOKENS = 1000


class DocumentAIClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.gcp.project_id:
            raise ValueError("GCP__PROJECT_ID est requis pour Document AI.")

        api_endpoint = f"{settings.gcp.document_ai_location}-documentai.googleapis.com"
        self._document_client = documentai.DocumentProcessorServiceAsyncClient(
            client_options=ClientOptions(api_endpoint=api_endpoint)
        )

    async def start_document_layout_parse(
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
                # Le style guide est toujours un PDF d'une page.
                # On préfère des chunks larges et peu nombreux, avec les headings ancetres
                # pour garder le contexte de section dans chaque chunk.
                process_options=documentai.ProcessOptions(
                    layout_config=documentai.ProcessOptions.LayoutConfig(
                        chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                            chunk_size=_STYLE_GUIDE_CHUNK_SIZE_TOKENS,
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

    async def check_document_layout_parse(
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

    async def extract_chunks(self, output_uri: str) -> list[StyleGuideChunkCandidate]:
        return await asyncio.to_thread(_extract_chunks_sync, output_uri)

    async def classify_technical_document(
        self,
        *,
        input_uri: str,
        mime_type: str = "application/pdf",
    ) -> TechnicalDocumentClassificationResult:
        gcp = self._settings.gcp
        if not gcp.document_ai_classifier_processor_id:
            raise ValueError("GCP__DOCUMENT_AI_CLASSIFIER_PROCESSOR_ID est requis.")

        processor_name = self._processor_name_for(
            processor_id=gcp.document_ai_classifier_processor_id,
            processor_version=gcp.document_ai_classifier_processor_version,
        )
        request = documentai.ProcessRequest(
            name=processor_name,
            gcs_document=documentai.GcsDocument(gcs_uri=input_uri, mime_type=mime_type),
            skip_human_review=True,
        )
        started = perf_counter()
        response = await self._document_client.process_document(request=request)
        latency_ms = int((perf_counter() - started) * 1000)

        document = response.document
        document_type, confidence = _resolve_document_type(document)

        return TechnicalDocumentClassificationResult(
            processor_resource_name=processor_name,
            processor_version=gcp.document_ai_classifier_processor_version,
            document_type=document_type,
            confidence=confidence,
            latency_ms=latency_ms,
            request_config_snapshot={
                "mode": "online",
                "processor_kind": "custom_classifier",
                "processor_resource_name": processor_name,
                "processor_version": gcp.document_ai_classifier_processor_version,
                "gcs_uri": input_uri,
                "mime_type": mime_type,
                "skip_human_review": True,
            },
            raw_response_summary={
                "entity_count": len(document.entities),
                "page_count": len(document.pages),
            },
        )

    async def extract_technical_facts(
        self,
        *,
        input_uri: str,
        document_type: str,
        mime_type: str = "application/pdf",
    ) -> TechnicalDocumentExtractionResult:
        gcp = self._settings.gcp
        if not gcp.document_ai_extractor_processor_id:
            raise ValueError("GCP__DOCUMENT_AI_EXTRACTOR_PROCESSOR_ID est requis.")

        processor_name = self._processor_name_for(
            processor_id=gcp.document_ai_extractor_processor_id,
            processor_version=gcp.document_ai_extractor_processor_version,
        )
        request = documentai.ProcessRequest(
            name=processor_name,
            gcs_document=documentai.GcsDocument(gcs_uri=input_uri, mime_type=mime_type),
            skip_human_review=True,
        )
        started = perf_counter()
        response = await self._document_client.process_document(request=request)
        latency_ms = int((perf_counter() - started) * 1000)
        document = response.document

        return TechnicalDocumentExtractionResult(
            processor_resource_name=processor_name,
            processor_version=gcp.document_ai_extractor_processor_version,
            latency_ms=latency_ms,
            request_config_snapshot={
                "mode": "online",
                "processor_kind": "custom_extractor_foundation_model",
                "processor_resource_name": processor_name,
                "processor_version": gcp.document_ai_extractor_processor_version,
                "gcs_uri": input_uri,
                "mime_type": mime_type,
                "document_type": document_type,
                "skip_human_review": True,
            },
            entities=[
                _entity_to_technical_fact(entity) for entity in _iter_entities(document.entities)
            ],
        )

    def _processor_name(self) -> str:
        gcp = self._settings.gcp
        if not gcp.document_ai_processor_id:
            raise ValueError("GCP__DOCUMENT_AI_PROCESSOR_ID est requis pour Document AI.")
        return self._processor_name_for(
            processor_id=gcp.document_ai_processor_id,
            processor_version=gcp.document_ai_processor_version,
        )

    def _processor_name_for(self, *, processor_id: str, processor_version: str | None) -> str:
        gcp = self._settings.gcp
        if processor_version:
            return self._document_client.processor_version_path(
                gcp.project_id,
                gcp.document_ai_location,
                processor_id,
                processor_version,
            )

        return self._document_client.processor_path(
            gcp.project_id,
            gcp.document_ai_location,
            processor_id,
        )


def _resolve_document_type(document: documentai.Document) -> tuple[str, float | None]:
    candidates: list[tuple[str, float | None]] = []
    for entity in document.entities:
        label = _normalize_text(getattr(entity, "type_", None))
        value = _normalize_text(getattr(entity, "mention_text", None))
        confidence = _to_float(getattr(entity, "confidence", None))
        generic_labels = {"document_type", "classification", "class", "type"}
        raw_label = value if label.lower() in generic_labels and value else label or value
        candidates.append((raw_label or "UNKNOWN", confidence))

    if not candidates:
        return "UNKNOWN", None

    raw_label, confidence = max(candidates, key=lambda item: item[1] if item[1] is not None else -1)
    return _map_document_type(raw_label), confidence


def _map_document_type(raw_label: str) -> str:
    normalized = raw_label.strip().lower().replace("-", "_").replace(" ", "_")
    aliases = {
        "technical_sheet": "TECHNICAL_SHEET",
        "fiche_technique": "TECHNICAL_SHEET",
        "technical": "TECHNICAL_SHEET",
        "blueprint": "BLUEPRINT",
        "plan": "BLUEPRINT",
        "eco_certificate": "ECO_CERTIFICATE",
        "certificat_ecologique": "ECO_CERTIFICATE",
        "certificate": "ECO_CERTIFICATE",
        "assembly_notice": "ASSEMBLY_NOTICE",
        "notice_montage": "ASSEMBLY_NOTICE",
        "assembly": "ASSEMBLY_NOTICE",
        "material_specification": "MATERIAL_SPECIFICATION",
        "matiere": "MATERIAL_SPECIFICATION",
        "materials": "MATERIAL_SPECIFICATION",
    }
    return aliases.get(normalized, normalized.upper() if normalized else "UNKNOWN")


def _entity_to_technical_fact(entity: documentai.Document.Entity) -> TechnicalDocumentEntity:
    raw_entity_json = _proto_to_dict(entity)
    page, bbox_json = _extract_page_anchor(entity)
    normalized_value = _extract_normalized_value(entity)
    return TechnicalDocumentEntity(
        field_name=_normalize_text(getattr(entity, "type_", None)),
        raw_value=_normalize_text(getattr(entity, "mention_text", None)) or None,
        normalized_value=normalized_value,
        unit=_extract_unit(raw_entity_json),
        confidence=_to_float(getattr(entity, "confidence", None)),
        evidence_text=_normalize_text(getattr(entity, "mention_text", None)) or None,
        page=page,
        bbox_json=bbox_json,
        raw_entity_json=raw_entity_json,
    )


def _iter_entities(entities: Any) -> list[documentai.Document.Entity]:
    flattened: list[documentai.Document.Entity] = []
    for entity in entities:
        flattened.append(entity)
        flattened.extend(_iter_entities(list(getattr(entity, "properties", []) or [])))
    return flattened


def _extract_page_anchor(
    entity: documentai.Document.Entity,
) -> tuple[int | None, dict[str, Any] | None]:
    page_anchor = getattr(entity, "page_anchor", None)
    page_refs = list(getattr(page_anchor, "page_refs", []) or [])
    if not page_refs:
        return None, None

    first_ref = page_refs[0]
    page = _to_int(getattr(first_ref, "page", None))
    page_number = page + 1 if page is not None else None
    bbox = getattr(first_ref, "bounding_poly", None)
    if bbox is None:
        return page_number, None
    return page_number, _proto_to_dict(bbox)


def _extract_normalized_value(entity: documentai.Document.Entity) -> str | None:
    normalized = getattr(entity, "normalized_value", None)
    if normalized is None:
        return _normalize_text(getattr(entity, "mention_text", None)) or None

    text_value = _normalize_text(getattr(normalized, "text", None))
    if text_value:
        return text_value
    return _normalize_text(getattr(entity, "mention_text", None)) or None


def _extract_unit(raw_entity_json: dict[str, Any]) -> str | None:
    normalized = raw_entity_json.get("normalizedValue")
    if isinstance(normalized, dict):
        unit = normalized.get("unit") or normalized.get("currencyCode")
        if isinstance(unit, str) and unit.strip():
            return unit.strip()
    return None


def _proto_to_dict(value: object) -> dict[str, Any]:
    proto = getattr(value, "_pb", value)
    try:
        message = proto if isinstance(proto, Message) else value
        return dict(
            MessageToDict(
                cast(Message, message),
                preserving_proto_field_name=False,
                use_integers_for_enums=False,
            )
        )
    except Exception:
        return {}


def _to_float(value: object) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    return None


def _extract_chunks_sync(output_uri: str) -> list[StyleGuideChunkCandidate]:
    result_uri = parse_gcs_uri(output_uri)

    document = documentai_toolbox.Document.from_gcs(
        gcs_bucket_name=result_uri.bucket_name,
        gcs_prefix=result_uri.object_name,
    )

    return _toolbox_document_to_chunks(document)


def _toolbox_document_to_chunks(
    document: documentai_toolbox.Document,
) -> list[StyleGuideChunkCandidate]:
    chunk_candidates: list[StyleGuideChunkCandidate] = []

    for chunk_index, raw_chunk in enumerate(document.chunks, start=1):
        contenu = _normalize_text(getattr(raw_chunk, "content", ""))

        if not contenu:
            continue

        provider_id = _normalize_text(getattr(raw_chunk, "chunk_id", "")) or f"chunk-{chunk_index}"
        page_span = getattr(raw_chunk, "page_span", None)  # la plage de pages couverte par un chunk
        page_start = _to_int(getattr(page_span, "page_start", None))
        page_end = _to_int(getattr(page_span, "page_end", None)) or page_start

        chunk_candidates.append(
            StyleGuideChunkCandidate(
                provider_id=provider_id,
                index_chunk=chunk_index,
                contenu=contenu,
                page_start=page_start,
                page_end=page_end,
                evidence_json={"source": "chunk"},
            )
        )

    return chunk_candidates


def _to_int(value: object) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _normalize_text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


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
