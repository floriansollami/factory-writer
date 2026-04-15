from __future__ import annotations

from pydantic import Field

from factory_writer.temporal.common.contracts import TemporalPayloadModel, WorkflowExecutionStatus


class StyleGuideIngestionInput(TemporalPayloadModel):
    source_id: str = Field(..., description="UUID du document source en base")
    file_uri: str = Field(..., description="URI GCS du PDF du style guide")


class StyleGuideApprovalSignalInput(TemporalPayloadModel):
    approved: bool
    reviewer_id: str | None = None
    comment: str | None = None


class StyleGuideWorkflowState(TemporalPayloadModel):
    status: WorkflowExecutionStatus = WorkflowExecutionStatus.WAITING_FOR_STYLE_APPROVAL
    draft_pack_id: str | None = None
    approved: bool | None = None


class StyleGuideLayoutParseResult(TemporalPayloadModel):
    source_id: str
    source_generation: str | None = None
    layout_operation_id: str
    output_uri: str


class StyleGuideChunkPersistResult(TemporalPayloadModel):
    fragment_ids: list[str]


class StylePackDraftResult(TemporalPayloadModel):
    draft_pack_id: str
    draft_version_label: str


class StyleGuideIngestionOutput(TemporalPayloadModel):
    status: str
    pack_id: str | None = None
