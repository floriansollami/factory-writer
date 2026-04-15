from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.domain.temporal_models import (
    PromptPackageLoadInput,
    PromptPackageResult,
    PublicationDecision,
    PublishContentInput,
    PublishContentResult,
    PublishGateDecision,
    PublishGateInput,
    SignalSnapshotLoadInput,
    SignalSnapshotResult,
    StylePackLoadInput,
    StylePackResult,
)

logger = structlog.get_logger(__name__)


@activity.defn(name="load_signal_snapshot_activity")
async def load_signal_snapshot_activity(
    payload: SignalSnapshotLoadInput,
) -> SignalSnapshotResult:
    """TODO: lire le meilleur signal snapshot matérialisé dans BigQuery."""
    logger.info("load_signal_snapshot_activity.started", sku=payload.product.sku)
    await asyncio.sleep(0)
    return SignalSnapshotResult(
        signal_snapshot_id=f"signal-{payload.product.sku.lower()}-latest",
        cohort_key_used=(
            f"{payload.product.famille_code}.{payload.product.sous_famille_code}."
            f"{payload.product.segment_prix_code or 'default'}"
        ),
        snapshot_status="placeholder_final_ready",
    )


@activity.defn(name="load_style_pack_active_activity")
async def load_style_pack_active_activity(payload: StylePackLoadInput) -> StylePackResult:
    """TODO: charger le style pack actif depuis PostgreSQL."""
    logger.info("load_style_pack_active_activity.started", sku=payload.product.sku)
    await asyncio.sleep(0)
    return StylePackResult(
        style_pack_id="style-pack-active-placeholder",
        version_label="style-pack-v1-placeholder",
    )


@activity.defn(name="load_prompt_package_active_activity")
async def load_prompt_package_active_activity(
    payload: PromptPackageLoadInput,
) -> PromptPackageResult:
    """TODO: charger le prompt package actif depuis PostgreSQL."""
    logger.info("load_prompt_package_active_activity.started", sku=payload.product.sku)
    await asyncio.sleep(0)
    return PromptPackageResult(
        prompt_package_id="prompt-package-active-placeholder",
        version_label="prompt-package-v1-placeholder",
    )


@activity.defn(name="evaluate_publish_gate_activity")
async def evaluate_publish_gate_activity(payload: PublishGateInput) -> PublishGateDecision:
    """
    TODO:
    - appliquer les règles du publish gate
    - décider publish vs pending_editor_review
    """
    logger.info(
        "evaluate_publish_gate_activity.started",
        sku=payload.context_snapshot.product.sku,
        review_artifact_id=payload.review_artifact.artifact_id,
    )
    await asyncio.sleep(0)
    return PublishGateDecision(
        decision=PublicationDecision.PENDING_EDITOR_REVIEW,
        reason="placeholder_publish_gate_requires_human_validation",
    )


@activity.defn(name="publish_generated_content_activity")
async def publish_generated_content_activity(
    payload: PublishContentInput,
) -> PublishContentResult:
    """TODO: publier la fiche dans le PIM / CMS / Product Content API."""
    logger.info(
        "publish_generated_content_activity.started",
        sku=payload.context_snapshot.product.sku,
        review_artifact_id=payload.review_artifact.artifact_id,
    )
    await asyncio.sleep(0)
    return PublishContentResult(
        published_content_id=f"content-{payload.context_snapshot.product.sku.lower()}-placeholder",
        target_system="product-content-api",
    )
