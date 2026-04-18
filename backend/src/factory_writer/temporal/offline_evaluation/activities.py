from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.temporal.offline_evaluation.contracts import (
    GenerationRecipeCandidateResult,
    OfflineEvaluationBatch,
    OfflineEvaluationInput,
)

logger = structlog.get_logger(__name__)


@activity.defn
async def load_evaluation_batch(
    payload: OfflineEvaluationInput,
) -> OfflineEvaluationBatch:
    logger.info(
        "load_evaluation_batch.started",
        scope=payload.evaluation_scope,
        trigger_source=payload.trigger_source,
    )
    await asyncio.sleep(0)
    return OfflineEvaluationBatch(
        batch_id=f"offline-batch-{payload.evaluation_scope}-placeholder",
        source_dataset="bigquery://factory_writer/offline_eval_dataset",
        case_count=0,
    )


@activity.defn
async def run_vertex_prompt_evaluation(
    payload: OfflineEvaluationBatch,
) -> GenerationRecipeCandidateResult:
    logger.info(
        "run_vertex_prompt_evaluation.started",
        batch_id=payload.batch_id,
        case_count=payload.case_count,
    )
    await asyncio.sleep(0)
    return GenerationRecipeCandidateResult(
        generation_recipe_id=f"generation-recipe-candidate-{payload.batch_id}",
        version_label="generation-recipe-candidate-placeholder",
        source="vertex-ai-placeholder",
    )


@activity.defn
async def promote_generation_recipe_candidate(
    payload: GenerationRecipeCandidateResult,
) -> str:
    logger.info(
        "promote_generation_recipe_candidate.started",
        generation_recipe_id=payload.generation_recipe_id,
    )
    await asyncio.sleep(0)
    return payload.generation_recipe_id
