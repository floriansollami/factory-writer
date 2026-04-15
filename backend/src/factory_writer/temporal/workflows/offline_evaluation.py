from __future__ import annotations

from temporalio import workflow

from factory_writer.domain.temporal_models import (
    OfflineEvaluationInput,
    OfflineEvaluationOutput,
    OfflineEvaluationState,
    WorkflowExecutionStatus,
)
from factory_writer.temporal.activity_options import MEDIUM_ACTIVITY_TIMEOUT, OFFLINE_RETRY_POLICY
from factory_writer.temporal.task_queues import TaskQueue

with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.activities.offline_eval_activities import (
        load_offline_evaluation_batch_activity,
        promote_prompt_package_candidate_activity,
        run_vertex_prompt_evaluation_activity,
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
            load_offline_evaluation_batch_activity,
            payload,
            task_queue=TaskQueue.OFFLINE_EVAL.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=OFFLINE_RETRY_POLICY,
        )
        self.state.batch_id = batch.batch_id

        candidate = await workflow.execute_activity(
            run_vertex_prompt_evaluation_activity,
            batch,
            task_queue=TaskQueue.OFFLINE_EVAL.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=OFFLINE_RETRY_POLICY,
        )
        self.state.candidate_prompt_package_id = candidate.prompt_package_id

        promoted_prompt_package_id: str | None = None
        if not payload.dry_run:
            promoted_prompt_package_id = await workflow.execute_activity(
                promote_prompt_package_candidate_activity,
                candidate,
                task_queue=TaskQueue.OFFLINE_EVAL.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=OFFLINE_RETRY_POLICY,
            )
            self.state.promoted_prompt_package_id = promoted_prompt_package_id

        return OfflineEvaluationOutput(
            status="success",
            candidate_prompt_package_id=candidate.prompt_package_id,
            promoted_prompt_package_id=promoted_prompt_package_id,
        )
