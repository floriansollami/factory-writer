from __future__ import annotations

import structlog
from temporalio import activity

from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.temporal.product_sheet_generation.contracts import (
    GenerateProductSheetCandidateInput,
    GenerateProductSheetCandidateResult,
    MarkProductSheetGenerationFailedInput,
    MarkProductSheetGenerationFailedResult,
    PersistProductSheetGenerationInput,
    PersistProductSheetGenerationResult,
)

logger = structlog.get_logger(__name__)


class ProductSheetGenerationActivities:
    def __init__(self, service: ProductTechnicalIngestionService) -> None:
        self._service = service

    @activity.defn
    async def generate_product_sheet_candidate(
        self,
        payload: GenerateProductSheetCandidateInput,
    ) -> GenerateProductSheetCandidateResult:
        logger.info(
            "Product sheet | generation activity started",
            generation_id=payload.generation_id,
        )
        result = await self._service.generate_product_sheet_candidate(
            generation_id=payload.generation_id
        )
        return GenerateProductSheetCandidateResult(
            status=str(result["status"]),
            sheet_json=result["sheet_json"],
            self_check_json=result["self_check_json"],
            metadata=result["metadata"],
        )

    @activity.defn
    async def persist_product_sheet_generation_result(
        self,
        payload: PersistProductSheetGenerationInput,
    ) -> PersistProductSheetGenerationResult:
        generation = await self._service.persist_product_sheet_generation_result(
            generation_id=payload.generation_id,
            generation_result=payload.generation_result,
        )
        return PersistProductSheetGenerationResult(generation=generation)

    @activity.defn
    async def mark_product_sheet_generation_failed(
        self,
        payload: MarkProductSheetGenerationFailedInput,
    ) -> MarkProductSheetGenerationFailedResult:
        generation = await self._service.mark_product_sheet_generation_failed(
            generation_id=payload.generation_id,
            error_message=payload.error_message,
        )
        return MarkProductSheetGenerationFailedResult(generation=generation)
