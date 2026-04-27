import asyncio
from dataclasses import dataclass
from pathlib import Path

import pytest
from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_v1.types import geometry

from factory_writer.application.ports.product_technical_ingestion import TechnicalExtractorRoute
from factory_writer.core.config import GCPSettings, Settings
from factory_writer.infrastructure.gcp.document_ai_client import (
    DocumentAIClient,
    _document_to_chunks,
)


@dataclass(frozen=True)
class _FakeProcessResponse:
    document: documentai.Document


class _FakeDocumentProcessorClient:
    def __init__(self, response: _FakeProcessResponse) -> None:
        self.response = response
        self.requests: list[documentai.ProcessRequest] = []
        self.timeouts: list[float | None] = []

    async def process_document(
        self,
        request: documentai.ProcessRequest,
        timeout: float | None = None,
    ) -> _FakeProcessResponse:
        self.requests.append(request)
        self.timeouts.append(timeout)
        return self.response

    def processor_version_path(
        self,
        project_id: str,
        location: str,
        processor_id: str,
        processor_version: str,
    ) -> str:
        return (
            f"projects/{project_id}/locations/{location}/processors/{processor_id}"
            f"/processorVersions/{processor_version}"
        )

    def processor_path(
        self,
        project_id: str,
        location: str,
        processor_id: str,
    ) -> str:
        return f"projects/{project_id}/locations/{location}/processors/{processor_id}"


def test_online_layout_parse_uses_process_document_and_returns_chunks() -> None:
    chunk = documentai.Document.ChunkedDocument.Chunk(
        chunk_id="c1",
        content="VG-01 | hard Vouvoiement constant",
    )
    chunk.page_span.page_start = 1
    chunk.page_span.page_end = 1
    document = documentai.Document(
        chunked_document=documentai.Document.ChunkedDocument(chunks=[chunk])
    )
    fake_client = _FakeDocumentProcessorClient(_FakeProcessResponse(document=document))
    client = DocumentAIClient(
        Settings(
            gcp=GCPSettings(
                project_id="factory-writer-test",
                document_ai_location="eu",
                document_ai_processor_id="layout-parser",
                document_ai_processor_version="pretrained-layout-parser-v1.6-2026-01-13",
            )
        )
    )
    client._document_client = fake_client  # type: ignore[assignment]

    result = asyncio.run(client.parse_document_layout("gs://bucket/guide.pdf"))

    assert len(fake_client.requests) == 1
    request = fake_client.requests[0]
    assert request.name == (
        "projects/factory-writer-test/locations/eu/processors/layout-parser"
        "/processorVersions/pretrained-layout-parser-v1.6-2026-01-13"
    )
    assert request.gcs_document.gcs_uri == "gs://bucket/guide.pdf"
    assert request.gcs_document.mime_type == "application/pdf"
    assert request.skip_human_review is True
    assert fake_client.timeouts == [120.0]
    assert request.process_options.layout_config.chunking_config.chunk_size == 1000
    assert request.process_options.layout_config.chunking_config.include_ancestor_headings is True
    assert result.processor_resource_name == request.name
    assert result.latency_ms >= 0
    assert len(result.chunks) == 1
    assert result.chunks[0].provider_id == "c1"
    assert result.chunks[0].contenu == "VG-01 | hard Vouvoiement constant"
    assert result.chunks[0].page_start == 1
    assert result.chunks[0].page_end == 1
    assert result.chunks[0].evidence_json == {"source": "chunk", "bounding_boxes": []}


def test_chunks_from_provider_document_extract_chunk_id_text_page_span_and_grounding() -> None:
    document = documentai.Document.from_json(
        Path(__file__)
        .resolve()
        .parents[3]
        .joinpath("docs/brand_style_extraction/document_ai_raw_dump/AXOLOTL_STYLE_GUIDE_V4-0.json")
        .read_text()
    )

    chunks = _document_to_chunks(document)

    assert len(chunks) == 1
    assert chunks[0].provider_id == "c1"
    assert chunks[0].index_chunk == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].evidence_json["source"] == "chunk"
    assert chunks[0].evidence_json["bounding_boxes"] != []
    assert "VG-01 | hard Vouvoiement constant" in chunks[0].contenu


def test_chunks_preserve_zero_coordinate_bounding_boxes() -> None:
    chunk = documentai.Document.ChunkedDocument.Chunk(
        chunk_id="c1",
        content="Guide de style complet",
        source_block_ids=["b1"],
    )
    chunk.page_span.page_start = 1
    chunk.page_span.page_end = 1

    block = documentai.Document.DocumentLayout.DocumentLayoutBlock(
        block_id="b1",
        bounding_box=geometry.BoundingPoly(
            normalized_vertices=[
                geometry.NormalizedVertex(x=0.0, y=0.0),
                geometry.NormalizedVertex(x=1.0, y=1.0),
            ]
        ),
    )
    document = documentai.Document(
        chunked_document=documentai.Document.ChunkedDocument(chunks=[chunk]),
        document_layout=documentai.Document.DocumentLayout(blocks=[block]),
    )

    chunks = _document_to_chunks(document)

    assert chunks[0].evidence_json["bounding_boxes"] == [
        {
            "normalizedVertices": [
                {"x": 0.0, "y": 0.0},
                {"x": 1.0, "y": 1.0},
            ],
            "vertices": [],
        }
    ]


def test_chunks_return_empty_list_when_provider_has_no_chunks() -> None:
    document = documentai.Document(text="Texte complet")

    chunks = _document_to_chunks(document)

    assert chunks == []


def test_chunks_generate_fallback_provider_id_if_chunk_id_is_missing() -> None:
    chunk = documentai.Document.ChunkedDocument.Chunk(
        chunk_id="",
        content="Guide de style complet",
    )
    chunk.page_span.page_start = 1
    chunk.page_span.page_end = 1
    document = documentai.Document(
        chunked_document=documentai.Document.ChunkedDocument(chunks=[chunk])
    )

    chunks = _document_to_chunks(document)

    assert len(chunks) == 1
    assert chunks[0].provider_id == "chunk-1"
    assert chunks[0].index_chunk == 1
    assert chunks[0].contenu == "Guide de style complet"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1


def test_classifier_uses_online_timeout() -> None:
    entity = documentai.Document.Entity(type_="document_type", mention_text="notice_montage")
    document = documentai.Document(entities=[entity])
    fake_client = _FakeDocumentProcessorClient(_FakeProcessResponse(document=document))
    client = DocumentAIClient(
        Settings(
            gcp=GCPSettings(
                project_id="factory-writer-test",
                document_ai_location="eu",
                document_ai_classifier_processor_id="classifier",
                document_ai_classifier_processor_version="classifier-v1",
            )
        )
    )
    client._document_client = fake_client  # type: ignore[assignment]

    result = asyncio.run(client.classify_technical_document(input_uri="gs://bucket/notice.pdf"))

    assert result.document_type == "ASSEMBLY_NOTICE"
    assert fake_client.timeouts == [120.0]
    request = fake_client.requests[0]
    assert list(request.field_mask.paths) == ["entities", "pages.page_number"]


def test_extractor_maps_flat_entities() -> None:
    document = documentai.Document(
        entities=[
            documentai.Document.Entity(
                type_="dimension_width",
                mention_text="220 cm",
            )
        ]
    )
    fake_client = _FakeDocumentProcessorClient(_FakeProcessResponse(document=document))
    client = DocumentAIClient(
        Settings(
            gcp=GCPSettings(
                project_id="factory-writer-test",
                document_ai_location="eu",
                document_ai_technical_sheet_extractor_processor_id="51d79fcf170d4db5",
            )
        )
    )
    client._document_client = fake_client  # type: ignore[assignment]

    result = asyncio.run(
        client.extract_technical_facts(
            input_uri="gs://bucket/fiche.pdf",
            document_type="TECHNICAL_SHEET",
            extractor_route=TechnicalExtractorRoute(
                document_type="TECHNICAL_SHEET",
                processor_id="51d79fcf170d4db5",
                processor_version=None,
                extractor_name="fw-technical-sheet-extractor",
            ),
        )
    )

    assert result.entities[0].field_name == "dimension_width"
    assert result.entities[0].raw_value == "220 cm"
    assert fake_client.requests[0].name == (
        "projects/factory-writer-test/locations/eu/processors/51d79fcf170d4db5"
    )
    assert fake_client.timeouts == [120.0]


@pytest.mark.parametrize(
    ("document_type", "processor_id"),
    [
        ("TECHNICAL_SHEET", "51d79fcf170d4db5"),
        ("MATERIAL_SPECIFICATION", "6a06ee761cf984a5"),
        ("ASSEMBLY_NOTICE", "e4c1655a493f899e"),
    ],
)
def test_extractor_uses_explicit_route(
    document_type: str,
    processor_id: str,
) -> None:
    document = documentai.Document()
    fake_client = _FakeDocumentProcessorClient(_FakeProcessResponse(document=document))
    client = DocumentAIClient(
        Settings(
            gcp=GCPSettings(
                project_id="factory-writer-test",
                document_ai_location="eu",
                document_ai_technical_sheet_extractor_processor_id="51d79fcf170d4db5",
                document_ai_material_specification_extractor_processor_id="6a06ee761cf984a5",
                document_ai_assembly_notice_extractor_processor_id="e4c1655a493f899e",
            )
        )
    )
    client._document_client = fake_client  # type: ignore[assignment]

    result = asyncio.run(
        client.extract_technical_facts(
            input_uri=f"gs://bucket/{document_type}.pdf",
            document_type=document_type,
            extractor_route=TechnicalExtractorRoute(
                document_type=document_type,
                processor_id=processor_id,
                processor_version=None,
                extractor_name=f"{document_type.lower()}-extractor",
            ),
        )
    )

    assert fake_client.requests[0].name == (
        f"projects/factory-writer-test/locations/eu/processors/{processor_id}"
    )
    assert result.request_config_snapshot["extractor_document_type"] == document_type
    assert result.request_config_snapshot["processor_kind"] == "custom_extractor_foundation_model"
