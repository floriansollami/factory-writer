from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.application.services.style_guide_ingestion_service import (
    StyleGuideIngestionService,
)
from factory_writer.temporal.style_guide_ingestion.contracts import (
    StyleGuideChunkPersistResult,
    StyleGuideIngestionInput,
    StyleGuideLayoutParseResult,
    StylePackDraftResult,
)

logger = structlog.get_logger(__name__)


class StyleGuideActivities:
    def __init__(self, service: StyleGuideIngestionService) -> None:
        self._service = service

    @activity.defn
    async def mark_source_in_progress(self, source_id: str) -> None:
        await self._service.mark_source_in_progress(source_id)

    @activity.defn
    async def mark_source_failed(self, source_id: str) -> None:
        await self._service.mark_source_failed(source_id)

    @activity.defn
    async def parse_layout(
        self,
        payload: StyleGuideIngestionInput,
    ) -> StyleGuideLayoutParseResult:

        result = await self._service.parse_style_guide_with_docai(
            payload,
            heartbeat=lambda details: activity.heartbeat(details),
        )

        return result

    @activity.defn
    async def persist_fragments(
        self,
        payload: StyleGuideLayoutParseResult,
    ) -> StyleGuideChunkPersistResult:

        activity.heartbeat("fragments_persisted")
        await asyncio.sleep(0)
        return StyleGuideChunkPersistResult(
            fragment_ids=[
                f"{payload.layout_operation_id}-fragment-1",
                f"{payload.layout_operation_id}-fragment-2",
            ]
        )

    @activity.defn
    async def generate_draft_pack(
        self,
        payload: StyleGuideChunkPersistResult,
    ) -> StylePackDraftResult:
        await asyncio.sleep(0)
        return StylePackDraftResult(
            draft_pack_id="style-pack-draft-placeholder",
            draft_version_label="style-pack-draft-v1-placeholder",
        )

    @activity.defn
    async def promote_pack(self, payload: StylePackDraftResult) -> str:
        await asyncio.sleep(0)
        return payload.draft_pack_id
