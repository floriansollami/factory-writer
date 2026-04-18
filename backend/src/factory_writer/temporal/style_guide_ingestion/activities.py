from __future__ import annotations

import uuid

from temporalio import activity

from factory_writer.application.ports.style_guide_ingestion import (
    StyleGuideChunkPersistResult,
    StyleGuideIngestionInput,
    StyleGuideLayoutJobResult,
    StyleGuideLayoutParseResult,
)
from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StylePackDraftResult,
)


class StyleGuideActivities:
    def __init__(self, service: StyleGuideIngestionService) -> None:
        self._service = service

    @activity.defn
    async def mark_source_in_progress(self, source_id: uuid.UUID) -> None:
        await self._service.mark_source_in_progress(source_id)

    @activity.defn
    async def mark_source_failed(
        self,
        source_id: uuid.UUID,
        message: str | None = None,
    ) -> None:
        await self._service.mark_source_failed(source_id, message)

    @activity.defn
    async def start_docai_job(
        self,
        payload: StyleGuideIngestionInput,
    ) -> StyleGuideLayoutJobResult:
        return await self._service.start_layout_parse(payload)

    @activity.defn
    async def check_docai_job(
        self,
        payload: StyleGuideLayoutJobResult,
    ) -> StyleGuideLayoutParseResult | None:
        return await self._service.check_layout_parse(payload)

    @activity.defn
    async def persist_fragments(
        self,
        payload: StyleGuideLayoutParseResult,
    ) -> StyleGuideChunkPersistResult:
        return await self._service.persist_fragments(payload)

    @activity.defn
    async def generate_draft_pack(
        self,
        payload: StyleGuideChunkPersistResult,
    ) -> StylePackDraftResult:
        result = await self._service.generate_draft_pack(payload)

        return StylePackDraftResult(
            draft_pack_id=result.draft_pack_id,
        )

    @activity.defn
    async def promote_pack(self, payload: StylePackDraftResult) -> str:
        return await self._service.promote_pack(payload.draft_pack_id)
