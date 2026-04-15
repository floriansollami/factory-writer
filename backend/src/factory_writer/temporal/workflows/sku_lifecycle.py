from __future__ import annotations

import asyncio

from temporalio import workflow

from factory_writer.domain.temporal_models import (
    ContextSnapshot,
    GenerationStepInput,
    ProductContextRef,
    PromptPackageLoadInput,
    PublicationDecision,
    PublishContentInput,
    PublishGateInput,
    SignalSnapshotLoadInput,
    SkuLifecycleInput,
    SkuLifecycleOutput,
    SkuLifecycleState,
    StylePackLoadInput,
    TechnicalArchiveSignalInput,
    TechnicalFactsExtractionInput,
    WorkflowExecutionStatus,
)
from factory_writer.temporal.activity_options import (
    DB_RETRY_POLICY,
    DOC_AI_RETRY_POLICY,
    LLM_RETRY_POLICY,
    LONG_ACTIVITY_TIMEOUT,
    MEDIUM_ACTIVITY_TIMEOUT,
    SHORT_ACTIVITY_TIMEOUT,
)
from factory_writer.temporal.task_queues import TaskQueue

with workflow.unsafe.imports_passed_through():
    from factory_writer.temporal.activities.context_activities import (
        evaluate_publish_gate_activity,
        load_prompt_package_active_activity,
        load_signal_snapshot_activity,
        load_style_pack_active_activity,
        publish_generated_content_activity,
    )
    from factory_writer.temporal.activities.docai_activities import (
        extract_archive_and_facts_activity,
    )
    from factory_writer.temporal.activities.llm_generation_activities import (
        generate_claim_plan_activity,
        generate_final_draft_activity,
        generate_redaction_plan_activity,
        review_and_rewrite_activity,
    )


@workflow.defn(name="SkuLifecycleWorkflow")
class SkuLifecycleWorkflow:
    def __init__(self) -> None:
        self.state = SkuLifecycleState()
        self.product: ProductContextRef | None = None
        self.archive_signal: TechnicalArchiveSignalInput | None = None

    @workflow.signal
    def technical_archive_received(self, payload: TechnicalArchiveSignalInput) -> None:
        self.archive_signal = payload
        self.state.technical_archive_received = True
        self.state.technical_archive_uri = payload.archive_uri

    @workflow.query
    def get_state(self) -> SkuLifecycleState:
        return self.state

    @workflow.run
    async def run(self, payload: SkuLifecycleInput) -> SkuLifecycleOutput:
        self.product = payload.product
        if payload.resume_state is not None:
            self.state = payload.resume_state

        workflow.logger.info("SkuLifecycleWorkflow.started", sku=payload.product.sku)

        self.state.status = WorkflowExecutionStatus.WAITING_FOR_TECHNICAL_ARCHIVE
        await workflow.wait_condition(lambda: self.archive_signal is not None)
        archive_signal = self.archive_signal
        assert archive_signal is not None

        if workflow.info().is_continue_as_new_suggested():
            workflow.continue_as_new(
                SkuLifecycleInput(product=payload.product, resume_state=self.state)
            )

        self.state.status = WorkflowExecutionStatus.EXTRACTING_FACTS
        facts_result = await workflow.execute_activity(
            extract_archive_and_facts_activity,
            TechnicalFactsExtractionInput(
                product=payload.product,
                archive_signal=archive_signal,
            ),
            task_queue=TaskQueue.DOCAI_ACTIVITIES.value,
            start_to_close_timeout=LONG_ACTIVITY_TIMEOUT,
            retry_policy=DOC_AI_RETRY_POLICY,
        )
        self.state.facts_snapshot_id = facts_result.facts_snapshot_id

        self.state.status = WorkflowExecutionStatus.BUILDING_CONTEXT
        signal_task = workflow.execute_activity(
            load_signal_snapshot_activity,
            SignalSnapshotLoadInput(product=payload.product),
            task_queue=TaskQueue.SKU_LIFECYCLE.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )
        style_task = workflow.execute_activity(
            load_style_pack_active_activity,
            StylePackLoadInput(product=payload.product),
            task_queue=TaskQueue.SKU_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )
        prompt_task = workflow.execute_activity(
            load_prompt_package_active_activity,
            PromptPackageLoadInput(product=payload.product),
            task_queue=TaskQueue.SKU_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )

        signal_snapshot, style_pack, prompt_package = await asyncio.gather(
            signal_task,
            style_task,
            prompt_task,
        )
        self.state.signal_snapshot_id = signal_snapshot.signal_snapshot_id
        self.state.style_pack_id = style_pack.style_pack_id
        self.state.prompt_package_id = prompt_package.prompt_package_id

        context_snapshot = ContextSnapshot(
            product=payload.product,
            facts=facts_result,
            signals=signal_snapshot,
            style_pack=style_pack,
            prompt_package=prompt_package,
        )

        self.state.status = WorkflowExecutionStatus.GENERATING_COPY
        claim_plan = await workflow.execute_activity(
            generate_claim_plan_activity,
            GenerationStepInput(context_snapshot=context_snapshot),
            task_queue=TaskQueue.LLM_GENERATION.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=LLM_RETRY_POLICY,
        )
        redaction_plan = await workflow.execute_activity(
            generate_redaction_plan_activity,
            GenerationStepInput(
                context_snapshot=context_snapshot,
                upstream_artifact_id=claim_plan.artifact_id,
            ),
            task_queue=TaskQueue.LLM_GENERATION.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=LLM_RETRY_POLICY,
        )
        final_draft = await workflow.execute_activity(
            generate_final_draft_activity,
            GenerationStepInput(
                context_snapshot=context_snapshot,
                upstream_artifact_id=redaction_plan.artifact_id,
            ),
            task_queue=TaskQueue.LLM_GENERATION.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=LLM_RETRY_POLICY,
        )
        review_artifact = await workflow.execute_activity(
            review_and_rewrite_activity,
            GenerationStepInput(
                context_snapshot=context_snapshot,
                upstream_artifact_id=final_draft.artifact_id,
            ),
            task_queue=TaskQueue.LLM_GENERATION.value,
            start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
            retry_policy=LLM_RETRY_POLICY,
        )

        publish_gate = await workflow.execute_activity(
            evaluate_publish_gate_activity,
            PublishGateInput(
                context_snapshot=context_snapshot,
                review_artifact=review_artifact,
            ),
            task_queue=TaskQueue.SKU_LIFECYCLE.value,
            start_to_close_timeout=SHORT_ACTIVITY_TIMEOUT,
            retry_policy=DB_RETRY_POLICY,
        )
        self.state.publication_decision = publish_gate.decision

        if publish_gate.decision == PublicationDecision.READY_TO_PUBLISH:
            publish_result = await workflow.execute_activity(
                publish_generated_content_activity,
                PublishContentInput(
                    context_snapshot=context_snapshot,
                    review_artifact=review_artifact,
                ),
                task_queue=TaskQueue.SKU_LIFECYCLE.value,
                start_to_close_timeout=MEDIUM_ACTIVITY_TIMEOUT,
                retry_policy=DB_RETRY_POLICY,
            )
            self.state.status = WorkflowExecutionStatus.PUBLISHED
            self.state.published_content_id = publish_result.published_content_id
            return SkuLifecycleOutput(
                status=self.state.status,
                publication_decision=publish_gate.decision,
                published_content_id=publish_result.published_content_id,
            )

        self.state.status = WorkflowExecutionStatus.PENDING_EDITOR_REVIEW
        return SkuLifecycleOutput(
            status=self.state.status,
            publication_decision=publish_gate.decision,
            published_content_id=None,
        )
