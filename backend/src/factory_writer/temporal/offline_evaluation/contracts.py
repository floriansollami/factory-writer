from __future__ import annotations

from factory_writer.temporal.common.contracts import TemporalPayloadModel, WorkflowExecutionStatus


class OfflineEvaluationInput(TemporalPayloadModel):
    evaluation_scope: str = "full"
    trigger_source: str = "cron"
    candidate_prompt_package_id: str | None = None
    dry_run: bool = False


class OfflineEvaluationState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.RUNNING_OFFLINE_EVAL
    batch_id: str | None = None
    candidate_prompt_package_id: str | None = None
    promoted_prompt_package_id: str | None = None


class OfflineEvaluationBatch(TemporalPayloadModel):
    batch_id: str
    source_dataset: str
    case_count: int


class PromptPackageCandidateResult(TemporalPayloadModel):
    prompt_package_id: str
    version_label: str
    source: str


class OfflineEvaluationOutput(TemporalPayloadModel):
    status: str
    candidate_prompt_package_id: str | None = None
    promoted_prompt_package_id: str | None = None
