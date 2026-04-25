from __future__ import annotations

from contextlib import suppress

from temporalio import workflow

from factory_writer.temporal.common.config import (
    DB_RETRY_POLICY,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.sku_lifecycle.contracts import (
    CommercialSnapshotAvailableSignal,
    ContextReadinessCheckInput,
    CreateProductContextSnapshotInput,
    LoadCanonicalProductInput,
    ProductContextRef,
    ProductLifecycleInput,
    ProductLifecycleOutput,
    ProductLifecycleState,
    StylePackActivatedSignal,
    TechnicalSourcesUploadedSignal,
)
from factory_writer.temporal.technical_dossier_ingestion.contracts import (
    TechnicalDossierIngestionInput,
)
from factory_writer.temporal.technical_dossier_ingestion.workflow import (
    TechnicalDossierIngestionWorkflow,
)

with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.sku_lifecycle.activities import ProductLifecycleActivities


_READINESS_RECHECK_INTERVAL = SHORT_ACTIVITY_TIMEOUT


@workflow.defn(name="ProductLifecycleWorkflow")
class ProductLifecycleWorkflow:
    def __init__(self) -> None:
        self.state = ProductLifecycleState()
        self.product: ProductContextRef | None = None
        self.sources_signal: TechnicalSourcesUploadedSignal | None = None

    @workflow.signal
    def technical_sources_uploaded(self, payload: TechnicalSourcesUploadedSignal) -> None:
        workflow.logger.info(
            "Product lifecycle | PDFs techniques signalés | "
            f"ingestion_run_id={payload.ingestion_run_id} "
            f"document_source_ids={payload.document_source_ids} "
            f"source_event_id={payload.source_event_id}"
        )
        self.sources_signal = payload
        self.state.technical_sources_uploaded = True
        self.state.technical_ingestion_run_id = payload.ingestion_run_id
        self.state.technical_document_source_ids = payload.document_source_ids

    @workflow.signal
    def style_pack_activated(self, payload: StylePackActivatedSignal) -> None:
        self.state.style_pack_id = payload.style_pack_id
        self.state.readiness_event_count += 1

    @workflow.signal
    def commercial_snapshot_available(self, payload: CommercialSnapshotAvailableSignal) -> None:
        self.state.commercial_signal_snapshot_id = payload.snapshot_id
        self.state.readiness_event_count += 1

    @workflow.query
    def get_state(self) -> ProductLifecycleState:
        return self.state

    @workflow.run
    async def run(self, payload: ProductLifecycleInput) -> ProductLifecycleOutput:
        self.product = payload.product

        if payload.resume_state is not None:
            self.state = payload.resume_state

        workflow.logger.info(
            "Product lifecycle | workflow démarré | "
            f"product_id={payload.product.product_id} sku={payload.product.sku}"
        )

        canonical_product_result = await workflow.execute_activity_method(
            ProductLifecycleActivities.load_canonical_product,
            LoadCanonicalProductInput(product=payload.product),
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        canonical_product = canonical_product_result.product
        self.product = canonical_product
        self.state.product_loaded = True

        self.state.status = WorkflowExecutionStatus.WAITING_TECHNICAL_SOURCES
        workflow.logger.info(
            "Product lifecycle | en attente des PDFs techniques | "
            f"product_id={canonical_product.product_id} sku={canonical_product.sku}"
        )
        await workflow.wait_condition(lambda: self.sources_signal is not None)
        sources_signal = self.sources_signal
        if sources_signal is None:
            raise RuntimeError("Aucun signal de sources techniques reçu.")

        workflow.logger.info(
            "Product lifecycle | PDFs techniques reçus | "
            f"product_id={canonical_product.product_id} "
            f"sku={canonical_product.sku} "
            f"ingestion_run_id={sources_signal.ingestion_run_id} "
            f"document_source_ids={sources_signal.document_source_ids}"
        )

        self.state.status = WorkflowExecutionStatus.EXTRACTING_FACTS

        technical_result = await workflow.execute_child_workflow(
            TechnicalDossierIngestionWorkflow.run,
            TechnicalDossierIngestionInput(
                product=canonical_product,
                sources_signal=sources_signal,
            ),
            id=f"technical-dossier-{sources_signal.ingestion_run_id}",
            task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
            static_summary="Factory Writer technical dossier ingestion",
            static_details=f"Technical dossier ingestion for SKU {canonical_product.sku}",
        )

        self.state.technical_facts_ready = (
            technical_result.status == WorkflowExecutionStatus.TECHNICAL_FACTS_READY
        )
        self.state.technical_ingestion_run_id = technical_result.ingestion_run_id

        context_snapshot_id = await self._wait_and_create_context_snapshot(
            canonical_product,
            technical_result.ingestion_run_id,
        )
        self.state.status = WorkflowExecutionStatus.CONTEXT_READY
        self.state.product_context_snapshot_id = context_snapshot_id
        return ProductLifecycleOutput(
            status=self.state.status,
            product_context_snapshot_id=context_snapshot_id,
        )

    async def _wait_and_create_context_snapshot(
        self,
        product: ProductContextRef,
        technical_ingestion_run_id: str,
    ) -> str:
        while True:
            self.state.status = WorkflowExecutionStatus.BUILDING_CONTEXT
            readiness = await workflow.execute_activity_method(
                ProductLifecycleActivities.check_product_context_readiness,
                ContextReadinessCheckInput(
                    product=product,
                    technical_ingestion_run_id=technical_ingestion_run_id,
                ),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            if readiness.ready:
                snapshot = await workflow.execute_activity_method(
                    ProductLifecycleActivities.create_product_context_snapshot,
                    CreateProductContextSnapshotInput(
                        product=product,
                        technical_ingestion_run_id=technical_ingestion_run_id,
                        readiness=readiness,
                    ),
                    task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                    start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                    retry_policy=DB_RETRY_POLICY,
                )
                self.state.style_pack_id = readiness.style_pack_id
                self.state.commercial_signal_snapshot_id = readiness.commercial_signal_snapshot_id
                return snapshot.product_context_snapshot_id

            self.state.waiting_reason = ",".join(readiness.missing_prerequisites)
            self.state.status = (
                readiness.waiting_status or WorkflowExecutionStatus.WAITING_TECH_FACTS
            )
            event_count = self.state.readiness_event_count

            def readiness_event_received(previous_count: int = event_count) -> bool:
                return self.state.readiness_event_count > previous_count

            with suppress(TimeoutError):
                await workflow.wait_condition(
                    readiness_event_received,
                    timeout=_READINESS_RECHECK_INTERVAL,
                )
