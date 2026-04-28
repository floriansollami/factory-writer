from __future__ import annotations

import structlog
from temporalio import activity

from factory_writer.application.ports.product_technical_ingestion import (
    ProductContextReadiness,
    ProductContextReference,
)
from factory_writer.application.services.product_technical_ingestion_service import (
    ProductTechnicalIngestionService,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.sku_lifecycle.contracts import (
    ContextReadinessCheckInput,
    CreateProductContextSnapshotInput,
    LoadCanonicalProductInput,
    LoadCanonicalProductResult,
    ProductContextReadinessResult,
    ProductContextRef,
    ProductContextSnapshotResult,
)

logger = structlog.get_logger(__name__)


class ProductLifecycleActivities:
    def __init__(self, service: ProductTechnicalIngestionService) -> None:
        self._service = service

    @activity.defn
    async def load_canonical_product(
        self,
        payload: LoadCanonicalProductInput,
    ) -> LoadCanonicalProductResult:
        logger.info(
            "Product lifecycle | canonical product loading",
            product_id=payload.product.product_id,
            sku=payload.product.sku,
        )

        result = await self._service.load_canonical_product(_to_app_product_ref(payload.product))

        return LoadCanonicalProductResult(product=_to_temporal_product_ref(result.product))

    @activity.defn
    async def check_product_context_readiness(
        self,
        payload: ContextReadinessCheckInput,
    ) -> ProductContextReadinessResult:
        logger.info(
            "Product lifecycle | context readiness check",
            product_id=payload.product.product_id,
            sku=payload.product.sku,
            technical_ingestion_run_id=payload.technical_ingestion_run_id,
        )
        readiness = await self._service.check_product_context_readiness(
            product=_to_app_product_ref(payload.product),
            technical_ingestion_run_id=payload.technical_ingestion_run_id,
        )
        return _to_temporal_readiness(readiness)

    @activity.defn
    async def create_product_context_snapshot(
        self,
        payload: CreateProductContextSnapshotInput,
    ) -> ProductContextSnapshotResult:
        logger.info(
            "Product lifecycle | context snapshot creation",
            product_id=payload.product.product_id,
            sku=payload.product.sku,
            technical_ingestion_run_id=payload.technical_ingestion_run_id,
        )
        result = await self._service.create_product_context_snapshot(
            product=_to_app_product_ref(payload.product),
            technical_ingestion_run_id=payload.technical_ingestion_run_id,
            readiness=_to_app_readiness(payload.readiness),
        )
        return ProductContextSnapshotResult(
            product_context_snapshot_id=result.product_context_snapshot_id
        )


def _to_app_product_ref(product: ProductContextRef) -> ProductContextReference:
    return ProductContextReference(
        product_id=product.product_id,
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _to_temporal_product_ref(product: ProductContextReference) -> ProductContextRef:
    return ProductContextRef(
        product_id=product.product_id,
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _to_temporal_readiness(readiness: ProductContextReadiness) -> ProductContextReadinessResult:
    return ProductContextReadinessResult(
        ready=readiness.ready,
        missing_prerequisites=readiness.missing_prerequisites,
        waiting_status=_to_temporal_workflow_status(readiness.waiting_status),
        style_pack_id=readiness.style_pack_id,
        style_pack_version_label=readiness.style_pack_version_label,
        commercial_signal_snapshot_id=readiness.commercial_signal_snapshot_id,
        commercial_snapshot_id=readiness.commercial_snapshot_id,
        commercial_cohort_key=readiness.commercial_cohort_key,
        commercial_selection_reason=readiness.commercial_selection_reason,
        commercial_matched_fields=readiness.commercial_matched_fields,
        technical_fact_ids=readiness.technical_fact_ids,
        technical_facts=readiness.technical_facts,
        product_sheet_readiness=readiness.product_sheet_readiness,
    )


def _to_temporal_workflow_status(value: str | None) -> WorkflowExecutionStatus | None:
    if value is None:
        return None

    try:
        return WorkflowExecutionStatus(value)
    except ValueError:
        normalized = value.lower()

    return WorkflowExecutionStatus(normalized)


def _to_app_readiness(readiness: ProductContextReadinessResult) -> ProductContextReadiness:
    return ProductContextReadiness(
        ready=readiness.ready,
        missing_prerequisites=readiness.missing_prerequisites,
        waiting_status=readiness.waiting_status.value if readiness.waiting_status else None,
        style_pack_id=readiness.style_pack_id,
        style_pack_version_label=readiness.style_pack_version_label,
        commercial_signal_snapshot_id=readiness.commercial_signal_snapshot_id,
        commercial_snapshot_id=readiness.commercial_snapshot_id,
        commercial_cohort_key=readiness.commercial_cohort_key,
        commercial_selection_reason=readiness.commercial_selection_reason,
        commercial_matched_fields=readiness.commercial_matched_fields,
        technical_fact_ids=readiness.technical_fact_ids,
        technical_facts=readiness.technical_facts,
        product_sheet_readiness=readiness.product_sheet_readiness,
    )
