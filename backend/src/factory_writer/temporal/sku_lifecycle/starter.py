from __future__ import annotations

import structlog
from temporalio.client import Client
from temporalio.common import WorkflowIDConflictPolicy
from temporalio.service import RPCError, RPCStatusCode

from factory_writer.application.ports.product_technical_ingestion import (
    ProductContextReference,
    TechnicalSourcesUploaded,
)
from factory_writer.temporal.common.config import TaskQueue
from factory_writer.temporal.product_sheet_generation.contracts import (
    ProductSheetGenerationInput,
)
from factory_writer.temporal.product_sheet_generation.workflow import (
    ProductSheetGenerationWorkflow,
)
from factory_writer.temporal.sku_lifecycle.contracts import (
    CommercialSnapshotAvailableSignal,
    ProductLifecycleInput,
    ReviewCaseResolvedSignal,
    StylePackActivatedSignal,
    TechnicalFactsReadySignal,
)
from factory_writer.temporal.sku_lifecycle.contracts import (
    ProductContextRef as TemporalProductContextRef,
)
from factory_writer.temporal.sku_lifecycle.contracts import (
    TechnicalSourcesUploadedSignal as TemporalTechnicalSourcesUploadedSignal,
)
from factory_writer.temporal.sku_lifecycle.workflow import ProductLifecycleWorkflow
from factory_writer.temporal.technical_dossier_ingestion.contracts import (
    TechnicalDossierIngestionInput,
)
from factory_writer.temporal.technical_dossier_ingestion.workflow import (
    TechnicalDossierIngestionWorkflow,
)

logger = structlog.get_logger(__name__)


class TemporalProductLifecycleWorkflowStarter:
    def __init__(self, temporal_client: Client):
        self._client = temporal_client

    async def start_product_lifecycle(self, product: ProductContextReference) -> str:
        workflow_id = _product_workflow_id(product.sku)
        try:
            logger.info(
                "Product lifecycle | Temporal | démarrage workflow",
                product_id=product.product_id,
                sku=product.sku,
                workflow_id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            )

            await self._client.start_workflow(
                ProductLifecycleWorkflow.run,
                ProductLifecycleInput(product=_to_temporal_product_ref(product)),
                id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer product lifecycle",
                static_details=f"Lifecycle orchestration for SKU {product.sku}",
            )

            logger.info(
                "Product lifecycle | Temporal | workflow démarré ou réutilisé",
                product_id=product.product_id,
                sku=product.sku,
                workflow_id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            )

            return workflow_id
        except Exception as exc:
            logger.exception(
                "Product lifecycle | Temporal | échec démarrage workflow",
                product_id=product.product_id,
                sku=product.sku,
                workflow_id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            )
            raise RuntimeError(
                f"Impossible de démarrer le workflow Temporal Product Lifecycle: {str(exc)}"
            ) from exc

    async def start_technical_dossier_ingestion(
        self,
        product: ProductContextReference,
        payload: TechnicalSourcesUploaded,
    ) -> str:
        workflow_id = _technical_dossier_workflow_id(payload.ingestion_run_id)
        try:
            logger.info(
                "Technical dossier | Temporal | démarrage workflow direct",
                product_id=product.product_id,
                sku=product.sku,
                workflow_id=workflow_id,
                ingestion_run_id=payload.ingestion_run_id,
                document_source_ids=payload.document_source_ids,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            )

            await self._client.start_workflow(
                TechnicalDossierIngestionWorkflow.run,
                TechnicalDossierIngestionInput(
                    product=_to_temporal_product_ref(product),
                    sources_signal=_to_temporal_sources_uploaded_signal(payload),
                ),
                id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer technical dossier ingestion",
                static_details=f"Technical dossier ingestion for SKU {product.sku}",
            )

            logger.info(
                "Technical dossier | Temporal | workflow direct démarré ou réutilisé",
                product_id=product.product_id,
                sku=product.sku,
                workflow_id=workflow_id,
                ingestion_run_id=payload.ingestion_run_id,
            )

            return workflow_id
        except Exception as exc:
            logger.exception(
                "Technical dossier | Temporal | échec démarrage workflow direct",
                product_id=product.product_id,
                sku=product.sku,
                workflow_id=workflow_id,
                ingestion_run_id=payload.ingestion_run_id,
            )
            raise RuntimeError(
                f"Impossible de démarrer le workflow Temporal Technical Dossier: {str(exc)}"
            ) from exc

    async def start_product_sheet_generation(
        self,
        *,
        product_id: str,
        generation_id: str,
    ) -> str:
        workflow_id = _product_sheet_generation_workflow_id(generation_id)
        try:
            logger.info(
                "Product sheet | Temporal | démarrage workflow",
                product_id=product_id,
                generation_id=generation_id,
                workflow_id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            )
            await self._client.start_workflow(
                ProductSheetGenerationWorkflow.run,
                ProductSheetGenerationInput(
                    product_id=product_id,
                    generation_id=generation_id,
                ),
                id=workflow_id,
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                id_conflict_policy=WorkflowIDConflictPolicy.USE_EXISTING,
                static_summary="Factory Writer product sheet generation",
                static_details=f"Product sheet generation for product {product_id}",
            )
            return workflow_id
        except Exception as exc:
            raise RuntimeError(
                f"Impossible de démarrer le workflow Temporal Product Sheet: {str(exc)}"
            ) from exc

    async def signal_technical_sources_uploaded(
        self,
        sku: str,
        payload: TechnicalSourcesUploaded,
    ) -> None:
        workflow_id = _product_workflow_id(sku)
        try:
            logger.info(
                "Product lifecycle | Temporal | signal PDFs techniques",
                sku=sku,
                workflow_id=workflow_id,
                ingestion_run_id=payload.ingestion_run_id,
                document_source_ids=payload.document_source_ids,
            )

            handle = self._client.get_workflow_handle(workflow_id)
            await handle.signal(
                ProductLifecycleWorkflow.technical_sources_uploaded,
                _to_temporal_sources_uploaded_signal(payload),
            )

            logger.info(
                "Product lifecycle | Temporal | signal PDFs techniques envoyé",
                sku=sku,
                workflow_id=workflow_id,
                ingestion_run_id=payload.ingestion_run_id,
            )
        except Exception as exc:
            logger.exception(
                "Product lifecycle | Temporal | échec signal PDFs techniques",
                sku=sku,
                workflow_id=workflow_id,
                ingestion_run_id=payload.ingestion_run_id,
            )
            raise RuntimeError(
                f"Impossible d'envoyer le signal au workflow produit: {str(exc)}"
            ) from exc

    async def signal_technical_facts_ready(
        self,
        *,
        sku: str,
        ingestion_run_id: str,
        promoted_fact_count: int,
    ) -> None:
        workflow_id = _product_workflow_id(sku)
        try:
            logger.info(
                "Product lifecycle | Temporal | signal facts techniques prêts",
                sku=sku,
                workflow_id=workflow_id,
                ingestion_run_id=ingestion_run_id,
                promoted_fact_count=promoted_fact_count,
            )
            handle = self._client.get_workflow_handle(workflow_id)
            await handle.signal(
                ProductLifecycleWorkflow.technical_facts_ready,
                TechnicalFactsReadySignal(
                    ingestion_run_id=ingestion_run_id,
                    promoted_fact_count=promoted_fact_count,
                ),
            )
            logger.info(
                "Product lifecycle | Temporal | signal facts techniques prêts envoyé",
                sku=sku,
                workflow_id=workflow_id,
                ingestion_run_id=ingestion_run_id,
                promoted_fact_count=promoted_fact_count,
            )
        except Exception as exc:
            logger.exception(
                "Product lifecycle | Temporal | échec signal facts techniques prêts",
                sku=sku,
                workflow_id=workflow_id,
                ingestion_run_id=ingestion_run_id,
                promoted_fact_count=promoted_fact_count,
            )
            raise RuntimeError(
                f"Impossible d'envoyer le signal facts techniques au workflow produit: {str(exc)}"
            ) from exc

    async def signal_technical_review_case_resolved(
        self,
        *,
        ingestion_run_id: str,
        case_id: str,
        open_review_case_count: int,
        review_complete: bool,
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
                    open_review_case_count=open_review_case_count,
                    review_complete=review_complete,
                ),
            )
        except Exception as exc:
            raise RuntimeError(
                f"Impossible d'envoyer le signal au workflow technique: {str(exc)}"
            ) from exc

    async def terminate_technical_dossier_ingestion(
        self,
        *,
        ingestion_run_id: str,
        reason: str,
    ) -> None:
        workflow_id = _technical_dossier_workflow_id(ingestion_run_id)
        try:
            handle = self._client.get_workflow_handle(workflow_id)
            await handle.terminate(reason=reason)
            logger.info(
                "Technical dossier | Temporal | workflow terminé",
                workflow_id=workflow_id,
                ingestion_run_id=ingestion_run_id,
                reason=reason,
            )
        except RPCError as exc:
            if exc.status in {RPCStatusCode.NOT_FOUND, RPCStatusCode.FAILED_PRECONDITION}:
                logger.info(
                    "Technical dossier | Temporal | workflow déjà absent ou fermé",
                    workflow_id=workflow_id,
                    ingestion_run_id=ingestion_run_id,
                    reason=reason,
                    rpc_status=exc.status.name,
                )
                return
            raise RuntimeError(f"Impossible de terminer le workflow technique: {str(exc)}") from exc
        except Exception as exc:
            raise RuntimeError(f"Impossible de terminer le workflow technique: {str(exc)}") from exc

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


def _product_sheet_generation_workflow_id(generation_id: str) -> str:
    return f"product-sheet-generation-{generation_id}"


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
