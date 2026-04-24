from __future__ import annotations

from enum import StrEnum

from pydantic import BaseModel, ConfigDict


class TemporalPayloadModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class WorkflowExecutionStatus(StrEnum):
    WAITING_TECHNICAL_SOURCES = "waiting_technical_sources"
    WAITING_STYLE_PACK = "waiting_style_pack"
    WAITING_COMMERCIAL_SNAPSHOT = "waiting_commercial_snapshot"
    WAITING_TECH_FACTS = "waiting_tech_facts"
    TECHNICAL_FACTS_READY = "technical_facts_ready"
    EXTRACTING_FACTS = "extracting_facts"
    BUILDING_CONTEXT = "building_context"
    CONTEXT_READY = "context_ready"
    PENDING_TECH_REVIEW = "pending_tech_review"
    GENERATING_COPY = "generating_copy"
    PENDING_EDITOR_REVIEW = "pending_editor_review"
    PUBLISHED = "published"
    FAILED = "failed"
