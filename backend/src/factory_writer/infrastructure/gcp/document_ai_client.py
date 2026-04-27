import json
from time import perf_counter
from typing import Any, cast

import structlog
from google.api_core.client_options import ClientOptions
from google.cloud import documentai_v1 as documentai
from google.protobuf import field_mask_pb2
from google.protobuf.json_format import MessageToDict
from google.protobuf.message import Message

from factory_writer.application.ports.product_technical_ingestion import (
    TechnicalDocumentClassificationResult,
    TechnicalDocumentEntity,
    TechnicalDocumentExtractionResult,
    TechnicalExtractorRoute,
)
from factory_writer.application.ports.style_guide_ingestion import (
    DocumentParserProcessResult,
    StyleGuideChunkCandidate,
)
from factory_writer.core.config import Settings

_STYLE_GUIDE_CHUNK_SIZE_TOKENS = 1000
_DOCUMENT_AI_ONLINE_TIMEOUT_SECONDS = 120.0

logger = structlog.get_logger(__name__)


class DocumentAIClient:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        if not settings.gcp.project_id:
            raise ValueError("GCP__PROJECT_ID est requis pour Document AI.")

        api_endpoint = f"{settings.gcp.document_ai_location}-documentai.googleapis.com"
        self._document_client = documentai.DocumentProcessorServiceAsyncClient(
            client_options=ClientOptions(api_endpoint=api_endpoint)
        )

    async def parse_document_layout(
        self,
        input_uri: str,
    ) -> DocumentParserProcessResult:
        processor_name = self._processor_name()

        request = documentai.ProcessRequest(
            name=processor_name,
            gcs_document=documentai.GcsDocument(
                gcs_uri=input_uri,
                mime_type="application/pdf",
            ),
            skip_human_review=True,
            process_options=_style_guide_layout_process_options(),
        )

        started = perf_counter()
        response = await self._document_client.process_document(
            request=request,
            timeout=_DOCUMENT_AI_ONLINE_TIMEOUT_SECONDS,
        )
        latency_ms = int((perf_counter() - started) * 1000)

        return DocumentParserProcessResult(
            processor_resource_name=processor_name,
            chunks=_document_to_chunks(response.document),
            latency_ms=latency_ms,
        )

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
            field_mask=field_mask_pb2.FieldMask(paths=["entities", "pages.page_number"]),
        )

        started = perf_counter()

        response = await self._document_client.process_document(
            request=request,
            timeout=_DOCUMENT_AI_ONLINE_TIMEOUT_SECONDS,
        )
        logger.info(
            "Document AI | Classifier | raw response\n"
            f"{json.dumps(_proto_to_dict(response), ensure_ascii=False, indent=2)}"
        )

        # {
        #     "document": {
        #         "pages": [
        #             {
        #                 "pageNumber": 1, # Document AI indique qu’il a traité la page 1.
        #                 "transforms": [],
        #                 "detectedLanguages": [],
        #                 "blocks": [],
        #                 "paragraphs": [],
        #                 "lines": [],
        #                 "tokens": [],
        #                 "visualElements": [],
        #                 "tables": [],
        #                 "formFields": [],
        #                 "symbols": [],
        #                 "detectedBarcodes": [],
        #             }
        #         ],
        #         "entities": [
        #             {
        #                 # Ça signifie que l’entité TECHNICAL_SHEET couvre le texte du caractère 0 jusqu’au caractère 1735 dans document.text.
        #                 "textAnchor": {
        #                     "textSegments": [{"endIndex": "1735", "startIndex": "0"}],
        #                     "content": "",
        #                 },
        #                 "type": "TECHNICAL_SHEET",  # résultat principal du classifier. Ici TECHNICAL_SHEET
        #                 # Le score 0.99963844 ne veut pas dire : “ce document est sûrement un dossier technique”.
        #                 # Il veut dire : “dans les labels que tu m’as donnés, le meilleur label est TECHNICAL_SHEET, avec une forte confiance”.
        #                 "confidence": 0.99999905, # confiance du modèle. Ici 0.99999905, donc très haut.
        #                 "mentionText": "",
        #                 "mentionId": "",
        #                 "id": "",
        #                 "properties": [],
        #                 "redacted": false,
        #                 "method": "METHOD_UNSPECIFIED",
        #             }
        #         ],
        #         "docid": "",
        #         "mimeType": "",
        #         "text": "",
        #         "textStyles": [],
        #         "entityRelations": [],
        #         "textChanges": [],
        #         "revisions": [],
        #         "blobAssets": [],
        #         "entitiesRevisions": [],
        #         "entitiesRevisionId": "",
        #     },
        #     "humanReviewStatus": {
        #         "state": "SKIPPED",
        #         "stateMessage": "",
        #         "humanReviewOperation": "",
        #     },
        # }

        #          {
        #    "document": {
        #      "pages": [
        #        {
        #          "pageNumber": 1,
        #          "transforms": [],
        #          "detectedLanguages": [],
        #          "blocks": [],
        #          "paragraphs": [],
        #          "lines": [],
        #          "tokens": [],
        #          "visualElements": [],
        #          "tables": [],
        #          "formFields": [],
        #          "symbols": [],
        #          "detectedBarcodes": []
        #        },
        #        {
        #          "pageNumber": 2,
        #          "transforms": [],
        #          "detectedLanguages": [],
        #          "blocks": [],
        #          "paragraphs": [],
        #          "lines": [],
        #          "tokens": [],
        #          "visualElements": [],
        #          "tables": [],
        #          "formFields": [],
        #          "symbols": [],
        #          "detectedBarcodes": []
        #        }
        #      ],
        #      "entities": [
        #        {
        #          "textAnchor": {
        #            "textSegments": [
        #              {
        #                "endIndex": "3133",
        #                "startIndex": "0"
        #              }
        #            ],
        #            "content": ""
        #          },
        #          "type": "OUT_OF_SCOPE_DOCUMENT",
        #          "confidence": 0.9999831,
        #          "mentionText": "",
        #          "mentionId": "",
        #          "id": "",
        #          "properties": [],
        #          "redacted": false,
        #          "method": "METHOD_UNSPECIFIED"
        #        }
        #      ],
        #      "docid": "",
        #      "mimeType": "",
        #      "text": "",
        #      "textStyles": [],
        #      "entityRelations": [],
        #      "textChanges": [],
        #      "revisions": [],
        #      "blobAssets": [],
        #      "entitiesRevisions": [],
        #      "entitiesRevisionId": ""
        #    },
        #    "humanReviewStatus": {
        #      "state": "SKIPPED",
        #      "stateMessage": "",
        #      "humanReviewOperation": ""
        #    }
        #  }

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
                "field_mask": ["entities", "pages.page_number"],
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
        extractor_route: TechnicalExtractorRoute,
        mime_type: str = "application/pdf",
    ) -> TechnicalDocumentExtractionResult:
        processor_name = self._processor_name_for(
            processor_id=extractor_route.processor_id,
            processor_version=extractor_route.processor_version,
        )

        request = documentai.ProcessRequest(
            name=processor_name,
            gcs_document=documentai.GcsDocument(gcs_uri=input_uri, mime_type=mime_type),
            skip_human_review=True,
            field_mask=field_mask_pb2.FieldMask(paths=["entities"]),
        )
        started = perf_counter()
        response = await self._document_client.process_document(
            request=request,
            timeout=_DOCUMENT_AI_ONLINE_TIMEOUT_SECONDS,
        )

        latency_ms = int((perf_counter() - started) * 1000)
        document = response.document

        logger.info(
            "Document AI | Extractor | raw response JSON",
            raw_response_json=_proto_to_dict(response),
        )

        #      {
        #   "document": {
        #     "entities": [
        #       {
        #         "textAnchor": {
        #           "textSegments": [
        #             {
        #               "startIndex": "466",
        #               "endIndex": "483"
        #             }
        #           ],
        #           "content": ""
        #         },
        #         "type": "assembly_site",
        #         "mentionText": "Jepara, Indonésie",
        #         "confidence": 0.9999001,
        #         "pageAnchor": {
        #           "pageRefs": [
        #             {
        #               "boundingPoly": {
        #                 "normalizedVertices": [
        #                   {
        #                     "x": 0.28732896,
        #                     "y": 0.3480454
        #                   },
        #                   {
        #                     "x": 0.40273646,
        #                     "y": 0.3480454
        #                   },
        #                   {
        #                     "x": 0.40273646,
        #                     "y": 0.3577133
        #                   },
        #                   {
        #                     "x": 0.28732896,
        #                     "y": 0.3577133
        #                   }
        #                 ],
        #                 "vertices": []
        #               },
        #               "page": "0",
        #               "layoutType": "LAYOUT_TYPE_UNSPECIFIED",
        #               "layoutId": "",
        #               "confidence": 0.0
        #             }
        #           ]
        #         },
        #         "id": "0",
        #         "mentionId": "",
        #         "properties": [],
        #         "redacted": false,
        #         "method": "METHOD_UNSPECIFIED"
        #       },
        #     ],
        #     "docid": "",
        #     "mimeType": "",
        #     "text": "",
        #     "textStyles": [],
        #     "pages": [],
        #     "entityRelations": [],
        #     "textChanges": [],
        #     "revisions": [],
        #     "blobAssets": [],
        #     "entitiesRevisions": [],
        #     "entitiesRevisionId": ""
        #   },
        #   "humanReviewStatus": {
        #     "state": "SKIPPED",
        #     "stateMessage": "",
        #     "humanReviewOperation": ""
        #   }
        # }

        return TechnicalDocumentExtractionResult(
            processor_resource_name=processor_name,
            processor_version=extractor_route.processor_version,
            latency_ms=latency_ms,
            request_config_snapshot={
                "mode": "online",
                "processor_kind": "custom_extractor_foundation_model",
                "extractor_document_type": extractor_route.document_type,
                "extractor_processor_name": extractor_route.extractor_name,
                "processor_resource_name": processor_name,
                "processor_version": extractor_route.processor_version,
                "gcs_uri": input_uri,
                "mime_type": mime_type,
                "document_type": document_type,
                "skip_human_review": True,
                "field_mask": ["entities"],
            },
            entities=[_entity_to_technical_fact(entity) for entity in document.entities],
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


def _style_guide_layout_process_options() -> documentai.ProcessOptions:
    return documentai.ProcessOptions(
        layout_config=documentai.ProcessOptions.LayoutConfig(
            chunking_config=documentai.ProcessOptions.LayoutConfig.ChunkingConfig(
                chunk_size=_STYLE_GUIDE_CHUNK_SIZE_TOKENS,
                include_ancestor_headings=True,
            )
        )
    )


def _document_to_chunks(document: documentai.Document) -> list[StyleGuideChunkCandidate]:
    spatial_index = _document_layout_spatial_index(document)
    chunked_document = getattr(document, "chunked_document", None)
    raw_chunks = list(getattr(chunked_document, "chunks", []) or [])
    chunk_candidates: list[StyleGuideChunkCandidate] = []

    for chunk_index, raw_chunk in enumerate(raw_chunks, start=1):
        contenu = _normalize_text(getattr(raw_chunk, "content", ""))

        if not contenu:
            continue

        provider_id = _normalize_text(getattr(raw_chunk, "chunk_id", "")) or f"chunk-{chunk_index}"
        page_span = getattr(raw_chunk, "page_span", None)
        page_start = _to_int(getattr(page_span, "page_start", None))
        page_end = _to_int(getattr(page_span, "page_end", None)) or page_start
        bounding_boxes = [
            spatial_index[source_block_id]
            for source_block_id in list(getattr(raw_chunk, "source_block_ids", []) or [])
            if source_block_id in spatial_index
        ]

        chunk_candidates.append(
            StyleGuideChunkCandidate(
                provider_id=provider_id,
                index_chunk=chunk_index,
                contenu=contenu,
                page_start=page_start,
                page_end=page_end,
                evidence_json={
                    "source": "chunk",
                    "bounding_boxes": bounding_boxes,
                },
            )
        )

    return chunk_candidates


def _document_layout_spatial_index(document: documentai.Document) -> dict[str, dict[str, Any]]:
    document_layout = getattr(document, "document_layout", None)
    blocks = list(getattr(document_layout, "blocks", []) or [])
    spatial_index: dict[str, dict[str, Any]] = {}

    for block in blocks:
        block_id = _normalize_text(getattr(block, "block_id", ""))
        bounding_box = getattr(block, "bounding_box", None)
        if not block_id or bounding_box is None:
            continue

        bbox_json = _proto_to_dict(bounding_box)
        if bbox_json:
            spatial_index[block_id] = bbox_json

    return spatial_index


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


def _entity_to_technical_fact(
    entity: documentai.Document.Entity,
) -> TechnicalDocumentEntity:
    page, bbox_json = _extract_page_anchor(entity)
    return TechnicalDocumentEntity(
        field_name=_normalize_text(getattr(entity, "type_", None)),
        raw_value=_normalize_text(getattr(entity, "mention_text", None)) or None,
        confidence=_to_float(getattr(entity, "confidence", None)),
        page=page,
        bbox_json=bbox_json,
    )


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


def _proto_to_dict(value: object) -> dict[str, Any]:
    proto = getattr(value, "_pb", value)
    try:
        message = proto if isinstance(proto, Message) else value
        return dict(
            MessageToDict(
                cast(Message, message),
                preserving_proto_field_name=False,
                use_integers_for_enums=False,
                always_print_fields_with_no_presence=True,
            )
        )
    except Exception:
        return {}


def _to_float(value: object) -> float | None:
    if isinstance(value, (float, int)):
        return float(value)
    return None


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
