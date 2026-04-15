from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.domain.temporal_models import (
    TechnicalFactsExtractionInput,
    TechnicalFactsExtractionResult,
)

logger = structlog.get_logger(__name__)


@activity.defn(name="extract_archive_and_facts_activity")
async def extract_archive_and_facts_activity(
    payload: TechnicalFactsExtractionInput,
) -> TechnicalFactsExtractionResult:
    """
    TODO:
    - télécharger le zip scellé
    - appeler Document AI / extracteurs adaptés
    - normaliser les facts
    - persister l'evidence bundle
    - valider le snapshot technique
    """
    logger.info(
        "extract_archive_and_facts_activity.started",
        sku=payload.product.sku,
        archive_uri=payload.archive_signal.archive_uri,
    )
    activity.heartbeat("archive_received")
    await asyncio.sleep(0)
    return TechnicalFactsExtractionResult(
        facts_snapshot_id=f"facts-{payload.product.sku.lower()}-placeholder",
        evidence_bundle_id=f"evidence-{payload.product.sku.lower()}-placeholder",
        validation_status="placeholder_validated",
    )
