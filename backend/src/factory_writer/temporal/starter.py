from __future__ import annotations

from factory_writer.temporal.offline_evaluation import starter as offline_evaluation_starter
from factory_writer.temporal.sku_lifecycle import starter as sku_lifecycle_starter
from factory_writer.temporal.style_guide_ingestion import (
    starter as style_guide_ingestion_starter,
)

build_offline_eval_workflow_id = offline_evaluation_starter.build_workflow_id
start_offline_evaluation_workflow = offline_evaluation_starter.start_workflow

build_sku_workflow_id = sku_lifecycle_starter.build_workflow_id
start_sku_lifecycle_workflow = sku_lifecycle_starter.start_workflow
signal_technical_archive_received = sku_lifecycle_starter.signal_technical_archive_received

build_style_guide_workflow_id = style_guide_ingestion_starter.build_workflow_id
start_style_guide_ingestion_workflow = style_guide_ingestion_starter.start_workflow
TemporalStyleGuideWorkflowStarter = (
    style_guide_ingestion_starter.TemporalStyleGuideWorkflowStarter
)

__all__ = [
    "TemporalStyleGuideWorkflowStarter",
    "build_offline_eval_workflow_id",
    "build_sku_workflow_id",
    "build_style_guide_workflow_id",
    "signal_technical_archive_received",
    "start_offline_evaluation_workflow",
    "start_sku_lifecycle_workflow",
    "start_style_guide_ingestion_workflow",
]
