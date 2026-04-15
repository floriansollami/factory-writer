from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.domain.temporal_models import (
    StyleGuideChunkPersistResult,
    StyleGuideIngestionInput,
    StyleGuideLayoutParseResult,
    StylePackDraftResult,
)

logger = structlog.get_logger(__name__)


@activity.defn(name="mark_style_source_in_progress_activity")
async def mark_style_source_in_progress_activity(source_id: str) -> None:
    """TODO: passer le document source à EN_COURS."""
    logger.info("mark_style_source_in_progress_activity.started", source_id=source_id)
    await asyncio.sleep(0)


@activity.defn(name="mark_style_source_failed_activity")
async def mark_style_source_failed_activity(source_id: str) -> None:
    """TODO: passer le document source à ERREUR."""
    logger.info("mark_style_source_failed_activity.started", source_id=source_id)
    await asyncio.sleep(0)


@activity.defn(name="trigger_style_layout_parse_activity")
async def trigger_style_layout_parse_activity(
    payload: StyleGuideIngestionInput,
) -> StyleGuideLayoutParseResult:
    """TODO: déclencher Document AI Layout Parser sur le PDF de style."""
    logger.info("trigger_style_layout_parse_activity.started", file_uri=payload.file_uri)
    await asyncio.sleep(0)
    return StyleGuideLayoutParseResult(
        layout_operation_id=f"layout-op-{payload.source_id}",
        output_uri=f"{payload.file_uri}.layout.json",
    )


@activity.defn(name="persist_style_fragments_activity")
async def persist_style_fragments_activity(
    payload: StyleGuideLayoutParseResult,
) -> StyleGuideChunkPersistResult:
    """TODO: persister les fragments / chunks du style guide en base."""
    logger.info(
        "persist_style_fragments_activity.started",
        layout_operation_id=payload.layout_operation_id,
    )
    activity.heartbeat("fragments_persisted")
    await asyncio.sleep(0)
    return StyleGuideChunkPersistResult(
        fragment_ids=[
            f"{payload.layout_operation_id}-fragment-1",
            f"{payload.layout_operation_id}-fragment-2",
        ]
    )


@activity.defn(name="generate_style_pack_draft_activity")
async def generate_style_pack_draft_activity(
    payload: StyleGuideChunkPersistResult,
) -> StylePackDraftResult:
    """TODO: appeler LiteLLM pour structurer les règles du style guide."""
    logger.info(
        "generate_style_pack_draft_activity.started",
        fragment_count=len(payload.fragment_ids),
    )
    await asyncio.sleep(0)
    return StylePackDraftResult(
        draft_pack_id="style-pack-draft-placeholder",
        draft_version_label="style-pack-draft-v1-placeholder",
    )


@activity.defn(name="promote_style_pack_activity")
async def promote_style_pack_activity(payload: StylePackDraftResult) -> str:
    """TODO: promouvoir le style pack draft en version active."""
    logger.info("promote_style_pack_activity.started", draft_pack_id=payload.draft_pack_id)
    await asyncio.sleep(0)
    return payload.draft_pack_id
