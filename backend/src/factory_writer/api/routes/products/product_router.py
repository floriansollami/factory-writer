from __future__ import annotations

import uuid
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.exc import IntegrityError

from factory_writer.api.routes.products.dependencies import (
    get_product_read_service,
    get_product_upload_service,
    get_product_workflow_service,
)
from factory_writer.api.routes.products.schemas import (
    ProductCreateRequest,
    TechnicalReviewCaseResolveRequest,
)
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)

router = APIRouter()


@router.post("", status_code=status.HTTP_201_CREATED)
async def create_product(
    payload: ProductCreateRequest,
    service: ProductTechnicalIngestionService = Depends(get_product_workflow_service),
) -> dict[str, Any]:
    try:
        return await service.create_product(
            sku=payload.sku,
            name=payload.name,
            famille_code=payload.famille_code,
            sous_famille_code=payload.sous_famille_code,
            season_code=payload.season_code,
            segment_prix_code=payload.segment_prix_code,
            langue_principale=payload.langue_principale,
        )
    except IntegrityError as exc:
        if _is_product_sku_unique_violation(exc):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Un produit existe déjà avec le SKU {payload.sku}.",
            ) from exc

        raise
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.get("")
async def list_products(
    service: ProductTechnicalIngestionService = Depends(get_product_read_service),
) -> dict[str, Any]:
    return await service.list_products()


@router.get("/taxonomies")
async def list_product_taxonomies(
    service: ProductTechnicalIngestionService = Depends(get_product_read_service),
) -> dict[str, Any]:
    return await service.list_product_taxonomies()


@router.get("/{product_id}/overview")
async def get_product_overview(
    product_id: uuid.UUID,
    service: ProductTechnicalIngestionService = Depends(get_product_read_service),
) -> dict[str, Any]:
    try:
        return await service.get_product_overview(product_id=product_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/{product_id}/technical-sources", status_code=status.HTTP_201_CREATED)
async def upload_technical_sources(
    product_id: uuid.UUID,
    files: list[UploadFile] = File(...),
    service: ProductTechnicalIngestionService = Depends(get_product_upload_service),
) -> dict[str, Any]:
    try:
        payload_files: list[tuple[str, bytes, str]] = []
        for file in files:
            content = await file.read()
            payload_files.append(
                (
                    file.filename or "technical-document.pdf",
                    content,
                    file.content_type or "application/pdf",
                )
            )
        return await service.upload_technical_sources(product_id=product_id, files=payload_files)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


def _is_product_sku_unique_violation(exc: IntegrityError) -> bool:
    constraint_name = getattr(getattr(exc.orig, "diag", None), "constraint_name", None)

    return constraint_name == "ix_product_sku"


@router.post("/{product_id}/technical-sources/start-ingestion")
async def start_technical_sources_ingestion(
    product_id: uuid.UUID,
    service: ProductTechnicalIngestionService = Depends(get_product_workflow_service),
) -> dict[str, Any]:
    try:
        return await service.start_technical_ingestion(product_id=product_id)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc


@router.patch("/{product_id}/technical-review-cases/{case_id}")
async def resolve_technical_review_case(
    product_id: uuid.UUID,
    case_id: uuid.UUID,
    payload: TechnicalReviewCaseResolveRequest,
    service: ProductTechnicalIngestionService = Depends(get_product_workflow_service),
) -> dict[str, Any]:
    try:
        return await service.resolve_review_case(
            product_id=product_id,
            case_id=case_id,
            action=payload.action,
            resolved_by=payload.resolved_by,
            corrected_value=payload.corrected_value,
            corrected_unit=payload.corrected_unit,
            comment=payload.comment,
        )
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
