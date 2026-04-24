from pathlib import Path
from typing import Any, cast

from google.cloud.documentai_toolbox import document as toolbox_document

from factory_writer.infrastructure.gcp.document_ai_client import _toolbox_document_to_chunks


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
