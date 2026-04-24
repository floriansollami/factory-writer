from __future__ import annotations

from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy

from factory_writer.application.ports.product_technical_ingestion import (
    ProductContextReference,
    TechnicalSourcesUploaded,
)
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.sku_lifecycle.contracts import (
    CommercialSnapshotAvailableSignal,
    ProductLifecycleInput,
    ReviewCaseResolvedSignal,
    StylePackActivatedSignal,
)
from factory_writer.temporal.sku_lifecycle.contracts import (
    ProductContextRef as TemporalProductContextRef,
)
from factory_writer.temporal.sku_lifecycle.contracts import (
    TechnicalSourcesUploadedSignal as TemporalTechnicalSourcesUploadedSignal,
)
from factory_writer.temporal.sku_lifecycle.workflow import ProductLifecycleWorkflow
from factory_writer.temporal.technical_dossier_ingestion.workflow import (
    TechnicalDossierIngestionWorkflow,
)


class TemporalProductLifecycleWorkflowStarter:
    def __init__(self, temporal_client: Client):
        self._client = temporal_client

    async def start_product_lifecycle(self, product: ProductContextReference) -> str:
        workflow_id = _product_workflow_id(product.sku)
        try:
            await self._client.start_workflow(
                ProductLifecycleWorkflow.run,
                ProductLifecycleInput(product=_to_temporal_product_ref(product)),
                id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer product lifecycle",
                static_details=f"Lifecycle orchestration for SKU {product.sku}",
            )
            return workflow_id
        except Exception as exc:
            raise RuntimeError(
                f"Impossible de démarrer le workflow Temporal Product Lifecycle: {str(exc)}"
            ) from exc

    async def signal_technical_sources_uploaded(
        self,
        sku: str,
        payload: TechnicalSourcesUploaded,
    ) -> None:
        try:
            handle = self._client.get_workflow_handle(_product_workflow_id(sku))
            await handle.signal(
                ProductLifecycleWorkflow.technical_sources_uploaded,
                _to_temporal_sources_uploaded_signal(payload),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Impossible d'envoyer le signal au workflow produit: {str(exc)}"
            ) from exc

    async def signal_technical_review_case_resolved(
        self,
        *,
        ingestion_run_id: str,
        case_id: str,
    ) -> None:
        try:
            handle = self._client.get_workflow_handle(
                _technical_dossier_workflow_id(ingestion_run_id)
            )
            await handle.signal(
                TechnicalDossierIngestionWorkflow.review_case_resolved,
                ReviewCaseResolvedSignal(
                    ingestion_run_id=ingestion_run_id,
                    case_id=case_id,
                ),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Impossible d'envoyer le signal au workflow technique: {str(exc)}"
            ) from exc

    async def signal_style_pack_activated(self, *, sku: str, style_pack_id: str) -> None:
        try:
            handle = self._client.get_workflow_handle(_product_workflow_id(sku))
            await handle.signal(
                ProductLifecycleWorkflow.style_pack_activated,
                StylePackActivatedSignal(style_pack_id=style_pack_id),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Impossible d'envoyer le signal style pack au workflow produit: {str(exc)}"
            ) from exc

    async def signal_commercial_snapshot_available(self, *, sku: str, snapshot_id: str) -> None:
        try:
            handle = self._client.get_workflow_handle(_product_workflow_id(sku))
            await handle.signal(
                ProductLifecycleWorkflow.commercial_snapshot_available,
                CommercialSnapshotAvailableSignal(snapshot_id=snapshot_id),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Impossible d'envoyer le signal snapshot au workflow produit: {str(exc)}"
            ) from exc


def _product_workflow_id(sku: str) -> str:
    return f"product-lifecycle-{sku}"


def _technical_dossier_workflow_id(ingestion_run_id: str) -> str:
    return f"technical-dossier-{ingestion_run_id}"


def _to_temporal_product_ref(product: ProductContextReference) -> TemporalProductContextRef:
    return TemporalProductContextRef(
        product_id=product.product_id,
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _to_temporal_sources_uploaded_signal(
    payload: TechnicalSourcesUploaded,
) -> TemporalTechnicalSourcesUploadedSignal:
    return TemporalTechnicalSourcesUploadedSignal(
        document_source_ids=payload.document_source_ids,
        ingestion_run_id=payload.ingestion_run_id,
        source_event_id=payload.source_event_id,
    )
