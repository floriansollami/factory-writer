from __future__ import annotations

from temporalio import workflow

from factory_writer.temporal.common.config import (
    DB_RETRY_POLICY,
    LLM_RETRY_POLICY,
    LONG_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
    TaskQueue,
)
from factory_writer.temporal.common.contracts import WorkflowExecutionStatus
from factory_writer.temporal.product_sheet_generation.contracts import (
    GenerateProductSheetCandidateInput,
    MarkProductSheetGenerationFailedInput,
    PersistProductSheetGenerationInput,
    ProductSheetGenerationInput,
    ProductSheetGenerationOutput,
)

with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.product_sheet_generation.activities import (
        ProductSheetGenerationActivities,
    )


@workflow.defn(name="ProductSheetGenerationWorkflow")
class ProductSheetGenerationWorkflow:
    @workflow.run
    async def run(
        self,
        payload: ProductSheetGenerationInput,
    ) -> ProductSheetGenerationOutput:
        workflow.logger.info(
            "Product sheet | workflow démarré | "
            f"product_id={payload.product_id} generation_id={payload.generation_id}"
        )
        try:
            generation_result = await workflow.execute_activity_method(
                ProductSheetGenerationActivities.generate_product_sheet_candidate,
                GenerateProductSheetCandidateInput(generation_id=payload.generation_id),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
                retry_policy=LLM_RETRY_POLICY,
            )
            persisted = await workflow.execute_activity_method(
                ProductSheetGenerationActivities.persist_product_sheet_generation_result,
                PersistProductSheetGenerationInput(
                    generation_id=payload.generation_id,
                    generation_result=generation_result.model_dump(mode="json"),
                ),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            status = persisted.generation.get("status")
            workflow_status = (
                WorkflowExecutionStatus.PENDING_EDITOR_REVIEW
                if status == "A_VALIDER"
                else WorkflowExecutionStatus.PRODUCT_SHEET_READY
            )
            return ProductSheetGenerationOutput(
                status=workflow_status,
                generation_id=payload.generation_id,
            )
        except Exception as exc:
            await workflow.execute_activity_method(
                ProductSheetGenerationActivities.mark_product_sheet_generation_failed,
                MarkProductSheetGenerationFailedInput(
                    generation_id=payload.generation_id,
                    error_message=str(exc),
                ),
                task_queue=TaskQueue.PRODUCT_LIFECYCLE.value,
                start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            raise
