from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TemporalPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowExecutionStatus(StrEnum):
    WAITING_FOR_TECHNICAL_ARCHIVE = "waiting_for_technical_archive"
    EXTRACTING_FACTS = "extracting_facts"
    BUILDING_CONTEXT = "building_context"
    GENERATING_COPY = "generating_copy"
    WAITING_FOR_STYLE_APPROVAL = "waiting_for_style_approval"
    RUNNING_OFFLINE_EVAL = "running_offline_eval"
    PENDING_EDITOR_REVIEW = "pending_editor_review"
    PUBLISHED = "published"
    FAILED = "failed"


class PublicationDecision(StrEnum):
    READY_TO_PUBLISH = "ready_to_publish"
    PENDING_EDITOR_REVIEW = "pending_editor_review"
