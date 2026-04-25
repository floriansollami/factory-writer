from __future__ import annotations

import uuid

import structlog
from temporalio import activity

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideIngestionInput,
    StyleGuideLayoutParseResult,
)
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StyleGuideDraftStylePackResult,
)

logger = structlog.get_logger(__name__)


class StyleGuideActivities:
    def __init__(
        self,
        service: StyleGuideIngestionService,
        product_notification_service: ProductTechnicalIngestionService | None = None,
    ) -> None:
        self._service = service
        self._product_notification_service = product_notification_service

    @activity.defn
    async def mark_ingestion_failed(
        self,
        ingestion_run_id: uuid.UUID,
        message: str | None = None,
    ) -> None:
        logger.info(
            "Style guide | échec | marquage du run",
            ingestion_run_id=str(ingestion_run_id),
        )
        await self._service.mark_ingestion_failed(
            ingestion_run_id=ingestion_run_id,
            message=message,
        )
        logger.info(
            "Style guide | échec | run mis à jour",
            ingestion_run_id=str(ingestion_run_id),
        )

    @activity.defn
    async def parse_docai_document(
        self,
        payload: StyleGuideIngestionInput,
    ) -> StyleGuideLayoutParseResult:
        logger.info(
            "Style guide | Document AI | analyse démarrée",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
        )
        result = await self._service.parse_document_layout(payload)
        logger.info(
            "Style guide | Document AI | analyse terminée",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
            chunk_count=len(result.chunks),
        )
        return result

    @activity.defn
    async def generate_draft_pack(
        self,
        payload: StyleGuideLayoutParseResult,
    ) -> StyleGuideDraftStylePackResult:
        logger.info(
            "Style guide | Draft pack | génération démarrée",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
        )
        result = await self._service.generate_draft_pack(payload)
        logger.info(
            "Style guide | Draft pack | génération terminée",
            ingestion_run_id=str(payload.ingestion_run_id),
            document_source_id=str(payload.document_source_id),
            draft_style_pack_id=result.draft_pack_id,
        )

        return StyleGuideDraftStylePackResult(
            draft_style_pack_id=result.draft_pack_id,
        )

    @activity.defn
    async def finalize_style_pack_approval(
        self,
        style_pack_id: str,
    ) -> str:
        logger.info(
            "Style guide | Validation | approbation démarrée",
            style_pack_id=style_pack_id,
        )
        result = await self._service.finalize_style_pack_approval(
            style_pack_id=uuid.UUID(style_pack_id),
        )
        logger.info(
            "Style guide | Validation | approbation terminée",
            style_pack_id=result,
        )
        return result

    @activity.defn
    async def notify_style_pack_activated(
        self,
        style_pack_id: str,
    ) -> int:
        if self._product_notification_service is None:
            return 0
        return await self._product_notification_service.notify_style_pack_activated(
            style_pack_id=uuid.UUID(style_pack_id)
        )

    @activity.defn
    async def finalize_style_pack_rejection(
        self,
        style_pack_id: str,
    ) -> str:
        logger.info(
            "Style guide | Validation | rejet démarré",
            style_pack_id=style_pack_id,
        )
        result = await self._service.finalize_style_pack_rejection(
            style_pack_id=uuid.UUID(style_pack_id),
        )
        logger.info(
            "Style guide | Validation | rejet terminé",
            style_pack_id=result,
        )
        return result
