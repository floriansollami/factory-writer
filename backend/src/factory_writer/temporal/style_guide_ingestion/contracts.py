from __future__ import annotations

from enum import StrEnum

from factory_writer.temporal.common.contracts import TemporalPayloadModel, WorkflowExecutionStatus


class StyleGuideFinalDecision(StrEnum):
    APPROVE = "APPROVE"
    REJECT = "REJECT"


class StyleGuideWorkflowState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.BUILDING_CONTEXT
    ingestion_run_id: str | None = None
    draft_style_pack_id: str | None = None
    final_decision: StyleGuideFinalDecision | None = None
    decision_received_at: str | None = None


class StyleGuideDraftStylePackResult(TemporalPayloadModel):
    draft_style_pack_id: str


class StyleGuideIngestionOutput(TemporalPayloadModel):
    status: str
    style_pack_id: str | None = None
