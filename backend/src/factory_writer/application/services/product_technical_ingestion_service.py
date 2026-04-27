from __future__ import annotations

import uuid
from dataclasses import asdict
from time import perf_counter
from typing import Any

import structlog

from factory_writer.application.ports.product_technical_ingestion import (
    STATUS_PENDING_TECH_REVIEW,
    STATUS_TECHNICAL_FACTS_READY,
    ClassifyTechnicalSourcesResult,
    CreateProductContextSnapshotResult,
    ExtractTechnicalFactCandidatesResult,
    FinalizeTechnicalReviewResult,
    LoadCanonicalProductResult,
    PersistClassificationResult,
    PersistTechnicalFactCandidatesResult,
    PrepareTechnicalIngestionResult,
    ProductContextReadiness,
    ProductContextReference,
    ProductLifecycleWorkflowPort,
    ProductSnapshot,
    ProductTechnicalRepositoryPort,
    PromotedTechnicalFactPayload,
    PromoteTechnicalFactsResult,
    TechnicalClassificationPayload,
    TechnicalDocumentProcessorPort,
    TechnicalDocumentSourceReference,
    TechnicalExtractorRouterPort,
    TechnicalFactCandidateInput,
    TechnicalFactCandidatePayload,
    TechnicalReviewCasePayload,
    TechnicalSourceStoragePort,
    TechnicalSourcesUploaded,
    UploadedTechnicalSourceData,
    ValidateTechnicalFactsResult,
)
from factory_writer.application.services.document_storage_paths import (
    build_technical_dossier_pdf_object_name,
)
from factory_writer.application.services.product_sheet_requirement_profile import (
    ProductSheetRequirementProfile as _ProductSheetRequirementProfile,
)
from factory_writer.application.services.product_sheet_requirement_profile import (
    parse_product_sheet_requirement_profile as _parse_product_sheet_requirement_profile,
)
from factory_writer.application.services.product_technical_ingestion_mappers import (
    _candidate_input_to_payload,
    _candidate_payload_to_input,
    _payload_product_to_snapshot,
    _product_readiness_status_from_overview,
    _product_snapshot_to_dict,
    _product_snapshot_to_list_item,
    _product_taxonomy_to_dict,
    _product_to_context_reference,
    _promoted_fact_input_to_payload,
    _promoted_fact_payload_to_input,
    _readiness_waiting_status,
    _review_case_input_to_payload,
    _review_case_payload_to_input,
    _run_snapshot_to_dict,
    _source_snapshot_to_dict,
    _source_snapshot_to_ref,
    _technical_fact_snapshot_to_dict,
)
from factory_writer.application.services.technical_classification_validation import (
    classification_review_cases as _classification_review_cases,
)
from factory_writer.application.services.technical_extractor_router import (
    ConfiguredTechnicalExtractorRouter,
)
from factory_writer.application.services.technical_fact_normalization import (
    entity_to_raw_candidate_input as _entity_to_raw_candidate_input,
)
from factory_writer.application.services.technical_fact_validation import (
    _mark_review_candidates,
    _validate_technical_candidates,
    _ValidationResult,
)
from factory_writer.core.config import Settings
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    StatutDocumentIngestionRun,
    TechnicalReviewResolutionAction,
)

logger = structlog.get_logger(__name__)


class ProductTechnicalIngestionService:
    def __init__(
        self,
        *,
        settings: Settings,
        repository: ProductTechnicalRepositoryPort,
        storage: TechnicalSourceStoragePort | None = None,
        workflow_starter: ProductLifecycleWorkflowPort | None = None,
        document_processor: TechnicalDocumentProcessorPort | None = None,
        extractor_router: TechnicalExtractorRouterPort | None = None,
    ) -> None:
        self._settings = settings
        self._repository = repository
        self._storage = storage
        self._workflow_starter = workflow_starter
        self._document_processor = document_processor
        self._extractor_router = extractor_router or ConfiguredTechnicalExtractorRouter(settings)

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
        readiness_status_by_product_id: dict[uuid.UUID, str] = {}

        for product in products:
            commercial_signals_ready_by_product_id[
                product.id
            ] = await self._has_commercial_signal_snapshot(product)
            readiness_status_by_product_id[product.id] = _product_readiness_status_from_overview(
                await self._repository.get_product_overview(product.id)
            )

        return {
            "products": [
                _product_snapshot_to_list_item(
                    product,
                    readiness_status=readiness_status_by_product_id[product.id],
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
        uploaded_sources = await self._upload_technical_source_files(
            product_id=product_id,
            files=files,
        )

        sources = await self._repository.create_technical_sources(
            product_id=product_id,
            sources=uploaded_sources,
        )

        return {"sources": [_source_snapshot_to_dict(source) for source in sources]}

    async def replace_technical_sources_lot(
        self,
        *,
        product_id: uuid.UUID,
        files: list[tuple[str, bytes, str]],
    ) -> dict[str, Any]:
        if self._workflow_starter is None:
            raise RuntimeError("Workflow starter non configuré pour l'ingestion technique.")

        uploaded_sources = await self._upload_technical_source_files(
            product_id=product_id,
            files=files,
        )

        replacement = await self._repository.replace_technical_sources_lot(
            product_id=product_id,
            sources=uploaded_sources,
        )

        if replacement.replaced_ingestion_run_id is not None:
            await self._workflow_starter.terminate_technical_dossier_ingestion(
                ingestion_run_id=str(replacement.replaced_ingestion_run_id),
                reason="Lot technique remplacé par un nouvel import.",
            )

        preparation = await self._repository.prepare_technical_ingestion_start(
            product_id=product_id
        )
        workflow_id = await self._workflow_starter.start_technical_dossier_ingestion(
            _product_to_context_reference(preparation.product),
            TechnicalSourcesUploaded(
                document_source_ids=tuple(str(source.id) for source in preparation.sources),
                ingestion_run_id=str(preparation.run.id),
                source_event_id=str(preparation.run.id),
            ),
        )

        logger.info(
            "Technical dossier | Remplacement du lot | analyse relancée",
            product_id=str(product_id),
            collection_id=str(preparation.collection_id),
            ingestion_run_id=str(preparation.run.id),
            workflow_id=workflow_id,
            source_count=len(preparation.sources),
        )

        return {
            "product": _product_snapshot_to_dict(preparation.product),
            "collection_id": str(preparation.collection_id),
            "run": _run_snapshot_to_dict(preparation.run),
            "sources": [_source_snapshot_to_dict(source) for source in preparation.sources],
            "reused_existing_run": preparation.reused_existing_run,
        }

    async def _upload_technical_source_files(
        self,
        *,
        product_id: uuid.UUID,
        files: list[tuple[str, bytes, str]],
    ) -> list[UploadedTechnicalSourceData]:
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

        return uploaded_sources

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
        selected_candidate_id: uuid.UUID | None = None,
        comment: str | None = None,
    ) -> dict[str, Any]:
        result = await self._repository.resolve_review_case(
            product_id=product_id,
            case_id=case_id,
            action=action,
            resolved_by=resolved_by,
            corrected_value=corrected_value,
            corrected_unit=corrected_unit,
            selected_candidate_id=selected_candidate_id,
            comment=comment,
        )

        if self._workflow_starter is not None:
            await self._workflow_starter.signal_technical_review_case_resolved(
                ingestion_run_id=result["ingestion_run_id"],
                case_id=str(case_id),
                open_review_case_count=result["open_review_case_count"],
                review_complete=result["review_complete"],
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
        logger.info(
            "Technical dossier | Préparation | contexte chargé",
            product_id=str(parsed_product_id),
            ingestion_run_id=str(run_id),
            source_count=len(context["sources"]),
        )

        # {
        #   "product": {
        #     "id": "uuid",
        #     "sku": "AX-TB-RIV-220-TKGR",
        #     "name": "Table Rivage 220",
        #     "famille_code": "mobilier_jardin",
        #     "sous_famille_code": "table_repas_exterieur",
        #     "season_code": "printemps_ete",
        #     "segment_prix_code": "premium",
        #     "langue_principale": "fr-FR",
        #     "created_at": "2026-04-25T20:23:58.619881"
        #   },
        #   "run": {
        #     "id": "uuid",
        #     "collection_id": "uuid",
        #     "workflow_id": "product-lifecycle-AX-TB-RIV-220-TKGR",
        #     "statut": "EN_COURS",
        #     "current_step": "UPLOAD",
        #     "validation_summary_json": null,
        #     "extraction_steps_json": null
        #   },
        #   "sources": [
        #     {
        #       "id": "uuid",
        #       "collection_id": "uuid",
        #       "original_file_name": "AXOLOTL_RIVAGE_220_FICHE_ATELIER.pdf",
        #       "storage_uri": "gs://bucket/sources/technical-dossiers/product_id/source_id/file.pdf",
        #       "storage_generation": "177714...",
        #       "storage_metageneration": "1",
        #       "storage_content_type": "application/pdf",
        #       "storage_size_bytes": 123456,
        #       "document_type": "UNKNOWN",
        #       "classification_confidence": null,
        #       "statut": "EN_COURS",
        #       "created_at": "2026-04-25T20:25:44.000000",
        #       "updated_at": "2026-04-25T20:25:44.000000"
        #     }, ...
        #   ]
        # }

        run = context["run"]

        await self._repository.update_ingestion_run_step(
            run_id=run_id,
            current_step=CurrentStep.DOCUMENT_CLASSIFICATION,
            statut=StatutDocumentIngestionRun.EN_COURS,
        )
        logger.info(
            "Technical dossier | Préparation | étape du run mise à jour",
            ingestion_run_id=str(run_id),
            current_step=CurrentStep.DOCUMENT_CLASSIFICATION.value,
            statut=StatutDocumentIngestionRun.EN_COURS.value,
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
        #     [
        #   {
        #     "document_source_id": "uuid-du-document-source-1",
        #     "storage_uri": "gs://factory-writer-poc-.../sources/technical-dossiers/.../AXOLOTL_RIVAGE_220_FICHE_ATELIER.pdf",
        #     "mime_type": "application/pdf"
        #   },
        #   {
        #     "document_source_id": "uuid-du-document-source-2",
        #     "storage_uri": "gs://factory-writer-poc-.../sources/technical-dossiers/.../AXOLOTL_RIVAGE_220_NOTICE_MONTAGE.pdf",
        #     "mime_type": "application/pdf"
        #   },
        #   {
        #     "document_source_id": "uuid-du-document-source-3",
        #     "storage_uri": "gs://factory-writer-poc-.../sources/technical-dossiers/.../AXOLOTL_RIVAGE_220_ATTESTATION_MATIERE.pdf",
        #     "mime_type": "application/pdf"
        #   }
        # ]

        if self._document_processor is None:
            raise RuntimeError("Document AI client non configuré pour l'ingestion technique.")

        classifications: list[TechnicalClassificationPayload] = []

        logger.info(
            "Technical dossier | Classification | démarrage",
            source_count=len(sources),
        )

        for source in sources:
            logger.info(
                "Technical dossier | Classification | Document AI démarré",
                document_source_id=source.document_source_id,
                storage_uri=source.storage_uri,
                mime_type=source.mime_type,
            )

            classification = await self._document_processor.classify_technical_document(
                input_uri=source.storage_uri,
                mime_type=source.mime_type,
            )

            logger.info(
                "Technical dossier | Classification | Document AI terminé",
                document_source_id=source.document_source_id,
                document_type=classification.document_type,
                confidence=classification.confidence,
                latency_ms=classification.latency_ms,
                processor_resource_name=classification.processor_resource_name,
                processor_version=classification.processor_version,
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
                        "processor_resource_name": classification.processor_resource_name,
                        "processor_version": classification.processor_version,
                        "request_config_snapshot": classification.request_config_snapshot,
                        "raw_response_summary": classification.raw_response_summary,
                    },
                )
            )

        logger.info(
            "Technical dossier | Classification | terminée",
            classification_count=len(classifications),
            document_types=tuple(
                classification.document_type for classification in classifications
            ),
        )

        #         [
        #   {
        #     "document_source_id": "0f5d8a67-7b2e-4d59-9a84-7d8df0f3f101",
        #     "file_name": "AXOLOTL_RIVAGE_220_FICHE_ATELIER.pdf",
        #     "document_type": "TECHNICAL_SHEET",
        #     "confidence": 0.9993
        #   },
        #   {
        #     "document_source_id": "4f34e3af-53b9-4e16-8b43-2a2f76b31a20",
        #     "file_name": "AXOLOTL_RIVAGE_220_ATTESTATION_MATIERE.pdf",
        #     "document_type": "MATERIAL_SPECIFICATION",
        #     "confidence": 0.9988
        #   },
        #   {
        #     "document_source_id": "a6c9f8b0-90b7-4664-8f4a-5c33c4e6408c",
        #     "file_name": "AXOLOTL_RIVAGE_220_NOTICE_MONTAGE.pdf",
        #     "document_type": "ASSEMBLY_NOTICE",
        #     "confidence": 0.9976
        #   },
        #   {
        #     "document_source_id": "91d9fd40-87f1-46de-8f2a-4f59d6205e44",
        #     "file_name": "Florian_Sollami_-_Senior_Software_Engineer.pdf",
        #     "document_type": "OUT_OF_SCOPE_DOCUMENT",
        #     "confidence": 0.9999
        #   },
        #   {
        #     "document_source_id": "bb6e4c5f-e0d4-4fd4-9dc9-6b947991b27c",
        #     "file_name": "AXOLOTL_RIVAGE_220_DOCUMENT_AMBIGU_CONFIDENCE_TEST.pdf",
        #     "document_type": "MIXED_TECHNICAL_DOSSIER",
        #     "confidence": 0.9537
        #   }
        # ]

        return ClassifyTechnicalSourcesResult(classifications=tuple(classifications))

    async def persist_classification_results(
        self,
        *,
        ingestion_run_id: str,
        classifications: tuple[TechnicalClassificationPayload, ...],
    ) -> PersistClassificationResult:
        for classification in classifications:
            logger.info(
                "Technical dossier | Classification | mise à jour source",
                ingestion_run_id=ingestion_run_id,
                document_source_id=classification.document_source_id,
                document_type=classification.document_type,
                confidence=classification.confidence,
            )

            await self._repository.update_source_classification(
                source_id=uuid.UUID(classification.document_source_id),
                document_type=classification.document_type,
                confidence=classification.confidence,
                quality_metadata_json=classification.quality_metadata_json,
            )

        extraction_steps_json = {
            "steps": [classification.extraction_step_json for classification in classifications],
        }

        review_cases = _classification_review_cases(
            classifications,
            threshold=self._settings.technical_dossier.classification_confidence_threshold,
        )

        # si document_type est routable et confidence >= 0.90, aucun review case

        if review_cases:
            review_case_count = await self._repository.create_classification_review_cases(
                run_id=uuid.UUID(ingestion_run_id),
                review_cases=review_cases,
                extraction_steps_json=extraction_steps_json,
            )

            logger.info(
                "Technical dossier | Classification | review requise",
                ingestion_run_id=ingestion_run_id,
                classification_count=len(classifications),
                review_case_count=review_case_count,
                threshold=self._settings.technical_dossier.classification_confidence_threshold,
            )

            return PersistClassificationResult(
                classification_count=len(classifications),
                review_case_count=review_case_count,
            )

        await self._repository.update_ingestion_run_step(
            run_id=uuid.UUID(ingestion_run_id),
            current_step=CurrentStep.FACT_EXTRACTION,
            statut=StatutDocumentIngestionRun.EN_COURS,
            extraction_steps_json=extraction_steps_json,
        )
        logger.info(
            "Technical dossier | Classification | étape suivante enregistrée",
            ingestion_run_id=ingestion_run_id,
            current_step=CurrentStep.FACT_EXTRACTION.value,
            classification_count=len(classifications),
        )

        return PersistClassificationResult(
            classification_count=len(classifications),
            review_case_count=0,
        )

    async def extract_technical_fact_candidates(
        self,
        *,
        sources: tuple[TechnicalDocumentSourceReference, ...],
        classifications: tuple[TechnicalClassificationPayload, ...],
        ingestion_run_id: str | None = None,
    ) -> ExtractTechnicalFactCandidatesResult:

        # {
        #   "sources": [
        #     {
        #       "document_source_id": "8b7d6e42-8f7a-4c9f-95a4-0f32c26d91a1",
        #       "storage_uri": "gs://factory-writer-poc-1776097019-brand-styles/sources/technical-dossiers/product_id=.../document_source_id=8b7d6e42-8f7a-4c9f-95a4-0f32c26d91a1/AXOLOTL_RIVAGE_220_FICHE_ATELIER.pdf",
        #       "mime_type": "application/pdf"
        #     },
        #     {
        #       "document_source_id": "3a6fa7f5-3fd1-4144-9309-3e432fb9b951",
        #       "storage_uri": "gs://factory-writer-poc-1776097019-brand-styles/sources/technical-dossiers/product_id=.../document_source_id=3a6fa7f5-3fd1-4144-9309-3e432fb9b951/AXOLOTL_RIVAGE_220_ATTESTATION_MATIERE.pdf",
        #       "mime_type": "application/pdf"
        #     }
        #   ],
        #   "classifications": [
        #     {
        #       "document_source_id": "8b7d6e42-8f7a-4c9f-95a4-0f32c26d91a1",
        #       "document_type": "TECHNICAL_SHEET",
        #       "confidence": 0.99394834,
        #       "quality_metadata_json": {
        #         "classifier": {
        #           "processor_resource_name": "projects/623736074911/locations/eu/processors/2eb82286210dea7/processorVersions/pretrained-classifier-v1.5-2025-08-05",
        #           "processor_version": "pretrained-classifier-v1.5-2025-08-05",
        #           "latency_ms": 1420,
        #           "raw_response_summary": {
        #             "entity_count": 1,
        #             "page_count": 2
        #           }
        #         }
        #       },
        #       "extraction_step_json": {
        #         "step": "classification",
        #         "source_id": "8b7d6e42-8f7a-4c9f-95a4-0f32c26d91a1",
        #         "document_type": "TECHNICAL_SHEET",
        #         "confidence": 0.99394834,
        #         "latency_ms": 1420
        #       }
        #     },
        #     {
        #       "document_source_id": "3a6fa7f5-3fd1-4144-9309-3e432fb9b951",
        #       "document_type": "MATERIAL_SPECIFICATION",
        #       "confidence": 0.99912065,
        #       "quality_metadata_json": {
        #         "classifier": {
        #           "processor_resource_name": "projects/623736074911/locations/eu/processors/2eb82286210dea7/processorVersions/pretrained-classifier-v1.5-2025-08-05",
        #           "processor_version": "pretrained-classifier-v1.5-2025-08-05",
        #           "latency_ms": 1318,
        #           "raw_response_summary": {
        #             "entity_count": 1,
        #             "page_count": 1
        #           }
        #         }
        #       },
        #       "extraction_step_json": {
        #         "step": "classification",
        #         "source_id": "3a6fa7f5-3fd1-4144-9309-3e432fb9b951",
        #         "document_type": "MATERIAL_SPECIFICATION",
        #         "confidence": 0.99912065,
        #         "latency_ms": 1318
        #       }
        #     }
        #   ]
        # }

        if self._document_processor is None:
            raise RuntimeError("Document AI client non configuré pour l'ingestion technique.")

        classifications_by_source_id = {
            classification.document_source_id: classification for classification in classifications
        }

        # classifications = [
        #     TechnicalClassificationPayload(
        #         document_source_id="src-001",
        #         document_type="TECHNICAL_SHEET",
        #         confidence=0.99394834,
        #         quality_metadata_json={...},
        #         extraction_step_json={...},
        #     ),
        #     TechnicalClassificationPayload(
        #         document_source_id="src-002",
        #         document_type="MATERIAL_SPECIFICATION",
        #         confidence=0.99912065,
        #         quality_metadata_json={...},
        #         extraction_step_json={...},
        #     ),
        #     TechnicalClassificationPayload(
        #         document_source_id="src-003",
        #         document_type="ASSEMBLY_NOTICE",
        #         confidence=0.99761241,
        #         quality_metadata_json={...},
        #         extraction_step_json={...},
        #     ),
        # ]

        total_started = perf_counter()

        extraction_steps: list[dict[str, Any]] = [
            classification.extraction_step_json for classification in classifications
        ]

        candidates: list[TechnicalFactCandidatePayload] = []

        logger.info(
            "Technical dossier | Extraction | démarrage",
            source_count=len(sources),
            classification_count=len(classifications),
        )

        for source in sources:
            classification = classifications_by_source_id.get(source.document_source_id)

            if classification is None:
                raise RuntimeError(
                    f"Classification manquante pour la source {source.document_source_id}."
                )

            # le bon extractor selon le type de document (a les infos de la config)
            extractor_route = self._extractor_router.route_for_document_type(
                classification.document_type
            )

            # {
            #     "document_type": "TECHNICAL_SHEET",
            #     "extractor_name": "fw-technical-sheet-extractor",
            #     "processor_id": "51d79fcf170d4db5",
            #     "processor_version": null,
            # }

            logger.info(
                "Technical dossier | Extraction | Document AI démarré",
                document_source_id=source.document_source_id,
                document_type=classification.document_type,
                storage_uri=source.storage_uri,
                mime_type=source.mime_type,
                extractor_name=extractor_route.extractor_name,
                extractor_processor_id=extractor_route.processor_id,
                extractor_processor_version=extractor_route.processor_version,
            )

            extraction = await self._document_processor.extract_technical_facts(
                input_uri=source.storage_uri,
                document_type=classification.document_type,
                extractor_route=extractor_route,
                mime_type=source.mime_type,
            )

            #             {
            #   "processor_resource_name": "projects/623736074911/locations/eu/processors/6a06ee761cf984a5/processorVersions/pretrained-foundation-model-v1.5-pro-2025-06-20",
            #   "processor_version": "pretrained-foundation-model-v1.5-pro-2025-06-20",
            #   "latency_ms": 1842,
            #   "request_config_snapshot": {
            #     "mode": "online",
            #     "processor_kind": "custom_extractor_foundation_model",
            #     "extractor_document_type": "MATERIAL_SPECIFICATION",
            #     "extractor_processor_name": "fw-material-spec-extractor",
            #     "processor_resource_name": "projects/623736074911/locations/eu/processors/6a06ee761cf984a5/processorVersions/pretrained-foundation-model-v1.5-pro-2025-06-20",
            #     "processor_version": "pretrained-foundation-model-v1.5-pro-2025-06-20",
            #     "gcs_uri": "gs://factory-writer-poc-1776097019-brand-styles/sources/technical-dossiers/product_id=.../document_source_id=.../AXOLOTL_RIVAGE_220_ATTESTATION_MATIERE.pdf",
            #     "mime_type": "application/pdf",
            #     "document_type": "MATERIAL_SPECIFICATION",
            #     "skip_human_review": true,
            #     "field_mask": ["entities"]
            #   },
            #   "entities": [
            #     {
            #       "field_name": "assembly_site",
            #       "raw_value": "Jepara, Indonésie",
            #       "confidence": 0.9999001,
            #       "page": 1,
            #       "bbox_json": {
            #         "normalizedVertices": [
            #           { "x": 0.28732896, "y": 0.3480454 },
            #           { "x": 0.40273646, "y": 0.3480454 },
            #           { "x": 0.40273646, "y": 0.3577133 },
            #           { "x": 0.28732896, "y": 0.3577133 }
            #         ],
            #         "vertices": []
            #       },
            #       "raw_entity_json": {
            #         "textAnchor": {
            #           "textSegments": [
            #             {
            #               "startIndex": "466",
            #               "endIndex": "483"
            #             }
            #           ],
            #           "content": ""
            #         },
            #         "type": "assembly_site",
            #         "mentionText": "Jepara, Indonésie",
            #         "confidence": 0.9999001,
            #         "pageAnchor": {
            #           "pageRefs": [
            #             {
            #               "page": "0",
            #               "boundingPoly": {
            #                 "normalizedVertices": [
            #                   { "x": 0.28732896, "y": 0.3480454 },
            #                   { "x": 0.40273646, "y": 0.3480454 },
            #                   { "x": 0.40273646, "y": 0.3577133 },
            #                   { "x": 0.28732896, "y": 0.3577133 }
            #                 ],
            #                 "vertices": []
            #               },
            #               "layoutType": "LAYOUT_TYPE_UNSPECIFIED",
            #               "layoutId": "",
            #               "confidence": 0.0
            #             }
            #           ]
            #         },
            #         "id": "0",
            #         "mentionId": "",
            #         "properties": [],
            #         "redacted": false,
            #         "method": "METHOD_UNSPECIFIED"
            #       }
            #     },
            #     {
            #       "field_name": "material_primary",
            #       "raw_value": "Tectona grandis",
            #       "confidence": 0.82155496,
            #       "page": 1,
            #       "bbox_json": {
            #         "normalizedVertices": [
            #           { "x": 0.054134443, "y": 0.39386296 },
            #           { "x": 0.15704937, "y": 0.39386296 },
            #           { "x": 0.15704937, "y": 0.40311056 },
            #           { "x": 0.054134443, "y": 0.40311056 }
            #         ],
            #         "vertices": []
            #       },
            #       "raw_entity_json": {
            #         "type": "material_primary",
            #         "mentionText": "Tectona grandis",
            #         "confidence": 0.82155496
            #       }
            #     }
            #   ]
            # }

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

            source_candidate_inputs = [
                _entity_to_raw_candidate_input(uuid.UUID(source.document_source_id), entity)
                for entity in extraction.entities
            ]
            source_candidates = [
                _candidate_input_to_payload(candidate) for candidate in source_candidate_inputs
            ]

            candidates.extend(source_candidates)

            logger.info(
                "Technical dossier | Extraction | Document AI terminé",
                document_source_id=source.document_source_id,
                document_type=classification.document_type,
                raw_entity_count=len(extraction.entities),
                candidate_count=len(source_candidates),
                latency_ms=extraction.latency_ms,
                processor_resource_name=extraction.processor_resource_name,
                processor_version=extraction.processor_version,
            )

        total_elapsed_seconds = round(perf_counter() - total_started, 3)

        extraction_steps_json = {
            "steps": extraction_steps,
            "total_elapsed_seconds": total_elapsed_seconds,
        }

        if ingestion_run_id is not None:
            await self._repository.update_ingestion_run_step(
                run_id=uuid.UUID(ingestion_run_id),
                current_step=CurrentStep.FACT_EXTRACTION,
                statut=StatutDocumentIngestionRun.EN_COURS,
                extraction_steps_json=extraction_steps_json,
            )

        logger.info(
            "Technical dossier | Extraction | terminée",
            candidate_count=len(candidates),
            total_elapsed_seconds=total_elapsed_seconds,
        )

        # {
        #     "candidates": [
        #         {
        #             "source_id": "3ea067da-31f5-4cea-a984-dea6364afaba",
        #             "field_name": "component_dimensions",
        #             "raw_value": "28 mm nominal",
        #             "normalized_value": null,
        #             "unit": null,
        #             "extractor_confidence": 0.9231185913085938,
        #             "validation_status": "EXTRACTED",
        #             "source_page": 1,
        #         },
        #         {
        #             "source_id": "3ea067da-31f5-4cea-a984-dea6364afaba",
        #             "field_name": "component_dimensions",
        #             "raw_value": "Ø50 mm",
        #             "normalized_value": null,
        #             "unit": null,
        #             "extractor_confidence": 0.988102912902832,
        #             "validation_status": "EXTRACTED",
        #             "source_page": 1,
        #         },
        #         {
        #             "source_id": "3ea067da-31f5-4cea-a984-dea6364afaba",
        #             "field_name": "dimension_depth",
        #             "raw_value": "950",
        #             "normalized_value": null,
        #             "unit": null,
        #             "extractor_confidence": 0.9625529646873474,
        #             "validation_status": "EXTRACTED",
        #             "source_page": 1,
        #         },
        #     ],
        #     "extraction_steps_json": {
        #         "steps": [
        #             {
        #                 "step": "extraction",
        #                 "source_id": "3ea067da-31f5-4cea-a984-dea6364afaba",
        #                 "entity_count": 29,
        #                 "latency_ms": 9971,
        #                 "processor_resource_name": "projects/factory-writer-poc-1776097019/locations/eu/processors/51d79fcf170d4db5/processorVersions/pretrained-foundation-model-v1.5-pro-2025-06-20",
        #                 "processor_version": "pretrained-foundation-model-v1.5-pro-2025-06-20",
        #                 "request_config_snapshot": {
        #                     "mode": "online",
        #                     "processor_kind": "custom_extractor_foundation_model",
        #                     "extractor_document_type": "TECHNICAL_SHEET",
        #                     "extractor_processor_name": "fw-technical-sheet-extractor",
        #                     "mime_type": "application/pdf",
        #                     "document_type": "TECHNICAL_SHEET",
        #                     "skip_human_review": true,
        #                     "field_mask": ["entities"],
        #                 },
        #             }
        #         ],
        #         "total_elapsed_seconds": 33.228,
        #     },
        # }

        return ExtractTechnicalFactCandidatesResult(
            candidates=tuple(candidates),
            extraction_steps_json=extraction_steps_json,
        )

    async def refresh_technical_classifications(
        self,
        *,
        product_id: str,
        ingestion_run_id: str,
        sources: tuple[TechnicalDocumentSourceReference, ...],
        classifications: tuple[TechnicalClassificationPayload, ...],
    ) -> ClassifyTechnicalSourcesResult:
        parsed_product_id = uuid.UUID(product_id)
        run_id = uuid.UUID(ingestion_run_id)
        source_ids = tuple(uuid.UUID(source.document_source_id) for source in sources)
        context = await self._repository.get_technical_ingestion_context(
            product_id=parsed_product_id,
            document_source_ids=source_ids,
            ingestion_run_id=run_id,
        )
        sources_by_id = {str(source.id): source for source in context["sources"]}
        classifications_by_id = {
            classification.document_source_id: classification for classification in classifications
        }

        refreshed: list[TechnicalClassificationPayload] = []
        for source in sources:
            persisted_source = sources_by_id.get(source.document_source_id)
            previous = classifications_by_id.get(source.document_source_id)
            if persisted_source is None or previous is None:
                raise RuntimeError(
                    f"Classification persistée introuvable pour la source "
                    f"{source.document_source_id}."
                )

            document_type = persisted_source.document_type
            confidence = persisted_source.classification_confidence
            if confidence is None:
                confidence = previous.confidence

            extraction_step_json = dict(previous.extraction_step_json)
            extraction_step_json["document_type"] = document_type
            extraction_step_json["confidence"] = confidence
            if document_type != previous.document_type:
                extraction_step_json["review_override"] = True

            quality_metadata_json = dict(previous.quality_metadata_json)
            if document_type != previous.document_type:
                quality_metadata_json["review_override"] = {
                    "previous_document_type": previous.document_type,
                    "document_type": document_type,
                }

            refreshed.append(
                TechnicalClassificationPayload(
                    document_source_id=source.document_source_id,
                    document_type=document_type,
                    confidence=confidence,
                    quality_metadata_json=quality_metadata_json,
                    extraction_step_json=extraction_step_json,
                )
            )

        logger.info(
            "Technical dossier | Classification | classifications rechargées",
            ingestion_run_id=ingestion_run_id,
            document_types=tuple(classification.document_type for classification in refreshed),
        )
        return ClassifyTechnicalSourcesResult(classifications=tuple(refreshed))

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

        logger.info(
            "Technical dossier | Candidats | persistance démarrée",
            product_id=product.product_id,
            sku=product.sku,
            ingestion_run_id=ingestion_run_id,
            candidate_count=len(candidates),
        )

        await self._repository.persist_technical_fact_candidates(
            product_id=uuid.UUID(product.product_id),
            run_id=uuid.UUID(ingestion_run_id),
            candidates=[_candidate_payload_to_input(candidate) for candidate in candidates],
            extraction_steps_json=extraction_steps_json,
        )

        logger.info(
            "Technical dossier | Candidats | persistance terminée",
            product_id=product.product_id,
            ingestion_run_id=ingestion_run_id,
            candidate_count=len(candidates),
        )

        # {"candidate_count": 86}

        return PersistTechnicalFactCandidatesResult(candidate_count=len(candidates))

    async def validate_technical_facts(
        self,
        *,
        product: ProductContextReference,
        candidates: tuple[TechnicalFactCandidatePayload, ...],
        document_types: tuple[str, ...],
        source_document_types: dict[str, str] | None = None,
    ) -> ValidateTechnicalFactsResult:
        product_snapshot = _payload_product_to_snapshot(product)
        # {
        #     "id": "8be89833-c32c-4233-8a5b-3f25653893b8",
        #     "sku": "AX-TB-RIV-220-TKGR",
        #     "name": "AX-TB-RIV-220-TKGR",
        #     "famille_code": "mobilier_jardin",
        #     "sous_famille_code": "table_repas_exterieur",
        #     "season_code": "printemps_ete",
        #     "segment_prix_code": "premium",
        #     "langue_principale": "fr-FR",
        #     "created_at": null,
        # }

        requirement_profile = await self._load_product_sheet_requirement_profile(product_snapshot)

        # {
        #     "id": "00000000-0000-0000-0000-000000000201",
        #     "famille_code": "mobilier_jardin",
        #     "sous_famille_code": "table_repas_exterieur",
        #     "requirements": [
        #         {
        #             "field_name": "sku",
        #             "level": "REQUIRED",
        #             "target_unit": null,
        #             "require_unit": false,
        #             "min_confidence": 0.85,
        #             "conflict_confidence_threshold": 0.7,
        #             "bounds_min": null,
        #             "bounds_max": null,
        #             "condition": null,
        #             "missing_action": null,
        #             "cardinality": "SINGLE",
        #             "selection_policy": "CANONICAL_SINGLE",
        #             "conflict_policy": "BLOCK_ON_CREDIBLE_CONFLICT",
        #             "source_priority": [
        #                 "TECHNICAL_SHEET",
        #                 "MATERIAL_SPECIFICATION",
        #                 "ASSEMBLY_NOTICE",
        #             ],
        #         },
        #         {
        #             "field_name": "dimension_width",
        #             "level": "REQUIRED",
        #             "target_unit": "cm",
        #             "require_unit": true,
        #             "min_confidence": 0.9,
        #             "conflict_confidence_threshold": 0.7,
        #             "bounds_min": 120,
        #             "bounds_max": 360,
        #             "condition": null,
        #             "missing_action": null,
        #             "cardinality": "SINGLE",
        #             "selection_policy": "CANONICAL_SINGLE",
        #             "conflict_policy": "BLOCK_ON_CREDIBLE_CONFLICT",
        #             "source_priority": ["TECHNICAL_SHEET"],
        #         },
        #         {
        #             "field_name": "material_primary",
        #             "level": "REQUIRED",
        #             "target_unit": null,
        #             "require_unit": false,
        #             "min_confidence": 0.9,
        #             "conflict_confidence_threshold": 0.7,
        #             "bounds_min": null,
        #             "bounds_max": null,
        #             "condition": null,
        #             "missing_action": null,
        #             "cardinality": "SINGLE",
        #             "selection_policy": "CANONICAL_SINGLE",
        #             "conflict_policy": "BLOCK_ON_CREDIBLE_CONFLICT",
        #             "source_priority": ["MATERIAL_SPECIFICATION", "TECHNICAL_SHEET"],
        #         },
        #     ],
        # }

        candidate_inputs = [_candidate_payload_to_input(candidate) for candidate in candidates]

        #         [
        #   {
        #     "source_id": "3ea067da-31f5-4cea-a984-dea6364afaba",
        #     "field_name": "dimension_width",
        #     "raw_value": "2 200 mm",
        #     "normalized_value": null,
        #     "unit": null,
        #     "extractor_confidence": 0.91,
        #     "validation_status": "EXTRACTED",
        #     "source_page": 1
        #   },
        #   {
        #     "source_id": "3ea067da-31f5-4cea-a984-dea6364afaba",
        #     "field_name": "material_primary",
        #     "raw_value": "Tectona grandis",
        #     "normalized_value": null,
        #     "unit": null,
        #     "extractor_confidence": 0.92,
        #     "validation_status": "EXTRACTED",
        #     "source_page": 1
        #   }
        # ]

        logger.info(
            "Technical dossier | Validation | démarrage",
            product_id=str(product_snapshot.id),
            candidate_count=len(candidates),
            profile_id=str(requirement_profile.id),
            requirement_count=len(requirement_profile.requirements),
            document_types=document_types,
        )

        validation = _validate_technical_candidates(
            candidate_inputs,
            low_confidence_threshold=self._settings.technical_dossier.low_confidence_threshold,
            profile=requirement_profile,
            document_types=document_types,  # ["MATERIAL_SPECIFICATION", "TECHNICAL_SHEET", "ASSEMBLY_NOTICE"]
            source_document_types=source_document_types
            or {},  # {"3ea067da-31f5-4cea-a984-dea6364afaba": "MATERIAL_SPECIFICATION", "8b8f0cf1-1fa2-4c85-9a44-47f7756b4e7a": "TECHNICAL_SHEET", "98d8d379-9f67-4888-b372-64f8d92fd5b8": "ASSEMBLY_NOTICE"}
        )

        candidate_inputs = _mark_review_candidates(candidate_inputs, validation.review_cases)

        logger.info(
            "Technical dossier | Validation | terminée",
            candidate_count=len(candidate_inputs),
            review_case_count=len(validation.review_cases),
            promoted_fact_count=len(validation.promoted_facts),
            generation_ready=validation.generation_readiness.get("ready"),
        )

        return self._build_validate_technical_facts_result(candidate_inputs, validation)

    async def _load_product_sheet_requirement_profile(
        self,
        product_snapshot: ProductSnapshot,
    ) -> _ProductSheetRequirementProfile:
        profile_snapshot = await self._repository.load_product_sheet_requirement_profile(
            product=product_snapshot,
        )
        return _parse_product_sheet_requirement_profile(profile_snapshot)

    def _build_validate_technical_facts_result(
        self,
        candidate_inputs: list[TechnicalFactCandidateInput],
        validation: _ValidationResult,
    ) -> ValidateTechnicalFactsResult:
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
            generation_readiness=validation.generation_readiness,
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
        generation_readiness: dict[str, Any],
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
                "profile_id": generation_readiness.get("profile_id"),
                "required_fields": generation_readiness.get("required_fields", []),
            },
            "generation_readiness": generation_readiness,
        }

        logger.info(
            "Technical dossier | Promotion | écriture finale démarrée",
            product_id=product.product_id,
            sku=product.sku,
            ingestion_run_id=ingestion_run_id,
            candidate_count=len(candidates),
            review_case_count=len(review_cases),
            promoted_fact_count=len(promoted_facts),
            requires_review=bool(review_cases),
        )
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
        status = STATUS_PENDING_TECH_REVIEW if review_cases else STATUS_TECHNICAL_FACTS_READY
        logger.info(
            "Technical dossier | Promotion | écriture finale terminée",
            product_id=product.product_id,
            ingestion_run_id=ingestion_run_id,
            status=status,
            review_case_count=len(review_cases),
            promoted_fact_count=len(promoted_facts),
        )

        return PromoteTechnicalFactsResult(
            status=status,
            review_case_count=len(review_cases),
            promoted_fact_count=len(promoted_facts),
        )

    async def finalize_technical_review(
        self,
        *,
        product: ProductContextReference,
        ingestion_run_id: str,
    ) -> FinalizeTechnicalReviewResult:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour finaliser la revue technique.")

        overview = await self._repository.get_product_overview(uuid.UUID(product.product_id))
        generation_readiness = overview.get("generation_readiness") or {}
        required_fields = set(generation_readiness.get("required_fields") or [])
        facts = overview.get("facts") or []
        fact_fields = {fact.get("field_name") for fact in facts if isinstance(fact, dict)}
        missing = sorted(field for field in required_fields if field not in fact_fields)
        if missing:
            raise RuntimeError(
                f"Revue technique incomplète: facts requis manquants ({', '.join(missing)})."
            )

        logger.info(
            "Technical dossier | Revue | finalisation validée",
            product_id=product.product_id,
            ingestion_run_id=ingestion_run_id,
            promoted_fact_count=len(facts),
        )
        return FinalizeTechnicalReviewResult(promoted_fact_count=len(facts))

    async def mark_technical_ingestion_failed(
        self,
        *,
        product: ProductContextReference,
        error_message: str,
    ) -> None:
        if product.product_id is None:
            raise RuntimeError("product_id est requis pour marquer l'ingestion en erreur.")

        logger.error(
            "Technical dossier | Échec | marquage en base",
            product_id=product.product_id,
            sku=product.sku,
            error_message=error_message,
        )
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

        generation_readiness: dict[str, Any] | None = None

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

        try:
            requirement_profile = _parse_product_sheet_requirement_profile(
                await self._repository.load_product_sheet_requirement_profile(
                    product=product_snapshot,
                )
            )
            required_fact_names = {
                requirement.field_name
                for requirement in requirement_profile.requirements
                if requirement.level == "REQUIRED"
            }
            generation_readiness = {
                "profile_id": str(requirement_profile.id),
                "required_fields": sorted(required_fact_names),
                "ready": all(field_name in facts_by_field for field_name in required_fact_names),
            }
        except RuntimeError:
            required_fact_names = set()

        if not required_fact_names or any(
            field_name not in facts_by_field for field_name in required_fact_names
        ):
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
            generation_readiness=generation_readiness,
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
                "generation_readiness": readiness.generation_readiness,
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
