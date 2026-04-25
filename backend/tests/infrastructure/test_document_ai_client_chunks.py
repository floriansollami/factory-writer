import asyncio
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from google.cloud import documentai_v1 as documentai
from google.cloud.documentai_toolbox import document as toolbox_document

from factory_writer.core.config import GCPSettings, Settings
from factory_writer.infrastructure.gcp.document_ai_client import (
    DocumentAIClient,
    _toolbox_document_to_chunks,
)


@dataclass(frozen=True)
class _FakeProcessResponse:
    document: documentai.Document


class _FakeDocumentProcessorClient:
    def __init__(self, response: _FakeProcessResponse) -> None:
        self.response = response
        self.requests: list[documentai.ProcessRequest] = []

    async def process_document(
        self,
        request: documentai.ProcessRequest,
    ) -> _FakeProcessResponse:
        self.requests.append(request)
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
    assert request.process_options.layout_config.chunking_config.chunk_size == 1000
    assert request.process_options.layout_config.chunking_config.include_ancestor_headings is True
    assert result.processor_resource_name == request.name
    assert result.latency_ms >= 0
    assert len(result.chunks) == 1
    assert result.chunks[0].provider_id == "c1"
    assert result.chunks[0].contenu == "VG-01 | hard Vouvoiement constant"
    assert result.chunks[0].page_start == 1
    assert result.chunks[0].page_end == 1


def test_chunks_from_wrapped_document_extract_chunk_id_text_and_page_span() -> None:
    wrapped_document = toolbox_document.Document.from_document_path(
        str(
            Path(__file__)
            .resolve()
            .parents[3]
            .joinpath(
                "docs/brand_style_extraction/document_ai_raw_dump/AXOLOTL_STYLE_GUIDE_V4-0.json"
            )
        )
    )

    chunks = _toolbox_document_to_chunks(wrapped_document)

    assert len(chunks) == 1
    assert chunks[0].provider_id == "c1"
    assert chunks[0].index_chunk == 1
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
    assert chunks[0].evidence_json == {"source": "chunk"}
    assert "VG-01 | hard Vouvoiement constant" in chunks[0].contenu


def test_chunks_from_wrapped_document_return_empty_list_when_provider_has_no_chunks() -> None:
    class _FakeParagraph:
        def __init__(self, text: str) -> None:
            self.text = text

    class _FakePage:
        def __init__(self, paragraphs: list[object]) -> None:
            self.paragraphs = paragraphs

    class _FakeWrappedDocument:
        def __init__(self) -> None:
            self.chunks: list[object] = []
            self.pages = [
                _FakePage([_FakeParagraph("Guide de style complet")]),
                _FakePage([_FakeParagraph("sans chunk")]),
            ]
            self.text = "Texte complet"

    chunks = _toolbox_document_to_chunks(cast(Any, _FakeWrappedDocument()))

    assert chunks == []


def test_chunks_generate_fallback_provider_id_if_chunk_id_is_missing() -> None:
    class _FakePageSpan:
        def __init__(self, page_start: int, page_end: int) -> None:
            self.page_start = page_start
            self.page_end = page_end

    class _FakeChunk:
        def __init__(self) -> None:
            self.chunk_id = ""
            self.content = "Guide de style complet"
            self.page_span = _FakePageSpan(1, 1)

    class _FakeWrappedDocument:
        def __init__(self) -> None:
            self.chunks = [_FakeChunk()]

    chunks = _toolbox_document_to_chunks(cast(Any, _FakeWrappedDocument()))

    assert len(chunks) == 1
    assert chunks[0].provider_id == "chunk-1"
    assert chunks[0].index_chunk == 1
    assert chunks[0].contenu == "Guide de style complet"
    assert chunks[0].page_start == 1
    assert chunks[0].page_end == 1
