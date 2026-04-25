from __future__ import annotations

import uuid

import pytest

from factory_writer.application.services.document_storage_paths import (
    build_document_ai_parser_result_uri,
    build_style_guide_pdf_object_name,
    build_technical_dossier_pdf_object_name,
)


def test_build_style_guide_pdf_object_name_is_stable_and_safe() -> None:
    document_source_id = uuid.UUID("00000000-0000-0000-0000-000000000001")

    object_name = build_style_guide_pdf_object_name(
        document_source_id=document_source_id,
        file_name="Axo Lotl Style Guide V4.pdf",
    )

    assert (
        object_name == "sources/style-guides/00000000-0000-0000-0000-000000000001/"
        "Axo-Lotl-Style-Guide-V4.pdf"
    )


def test_build_technical_dossier_pdf_object_name_is_stable_and_safe() -> None:
    product_id = uuid.UUID("00000000-0000-0000-0000-000000000010")
    document_source_id = uuid.UUID("00000000-0000-0000-0000-000000000011")

    object_name = build_technical_dossier_pdf_object_name(
        product_id=product_id,
        document_source_id=document_source_id,
        file_name="Fiche technique #1.pdf",
    )

    assert (
        object_name == "sources/technical-dossiers/00000000-0000-0000-0000-000000000010/"
        "00000000-0000-0000-0000-000000000011/Fiche-technique-1.pdf"
    )


def test_pdf_object_name_rejects_non_pdf_file() -> None:
    with pytest.raises(ValueError, match="File must be a PDF"):
        build_style_guide_pdf_object_name(
            document_source_id=uuid.uuid4(),
            file_name="guide.txt",
        )


def test_build_document_ai_parser_result_uri_uses_source_bucket() -> None:
    document_source_id = uuid.UUID("00000000-0000-0000-0000-000000000021")

    result_uri = build_document_ai_parser_result_uri(
        input_uri=(
            "gs://factory-writer-style-guide-test/"
            "sources/style-guides/00000000-0000-0000-0000-000000000021/guide.pdf"
        ),
        extraction_type="style-guide-layout",
        document_source_id=document_source_id,
        generation="1776870775609567",
    )

    assert (
        result_uri == "gs://factory-writer-style-guide-test/"
        "_factory_writer/derived/document-ai/style-guide-layout/"
        "document_source_id=00000000-0000-0000-0000-000000000021/"
        "gcs_generation=1776870775609567/"
    )
