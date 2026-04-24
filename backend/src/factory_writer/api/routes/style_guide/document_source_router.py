import uuid

import structlog
from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from factory_writer.api.routes.style_guide.dependencies import (
    MAX_STYLE_GUIDE_PDF_BYTES,
    STYLE_GUIDE_TAG,
    get_style_guide_upload_service,
)
from factory_writer.api.routes.style_guide.mappers import to_upload_response
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)

router = APIRouter()
logger = structlog.get_logger(__name__)


@router.post("/upload", status_code=201, tags=[STYLE_GUIDE_TAG])
async def upload_style_guide_pdf(
    file: UploadFile = File(...),
    service: StyleGuideIngestionService = Depends(get_style_guide_upload_service),
) -> dict[str, str]:
    logger.info(
        "style_guide_upload_started",
        file_name=file.filename,
        declared_content_type=file.content_type,
        max_size_mb=_bytes_to_mb(MAX_STYLE_GUIDE_PDF_BYTES),
    )
    file_name, content, content_type = await _read_style_guide_pdf_upload(file)
    logger.info(
        "style_guide_upload_file_read",
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(content),
        size_mb=_bytes_to_mb(len(content)),
    )
    logger.info(
        "style_guide_upload_persisting",
        file_name=file_name,
        storage_backend="gcs",
    )

    result = await service.upload_document_source_pdf(
        file_name=file_name,
        content=content,
        content_type=content_type,
    )
    logger.info(
        "style_guide_upload_completed",
        document_source_id=str(result.document_source_id),
        storage_uri=result.storage_uri,
        storage_generation=result.storage_generation,
        storage_metageneration=result.storage_metageneration,
        status=result.status.value,
    )

    return to_upload_response(result, file_name)


@router.post(
    "/document-sources/{document_source_id}/reupload",
    status_code=201,
    tags=[STYLE_GUIDE_TAG],
)
async def reupload_style_guide_pdf(
    document_source_id: uuid.UUID,
    file: UploadFile = File(...),
    service: StyleGuideIngestionService = Depends(get_style_guide_upload_service),
) -> dict[str, str]:
    logger.info(
        "style_guide_reupload_started",
        replaced_document_source_id=str(document_source_id),
        file_name=file.filename,
        declared_content_type=file.content_type,
        max_size_mb=_bytes_to_mb(MAX_STYLE_GUIDE_PDF_BYTES),
    )
    file_name, content, content_type = await _read_style_guide_pdf_upload(file)
    logger.info(
        "style_guide_reupload_file_read",
        replaced_document_source_id=str(document_source_id),
        file_name=file_name,
        content_type=content_type,
        size_bytes=len(content),
        size_mb=_bytes_to_mb(len(content)),
    )
    logger.info(
        "style_guide_reupload_persisting",
        replaced_document_source_id=str(document_source_id),
        file_name=file_name,
        storage_backend="gcs",
    )

    try:
        result = await service.reupload_document_source_pdf(
            replaced_document_source_id=document_source_id,
            file_name=file_name,
            content=content,
            content_type=content_type,
        )
    except KeyError as exc:
        logger.warning(
            "style_guide_reupload_failed_missing_source",
            replaced_document_source_id=str(document_source_id),
            file_name=file_name,
        )
        raise HTTPException(status_code=404, detail="Source guide de style introuvable.") from exc
    except RuntimeError as exc:
        logger.warning(
            "style_guide_reupload_failed_conflict",
            replaced_document_source_id=str(document_source_id),
            file_name=file_name,
            reason=str(exc),
        )
        raise HTTPException(status_code=409, detail=str(exc)) from exc

    logger.info(
        "style_guide_reupload_completed",
        replaced_document_source_id=str(document_source_id),
        new_document_source_id=str(result.document_source_id),
        storage_uri=result.storage_uri,
        storage_generation=result.storage_generation,
        storage_metageneration=result.storage_metageneration,
        status=result.status.value,
    )

    return to_upload_response(result, file_name)


async def _read_style_guide_pdf_upload(file: UploadFile) -> tuple[str, bytes, str]:
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        logger.warning(
            "style_guide_upload_rejected_invalid_extension",
            file_name=file.filename,
            declared_content_type=file.content_type,
        )
        raise HTTPException(status_code=400, detail="Le guide de style doit être un PDF.")

    if file.content_type not in (None, "", "application/pdf", "application/octet-stream"):
        logger.warning(
            "style_guide_upload_rejected_invalid_content_type",
            file_name=file.filename,
            declared_content_type=file.content_type,
        )
        raise HTTPException(status_code=400, detail="Le fichier doit être un PDF.")

    file_name = file.filename
    content_type = file.content_type or "application/pdf"

    chunks: list[bytes] = []
    total_size = 0

    while chunk := await file.read(1024 * 1024):
        total_size += len(chunk)
        if total_size > MAX_STYLE_GUIDE_PDF_BYTES:
            logger.warning(
                "style_guide_upload_rejected_too_large",
                file_name=file_name,
                size_bytes=total_size,
                size_mb=_bytes_to_mb(total_size),
                max_size_mb=_bytes_to_mb(MAX_STYLE_GUIDE_PDF_BYTES),
            )
            raise HTTPException(
                status_code=413,
                detail="Le PDF dépasse la limite POC de 25 Mo.",
            )
        chunks.append(chunk)

    content = b"".join(chunks)
    if not content:
        logger.warning(
            "style_guide_upload_rejected_empty_file",
            file_name=file_name,
            declared_content_type=content_type,
        )
        raise HTTPException(status_code=400, detail="Le fichier PDF est vide.")

    return file_name, content, content_type


def _bytes_to_mb(size_bytes: int) -> str:
    return f"{size_bytes / (1024 * 1024):.2f}"
