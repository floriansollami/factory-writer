from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from factory_writer.temporal.activities.context_activities import (
    evaluate_publish_gate_activity,
    load_prompt_package_active_activity,
    load_signal_snapshot_activity,
    load_style_pack_active_activity,
    publish_generated_content_activity,
)
from factory_writer.temporal.activities.docai_activities import extract_archive_and_facts_activity
from factory_writer.temporal.activities.llm_generation_activities import (
    generate_claim_plan_activity,
    generate_final_draft_activity,
    generate_redaction_plan_activity,
    review_and_rewrite_activity,
)
from factory_writer.temporal.activities.offline_eval_activities import (
    load_offline_evaluation_batch_activity,
    promote_prompt_package_candidate_activity,
    run_vertex_prompt_evaluation_activity,
)
from factory_writer.temporal.activities.style_guide_activities import (
    generate_style_pack_draft_activity,
    mark_style_source_failed_activity,
    mark_style_source_in_progress_activity,
    persist_style_fragments_activity,
    promote_style_pack_activity,
    trigger_style_layout_parse_activity,
)
from factory_writer.temporal.task_queues import TaskQueue
from factory_writer.temporal.worker_roles import WorkerRole
from factory_writer.temporal.workflows.offline_evaluation import OfflineEvaluationWorkflow
from factory_writer.temporal.workflows.sku_lifecycle import SkuLifecycleWorkflow
from factory_writer.temporal.workflows.style_guide_ingestion import StyleGuideIngestionWorkflow


@dataclass(frozen=True)
class WorkerRegistration:
    role: WorkerRole
    task_queue: TaskQueue
    workflows: Sequence[type]
    activities: Sequence[Callable[..., object]]
    description: str


REGISTRY: dict[WorkerRole, WorkerRegistration] = {
    WorkerRole.ORCHESTRATOR: WorkerRegistration(
        role=WorkerRole.ORCHESTRATOR,
        task_queue=TaskQueue.SKU_LIFECYCLE,
        workflows=[SkuLifecycleWorkflow],
        activities=[
            load_signal_snapshot_activity,
            load_style_pack_active_activity,
            load_prompt_package_active_activity,
            evaluate_publish_gate_activity,
            publish_generated_content_activity,
        ],
        description="Lifecycle orchestration and publish gate",
    ),
    WorkerRole.DOCAI: WorkerRegistration(
        role=WorkerRole.DOCAI,
        task_queue=TaskQueue.DOCAI_ACTIVITIES,
        workflows=[],
        activities=[extract_archive_and_facts_activity],
        description="Technical archive extraction and fact normalization",
    ),
    WorkerRole.LLM: WorkerRegistration(
        role=WorkerRole.LLM,
        task_queue=TaskQueue.LLM_GENERATION,
        workflows=[],
        activities=[
            generate_claim_plan_activity,
            generate_redaction_plan_activity,
            generate_final_draft_activity,
            review_and_rewrite_activity,
        ],
        description="Structured generation chain",
    ),
    WorkerRole.STYLE_ADMIN: WorkerRegistration(
        role=WorkerRole.STYLE_ADMIN,
        task_queue=TaskQueue.STYLE_INGESTION,
        workflows=[StyleGuideIngestionWorkflow],
        activities=[
            mark_style_source_in_progress_activity,
            mark_style_source_failed_activity,
            trigger_style_layout_parse_activity,
            persist_style_fragments_activity,
            generate_style_pack_draft_activity,
            promote_style_pack_activity,
        ],
        description="Style guide ingestion and publication",
    ),
    WorkerRole.OFFLINE_LAB: WorkerRegistration(
        role=WorkerRole.OFFLINE_LAB,
        task_queue=TaskQueue.OFFLINE_EVAL,
        workflows=[OfflineEvaluationWorkflow],
        activities=[
            load_offline_evaluation_batch_activity,
            run_vertex_prompt_evaluation_activity,
            promote_prompt_package_candidate_activity,
        ],
        description="Offline evaluation and prompt promotion",
    ),
}


def get_worker_registration(role: WorkerRole) -> WorkerRegistration:
    return REGISTRY[role]
