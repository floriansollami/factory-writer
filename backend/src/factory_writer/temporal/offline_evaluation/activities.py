from __future__ import annotations

import asyncio

import structlog
from temporalio import activity

from factory_writer.temporal.offline_evaluation.contracts import (
    OfflineEvaluationBatch,
    OfflineEvaluationInput,
    PromptPackageCandidateResult,
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
) -> PromptPackageCandidateResult:
    logger.info(
        "run_vertex_prompt_evaluation.started",
        batch_id=payload.batch_id,
        case_count=payload.case_count,
    )
    await asyncio.sleep(0)
    return PromptPackageCandidateResult(
        prompt_package_id=f"prompt-candidate-{payload.batch_id}",
        version_label="prompt-package-candidate-placeholder",
        source="vertex-ai-placeholder",
    )


@activity.defn
async def promote_prompt_package_candidate(
    payload: PromptPackageCandidateResult,
) -> str:
    logger.info(
        "promote_prompt_package_candidate.started",
        prompt_package_id=payload.prompt_package_id,
    )
    await asyncio.sleep(0)
    return payload.prompt_package_id
