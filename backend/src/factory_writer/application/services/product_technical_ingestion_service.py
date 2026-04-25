from __future__ import annotations

import re
import uuid
from dataclasses import asdict, dataclass, replace
from time import perf_counter
from typing import Any

import structlog

from factory_writer.application.ports.product_technical_ingestion import (
    STATUS_PENDING_TECH_REVIEW,
    STATUS_TECHNICAL_FACTS_READY,
    STATUS_WAITING_COMMERCIAL_SNAPSHOT,
    STATUS_WAITING_STYLE_PACK,
    STATUS_WAITING_TECH_FACTS,
    CheckTechnicalReviewCompletionResult,
    ClassifyTechnicalSourcesResult,
    CreateProductContextSnapshotResult,
    DocumentSourceSnapshot,
    ExtractTechnicalFactCandidatesResult,
    IngestionRunSnapshot,
    LoadCanonicalProductResult,
    PersistClassificationResult,
    PersistTechnicalFactCandidatesResult,
    PrepareTechnicalIngestionResult,
    ProductContextReadiness,
    ProductContextReference,
    ProductLifecycleWorkflowPort,
    ProductSnapshot,
    ProductTaxonomySnapshot,
    ProductTechnicalRepositoryPort,
    PromotedTechnicalFactInput,
    PromotedTechnicalFactPayload,
    PromoteTechnicalFactsResult,
    TechnicalClassificationPayload,
    TechnicalDocumentEntity,
    TechnicalDocumentProcessorPort,
    TechnicalDocumentSourceReference,
    TechnicalFactCandidateInput,
    TechnicalFactCandidatePayload,
    TechnicalFactSnapshot,
    TechnicalReviewCaseInput,
    TechnicalReviewCasePayload,
    TechnicalSourceStoragePort,
    TechnicalSourcesUploaded,
    UploadedTechnicalSourceData,
    ValidateTechnicalFactsResult,
)
from factory_writer.application.services.document_storage_paths import (
    build_technical_dossier_pdf_object_name,
)
from factory_writer.core.config import Settings
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    StatutDocumentIngestionRun,
    StatutTechnicalFactCandidate,
    TechnicalReviewCaseType,
    TechnicalReviewResolutionAction,
    TechnicalReviewSeverity,
    TechnicalReviewTriggerSource,
)

logger = structlog.get_logger(__name__)

_REQUIRED_TECHNICAL_FACTS = (
    "product_name",
    "material_primary",
    "dimension_width_cm",
    "dimension_depth_cm",
    "dimension_height_cm",
    "assembly_constraints",
    "eco_certifications",
)
_DIMENSION_FIELDS = {
    "dimension_width_cm",
    "dimension_depth_cm",
    "dimension_height_cm",
}
_FIELD_ALIASES = {
    "product": "product_name",
    "product_name": "product_name",
    "nom_produit": "product_name",
    "name": "product_name",
    "material": "material_primary",
    "materials": "material_primary",
    "material_primary": "material_primary",
    "matiere": "material_primary",
    "materiau": "material_primary",
    "matiere_principale": "material_primary",
    "width": "dimension_width_cm",
    "largeur": "dimension_width_cm",
    "dimension_width": "dimension_width_cm",
    "dimension_width_cm": "dimension_width_cm",
    "depth": "dimension_depth_cm",
    "profondeur": "dimension_depth_cm",
    "dimension_depth": "dimension_depth_cm",
    "dimension_depth_cm": "dimension_depth_cm",
    "height": "dimension_height_cm",
    "hauteur": "dimension_height_cm",
    "dimension_height": "dimension_height_cm",
    "dimension_height_cm": "dimension_height_cm",
    "assembly": "assembly_constraints",
    "assembly_constraints": "assembly_constraints",
    "contrainte_assemblage": "assembly_constraints",
    "contraintes_assemblage": "assembly_constraints",
    "eco_certification": "eco_certifications",
    "eco_certifications": "eco_certifications",
    "certification": "eco_certifications",
    "certifications": "eco_certifications",
}
_DIMENSION_PATTERN = re.compile(r"(?P<number>\d+(?:[,.]\d+)?)\s*(?P<unit>mm|cm|m)?", re.I)


class ProductTechnicalIngestionService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: ProductTechnicalRepositoryPort,
        storage: TechnicalSourceStoragePort | None = None,
        workflow_starter: ProductLifecycleWorkflowPort | None = None,
        document_processor: TechnicalDocumentProcessorPort | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._storage = storage
        self._workflow_starter = workflow_starter
        self._document_processor = document_processor

    async def create_product(
        self,
        *,
        sku: str,
        name: str,
        famille_code: str,
        sous_famille_code: str | None,
        season_code: str | None,
        segment_prix_code: str | None,
        langue_principale: str,
    ) -> dict[str, Any]:
        logger.info(
            "Product | Création | demande reçue",
            sku=sku,
            name=name,
            famille_code=famille_code,
            sous_famille_code=sous_famille_code,
            season_code=season_code,
            segment_prix_code=segment_prix_code,
        )

        product = await self._repository.create_product(
            sku=sku,
            name=name,
            famille_code=famille_code,
            sous_famille_code=sous_famille_code,
            season_code=season_code,
            segment_prix_code=segment_prix_code,
            langue_principale=langue_principale,
        )

        logger.info(
            "Product | Création | produit créé en base",
            product_id=str(product.id),
            sku=product.sku,
            famille_code=product.famille_code,
            sous_famille_code=product.sous_famille_code,
            season_code=product.season_code,
            segment_prix_code=product.segment_prix_code,
        )

        workflow_id: str | None = None

        if self._workflow_starter is not None:
            logger.info(
                "Product lifecycle | démarrage du workflow demandé",
                product_id=str(product.id),
                sku=product.sku,
            )

            workflow_id = await self._workflow_starter.start_product_lifecycle(
                _product_to_context_reference(product)
            )

            logger.info(
                "Product lifecycle | workflow lancé",
                product_id=str(product.id),
                sku=product.sku,
                workflow_id=workflow_id,
            )
        else:
            logger.info(
                "Product lifecycle | workflow non démarré",
                product_id=str(product.id),
                sku=product.sku,
                reason="workflow_starter_non_configure",
            )

        return {
            "product": _product_snapshot_to_dict(product),
            "workflow_id": workflow_id,
        }

    async def list_products(self, *, limit: int = 50) -> dict[str, Any]:
        products = await self._repository.list_products(limit=limit)
        style_guide_ready = await self._is_style_guide_ready()
        commercial_signals_ready_by_product_id: dict[uuid.UUID, bool] = {}

        for product in products:
            commercial_signals_ready_by_product_id[
                product.id
            ] = await self._has_commercial_signal_snapshot(product)

        return {
            "products": [
                _product_snapshot_to_list_item(
                    product,
                    style_guide_ready=style_guide_ready,
                    commercial_signals_ready=commercial_signals_ready_by_product_id[product.id],
                )
                for product in products
            ],
        }

    async def list_product_taxonomies(self) -> dict[str, Any]:
        taxonomies = await self._repository.list_product_taxonomies()

        return {
            "taxonomies": [_product_taxonomy_to_dict(taxonomy) for taxonomy in taxonomies],
        }

    async def upload_technical_sources(
        self,
        *,
        product_id: uuid.UUID,
        files: list[tuple[str, bytes, str]],
    ) -> dict[str, Any]:
        if self._storage is None:
            raise RuntimeError("Storage client non configuré pour l'upload technique.")

        if not files:
            raise RuntimeError("Au moins un PDF technique est requis.")

        bucket_name = self._settings.gcp.technical_dossier_bucket_name

        if not bucket_name:
            raise RuntimeError("GCP technical dossier bucket non configuré.")

        uploaded_sources: list[UploadedTechnicalSourceData] = []

        for file_name, content, content_type in files:
            if len(content) > self._settings.technical_dossier.max_pdf_bytes:
                raise RuntimeError(f"PDF trop volumineux: {file_name}")

            document_source_id = uuid.uuid4()

            object_name = build_technical_dossier_pdf_object_name(
                product_id=product_id,
                document_source_id=document_source_id,
                file_name=file_name,
            )

            uploaded = await self._storage.upload_pdf_object(
                bucket_name=bucket_name,
                object_name=object_name,
                content=content,
                content_type=content_type,
            )

            uploaded_sources.append(
                UploadedTechnicalSourceData(
                    document_source_id=document_source_id,
                    original_file_name=file_name,
                    storage_uri=uploaded.storage_uri,
                    storage_bucket=uploaded.storage_bucket,
                    storage_object_name=uploaded.storage_object_name,
                    storage_generation=uploaded.generation,
                    storage_metageneration=uploaded.metageneration,
                    storage_content_type="application/pdf",
                    storage_size_bytes=len(content),
                )
            )

        sources = await self._repository.create_technical_sources(
            product_id=product_id,
            sources=uploaded_sources,
        )

        return {"sources": [_source_snapshot_to_dict(source) for source in sources]}

    async def start_technical_ingestion(self, *, product_id: uuid.UUID) -> dict[str, Any]:
        if self._workflow_starter is None:
            raise RuntimeError("Workflow starter non configuré pour l'ingestion technique.")

        preparation = await self._repository.prepare_technical_ingestion_start(
            product_id=product_id
        )

        await self._workflow_starter.signal_technical_sources_uploaded(
            preparation.product.sku,
            TechnicalSourcesUploaded(
                document_source_ids=tuple(str(source.id) for source in preparation.sources),
                ingestion_run_id=str(preparation.run.id),
                source_event_id=str(preparation.run.id),
            ),
        )

        return {
            "product": _product_snapshot_to_dict(preparation.product),
            "collection_id": str(preparation.collection_id),
            "run": _run_snapshot_to_dict(preparation.run),
            "sources": [_source_snapshot_to_dict(source) for source in preparation.sources],
            "reused_existing_run": preparation.reused_existing_run,
        }

    async def get_product_overview(self, *, product_id: uuid.UUID) -> dict[str, Any]:
        return await self._repository.get_product_overview(product_id)

    async def resolve_review_case(
        self,
        *,
        product_id: uuid.UUID,
        case_id: uuid.UUID,
        action: TechnicalReviewResolutionAction,
        resolved_by: str,
        corrected_value: str | None,
        corrected_unit: str | None,
        comment: str | None,
    ) -> dict[str, Any]:
        result = await self._repository.resolve_review_case(
            product_id=product_id,
            case_id=case_id,
            action=action,
            resolved_by=resolved_by,
            corrected_value=corrected_value,
            corrected_unit=corrected_unit,
            comment=comment,
        )

        if self._workflow_starter is not None:
            try:
                await self._workflow_starter.signal_technical_review_case_resolved(
                    ingestion_run_id=result["ingestion_run_id"],
                    case_id=str(case_id),
                )
            except RuntimeError:
                logger.info(
                    "Technical dossier | review signal ignored",
                    product_id=str(product_id),
                    case_id=str(case_id),
                    ingestion_run_id=result["ingestion_run_id"],
                )

        return result

    async def load_canonical_product(
        self,
        product: ProductContextReference,
    ) -> LoadCanonicalProductResult:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour charger le produit canonique.")

        canonical_product = await self._repository.get_product(uuid.UUID(product.product_id))

        if canonical_product is None:
            raise RuntimeError("Produit introuvable pour le workflow produit.")

        return LoadCanonicalProductResult(product=_product_to_context_reference(canonical_product))

    async def prepare_technical_ingestion_run(
        self,
        *,
        product_id: str,
        ingestion_run_id: str,
        document_source_ids: tuple[str, ...],
    ) -> PrepareTechnicalIngestionResult:
        parsed_product_id = uuid.UUID(product_id)

        source_ids = tuple(uuid.UUID(value) for value in document_source_ids)

        run_id = uuid.UUID(ingestion_run_id)

        context = await self._repository.get_technical_ingestion_context(
            product_id=parsed_product_id,
            document_source_ids=source_ids,
            ingestion_run_id=run_id,
        )

        run = context["run"]

        await self._repository.update_ingestion_run_step(
            run_id=run_id,
            current_step=CurrentStep.DOCUMENT_CLASSIFICATION,
            statut=StatutDocumentIngestionRun.EN_COURS,
        )

        return PrepareTechnicalIngestionResult(
            product=_product_to_context_reference(context["product"]),
            ingestion_run_id=str(run.id),
            collection_id=str(run.collection_id),
            sources=tuple(_source_snapshot_to_ref(source) for source in context["sources"]),
        )

    async def classify_technical_sources(
        self,
        sources: tuple[TechnicalDocumentSourceReference, ...],
    ) -> ClassifyTechnicalSourcesResult:
        if self._document_processor is None:
            raise RuntimeError("Document AI client non configuré pour l'ingestion technique.")

        classifications: list[TechnicalClassificationPayload] = []

        for source in sources:
            classification = await self._document_processor.classify_technical_document(
                input_uri=source.storage_uri,
                mime_type=source.mime_type,
            )

            classifications.append(
                TechnicalClassificationPayload(
                    document_source_id=source.document_source_id,
                    document_type=classification.document_type,
                    confidence=classification.confidence,
                    quality_metadata_json={
                        "classifier": {
                            "processor_resource_name": classification.processor_resource_name,
                            "processor_version": classification.processor_version,
                            "latency_ms": classification.latency_ms,
                            "request_config_snapshot": classification.request_config_snapshot,
                            "raw_response_summary": classification.raw_response_summary,
                        }
                    },
                    extraction_step_json={
                        "step": "classification",
                        "source_id": source.document_source_id,
                        "document_type": classification.document_type,
                        "confidence": classification.confidence,
                        "latency_ms": classification.latency_ms,
                    },
                )
            )

        return ClassifyTechnicalSourcesResult(classifications=tuple(classifications))

    async def persist_classification_results(
        self,
        *,
        ingestion_run_id: str,
        classifications: tuple[TechnicalClassificationPayload, ...],
    ) -> PersistClassificationResult:
        for classification in classifications:
            await self._repository.update_source_classification(
                source_id=uuid.UUID(classification.document_source_id),
                document_type=classification.document_type,
                confidence=classification.confidence,
                quality_metadata_json=classification.quality_metadata_json,
            )

        await self._repository.update_ingestion_run_step(
            run_id=uuid.UUID(ingestion_run_id),
            current_step=CurrentStep.FACT_EXTRACTION,
        )

        return PersistClassificationResult(classification_count=len(classifications))

    async def extract_technical_fact_candidates(
        self,
        *,
        sources: tuple[TechnicalDocumentSourceReference, ...],
        classifications: tuple[TechnicalClassificationPayload, ...],
    ) -> ExtractTechnicalFactCandidatesResult:
        if self._document_processor is None:
            raise RuntimeError("Document AI client non configuré pour l'ingestion technique.")

        classifications_by_source_id = {
            classification.document_source_id: classification for classification in classifications
        }

        total_started = perf_counter()

        extraction_steps: list[dict[str, Any]] = [
            classification.extraction_step_json for classification in classifications
        ]

        candidates: list[TechnicalFactCandidatePayload] = []

        for source in sources:
            classification = classifications_by_source_id.get(source.document_source_id)

            if classification is None:
                raise RuntimeError(
                    f"Classification manquante pour la source {source.document_source_id}."
                )

            extraction = await self._document_processor.extract_technical_facts(
                input_uri=source.storage_uri,
                document_type=classification.document_type,
                mime_type=source.mime_type,
            )

            extraction_steps.append(
                {
                    "step": "extraction",
                    "source_id": source.document_source_id,
                    "entity_count": len(extraction.entities),
                    "latency_ms": extraction.latency_ms,
                    "processor_resource_name": extraction.processor_resource_name,
                    "processor_version": extraction.processor_version,
                    "request_config_snapshot": extraction.request_config_snapshot,
                }
            )

            candidates.extend(
                _candidate_input_to_payload(
                    _entity_to_candidate_input(uuid.UUID(source.document_source_id), entity)
                )
                for entity in extraction.entities
                if _canonical_field_name(entity.field_name) is not None
            )

        total_elapsed_seconds = round(perf_counter() - total_started, 3)

        sla_status = (
            "AT_RISK"
            if total_elapsed_seconds > self._settings.technical_dossier.sla_budget_seconds
            else "OK"
        )

        if sla_status == "AT_RISK":
            logger.warning(
                "Technical dossier ingestion SLA at risk",
                elapsed_seconds=total_elapsed_seconds,
                budget_seconds=self._settings.technical_dossier.sla_budget_seconds,
            )

        return ExtractTechnicalFactCandidatesResult(
            candidates=tuple(candidates),
            extraction_steps_json={
                "steps": extraction_steps,
                "total_elapsed_seconds": total_elapsed_seconds,
                "sla_status": sla_status,
            },
        )

    async def persist_technical_fact_candidates(
        self,
        *,
        product: ProductContextReference,
        ingestion_run_id: str,
        candidates: tuple[TechnicalFactCandidatePayload, ...],
        extraction_steps_json: dict[str, Any],
    ) -> PersistTechnicalFactCandidatesResult:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour persister les facts candidats.")

        await self._repository.persist_technical_fact_candidates(
            product_id=uuid.UUID(product.product_id),
            run_id=uuid.UUID(ingestion_run_id),
            candidates=[_candidate_payload_to_input(candidate) for candidate in candidates],
            extraction_steps_json=extraction_steps_json,
        )

        return PersistTechnicalFactCandidatesResult(candidate_count=len(candidates))

    async def validate_technical_facts(
        self,
        candidates: tuple[TechnicalFactCandidatePayload, ...],
    ) -> ValidateTechnicalFactsResult:
        candidate_inputs = [_candidate_payload_to_input(candidate) for candidate in candidates]

        validation = _validate_technical_candidates(
            candidate_inputs,
            low_confidence_threshold=self._settings.technical_dossier.low_confidence_threshold,
        )

        candidate_inputs = _mark_review_candidates(candidate_inputs, validation.review_cases)

        return ValidateTechnicalFactsResult(
            candidates=tuple(
                _candidate_input_to_payload(candidate) for candidate in candidate_inputs
            ),
            review_cases=tuple(
                _review_case_input_to_payload(review_case)
                for review_case in validation.review_cases
            ),
            promoted_facts=tuple(
                _promoted_fact_input_to_payload(promoted_fact)
                for promoted_fact in validation.promoted_facts
            ),
        )

    async def promote_technical_facts(
        self,
        *,
        product: ProductContextReference,
        ingestion_run_id: str,
        candidates: tuple[TechnicalFactCandidatePayload, ...],
        review_cases: tuple[TechnicalReviewCasePayload, ...],
        promoted_facts: tuple[PromotedTechnicalFactPayload, ...],
        extraction_steps_json: dict[str, Any],
    ) -> PromoteTechnicalFactsResult:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour promouvoir les facts techniques.")

        extraction_steps_json = dict(extraction_steps_json)

        steps = list(extraction_steps_json.get("steps") or [])

        steps.append(
            {
                "step": "validation",
                "auto_validated": len(promoted_facts),
                "review_cases": len(review_cases),
            }
        )

        extraction_steps_json["steps"] = steps

        validation_summary_json = {
            "technical_validation": {
                "auto_validated": len(promoted_facts),
                "review_cases": len(review_cases),
                "required_fields": list(_REQUIRED_TECHNICAL_FACTS),
            },
            "sla_budget": {
                "target_seconds_total_future_generation": 120,
                "technical_ingestion_budget_seconds": (
                    self._settings.technical_dossier.sla_budget_seconds
                ),
                "reserved_generation_budget_seconds": 45,
                "sla_status": extraction_steps_json.get("sla_status", "OK"),
            },
        }

        await self._repository.complete_technical_ingestion(
            product_id=uuid.UUID(product.product_id),
            run_id=uuid.UUID(ingestion_run_id),
            candidates=[_candidate_payload_to_input(candidate) for candidate in candidates],
            review_cases=[
                _review_case_payload_to_input(review_case) for review_case in review_cases
            ],
            promoted_facts=[
                _promoted_fact_payload_to_input(promoted_fact) for promoted_fact in promoted_facts
            ],
            extraction_steps_json=extraction_steps_json,
            validation_summary_json=validation_summary_json,
            requires_review=bool(review_cases),
        )

        return PromoteTechnicalFactsResult(
            status=(STATUS_PENDING_TECH_REVIEW if review_cases else STATUS_TECHNICAL_FACTS_READY),
            review_case_count=len(review_cases),
            promoted_fact_count=len(promoted_facts),
        )

    async def check_technical_review_completion(
        self,
        ingestion_run_id: str,
    ) -> CheckTechnicalReviewCompletionResult:
        has_open_cases = await self._repository.has_open_technical_review_cases(
            run_id=uuid.UUID(ingestion_run_id)
        )

        return CheckTechnicalReviewCompletionResult(complete=not has_open_cases)

    async def mark_technical_ingestion_failed(
        self,
        *,
        product: ProductContextReference,
        error_message: str,
    ) -> None:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour marquer l'ingestion en erreur.")

        await self._repository.mark_technical_ingestion_failed(
            product_id=uuid.UUID(product.product_id),
            error_message=error_message,
        )

    async def check_product_context_readiness(
        self,
        *,
        product: ProductContextReference,
        technical_ingestion_run_id: str,
    ) -> ProductContextReadiness:
        product_snapshot = _payload_product_to_snapshot(product)
        _ = technical_ingestion_run_id

        missing: list[str] = []

        style_pack_id: str | None = None

        style_pack_version_label: str | None = None

        commercial_signal_snapshot_id: str | None = None

        commercial_snapshot_id: str | None = None

        commercial_cohort_key: str | None = None

        commercial_selection_reason: str | None = None

        commercial_matched_fields: dict[str, str | None] = {}

        try:
            style_pack = await self._repository.load_active_style_pack()

            style_pack_id = style_pack.style_pack_id

            style_pack_version_label = style_pack.version_label
        except RuntimeError:
            missing.append("style_pack")

        try:
            commercial_snapshot = await self._repository.select_commercial_signal_snapshot(
                product=product_snapshot
            )

            commercial_signal_snapshot_id = str(commercial_snapshot.id)

            commercial_snapshot_id = commercial_snapshot.snapshot_id

            commercial_cohort_key = commercial_snapshot.cohort_key

            commercial_selection_reason = commercial_snapshot.selection_reason

            commercial_matched_fields = commercial_snapshot.matched_fields
        except RuntimeError:
            missing.append("commercial_snapshot")

        facts = await self._repository.list_technical_facts(product_id=product_snapshot.id)

        facts_by_field = {fact.field_name: fact for fact in facts}

        if any(field_name not in facts_by_field for field_name in _REQUIRED_TECHNICAL_FACTS):
            missing.append("technical_facts")

        waiting_status = _readiness_waiting_status(missing)

        return ProductContextReadiness(
            ready=not missing,
            missing_prerequisites=tuple(missing),
            waiting_status=waiting_status,
            style_pack_id=style_pack_id,
            style_pack_version_label=style_pack_version_label,
            commercial_signal_snapshot_id=commercial_signal_snapshot_id,
            commercial_snapshot_id=commercial_snapshot_id,
            commercial_cohort_key=commercial_cohort_key,
            commercial_selection_reason=commercial_selection_reason,
            commercial_matched_fields=commercial_matched_fields,
            technical_fact_ids=tuple(str(fact.id) for fact in facts),
            technical_facts=tuple(_technical_fact_snapshot_to_dict(fact) for fact in facts),
        )

    async def create_product_context_snapshot(
        self,
        *,
        product: ProductContextReference,
        technical_ingestion_run_id: str,
        readiness: ProductContextReadiness,
    ) -> CreateProductContextSnapshotResult:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour créer le contexte produit.")

        if not readiness.ready:
            raise RuntimeError("Le contexte produit ne peut pas être figé avant readiness.")

        if (
            readiness.style_pack_id is None
            or readiness.commercial_signal_snapshot_id is None
            or not readiness.technical_fact_ids
        ):
            raise RuntimeError("Readiness incomplet pour créer le contexte produit.")

        result = await self._repository.create_product_context_snapshot(
            product_id=uuid.UUID(product.product_id),
            technical_ingestion_run_id=uuid.UUID(technical_ingestion_run_id),
            style_pack_id=uuid.UUID(readiness.style_pack_id),
            commercial_signal_snapshot_id=uuid.UUID(readiness.commercial_signal_snapshot_id),
            technical_fact_ids=tuple(uuid.UUID(value) for value in readiness.technical_fact_ids),
            snapshot_json={
                "product": asdict(product),
                "style_pack": {
                    "style_pack_id": readiness.style_pack_id,
                    "version_label": readiness.style_pack_version_label,
                },
                "commercial_signal_snapshot": {
                    "id": readiness.commercial_signal_snapshot_id,
                    "snapshot_id": readiness.commercial_snapshot_id,
                    "cohort_key": readiness.commercial_cohort_key,
                    "selection_reason": readiness.commercial_selection_reason,
                    "matched_fields": readiness.commercial_matched_fields,
                },
                "technical_facts": list(readiness.technical_facts),
            },
        )

        return CreateProductContextSnapshotResult(product_context_snapshot_id=str(result.id))

    async def notify_style_pack_activated(self, *, style_pack_id: uuid.UUID) -> int:
        if self._workflow_starter is None:
            return 0

        products = await self._repository.list_products_for_style_pack_activation()

        notified = 0

        for product in products:
            try:
                await self._workflow_starter.signal_style_pack_activated(
                    sku=product.sku,
                    style_pack_id=str(style_pack_id),
                )

                notified += 1
            except RuntimeError:
                logger.info(
                    "Product lifecycle | style pack activation signal ignored",
                    sku=product.sku,
                    style_pack_id=str(style_pack_id),
                )

        return notified

    async def _is_style_guide_ready(self) -> bool:
        try:
            await self._repository.load_active_style_pack()
        except RuntimeError:
            return False

        return True

    async def _has_commercial_signal_snapshot(self, product: ProductSnapshot) -> bool:
        try:
            await self._repository.select_commercial_signal_snapshot(product=product)
        except RuntimeError:
            return False

        return True


@dataclass(frozen=True)
class _ValidationResult:
    review_cases: list[TechnicalReviewCaseInput]
    promoted_facts: list[PromotedTechnicalFactInput]


def _validate_technical_candidates(
    candidates: list[TechnicalFactCandidateInput],
    *,
    low_confidence_threshold: float,
) -> _ValidationResult:
    review_cases: list[TechnicalReviewCaseInput] = []

    promoted_facts: list[PromotedTechnicalFactInput] = []

    by_field: dict[str, list[tuple[int, TechnicalFactCandidateInput]]] = {}

    for index, candidate in enumerate(candidates):
        by_field.setdefault(candidate.field_name, []).append((index, candidate))

    for field_name in _REQUIRED_TECHNICAL_FACTS:
        field_candidates = by_field.get(field_name, [])

        if not field_candidates:
            review_cases.append(
                TechnicalReviewCaseInput(
                    source_id=None,
                    candidate_index=None,
                    case_type=TechnicalReviewCaseType.MISSING_REQUIRED_FIELD,
                    trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
                    severity=TechnicalReviewSeverity.BLOCKING,
                    field_name=field_name,
                    title=f"Champ requis manquant: {field_name}",
                    description=f"Aucune preuve exploitable trouvée pour {field_name}.",
                )
            )
            continue

        valid_candidates: list[tuple[int, TechnicalFactCandidateInput]] = []

        for index, candidate in field_candidates:
            review = _candidate_review_case(index, candidate, low_confidence_threshold)

            if review is not None:
                review_cases.append(review)

                continue

            valid_candidates.append((index, candidate))

        distinct_values = {
            _normalize_comparable_value(candidate.normalized_value or candidate.raw_value)
            for _, candidate in valid_candidates
            if _normalize_comparable_value(candidate.normalized_value or candidate.raw_value)
        }

        if len(distinct_values) > 1:
            first_index, first_candidate = valid_candidates[0]

            review_cases.append(
                TechnicalReviewCaseInput(
                    source_id=first_candidate.source_id,
                    candidate_index=first_index,
                    case_type=TechnicalReviewCaseType.CONTRADICTION,
                    trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
                    severity=TechnicalReviewSeverity.BLOCKING,
                    field_name=field_name,
                    title=f"Contradiction détectée sur {field_name}",
                    description="Plusieurs valeurs incompatibles ont été extraites.",
                    detected_value=", ".join(sorted(distinct_values)),
                    metadata_json={"distinct_values": sorted(distinct_values)},
                )
            )

            continue

        if valid_candidates:
            selected_index, selected = max(
                valid_candidates,
                key=lambda item: item[1].extractor_confidence or 0.0,
            )

            value = selected.normalized_value or selected.raw_value

            if value:
                promoted_facts.append(
                    PromotedTechnicalFactInput(
                        candidate_index=selected_index,
                        field_name=field_name,
                        value=value,
                        unit=selected.unit,
                    )
                )

    return _ValidationResult(review_cases=review_cases, promoted_facts=promoted_facts)


def _mark_review_candidates(
    candidates: list[TechnicalFactCandidateInput],
    review_cases: list[TechnicalReviewCaseInput],
) -> list[TechnicalFactCandidateInput]:
    review_indexes = {
        review_case.candidate_index
        for review_case in review_cases
        if review_case.candidate_index is not None
    }

    return [
        replace(
            candidate,
            validation_status=StatutTechnicalFactCandidate.NEEDS_REVIEW,
            review_required=True,
            review_reason="deterministic_validation_failed",
        )
        if index in review_indexes
        else candidate
        for index, candidate in enumerate(candidates)
    ]


def _candidate_review_case(
    index: int,
    candidate: TechnicalFactCandidateInput,
    low_confidence_threshold: float,
) -> TechnicalReviewCaseInput | None:
    if not candidate.source_evidence_text:
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.EXACT_MATCH_FAILED,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Preuve source manquante pour {candidate.field_name}",
            description="Chaque fact critique doit être rattaché à une preuve source.",
            detected_value=candidate.raw_value,
            detected_unit=candidate.unit,
        )

    if (
        candidate.extractor_confidence is not None
        and candidate.extractor_confidence < low_confidence_threshold
    ):
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.LOW_CONFIDENCE,
            trigger_source=TechnicalReviewTriggerSource.CUSTOM_EXTRACTOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Confiance faible pour {candidate.field_name}",
            description="Le modèle a extrait une valeur sous le seuil de confiance.",
            detected_value=candidate.raw_value,
            detected_unit=candidate.unit,
            metadata_json={"extractor_confidence": candidate.extractor_confidence},
        )

    if candidate.field_name in _DIMENSION_FIELDS and (
        candidate.normalized_value is None or candidate.unit != "cm"
    ):
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Dimension non convertible en cm: {candidate.field_name}",
            description="La dimension critique doit être convertible en centimètres.",
            detected_value=candidate.raw_value,
            detected_unit=candidate.unit,
        )

    if candidate.field_name == "material_primary" and not candidate.normalized_value:
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.MISSING_REQUIRED_FIELD,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title="Matière principale vide",
            description="La matière principale doit être non vide et sourcée.",
        )

    return None


def _entity_to_candidate_input(
    source_id: uuid.UUID,
    entity: TechnicalDocumentEntity,
) -> TechnicalFactCandidateInput:
    field_name = _canonical_field_name(entity.field_name)

    if field_name is None:
        raise RuntimeError(f"Champ technique non reconnu: {entity.field_name}")

    normalized_value, unit = _normalize_candidate_value(field_name, entity)

    review_required = normalized_value is None and field_name in _REQUIRED_TECHNICAL_FACTS

    return TechnicalFactCandidateInput(
        source_id=source_id,
        field_name=field_name,
        raw_value=entity.raw_value,
        normalized_value=normalized_value,
        unit=unit,
        extractor_confidence=entity.confidence,
        validation_status=(
            StatutTechnicalFactCandidate.NEEDS_REVIEW
            if review_required
            else StatutTechnicalFactCandidate.AUTO_VALIDATED
        ),
        review_required=review_required,
        review_reason="normalized_value_missing" if review_required else None,
        source_evidence_text=entity.evidence_text,
        source_page=entity.page,
        source_bbox_json=entity.bbox_json,
        raw_entity_json=entity.raw_entity_json,
    )


def _normalize_candidate_value(
    field_name: str,
    entity: TechnicalDocumentEntity,
) -> tuple[str | None, str | None]:
    raw_value = entity.normalized_value or entity.raw_value

    if not raw_value:
        return None, entity.unit

    if field_name in _DIMENSION_FIELDS:
        return _normalize_dimension_cm(raw_value)

    return " ".join(raw_value.split()), entity.unit


def _normalize_dimension_cm(value: str) -> tuple[str | None, str | None]:
    match = _DIMENSION_PATTERN.search(value)

    if match is None:
        return None, None

    number = float(match.group("number").replace(",", "."))

    unit = (match.group("unit") or "cm").lower()

    if unit == "mm":
        number = number / 10
    elif unit == "m":
        number = number * 100

    normalized = f"{number:.2f}".rstrip("0").rstrip(".")

    return normalized, "cm"


def _canonical_field_name(value: str) -> str | None:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")

    return _FIELD_ALIASES.get(normalized)


def _normalize_comparable_value(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _source_snapshot_to_ref(source: DocumentSourceSnapshot) -> TechnicalDocumentSourceReference:
    return TechnicalDocumentSourceReference(
        document_source_id=str(source.id),
        storage_uri=source.storage_uri,
        mime_type=source.storage_content_type,
    )


def _candidate_input_to_payload(
    candidate: TechnicalFactCandidateInput,
) -> TechnicalFactCandidatePayload:
    return TechnicalFactCandidatePayload(
        source_id=str(candidate.source_id),
        field_name=candidate.field_name,
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        unit=candidate.unit,
        extractor_confidence=candidate.extractor_confidence,
        validation_status=candidate.validation_status.value,
        review_required=candidate.review_required,
        review_reason=candidate.review_reason,
        source_evidence_text=candidate.source_evidence_text,
        source_page=candidate.source_page,
        source_bbox_json=candidate.source_bbox_json,
        raw_entity_json=candidate.raw_entity_json,
    )


def _candidate_payload_to_input(
    candidate: TechnicalFactCandidatePayload,
) -> TechnicalFactCandidateInput:
    return TechnicalFactCandidateInput(
        source_id=uuid.UUID(candidate.source_id),
        field_name=candidate.field_name,
        raw_value=candidate.raw_value,
        normalized_value=candidate.normalized_value,
        unit=candidate.unit,
        extractor_confidence=candidate.extractor_confidence,
        validation_status=StatutTechnicalFactCandidate(candidate.validation_status),
        review_required=candidate.review_required,
        review_reason=candidate.review_reason,
        source_evidence_text=candidate.source_evidence_text,
        source_page=candidate.source_page,
        source_bbox_json=candidate.source_bbox_json,
        raw_entity_json=candidate.raw_entity_json,
    )


def _review_case_input_to_payload(
    review_case: TechnicalReviewCaseInput,
) -> TechnicalReviewCasePayload:
    return TechnicalReviewCasePayload(
        source_id=str(review_case.source_id) if review_case.source_id is not None else None,
        candidate_index=review_case.candidate_index,
        case_type=review_case.case_type.value,
        trigger_source=review_case.trigger_source.value,
        severity=review_case.severity.value,
        field_name=review_case.field_name,
        title=review_case.title,
        description=review_case.description,
        detected_value=review_case.detected_value,
        detected_unit=review_case.detected_unit,
        suggested_value=review_case.suggested_value,
        suggested_unit=review_case.suggested_unit,
        metadata_json=review_case.metadata_json,
    )


def _review_case_payload_to_input(
    review_case: TechnicalReviewCasePayload,
) -> TechnicalReviewCaseInput:
    return TechnicalReviewCaseInput(
        source_id=uuid.UUID(review_case.source_id) if review_case.source_id is not None else None,
        candidate_index=review_case.candidate_index,
        case_type=TechnicalReviewCaseType(review_case.case_type),
        trigger_source=TechnicalReviewTriggerSource(review_case.trigger_source),
        severity=TechnicalReviewSeverity(review_case.severity),
        field_name=review_case.field_name,
        title=review_case.title,
        description=review_case.description,
        detected_value=review_case.detected_value,
        detected_unit=review_case.detected_unit,
        suggested_value=review_case.suggested_value,
        suggested_unit=review_case.suggested_unit,
        metadata_json=review_case.metadata_json,
    )


def _promoted_fact_input_to_payload(
    promoted_fact: PromotedTechnicalFactInput,
) -> PromotedTechnicalFactPayload:
    return PromotedTechnicalFactPayload(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _promoted_fact_payload_to_input(
    promoted_fact: PromotedTechnicalFactPayload,
) -> PromotedTechnicalFactInput:
    return PromotedTechnicalFactInput(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _technical_fact_snapshot_to_dict(fact: TechnicalFactSnapshot) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "field_name": fact.field_name,
        "value": fact.value,
        "unit": fact.unit,
    }


def _readiness_waiting_status(missing: list[str]) -> str | None:
    if "technical_facts" in missing:
        return STATUS_WAITING_TECH_FACTS

    if "style_pack" in missing:
        return STATUS_WAITING_STYLE_PACK

    if "commercial_snapshot" in missing:
        return STATUS_WAITING_COMMERCIAL_SNAPSHOT

    return None


def _payload_product_to_snapshot(product: ProductContextReference) -> ProductSnapshot:
    if product.product_id is None:
        raise RuntimeError("product_id est requis pour charger le snapshot commercial.")

    return ProductSnapshot(
        id=uuid.UUID(product.product_id),
        sku=product.sku,
        name=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code,
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _product_to_context_reference(product: ProductSnapshot) -> ProductContextReference:
    return ProductContextReference(
        product_id=str(product.id),
        sku=product.sku,
        famille_code=product.famille_code,
        sous_famille_code=product.sous_famille_code or "",
        season_code=product.season_code,
        segment_prix_code=product.segment_prix_code,
        langue_principale=product.langue_principale,
    )


def _product_snapshot_to_dict(product: ProductSnapshot) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "famille_code": product.famille_code,
        "sous_famille_code": product.sous_famille_code,
        "season_code": product.season_code,
        "segment_prix_code": product.segment_prix_code,
        "langue_principale": product.langue_principale,
    }


def _product_snapshot_to_list_item(
    product: ProductSnapshot,
    *,
    style_guide_ready: bool,
    commercial_signals_ready: bool,
) -> dict[str, Any]:
    return {
        "id": str(product.id),
        "sku": product.sku,
        "name": product.name,
        "familleCode": product.famille_code,
        "sousFamilleCode": product.sous_famille_code,
        "seasonCode": product.season_code,
        "segmentPrixCode": product.segment_prix_code,
        "languePrincipale": product.langue_principale,
        "readinessStatus": "PRODUCT_CREATED",
        "styleGuideReady": style_guide_ready,
        "commercialSignalsReady": commercial_signals_ready,
        "createdAt": product.created_at.isoformat() if product.created_at is not None else None,
    }


def _product_taxonomy_to_dict(taxonomy: ProductTaxonomySnapshot) -> dict[str, Any]:
    return {
        "id": str(taxonomy.id),
        "code": taxonomy.code,
        "libelleFr": taxonomy.libelle_fr,
        "parentId": str(taxonomy.parent_id) if taxonomy.parent_id is not None else None,
    }


def _source_snapshot_to_dict(source: DocumentSourceSnapshot) -> dict[str, Any]:
    payload = asdict(source)

    return {
        key: str(value) if isinstance(value, uuid.UUID) else value for key, value in payload.items()
    }


def _run_snapshot_to_dict(run: IngestionRunSnapshot) -> dict[str, Any]:
    payload = asdict(run)

    return {
        key: str(value) if isinstance(value, uuid.UUID) else value for key, value in payload.items()
    }
