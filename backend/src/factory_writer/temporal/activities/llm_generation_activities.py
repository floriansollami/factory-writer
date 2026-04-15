from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.domain.temporal_models import GeneratedArtifactRef, GenerationStepInput

logger = structlog.get_logger(__name__)


def _artifact_id(kind: str, sku: str) -> str:
    return f"{kind}-{sku.lower()}-placeholder"


@activity.defn(name="generate_claim_plan_activity")
async def generate_claim_plan_activity(payload: GenerationStepInput) -> GeneratedArtifactRef:
    """TODO: appeler LiteLLM pour produire le claim plan structuré."""
    sku = payload.context_snapshot.product.sku
    logger.info("generate_claim_plan_activity.started", sku=sku)
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("claim-plan", sku),
        artifact_kind="claim_plan",
        status="placeholder_generated",
    )


@activity.defn(name="generate_redaction_plan_activity")
async def generate_redaction_plan_activity(payload: GenerationStepInput) -> GeneratedArtifactRef:
    """TODO: appeler LiteLLM pour produire le redaction plan structuré."""
    sku = payload.context_snapshot.product.sku
    logger.info(
        "generate_redaction_plan_activity.started",
        sku=sku,
        upstream_artifact_id=payload.upstream_artifact_id,
    )
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("redaction-plan", sku),
        artifact_kind="redaction_plan",
        status="placeholder_generated",
    )


@activity.defn(name="generate_final_draft_activity")
async def generate_final_draft_activity(payload: GenerationStepInput) -> GeneratedArtifactRef:
    """TODO: appeler LiteLLM pour produire le draft final."""
    sku = payload.context_snapshot.product.sku
    logger.info(
        "generate_final_draft_activity.started",
        sku=sku,
        upstream_artifact_id=payload.upstream_artifact_id,
    )
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("final-draft", sku),
        artifact_kind="final_draft",
        status="placeholder_generated",
    )


@activity.defn(name="review_and_rewrite_activity")
async def review_and_rewrite_activity(payload: GenerationStepInput) -> GeneratedArtifactRef:
    """TODO: appeler LiteLLM pour review / rewrite final."""
    sku = payload.context_snapshot.product.sku
    logger.info(
        "review_and_rewrite_activity.started",
        sku=sku,
        upstream_artifact_id=payload.upstream_artifact_id,
    )
    await asyncio.sleep(0)
    return GeneratedArtifactRef(
        artifact_id=_artifact_id("review", sku),
        artifact_kind="review",
        status="placeholder_generated",
    )
