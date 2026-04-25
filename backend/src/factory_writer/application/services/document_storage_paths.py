from __future__ import annotations

import re
import uuid
from pathlib import Path

_SOURCE_STYLE_GUIDE_PREFIX = "sources/style-guides"
_SOURCE_TECHNICAL_DOSSIER_PREFIX = "sources/technical-dossiers"
_INTERNAL_DERIVED_DOCUMENT_AI_PREFIX = "_factory_writer/derived/document-ai"
_MAX_SAFE_FILENAME_LENGTH = 120
_SAFE_FILENAME_PATTERN = re.compile(r"[^A-Za-z0-9._-]+")


def build_style_guide_pdf_object_name(
    *,
    document_source_id: uuid.UUID,
    file_name: str,
) -> str:
    safe_file_name = _safe_pdf_filename(file_name, fallback_stem="style-guide")
    return f"{_SOURCE_STYLE_GUIDE_PREFIX}/{document_source_id}/{safe_file_name}"


def build_technical_dossier_pdf_object_name(
    *,
    product_id: uuid.UUID,
    document_source_id: uuid.UUID,
    file_name: str,
) -> str:
    safe_file_name = _safe_pdf_filename(file_name, fallback_stem="technical-document")
    return f"{_SOURCE_TECHNICAL_DOSSIER_PREFIX}/{product_id}/{document_source_id}/{safe_file_name}"


def build_document_ai_parser_result_uri(
    *,
    input_uri: str,
    extraction_type: str,
    document_source_id: uuid.UUID,
    generation: str,
) -> str:
    bucket_name = _extract_gcs_bucket_name(input_uri)
    return (
        f"gs://{bucket_name}/"
        f"{_INTERNAL_DERIVED_DOCUMENT_AI_PREFIX}/"
        f"{extraction_type}/document_source_id={document_source_id}/gcs_generation={generation}/"
    )


def _safe_pdf_filename(file_name: str, fallback_stem: str) -> str:
    path = Path(file_name.strip())

    if path.suffix.lower() != ".pdf":
        raise ValueError(f"File must be a PDF: {file_name}")

    safe_stem = _SAFE_FILENAME_PATTERN.sub("-", path.stem).strip("-_.")
    safe_stem = (safe_stem or fallback_stem)[: _MAX_SAFE_FILENAME_LENGTH - 4]
    return f"{safe_stem}.pdf"


def _extract_gcs_bucket_name(storage_uri: str) -> str:
    if not storage_uri.startswith("gs://"):
        raise ValueError(f"URI GCS invalide: {storage_uri}")

    path = storage_uri.removeprefix("gs://")
    bucket_name, separator, object_name = path.partition("/")

    if not bucket_name or not separator or not object_name:
        raise ValueError(f"URI GCS invalide: {storage_uri}")

    return bucket_name
