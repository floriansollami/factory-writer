from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.domain.temporal_models import (
    OfflineEvaluationBatch,
    OfflineEvaluationInput,
    PromptPackageCandidateResult,
)

logger = structlog.get_logger(__name__)


@activity.defn(name="load_offline_evaluation_batch_activity")
async def load_offline_evaluation_batch_activity(
    payload: OfflineEvaluationInput,
) -> OfflineEvaluationBatch:
    """TODO: charger le batch offline depuis BigQuery / traces / gold set."""
    logger.info(
        "load_offline_evaluation_batch_activity.started",
        scope=payload.evaluation_scope,
        trigger_source=payload.trigger_source,
    )
    await asyncio.sleep(0)
    return OfflineEvaluationBatch(
        batch_id=f"offline-batch-{payload.evaluation_scope}-placeholder",
        source_dataset="bigquery://factory_writer/offline_eval_dataset",
        case_count=0,
    )


@activity.defn(name="run_vertex_prompt_evaluation_activity")
async def run_vertex_prompt_evaluation_activity(
    payload: OfflineEvaluationBatch,
) -> PromptPackageCandidateResult:
    """TODO: lancer Vertex AI Eval + prompt optimizer sur le batch."""
    logger.info(
        "run_vertex_prompt_evaluation_activity.started",
        batch_id=payload.batch_id,
        case_count=payload.case_count,
    )
    await asyncio.sleep(0)
    return PromptPackageCandidateResult(
        prompt_package_id=f"prompt-candidate-{payload.batch_id}",
        version_label="prompt-package-candidate-placeholder",
        source="vertex-ai-placeholder",
    )


@activity.defn(name="promote_prompt_package_candidate_activity")
async def promote_prompt_package_candidate_activity(
    payload: PromptPackageCandidateResult,
) -> str:
    """TODO: promouvoir le candidate prompt package en version active."""
    logger.info(
        "promote_prompt_package_candidate_activity.started",
        prompt_package_id=payload.prompt_package_id,
    )
    await asyncio.sleep(0)
    return payload.prompt_package_id
