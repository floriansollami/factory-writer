from __future__ import annotations

from temporalio import workflow

from factory_writer.temporal.common.config import (
    MEDIUM_ACTIVITY_TIMEOUT,
    OFFLINE_RETRY_POLICY,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.offline_evaluation.contracts import (
    OfflineEvaluationInput,
    OfflineEvaluationOutput,
    OfflineEvaluationState,
)

# On utilise imports_passed_through pour empêcher la Sandbox Temporal d'analyser le code des Activités.
# (Les activités importent SQLAlchemy, Google Cloud, etc. qui feraient crasher la sandbox déterministe).
with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.offline_evaluation.activities import (
        load_evaluation_batch,
        promote_generation_recipe_candidate,
        run_vertex_prompt_evaluation,
    )


@workflow.defn(name="OfflineEvaluationWorkflow")
class OfflineEvaluationWorkflow:
    def __init__(self) -> None:
        self.state = OfflineEvaluationState()

    @workflow.query
    def get_state(self) -> OfflineEvaluationState:
        return self.state

    @workflow.run
    async def run(self, payload: OfflineEvaluationInput) -> OfflineEvaluationOutput:
        workflow.logger.info(
            "OfflineEvaluationWorkflow.started",
            evaluation_scope=payload.evaluation_scope,
            trigger_source=payload.trigger_source,
        )
        self.state.status = WorkflowExecutionStatus.RUNNING_OFFLINE_EVAL

        batch = await workflow.execute_activity(
            load_evaluation_batch,
            payload,
            task_queue=TaskQueue.OFFLINE_EVALUATION.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=OFFLINE_RETRY_POLICY,
        )
        self.state.batch_id = batch.batch_id

        candidate = await workflow.execute_activity(
            run_vertex_prompt_evaluation,
            batch,
            task_queue=TaskQueue.OFFLINE_EVALUATION.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=OFFLINE_RETRY_POLICY,
        )
        self.state.candidate_generation_recipe_id = candidate.generation_recipe_id

        promoted_generation_recipe_id: str | None = None
        if not payload.dry_run:
            promoted_generation_recipe_id = await workflow.execute_activity(
                promote_generation_recipe_candidate,
                candidate,
                task_queue=TaskQueue.OFFLINE_EVALUATION.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=OFFLINE_RETRY_POLICY,
            )
            self.state.promoted_generation_recipe_id = promoted_generation_recipe_id

        return OfflineEvaluationOutput(
            status="success",
            candidate_generation_recipe_id=candidate.generation_recipe_id,
            promoted_generation_recipe_id=promoted_generation_recipe_id,
        )
