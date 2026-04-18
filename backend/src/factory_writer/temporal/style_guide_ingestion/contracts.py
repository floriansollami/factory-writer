from __future__ import annotations

from factory_writer.temporal.common.contracts import TemporalPayloadModel, WorkflowExecutionStatus


class StyleGuideApprovalSignalInput(TemporalPayloadModel):
    approved: bool


class StyleGuideWorkflowState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.WAITING_FOR_STYLE_APPROVAL
    draft_pack_id: str | None = None
    approved: bool | None = None


class StylePackDraftResult(TemporalPayloadModel):
    draft_pack_id: str


class StyleGuideIngestionOutput(TemporalPayloadModel):
    status: str
    pack_id: str | None = None
