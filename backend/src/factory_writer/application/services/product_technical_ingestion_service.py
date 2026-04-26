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
    ClassifyTechnicalSourcesResult,
    CreateProductContextSnapshotResult,
    DocumentSourceSnapshot,
    ExtractTechnicalFactCandidatesResult,
    FinalizeTechnicalReviewResult,
    GenerationReadinessProfileSnapshot,
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
    TechnicalExtractorRouterPort,
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
from factory_writer.application.services.technical_extractor_router import (
    ConfiguredTechnicalExtractorRouter,
)
from factory_writer.core.config import Settings
from factory_writer.domain.document_ingestion_types import (
    CurrentStep,
    DocumentType,
    StatutDocumentIngestionRun,
    StatutTechnicalFactCandidate,
    TechnicalReviewCaseType,
    TechnicalReviewResolutionAction,
    TechnicalReviewSeverity,
    TechnicalReviewTriggerSource,
)

logger = structlog.get_logger(__name__)

_GENERATION_READINESS_CHANNEL_CODE = "product_sheet"
_DIMENSION_FIELDS = {
    "dimension_width",
    "dimension_depth",
    "dimension_height",
}
_DIMENSION_CONTEXT_FIELD = "dimension_set_raw"
_FIELD_NAME_ALIASES = {
    "dimension_width_cm": "dimension_width",
    "dimension_depth_cm": "dimension_depth",
    "dimension_height_cm": "dimension_height",
    "weight_kg": "weight",
    "assembly_time_minutes": "assembly_time",
    "max_torque_nm": "max_torque",
}
_ROUTABLE_TECHNICAL_DOCUMENT_TYPES = {
    DocumentType.TECHNICAL_SHEET.value,
    DocumentType.ASSEMBLY_NOTICE.value,
    DocumentType.MATERIAL_SPECIFICATION.value,
}
_NUMBER_TOKEN = r"\d+(?:[ \u00a0]\d{3})*(?:[,.]\d+)?|\d+(?:[,.]\d+)?"
_DIMENSION_PATTERN = re.compile(
    rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>mm|cm|m)?\b",
    re.I,
)
_DIMENSION_UNIT_PATTERN = re.compile(r"(?<![a-zA-Z])(mm|cm|m)(?![a-zA-Z])", re.I)
_NUMBER_PATTERN = re.compile(rf"(?P<number>{_NUMBER_TOKEN})")
_WEIGHT_PATTERN = re.compile(rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>kg|g|t)?\b", re.I)
_TIME_PATTERN = re.compile(
    rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>minutes?|mins?|mn|h|heures?)?\b",
    re.I,
)
_TORQUE_PATTERN = re.compile(rf"(?P<number>{_NUMBER_TOKEN})\s*(?P<unit>n[·.]?m)?\b", re.I)


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

            source_candidate_inputs = _normalize_source_candidate_inputs(
                [
                    _entity_to_candidate_input(uuid.UUID(source.document_source_id), entity)
                    for entity in extraction.entities
                ]
            )
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
        profile_snapshot = await self._repository.load_generation_readiness_profile(
            product=product_snapshot,
            channel_code=_GENERATION_READINESS_CHANNEL_CODE,
        )
        readiness_profile = _parse_generation_readiness_profile(profile_snapshot)

        logger.info(
            "Technical dossier | Validation | démarrage",
            product_id=str(product_snapshot.id),
            candidate_count=len(candidates),
            profile_code=readiness_profile.profile_code,
            requirement_count=len(readiness_profile.requirements),
            document_types=document_types,
        )
        candidate_inputs = [_candidate_payload_to_input(candidate) for candidate in candidates]

        validation = _validate_technical_candidates(
            candidate_inputs,
            low_confidence_threshold=self._settings.technical_dossier.low_confidence_threshold,
            profile=readiness_profile,
            document_types=document_types,
            source_document_types=source_document_types or {},
        )

        candidate_inputs = _mark_review_candidates(candidate_inputs, validation.review_cases)
        logger.info(
            "Technical dossier | Validation | terminée",
            candidate_count=len(candidate_inputs),
            review_case_count=len(validation.review_cases),
            promoted_fact_count=len(validation.promoted_facts),
            generation_ready=validation.generation_readiness.get("ready"),
        )

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
                "profile_code": generation_readiness.get("profile_code"),
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
            readiness_profile = _parse_generation_readiness_profile(
                await self._repository.load_generation_readiness_profile(
                    product=product_snapshot,
                    channel_code=_GENERATION_READINESS_CHANNEL_CODE,
                )
            )
            required_fact_names = {
                requirement.field_name
                for requirement in readiness_profile.requirements
                if requirement.level == "REQUIRED"
            }
            generation_readiness = {
                "profile_code": readiness_profile.profile_code,
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


@dataclass(frozen=True)
class _ValidationResult:
    review_cases: list[TechnicalReviewCaseInput]
    promoted_facts: list[PromotedTechnicalFactInput]
    generation_readiness: dict[str, Any]


@dataclass(frozen=True)
class _ReadinessRequirement:
    field_name: str
    level: str
    target_unit: str | None
    require_unit: bool
    min_confidence: float | None
    conflict_confidence_threshold: float
    bounds_min: float | None
    bounds_max: float | None
    condition: str | None
    missing_action: str | None
    cardinality: str
    selection_policy: str
    conflict_policy: str
    source_priority: tuple[str, ...]


@dataclass(frozen=True)
class _GenerationReadinessProfile:
    profile_code: str
    famille_code: str
    sous_famille_code: str | None
    channel_code: str
    requirements: tuple[_ReadinessRequirement, ...]


def _classification_review_cases(
    classifications: tuple[TechnicalClassificationPayload, ...],
    *,
    threshold: float,
) -> list[TechnicalReviewCaseInput]:
    review_cases: list[TechnicalReviewCaseInput] = []

    for classification in classifications:
        document_type = classification.document_type
        confidence = classification.confidence
        if (
            document_type in _ROUTABLE_TECHNICAL_DOCUMENT_TYPES
            and confidence is not None
            and confidence >= threshold
        ):
            continue

        is_out_of_scope = document_type not in _ROUTABLE_TECHNICAL_DOCUMENT_TYPES
        classifier_metadata = classification.quality_metadata_json.get("classifier", {})
        metadata_json = {
            "confidence": confidence,
            "threshold": threshold,
            "is_out_of_scope": is_out_of_scope,
            "processor_resource_name": classifier_metadata.get("processor_resource_name"),
            "processor_version": classifier_metadata.get("processor_version"),
            "source_id": classification.document_source_id,
        }

        review_cases.append(
            TechnicalReviewCaseInput(
                source_id=uuid.UUID(classification.document_source_id),
                candidate_index=None,
                case_type=TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
                trigger_source=TechnicalReviewTriggerSource.CLASSIFIER,
                severity=TechnicalReviewSeverity.BLOCKING,
                field_name="document_type",
                title=(
                    "Document hors périmètre" if is_out_of_scope else "Type de document à confirmer"
                ),
                description=(
                    "Ce PDF ne correspond pas à un dossier technique produit exploitable."
                    if is_out_of_scope
                    else (
                        "Le classifier Document AI n'a pas assez de confiance pour router ce "
                        "PDF vers le bon extracteur."
                    )
                ),
                detected_value=document_type,
                detected_unit=None,
                suggested_value=None,
                suggested_unit=None,
                metadata_json=metadata_json,
            )
        )

    return review_cases


def _validate_technical_candidates(
    candidates: list[TechnicalFactCandidateInput],
    *,
    low_confidence_threshold: float,
    profile: _GenerationReadinessProfile,
    document_types: tuple[str, ...],
    source_document_types: dict[str, str] | None = None,
) -> _ValidationResult:
    source_document_types = source_document_types or {}
    review_cases: list[TechnicalReviewCaseInput] = []
    promoted_facts: list[PromotedTechnicalFactInput] = []
    readiness = _initial_generation_readiness_summary(profile, document_types)

    by_field: dict[str, list[tuple[int, TechnicalFactCandidateInput]]] = {}

    for index, candidate in enumerate(candidates):
        by_field.setdefault(candidate.field_name, []).append((index, candidate))

    for requirement in profile.requirements:
        active = _requirement_is_active(requirement, document_types)
        field_candidates = by_field.get(requirement.field_name, [])
        is_blocking_requirement = requirement.level in {"REQUIRED", "CONDITIONAL"} and active

        if is_blocking_requirement:
            readiness["required_fields"].append(requirement.field_name)

        if not field_candidates:
            if is_blocking_requirement:
                review_case = _missing_required_field_review_case(requirement, profile=profile)
                review_cases.append(review_case)
                readiness["required_missing"].append(requirement.field_name)
                readiness["field_checks"].append(
                    _field_check(
                        requirement,
                        status="BLOCKED",
                        blocking_reason=review_case.case_type.value,
                    )
                )
            elif requirement.missing_action == "DO_NOT_MENTION":
                readiness["do_not_mention"].append(requirement.field_name)
                readiness["field_checks"].append(
                    _field_check(requirement, status="SKIPPED", blocking_reason="DO_NOT_MENTION")
                )
            continue

        valid_candidates: list[tuple[int, TechnicalFactCandidateInput]] = []
        optional_warning: dict[str, Any] | None = None

        for index, candidate in field_candidates:
            review = _candidate_review_case(
                index,
                candidate,
                requirement=requirement,
                profile=profile,
                low_confidence_threshold=low_confidence_threshold,
                is_blocking_requirement=is_blocking_requirement,
                source_document_types=source_document_types,
            )

            if review is not None:
                if is_blocking_requirement:
                    review_cases.append(review)
                    _append_readiness_review(readiness, review)
                else:
                    optional_warning = {
                        "case_type": review.case_type.value,
                        "detected_value": review.detected_value,
                        "detected_unit": review.detected_unit,
                    }
                continue

            valid_candidates.append((index, candidate))

        if not valid_candidates:
            readiness["field_checks"].append(
                _field_check(
                    requirement,
                    status="WARNING" if optional_warning else "BLOCKED",
                    blocking_reason=(
                        optional_warning["case_type"] if optional_warning else "NO_VALID_CANDIDATE"
                    ),
                )
            )
            continue

        grouped_candidates = _candidate_groups_by_value(valid_candidates)

        if (
            requirement.cardinality == "MULTIPLE"
            or requirement.selection_policy == "KEEP_ALL_VALID"
        ):
            selected_candidates = [
                _select_best_candidate(group, requirement, source_document_types)
                for group in grouped_candidates.values()
            ]
            selected_candidates.sort(
                key=lambda item: _candidate_sort_key(item, requirement, source_document_types)
            )
            for occurrence_index, (selected_index, selected) in enumerate(selected_candidates):
                value = selected.normalized_value or selected.raw_value
                if value:
                    promoted_facts.append(
                        PromotedTechnicalFactInput(
                            candidate_index=selected_index,
                            field_name=requirement.field_name,
                            occurrence_index=occurrence_index,
                            value=value,
                            unit=selected.unit,
                        )
                    )
            readiness["field_checks"].append(
                _field_check(
                    requirement,
                    status="PASSED",
                    selected_candidates=selected_candidates,
                    source_document_types=source_document_types,
                )
            )
            continue

        selected_index, selected = _select_best_candidate(
            valid_candidates,
            requirement,
            source_document_types,
        )
        selected_value_key = _candidate_value_key(selected)
        credible_conflicts = [
            (index, candidate)
            for index, candidate in valid_candidates
            if _candidate_value_key(candidate) != selected_value_key
            and (candidate.extractor_confidence or 0.0) >= requirement.conflict_confidence_threshold
        ]

        if credible_conflicts and requirement.conflict_policy == "BLOCK_ON_CREDIBLE_CONFLICT":
            conflicting_candidates = [(selected_index, selected), *credible_conflicts]
            review_case = _contradiction_review_case(
                requirement,
                selected_index=selected_index,
                selected=selected,
                conflicting_candidates=conflicting_candidates,
                profile=profile,
                source_document_types=source_document_types,
            )
            review_cases.append(review_case)
            _append_readiness_review(readiness, review_case)
            readiness["field_checks"].append(
                _field_check(
                    requirement,
                    status="BLOCKED",
                    selected_candidates=[(selected_index, selected)],
                    alternatives=conflicting_candidates,
                    blocking_reason=review_case.case_type.value,
                    source_document_types=source_document_types,
                )
            )
            continue

        value = selected.normalized_value or selected.raw_value
        if value:
            promoted_facts.append(
                PromotedTechnicalFactInput(
                    candidate_index=selected_index,
                    field_name=requirement.field_name,
                    occurrence_index=0,
                    value=value,
                    unit=selected.unit,
                )
            )
        readiness["field_checks"].append(
            _field_check(
                requirement,
                status="WARNING" if credible_conflicts else "PASSED",
                selected_candidates=[(selected_index, selected)],
                alternatives=credible_conflicts,
                blocking_reason="PREFERRED_BEST_WITH_WARNING" if credible_conflicts else None,
                source_document_types=source_document_types,
            )
        )

    readiness["ready"] = len(review_cases) == 0
    readiness["blocking_count"] = len(review_cases)

    return _ValidationResult(
        review_cases=review_cases,
        promoted_facts=promoted_facts,
        generation_readiness=readiness,
    )


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


def _missing_required_field_review_case(
    requirement: _ReadinessRequirement,
    *,
    profile: _GenerationReadinessProfile,
) -> TechnicalReviewCaseInput:
    return TechnicalReviewCaseInput(
        source_id=None,
        candidate_index=None,
        case_type=TechnicalReviewCaseType.MISSING_REQUIRED_FIELD,
        trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
        severity=TechnicalReviewSeverity.BLOCKING,
        field_name=requirement.field_name,
        title=f"Champ requis manquant: {requirement.field_name}",
        description=f"Aucune preuve exploitable trouvée pour {requirement.field_name}.",
        metadata_json={
            "profile_code": profile.profile_code,
            "level": requirement.level,
            "condition": requirement.condition,
        },
    )


def _candidate_groups_by_value(
    candidates: list[tuple[int, TechnicalFactCandidateInput]],
) -> dict[str, list[tuple[int, TechnicalFactCandidateInput]]]:
    grouped: dict[str, list[tuple[int, TechnicalFactCandidateInput]]] = {}
    for index, candidate in candidates:
        grouped.setdefault(_candidate_value_key(candidate), []).append((index, candidate))
    return grouped


def _candidate_value_key(candidate: TechnicalFactCandidateInput) -> str:
    return _normalize_comparable_value(candidate.normalized_value or candidate.raw_value)


def _select_best_candidate(
    candidates: list[tuple[int, TechnicalFactCandidateInput]],
    requirement: _ReadinessRequirement,
    source_document_types: dict[str, str],
) -> tuple[int, TechnicalFactCandidateInput]:
    return sorted(
        candidates,
        key=lambda item: _candidate_sort_key(item, requirement, source_document_types),
    )[0]


def _candidate_sort_key(
    item: tuple[int, TechnicalFactCandidateInput],
    requirement: _ReadinessRequirement,
    source_document_types: dict[str, str],
) -> tuple[int, int, int, float, int, int]:
    index, candidate = item
    document_type = source_document_types.get(str(candidate.source_id))
    source_rank = (
        requirement.source_priority.index(document_type)
        if document_type in requirement.source_priority
        else len(requirement.source_priority)
    )
    has_expected_unit = (
        0
        if requirement.target_unit is not None and candidate.unit == requirement.target_unit
        else 1
        if requirement.target_unit is not None
        else 0
    )
    missing_evidence = 0 if candidate.source_evidence_text else 1
    confidence_rank = -(candidate.extractor_confidence or 0.0)
    page_rank = candidate.source_page if candidate.source_page is not None else 9999
    return (source_rank, has_expected_unit, missing_evidence, confidence_rank, page_rank, index)


def _contradiction_review_case(
    requirement: _ReadinessRequirement,
    *,
    selected_index: int,
    selected: TechnicalFactCandidateInput,
    conflicting_candidates: list[tuple[int, TechnicalFactCandidateInput]],
    profile: _GenerationReadinessProfile,
    source_document_types: dict[str, str],
) -> TechnicalReviewCaseInput:
    distinct_values = sorted(
        {
            _candidate_value_key(candidate)
            for _, candidate in conflicting_candidates
            if _candidate_value_key(candidate)
        }
    )
    return TechnicalReviewCaseInput(
        source_id=selected.source_id,
        candidate_index=selected_index,
        case_type=TechnicalReviewCaseType.CONTRADICTION,
        trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
        severity=TechnicalReviewSeverity.BLOCKING,
        field_name=requirement.field_name,
        title=f"Contradiction détectée sur {requirement.field_name}",
        description="Plusieurs valeurs incompatibles ont été extraites avec un score crédible.",
        detected_value=", ".join(distinct_values),
        detected_unit=selected.unit,
        metadata_json={
            "profile_code": profile.profile_code,
            "candidate_index": selected_index,
            "distinct_values": distinct_values,
            "threshold": requirement.conflict_confidence_threshold,
            "candidates": [
                _candidate_metadata(index, candidate, source_document_types)
                for index, candidate in conflicting_candidates
            ],
        },
    )


def _field_check(
    requirement: _ReadinessRequirement,
    *,
    status: str,
    selected_candidates: list[tuple[int, TechnicalFactCandidateInput]] | None = None,
    alternatives: list[tuple[int, TechnicalFactCandidateInput]] | None = None,
    blocking_reason: str | None = None,
    source_document_types: dict[str, str] | None = None,
) -> dict[str, Any]:
    source_document_types = source_document_types or {}
    selected_candidates = selected_candidates or []
    alternatives = alternatives or []
    confidences = [
        candidate.extractor_confidence
        for _, candidate in selected_candidates
        if candidate.extractor_confidence is not None
    ]
    return {
        "field_name": requirement.field_name,
        "level": requirement.level,
        "cardinality": requirement.cardinality,
        "status": status,
        "selected_values": [
            candidate.normalized_value or candidate.raw_value
            for _, candidate in selected_candidates
            if candidate.normalized_value or candidate.raw_value
        ],
        "selected_candidate_indexes": [index for index, _ in selected_candidates],
        "confidence": max(confidences) if confidences else None,
        "threshold": requirement.min_confidence,
        "alternatives": [
            _candidate_metadata(index, candidate, source_document_types)
            for index, candidate in alternatives
        ],
        "blocking_reason": blocking_reason,
    }


def _candidate_metadata(
    index: int,
    candidate: TechnicalFactCandidateInput,
    source_document_types: dict[str, str],
) -> dict[str, Any]:
    return {
        "candidate_index": index,
        "source_id": str(candidate.source_id),
        "source_document_type": source_document_types.get(str(candidate.source_id)),
        "field_name": candidate.field_name,
        "raw_value": candidate.raw_value,
        "normalized_value": candidate.normalized_value,
        "unit": candidate.unit,
        "confidence": candidate.extractor_confidence,
        "evidence_text": candidate.source_evidence_text,
        "page": candidate.source_page,
        "value_key": _candidate_value_key(candidate),
    }


def _candidate_review_case(
    index: int,
    candidate: TechnicalFactCandidateInput,
    *,
    requirement: _ReadinessRequirement,
    profile: _GenerationReadinessProfile,
    low_confidence_threshold: float,
    is_blocking_requirement: bool,
    source_document_types: dict[str, str],
) -> TechnicalReviewCaseInput | None:
    if is_blocking_requirement and not candidate.source_evidence_text:
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
            metadata_json={
                "profile_code": profile.profile_code,
                **_candidate_metadata(index, candidate, source_document_types),
            },
        )

    confidence_threshold = (
        requirement.min_confidence
        if requirement.min_confidence is not None
        else low_confidence_threshold
        if is_blocking_requirement
        else None
    )

    if confidence_threshold is not None and (
        candidate.extractor_confidence is None
        or candidate.extractor_confidence < confidence_threshold
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
            metadata_json={
                **_candidate_metadata(index, candidate, source_document_types),
                "extractor_confidence": candidate.extractor_confidence,
                "threshold": confidence_threshold,
                "profile_code": profile.profile_code,
            },
        )

    if requirement.target_unit is not None and (
        candidate.unit != requirement.target_unit
        if requirement.require_unit
        else candidate.unit is not None and candidate.unit != requirement.target_unit
    ):
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Unité invalide pour {candidate.field_name}",
            description=f"Le champ doit être exprimé en {requirement.target_unit}.",
            detected_value=candidate.raw_value,
            detected_unit=candidate.unit,
            metadata_json={
                **_candidate_metadata(index, candidate, source_document_types),
                "expected_unit": requirement.target_unit,
                "profile_code": profile.profile_code,
            },
        )

    numeric_value = _candidate_numeric_value(candidate)
    if (
        requirement.bounds_min is not None or requirement.bounds_max is not None
    ) and numeric_value is None:
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Valeur numérique invalide pour {candidate.field_name}",
            description="La valeur doit être numérique pour être contrôlée.",
            detected_value=candidate.raw_value,
            detected_unit=candidate.unit,
            metadata_json={
                **_candidate_metadata(index, candidate, source_document_types),
                "bounds": {
                    "min": requirement.bounds_min,
                    "max": requirement.bounds_max,
                },
                "profile_code": profile.profile_code,
            },
        )

    if numeric_value is not None and (
        (requirement.bounds_min is not None and numeric_value < requirement.bounds_min)
        or (requirement.bounds_max is not None and numeric_value > requirement.bounds_max)
    ):
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.VALUE_OUT_OF_RANGE,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Valeur hors borne pour {candidate.field_name}",
            description="La valeur extraite sort des bornes réalistes du profil de génération.",
            detected_value=candidate.normalized_value or candidate.raw_value,
            detected_unit=candidate.unit,
            metadata_json={
                **_candidate_metadata(index, candidate, source_document_types),
                "value": numeric_value,
                "bounds": {
                    "min": requirement.bounds_min,
                    "max": requirement.bounds_max,
                },
                "profile_code": profile.profile_code,
            },
        )

    if is_blocking_requirement and not (candidate.normalized_value or candidate.raw_value):
        return TechnicalReviewCaseInput(
            source_id=candidate.source_id,
            candidate_index=index,
            case_type=TechnicalReviewCaseType.MISSING_REQUIRED_FIELD,
            trigger_source=TechnicalReviewTriggerSource.PYTHON_VALIDATOR,
            severity=TechnicalReviewSeverity.BLOCKING,
            field_name=candidate.field_name,
            title=f"Valeur vide pour {candidate.field_name}",
            description="Le champ requis doit contenir une valeur exploitable.",
            metadata_json={
                "profile_code": profile.profile_code,
                **_candidate_metadata(index, candidate, source_document_types),
            },
        )

    return None


def _parse_generation_readiness_profile(
    snapshot: GenerationReadinessProfileSnapshot,
) -> _GenerationReadinessProfile:
    raw = snapshot.requirements_json or {}
    if not isinstance(raw, dict):
        raise RuntimeError(
            f"Profil readiness invalide: {snapshot.profile_code} requirements_json doit être un objet."
        )

    requirements: list[_ReadinessRequirement] = []
    for item in raw.get("requirements", []):
        if not isinstance(item, dict):
            continue

        field_name = str(item.get("field_name") or "").strip()
        level = str(item.get("level") or "").strip().upper()
        if not field_name or level not in {"REQUIRED", "CONDITIONAL", "OPTIONAL"}:
            raise RuntimeError(
                f"Requirement readiness invalide dans {snapshot.profile_code}: {item!r}"
            )

        raw_bounds = item.get("bounds")
        bounds: dict[str, Any] = raw_bounds if isinstance(raw_bounds, dict) else {}
        raw_defaults = raw.get("defaults")
        defaults: dict[str, Any] = raw_defaults if isinstance(raw_defaults, dict) else {}
        raw_source_priority = item.get("source_priority")
        source_priority = (
            tuple(str(value) for value in raw_source_priority if value)
            if isinstance(raw_source_priority, list)
            else ()
        )
        target_unit = item.get("target_unit") or item.get("unit")
        requirements.append(
            _ReadinessRequirement(
                field_name=field_name,
                level=level,
                target_unit=str(target_unit) if target_unit else None,
                require_unit=bool(item.get("require_unit")),
                min_confidence=_to_float(item.get("min_confidence")),
                conflict_confidence_threshold=(
                    _to_float(item.get("conflict_confidence_threshold"))
                    or _to_float(defaults.get("conflict_confidence_threshold"))
                    or 0.70
                ),
                bounds_min=_to_float(bounds.get("min")),
                bounds_max=_to_float(bounds.get("max")),
                condition=str(item["condition"]) if item.get("condition") else None,
                missing_action=(
                    str(item["missing_action"]).upper() if item.get("missing_action") else None
                ),
                cardinality=str(item.get("cardinality") or "SINGLE").upper(),
                selection_policy=str(item.get("selection_policy") or "CANONICAL_SINGLE").upper(),
                conflict_policy=str(
                    item.get("conflict_policy") or "BLOCK_ON_CREDIBLE_CONFLICT"
                ).upper(),
                source_priority=source_priority,
            )
        )

    if not requirements:
        raise RuntimeError(f"Profil readiness vide: {snapshot.profile_code}")

    return _GenerationReadinessProfile(
        profile_code=snapshot.profile_code,
        famille_code=snapshot.famille_code,
        sous_famille_code=snapshot.sous_famille_code,
        channel_code=snapshot.channel_code,
        requirements=tuple(requirements),
    )


def _initial_generation_readiness_summary(
    profile: _GenerationReadinessProfile,
    document_types: tuple[str, ...],
) -> dict[str, Any]:
    return {
        "profile_code": profile.profile_code,
        "famille_code": profile.famille_code,
        "sous_famille_code": profile.sous_famille_code,
        "channel_code": profile.channel_code,
        "document_types": list(document_types),
        "ready": False,
        "blocking_count": 0,
        "required_fields": [],
        "required_missing": [],
        "low_confidence": [],
        "out_of_bounds": [],
        "contradictions": [],
        "do_not_mention": [],
        "field_checks": [],
    }


def _requirement_is_active(
    requirement: _ReadinessRequirement,
    document_types: tuple[str, ...],
) -> bool:
    if requirement.level != "CONDITIONAL":
        return True

    if requirement.condition == "ASSEMBLY_NOTICE_PRESENT":
        return DocumentType.ASSEMBLY_NOTICE.value in set(document_types)

    return False


def _append_readiness_review(
    readiness: dict[str, Any],
    review_case: TechnicalReviewCaseInput,
) -> None:
    field_name = review_case.field_name or "unknown"
    metadata = review_case.metadata_json if isinstance(review_case.metadata_json, dict) else {}

    if review_case.case_type == TechnicalReviewCaseType.LOW_CONFIDENCE:
        readiness["low_confidence"].append(
            {
                "field_name": field_name,
                "confidence": metadata.get("extractor_confidence"),
                "threshold": metadata.get("threshold"),
            }
        )
    elif review_case.case_type == TechnicalReviewCaseType.VALUE_OUT_OF_RANGE:
        readiness["out_of_bounds"].append(
            {
                "field_name": field_name,
                "value": metadata.get("value", review_case.detected_value),
                "unit": review_case.detected_unit,
                "bounds": metadata.get("bounds"),
                "expected_unit": metadata.get("expected_unit"),
            }
        )
    elif review_case.case_type == TechnicalReviewCaseType.CONTRADICTION:
        readiness["contradictions"].append(
            {
                "field_name": field_name,
                "distinct_values": metadata.get("distinct_values"),
            }
        )


def _candidate_numeric_value(candidate: TechnicalFactCandidateInput) -> float | None:
    value = candidate.normalized_value or candidate.raw_value
    if value is None:
        return None

    match = _NUMBER_PATTERN.search(value)
    if match is None:
        return None

    return _parse_number(match.group("number"))


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _entity_to_candidate_input(
    source_id: uuid.UUID,
    entity: TechnicalDocumentEntity,
) -> TechnicalFactCandidateInput:
    field_name = _canonical_field_name(entity.field_name)

    normalized_value, unit = _normalize_candidate_value(field_name, entity)

    return TechnicalFactCandidateInput(
        source_id=source_id,
        field_name=field_name,
        raw_value=entity.raw_value,
        normalized_value=normalized_value,
        unit=unit,
        extractor_confidence=entity.confidence,
        validation_status=StatutTechnicalFactCandidate.AUTO_VALIDATED,
        review_required=False,
        review_reason=None,
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

    if field_name == "weight":
        return _normalize_weight_kg(raw_value)

    if field_name in {"usage_capacity", "assembly_people_required"}:
        return _normalize_plain_number(raw_value)

    if field_name == "assembly_time":
        return _normalize_time_minutes(raw_value)

    if field_name == "max_torque":
        return _normalize_torque_nm(raw_value)

    return " ".join(raw_value.split()), entity.unit


def _normalize_source_candidate_inputs(
    candidates: list[TechnicalFactCandidateInput],
) -> list[TechnicalFactCandidateInput]:
    dimension_unit_context = _dimension_unit_context(candidates)
    if dimension_unit_context is None:
        return candidates

    normalized_candidates: list[TechnicalFactCandidateInput] = []
    for candidate in candidates:
        if candidate.field_name not in _DIMENSION_FIELDS or candidate.unit is not None:
            normalized_candidates.append(candidate)
            continue

        raw_value = candidate.normalized_value or candidate.raw_value
        if raw_value is None:
            normalized_candidates.append(candidate)
            continue

        normalized_value, unit = _normalize_dimension_cm(
            raw_value,
            unit_context=dimension_unit_context,
        )
        if unit is None:
            normalized_candidates.append(candidate)
            continue

        normalized_candidates.append(
            replace(candidate, normalized_value=normalized_value, unit=unit)
        )

    return normalized_candidates


def _dimension_unit_context(candidates: list[TechnicalFactCandidateInput]) -> str | None:
    for candidate in candidates:
        if candidate.field_name != _DIMENSION_CONTEXT_FIELD:
            continue

        value = candidate.raw_value or candidate.normalized_value or candidate.source_evidence_text
        unit = _extract_dimension_unit(value)
        if unit is not None:
            return unit

    return None


def _extract_dimension_unit(value: str | None) -> str | None:
    if not value:
        return None

    match = _DIMENSION_UNIT_PATTERN.search(value)
    return match.group(1).lower() if match else None


def _normalize_dimension_cm(
    value: str,
    *,
    unit_context: str | None = None,
) -> tuple[str | None, str | None]:
    match = _DIMENSION_PATTERN.search(value)

    if match is None:
        return None, None

    number = _parse_number(match.group("number"))
    if number is None:
        return None, None

    unit = (match.group("unit") or unit_context or "").lower() or None
    if unit is None:
        return _format_number(number), None

    if unit == "mm":
        number = number / 10
    elif unit == "m":
        number = number * 100
    elif unit != "cm":
        return _format_number(number), None

    return _format_number(number), "cm"


def _normalize_weight_kg(value: str) -> tuple[str | None, str | None]:
    match = _WEIGHT_PATTERN.search(value)

    if match is None:
        return None, None

    number = _parse_number(match.group("number"))
    if number is None:
        return None, None

    unit = (match.group("unit") or "").lower() or None
    if unit is None:
        return _format_number(number), None

    if unit == "g":
        number = number / 1000
    elif unit == "t":
        number = number * 1000
    elif unit != "kg":
        return _format_number(number), None

    return _format_number(number), "kg"


def _normalize_time_minutes(value: str) -> tuple[str | None, str | None]:
    match = _TIME_PATTERN.search(value)

    if match is None:
        return None, None

    number = _parse_number(match.group("number"))
    if number is None:
        return None, None

    unit = (match.group("unit") or "").lower() or None
    if unit is None:
        return _format_number(number), None

    if unit in {"h", "heure", "heures"}:
        number = number * 60

    return _format_number(number), "minutes"


def _normalize_torque_nm(value: str) -> tuple[str | None, str | None]:
    match = _TORQUE_PATTERN.search(value)

    if match is None:
        return None, None

    number = _parse_number(match.group("number"))
    if number is None:
        return None, None

    unit = match.group("unit")
    return _format_number(number), "N·m" if unit else None


def _normalize_plain_number(
    value: str, *, unit: str | None = None
) -> tuple[str | None, str | None]:
    match = _NUMBER_PATTERN.search(value)

    if match is None:
        return None, unit

    number = _parse_number(match.group("number"))
    return _format_number(number) if number is not None else None, unit


def _parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.replace("\u00a0", " ").replace(" ", "").replace(",", ".")
    try:
        return float(normalized)
    except ValueError:
        return None


def _format_number(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def _canonical_field_name(value: str) -> str:
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    return _FIELD_NAME_ALIASES.get(normalized, normalized)


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
        occurrence_index=promoted_fact.occurrence_index,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _promoted_fact_payload_to_input(
    promoted_fact: PromotedTechnicalFactPayload,
) -> PromotedTechnicalFactInput:
    return PromotedTechnicalFactInput(
        candidate_index=promoted_fact.candidate_index,
        field_name=promoted_fact.field_name,
        occurrence_index=promoted_fact.occurrence_index,
        value=promoted_fact.value,
        unit=promoted_fact.unit,
    )


def _technical_fact_snapshot_to_dict(fact: TechnicalFactSnapshot) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "field_name": fact.field_name,
        "occurrence_index": fact.occurrence_index,
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
    readiness_status: str,
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
        "readinessStatus": readiness_status,
        "styleGuideReady": style_guide_ready,
        "commercialSignalsReady": commercial_signals_ready,
        "createdAt": product.created_at.isoformat() if product.created_at is not None else None,
    }


def _product_readiness_status_from_overview(overview: dict[str, Any]) -> str:
    run = overview.get("run")
    sources = overview.get("sources") or []
    review_cases = overview.get("review_cases") or []

    if overview.get("product_context_snapshot") is not None:
        return "CONTEXT_READY"

    if isinstance(run, dict):
        run_status = run.get("statut")
        if run_status == "ERREUR":
            return "FAILED"

        if any(
            case.get("status") in {"A_TRAITER", "DOCUMENT_A_REMPLACER"}
            for case in review_cases
            if isinstance(case, dict)
        ):
            return "PENDING_TECH_REVIEW"

        return "INGESTION_RUNNING"

    if len(sources) > 0:
        return "TECHNICAL_SOURCES_UPLOADED"

    return "PRODUCT_CREATED"


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
