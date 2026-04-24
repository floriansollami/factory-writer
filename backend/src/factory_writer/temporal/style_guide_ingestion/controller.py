from __future__ import annotations

from temporalio.client import Client

from factory_writer.temporal.style_guide_ingestion.workflow import StyleGuideIngestionWorkflow


class TemporalStyleGuideWorkflowController:
    def __init__(self, temporal_client: Client):
        self._client = temporal_client

    async def approve_style_pack(
        self,
        *,
        workflow_id: str,
        style_pack_id: str,
    ) -> None:
        try:
            handle = self._client.get_workflow_handle(workflow_id)
            await handle.execute_update(
                StyleGuideIngestionWorkflow.approve_style_pack,
                style_pack_id,
            )
            await handle.result()
        except Exception as exc:
            raise RuntimeError(
                f"Impossible d'approuver le pack de style via Temporal: {str(exc)}"
            ) from exc

    async def reject_style_pack(
        self,
        *,
        workflow_id: str,
        style_pack_id: str,
    ) -> None:
        try:
            handle = self._client.get_workflow_handle(workflow_id)
            await handle.execute_update(
                StyleGuideIngestionWorkflow.reject_style_pack,
                style_pack_id,
            )
            await handle.result()
        except Exception as exc:
            raise RuntimeError(
                f"Impossible de rejeter le pack de style via Temporal: {str(exc)}"
            ) from exc
