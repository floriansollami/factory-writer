from __future__ import annotations

from typing import Any

from factory_writer.temporal.common.contracts import TemporalPayloadModel, WorkflowExecutionStatus


class ProductSheetGenerationInput(TemporalPayloadModel):
    product_id: str
    generation_id: str


class ProductSheetGenerationOutput(TemporalPayloadModel):
    status: WorkflowExecutionStatus
    generation_id: str


class GenerateProductSheetCandidateInput(TemporalPayloadModel):
    generation_id: str


class GenerateProductSheetCandidateResult(TemporalPayloadModel):
    status: str
    sheet_json: dict[str, Any]
    self_check_json: dict[str, Any]
    metadata: dict[str, Any]


class PersistProductSheetGenerationInput(TemporalPayloadModel):
    generation_id: str
    generation_result: dict[str, Any]


class PersistProductSheetGenerationResult(TemporalPayloadModel):
    generation: dict[str, Any]


class MarkProductSheetGenerationFailedInput(TemporalPayloadModel):
    generation_id: str
    error_message: str


class MarkProductSheetGenerationFailedResult(TemporalPayloadModel):
    generation: dict[str, Any]


__all__ = [
    "GenerateProductSheetCandidateInput",
    "GenerateProductSheetCandidateResult",
    "MarkProductSheetGenerationFailedInput",
    "MarkProductSheetGenerationFailedResult",
    "PersistProductSheetGenerationInput",
    "PersistProductSheetGenerationResult",
    "ProductSheetGenerationInput",
    "ProductSheetGenerationOutput",
]
