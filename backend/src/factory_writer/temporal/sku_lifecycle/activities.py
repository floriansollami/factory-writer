from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.temporal.common.contracts import PublicationDecision
from factory_writer.temporal.sku_lifecycle.contracts import (
    GeneratedArtifactRef,
    GenerationStepInput,
    PromptPackageLoadInput,
    PromptPackageResult,
    PublishContentInput,
    PublishContentResult,
    PublishGateDecision,
    PublishGateInput,
    SignalSnapshotLoadInput,
    SignalSnapshotResult,
    StylePackLoadInput,
    StylePackResult,
    TechnicalFactsExtractionInput,
    TechnicalFactsExtractionResult,
)

logger = structlog.get_logger(__name__)


def _artifact_id(kind: str, sku: str) -> str:
    return f"{kind}-{sku.lower()}-placeholder"


@activity.defn
async def extract_archive_and_facts(
    payload: TechnicalFactsExtractionInput,
) -> TechnicalFactsExtractionResult:
    logger.info(
        "extract_archive_and_facts.started",
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


@activity.defn
async def load_signal_snapshot(payload: SignalSnapshotLoadInput) -> SignalSnapshotResult:
    logger.info("load_signal_snapshot.started", sku=payload.product.sku)
    await asyncio.sleep(0)
    return SignalSnapshotResult(
        signal_snapshot_id=f"signal-{payload.product.sku.lower()}-latest",
        cohort_key_used=(
            f"{payload.product.famille_code}.{payload.product.sous_famille_code}."
            f"{payload.product.segment_prix_code or 'default'}"
        ),
        snapshot_status="placeholder_final_ready",
    )


@activity.defn
async def load_style_pack(payload: StylePackLoadInput) -> StylePackResult:
    logger.info("load_style_pack.started", sku=payload.product.sku)
    await asyncio.sleep(0)
    return StylePackResult(
        style_pack_id="style-pack-active-placeholder",
        version_label="style-pack-v1-placeholder",
    )


@activity.defn
async def load_prompt_package(payload: PromptPackageLoadInput) -> PromptPackageResult:
    logger.info("load_prompt_package.started", sku=payload.product.sku)
    await asyncio.sleep(0)
    return PromptPackageResult(
        prompt_package_id="prompt-package-active-placeholder",
        version_label="prompt-package-v1-placeholder",
    )


@activity.defn
async def generate_claim_plan(payload: GenerationStepInput) -> GeneratedArtifactRef:
    sku = payload.context_snapshot.product.sku
    logger.info("generate_claim_plan.started", sku=sku)
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("claim-plan", sku),
        artifact_kind="claim_plan",
        status="placeholder_generated",
    )


@activity.defn
async def generate_redaction_plan(payload: GenerationStepInput) -> GeneratedArtifactRef:
    sku = payload.context_snapshot.product.sku
    logger.info(
        "generate_redaction_plan.started",
        sku=sku,
        upstream_artifact_id=payload.upstream_artifact_id,
    )
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("redaction-plan", sku),
        artifact_kind="redaction_plan",
        status="placeholder_generated",
    )


@activity.defn
async def generate_final_draft(payload: GenerationStepInput) -> GeneratedArtifactRef:
    sku = payload.context_snapshot.product.sku
    logger.info(
        "generate_final_draft.started",
        sku=sku,
        upstream_artifact_id=payload.upstream_artifact_id,
    )
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("final-draft", sku),
        artifact_kind="final_draft",
        status="placeholder_generated",
    )


@activity.defn
async def review_and_rewrite(payload: GenerationStepInput) -> GeneratedArtifactRef:
    sku = payload.context_snapshot.product.sku
    logger.info(
        "review_and_rewrite.started",
        sku=sku,
        upstream_artifact_id=payload.upstream_artifact_id,
    )
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("review", sku),
        artifact_kind="review",
        status="placeholder_generated",
    )


@activity.defn
async def evaluate_publish_gate(payload: PublishGateInput) -> PublishGateDecision:
    logger.info(
        "evaluate_publish_gate.started",
        sku=payload.context_snapshot.product.sku,
        review_artifact_id=payload.review_artifact.artifact_id,
    )
    await asyncio.sleep(0)
    return PublishGateDecision(
        decision=PublicationDecision.PENDING_EDITOR_REVIEW,
        reason="placeholder_publish_gate_requires_human_validation",
    )


@activity.defn
async def publish_generated_content(payload: PublishContentInput) -> PublishContentResult:
    logger.info(
        "publish_generated_content.started",
        sku=payload.context_snapshot.product.sku,
        review_artifact_id=payload.review_artifact.artifact_id,
    )
    await asyncio.sleep(0)
    return PublishContentResult(
        published_content_id=f"content-{payload.context_snapshot.product.sku.lower()}-placeholder",
        target_system="product-content-api",
    )
