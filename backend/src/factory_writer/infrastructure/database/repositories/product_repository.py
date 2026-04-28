from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from factory_writer.application.ports.product_technical_ingestion import (
    CommercialSignalSnapshotSelection,
    DocumentSourceSnapshot,
    IngestionRunSnapshot,
    ProductContextSnapshotResult,
    ProductSheetGenerationContext,
    ProductSheetGenerationSnapshot,
    ProductSheetRequirementProfileSnapshot,
    ProductSnapshot,
    ProductTaxonomySnapshot,
    PromotedTechnicalFactInput,
    StylePackRuntimeSnapshot,
    TechnicalFactCandidateInput,
    TechnicalFactSnapshot,
    TechnicalIngestionStartPreparation,
    TechnicalReviewCaseInput,
    TechnicalSourcesLotReplacementResult,
    UploadedTechnicalSourceData,
)
from factory_writer.domain.document_ingestion_types import (
    CollectionKind,
    CurrentStep,
    DocumentType,
    ExtractionMethod,
    ProductSheetGenerationStatus,
    StatutDocumentCollection,
    StatutDocumentIngestionRun,
    StatutStylePack,
    StatutTechnicalFactCandidate,
    TechnicalFactValidationSource,
    TechnicalReviewCaseType,
    TechnicalReviewResolutionAction,
    TechnicalReviewSeverity,
    TechnicalReviewStatus,
)
from factory_writer.domain.style_guide_types import StatutSource
from factory_writer.infrastructure.database.models.poc_ingestion import (
    CommercialSignalSnapshot,
    DocumentCollection,
    DocumentIngestionRun,
    DocumentSource,
    Product,
    ProductContextSnapshot,
    ProductSheetGeneration,
    ProductSheetRequirementProfile,
    StylePack,
    StyleRule,
    TechnicalFact,
    TechnicalFactCandidate,
    TechnicalReviewCase,
)
from factory_writer.infrastructure.database.models.taxonomy import TaxonomieProduit
from factory_writer.infrastructure.database.repositories.product_repository_mappers import (
    _active_current_sources,
    _candidate_to_dict,
    _choose_commercial_snapshot,
    _collection_to_dict,
    _commercial_snapshot_missing_message,
    _is_routable_technical_document_type,
    _product_sheet_generation_to_dict,
    _product_sheet_requirement_profile_specificity,
    _product_taxonomy_load_option,
    _product_to_dict,
    _review_case_metadata_with_candidate_ids,
    _review_case_occurrence_index,
    _review_case_to_dict,
    _run_to_dict,
    _source_to_dict,
    _technical_classifications_to_dict,
    _technical_fact_to_dict,
    _to_document_type,
    _to_product_context_snapshot_result,
    _to_product_sheet_generation_snapshot,
    _to_product_sheet_requirement_profile_snapshot,
)


class ProductRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

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
    ) -> ProductSnapshot:
        async with self._session_factory() as session, session.begin():
            existing_product = await session.scalar(select(Product).where(Product.sku == sku))

            if existing_product is not None:
                raise RuntimeError(f"Un produit existe déjà avec le SKU {sku}.")

            taxonomy = await self._resolve_product_taxonomy(
                session,
                famille_code=famille_code,
                sous_famille_code=sous_famille_code,
            )
            product = Product(
                sku=sku,
                name=name,
                taxonomie_produit_id=taxonomy.id,
                taxonomie_produit=taxonomy,
                sous_famille_code=(
                    taxonomy.famille_code if taxonomy.parent_id is not None else None
                ),
                season_code=season_code,
                segment_prix_code=segment_prix_code,
                langue_principale=langue_principale,
            )
            session.add(product)
            await session.flush()
            return self._to_product_snapshot(product)

    async def get_product(self, product_id: uuid.UUID) -> ProductSnapshot | None:
        async with self._session_factory() as session:
            product = await self._get_product(session, product_id)
            return self._to_product_snapshot(product) if product is not None else None

    async def list_products(self, *, limit: int = 50) -> tuple[ProductSnapshot, ...]:
        async with self._session_factory() as session:
            stmt = (
                select(Product)
                .options(_product_taxonomy_load_option())
                .order_by(Product.created_at.desc())
                .limit(limit)
            )

            products = list((await session.scalars(stmt)).all())

            return tuple(self._to_product_snapshot(product) for product in products)

    async def list_product_taxonomies(self) -> tuple[ProductTaxonomySnapshot, ...]:
        async with self._session_factory() as session:
            stmt = select(TaxonomieProduit).order_by(
                TaxonomieProduit.parent_id.asc().nullsfirst(),
                TaxonomieProduit.libelle_fr.asc(),
                TaxonomieProduit.famille_code.asc(),
            )

            taxonomies = list((await session.scalars(stmt)).all())

            return tuple(self._to_product_taxonomy_snapshot(taxonomy) for taxonomy in taxonomies)

    async def create_technical_sources(
        self,
        *,
        product_id: uuid.UUID,
        sources: list[UploadedTechnicalSourceData],
    ) -> tuple[DocumentSourceSnapshot, ...]:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id)
            collection = await self._get_or_create_open_technical_collection(
                session,
                product,
            )
            existing_sources = await self._list_collection_sources(session, collection.id)
            persisted_sources: list[DocumentSource] = []
            for source in sources:
                document_source = DocumentSource(
                    id=source.document_source_id,
                    collection_id=collection.id,
                    original_file_name=source.original_file_name,
                    storage_uri=source.storage_uri,
                    storage_bucket=source.storage_bucket,
                    storage_object_name=source.storage_object_name,
                    storage_generation=source.storage_generation,
                    storage_metageneration=source.storage_metageneration,
                    storage_content_type=source.storage_content_type,
                    storage_size_bytes=source.storage_size_bytes,
                    document_type=DocumentType.UNKNOWN,
                    classification_confidence=None,
                    statut=StatutSource.EN_ATTENTE,
                )
                session.add(document_source)
                persisted_sources.append(document_source)
            await session.flush()

            new_source_ids_by_file_name = {
                source.original_file_name: source.id for source in persisted_sources
            }
            for existing_source in existing_sources:
                replacement_id = new_source_ids_by_file_name.get(existing_source.original_file_name)
                if (
                    replacement_id is not None
                    and existing_source.id != replacement_id
                    and existing_source.replaced_by_source_id is None
                ):
                    existing_source.replaced_by_source_id = replacement_id
            await session.flush()

            return tuple(self._to_source_snapshot(source) for source in persisted_sources)

    async def replace_technical_sources_lot(
        self,
        *,
        product_id: uuid.UUID,
        sources: list[UploadedTechnicalSourceData],
    ) -> TechnicalSourcesLotReplacementResult:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id, for_update=True)
            previous_collection = await self._get_latest_technical_collection(
                session,
                product.id,
                for_update=True,
            )
            replaced_ingestion_run_id: uuid.UUID | None = None

            new_collection = DocumentCollection(
                collection_kind=CollectionKind.TECHNICAL_DOSSIER,
                product_id=product.id,
                statut=StatutDocumentCollection.EN_ATTENTE,
            )
            session.add(new_collection)
            await session.flush()

            if previous_collection is not None:
                previous_collection.replaced_by_collection_id = new_collection.id
                previous_collection.statut = StatutDocumentCollection.ERREUR
                previous_collection.dernier_message_erreur = (
                    "Lot technique remplacé par un nouvel import."
                )
                replaced_ingestion_run_id = await self._cancel_latest_run_for_replaced_lot(
                    session,
                    previous_collection.id,
                )

            persisted_sources: list[DocumentSource] = []
            for source in sources:
                document_source = DocumentSource(
                    id=source.document_source_id,
                    collection_id=new_collection.id,
                    original_file_name=source.original_file_name,
                    storage_uri=source.storage_uri,
                    storage_bucket=source.storage_bucket,
                    storage_object_name=source.storage_object_name,
                    storage_generation=source.storage_generation,
                    storage_metageneration=source.storage_metageneration,
                    storage_content_type=source.storage_content_type,
                    storage_size_bytes=source.storage_size_bytes,
                    document_type=DocumentType.UNKNOWN,
                    classification_confidence=None,
                    statut=StatutSource.EN_ATTENTE,
                )
                session.add(document_source)
                persisted_sources.append(document_source)

            await session.flush()
            return TechnicalSourcesLotReplacementResult(
                sources=tuple(self._to_source_snapshot(source) for source in persisted_sources),
                replaced_ingestion_run_id=replaced_ingestion_run_id,
            )

    async def prepare_technical_ingestion_start(
        self,
        *,
        product_id: uuid.UUID,
    ) -> TechnicalIngestionStartPreparation:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id, for_update=True)
            collection = await self._get_latest_technical_collection(
                session,
                product_id,
                for_update=True,
            )
            if collection is None:
                raise RuntimeError("Aucun dossier technique uploadé pour ce produit.")

            sources = list(_active_current_sources(collection.document_sources))
            if not sources:
                raise RuntimeError("Aucun PDF technique actif pour ce produit.")

            latest_run = await self._get_latest_run(session, collection.id, for_update=True)
            if latest_run is not None and latest_run.statut == StatutDocumentIngestionRun.EN_COURS:
                return TechnicalIngestionStartPreparation(
                    product=self._to_product_snapshot(product),
                    collection_id=collection.id,
                    run=self._to_run_snapshot(latest_run),
                    sources=tuple(self._to_source_snapshot(source) for source in sources),
                    reused_existing_run=True,
                )

            run_id = uuid.uuid4()
            workflow_id = f"technical-dossier-{run_id}"
            run = DocumentIngestionRun(
                id=run_id,
                collection_id=collection.id,
                pipeline_kind="TECHNICAL_DOSSIER_EXTRACTION",
                statut=StatutDocumentIngestionRun.EN_COURS,
                current_step=CurrentStep.UPLOAD,
                temporal_workflow_id=workflow_id,
                started_at=datetime.now(UTC),
            )
            collection.statut = StatutDocumentCollection.EN_COURS
            for source in sources:
                source.statut = StatutSource.EN_COURS
            session.add(run)
            await session.flush()

            return TechnicalIngestionStartPreparation(
                product=self._to_product_snapshot(product),
                collection_id=collection.id,
                run=self._to_run_snapshot(run),
                sources=tuple(self._to_source_snapshot(source) for source in sources),
                reused_existing_run=False,
            )

    async def get_technical_ingestion_context(
        self,
        *,
        product_id: uuid.UUID,
        document_source_ids: tuple[uuid.UUID, ...],
        ingestion_run_id: uuid.UUID | None = None,
    ) -> dict[str, Any]:
        async with self._session_factory() as session:
            product = await self._require_product(session, product_id)
            source_stmt = (
                select(DocumentSource)
                .where(DocumentSource.id.in_(document_source_ids))
                .options(selectinload(DocumentSource.collection))
            )
            sources = list((await session.scalars(source_stmt)).all())
            if not sources:
                raise RuntimeError("Aucune source technique trouvée pour l'ingestion.")
            collection_ids = {source.collection_id for source in sources}
            if len(collection_ids) != 1:
                raise RuntimeError("Les sources techniques ne sont pas dans le même dossier.")

            collection_id = next(iter(collection_ids))
            if sources[0].collection.product_id != product.id:
                raise RuntimeError("Les sources techniques n'appartiennent pas au produit demandé.")
            run = (
                await self._require_run(session, ingestion_run_id)
                if ingestion_run_id is not None
                else await self._get_latest_run(session, collection_id)
            )
            if run is None:
                raise RuntimeError("Aucun run technique en cours pour ce dossier.")
            if run.collection_id != collection_id:
                raise RuntimeError("Le run technique ne correspond pas aux sources reçues.")

            return {
                "product": self._to_product_snapshot(product),
                "run": self._to_run_snapshot(run),
                "sources": tuple(self._to_source_snapshot(source) for source in sources),
            }

    async def select_commercial_signal_snapshot(
        self,
        *,
        product: ProductSnapshot,
    ) -> CommercialSignalSnapshotSelection:
        if product.season_code is None or product.segment_prix_code is None:
            raise RuntimeError(_commercial_snapshot_missing_message(product))

        async with self._session_factory() as session:
            stmt = (
                select(CommercialSignalSnapshot)
                .where(
                    CommercialSignalSnapshot.is_active.is_(True),
                    CommercialSignalSnapshot.famille_code == product.famille_code,
                    CommercialSignalSnapshot.season_code == product.season_code,
                    CommercialSignalSnapshot.segment_prix_code == product.segment_prix_code,
                )
                .order_by(CommercialSignalSnapshot.created_at.desc())
            )
            snapshots = list((await session.scalars(stmt)).all())
            snapshot, reason = _choose_commercial_snapshot(product, snapshots)

            return CommercialSignalSnapshotSelection(
                id=snapshot.id,
                snapshot_id=snapshot.snapshot_id,
                cohort_key=snapshot.cohort_key,
                famille_code=snapshot.famille_code,
                segment_prix_code=snapshot.segment_prix_code,
                season_code=snapshot.season_code,
                sales_signals_json=snapshot.sales_signals_json,
                feedback_signals_json=snapshot.feedback_signals_json,
                selection_reason=reason,
                matched_fields={
                    "famille_code": product.famille_code,
                    "segment_prix_code": product.segment_prix_code,
                    "season_code": product.season_code,
                },
            )

    async def load_product_sheet_requirement_profile(
        self,
        *,
        product: ProductSnapshot,
    ) -> ProductSheetRequirementProfileSnapshot:
        async with self._session_factory() as session:
            stmt = (
                select(ProductSheetRequirementProfile)
                .where(
                    ProductSheetRequirementProfile.is_active.is_(True),
                    ProductSheetRequirementProfile.famille_code.in_([product.famille_code, "*"]),
                )
                .order_by(ProductSheetRequirementProfile.created_at.desc())
            )
            profiles = list((await session.scalars(stmt)).all())

            matching_profiles = [
                profile
                for profile in profiles
                if profile.sous_famille_code in {product.sous_famille_code, None, "*"}
            ]
            if not matching_profiles:
                raise RuntimeError(
                    "Aucun profil de prérequis fiche produit actif pour "
                    f"{product.famille_code}/{product.sous_famille_code or '*'}."
                )

            selected = max(
                matching_profiles,
                key=lambda profile: _product_sheet_requirement_profile_specificity(
                    product=product,
                    profile=profile,
                ),
            )
            return _to_product_sheet_requirement_profile_snapshot(selected)

    async def load_active_style_pack(self) -> StylePackRuntimeSnapshot:
        async with self._session_factory() as session:
            stmt = select(StylePack).where(
                StylePack.est_actif.is_(True),
                StylePack.statut == StatutStylePack.ACTIF,
            )
            style_pack = (await session.scalars(stmt)).first()
            if style_pack is None:
                raise RuntimeError("Aucun style pack actif disponible.")
            return StylePackRuntimeSnapshot(
                style_pack_id=str(style_pack.id),
                version_label=f"{style_pack.prompt_name}:{style_pack.prompt_version}",
            )

    async def update_ingestion_run_step(
        self,
        *,
        run_id: uuid.UUID,
        current_step: CurrentStep,
        statut: StatutDocumentIngestionRun | None = None,
        extraction_steps_json: Any | None = None,
    ) -> IngestionRunSnapshot:
        async with self._session_factory() as session, session.begin():
            run = await self._require_run(session, run_id, for_update=True)
            run.current_step = current_step
            if statut is not None:
                run.statut = statut
            if extraction_steps_json is not None:
                run.extraction_steps_json = extraction_steps_json
            await session.flush()
            return self._to_run_snapshot(run)

    async def update_source_classification(
        self,
        *,
        source_id: uuid.UUID,
        document_type: str,
        confidence: float | None,
        quality_metadata_json: Any | None,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            source = await session.get(DocumentSource, source_id)
            if source is None:
                raise RuntimeError(f"Source technique introuvable: {source_id}")
            source.document_type = _to_document_type(document_type)
            source.classification_confidence = confidence
            source.quality_metadata_json = quality_metadata_json

    async def create_classification_review_cases(
        self,
        *,
        run_id: uuid.UUID,
        review_cases: list[TechnicalReviewCaseInput],
        extraction_steps_json: Any,
    ) -> int:
        async with self._session_factory() as session, session.begin():
            run = await self._require_run(session, run_id, for_update=True)
            collection = await self._require_collection(session, run.collection_id)

            await session.execute(
                delete(TechnicalReviewCase).where(
                    TechnicalReviewCase.ingestion_run_id == run_id,
                    TechnicalReviewCase.case_type
                    == TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN,
                )
            )
            await session.flush()

            for review_case in review_cases:
                session.add(
                    TechnicalReviewCase(
                        ingestion_run_id=run.id,
                        source_id=review_case.source_id,
                        fact_candidate_id=None,
                        case_type=review_case.case_type,
                        trigger_source=review_case.trigger_source,
                        severity=review_case.severity,
                        status=TechnicalReviewStatus.A_TRAITER,
                        field_name=review_case.field_name,
                        title=review_case.title,
                        description=review_case.description,
                        detected_value=review_case.detected_value,
                        detected_unit=review_case.detected_unit,
                        suggested_value=review_case.suggested_value,
                        suggested_unit=review_case.suggested_unit,
                        metadata_json=review_case.metadata_json,
                    )
                )

            run.statut = StatutDocumentIngestionRun.A_VALIDER
            run.current_step = CurrentStep.HUMAN_REVIEW
            run.extraction_steps_json = extraction_steps_json
            run.completed_at = None
            collection.statut = StatutDocumentCollection.A_VALIDER
            await session.flush()
            return len(review_cases)

    async def persist_technical_fact_candidates(
        self,
        *,
        product_id: uuid.UUID,
        run_id: uuid.UUID,
        candidates: list[TechnicalFactCandidateInput],
        extraction_steps_json: Any,
    ) -> IngestionRunSnapshot:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id, for_update=True)
            run = await self._require_run(session, run_id, for_update=True)

            await session.execute(
                delete(TechnicalReviewCase).where(TechnicalReviewCase.ingestion_run_id == run_id)
            )
            await session.execute(
                delete(TechnicalFactCandidate).where(
                    TechnicalFactCandidate.ingestion_run_id == run_id
                )
            )
            await session.execute(
                delete(TechnicalFact).where(TechnicalFact.product_id == product.id)
            )
            await session.flush()

            for candidate in candidates:
                session.add(
                    TechnicalFactCandidate(
                        ingestion_run_id=run.id,
                        source_id=candidate.source_id,
                        field_name=candidate.field_name,
                        raw_value=candidate.raw_value,
                        normalized_value=candidate.normalized_value,
                        unit=candidate.unit,
                        extractor_confidence=candidate.extractor_confidence,
                        extraction_method=ExtractionMethod.EXTRACT,
                        validation_status=candidate.validation_status,
                        source_page=candidate.source_page,
                    )
                )

            run.current_step = CurrentStep.DETERMINISTIC_VALIDATION
            run.extraction_steps_json = extraction_steps_json
            await session.flush()
            return self._to_run_snapshot(run)

    async def complete_technical_ingestion(
        self,
        *,
        product_id: uuid.UUID,
        run_id: uuid.UUID,
        candidates: list[TechnicalFactCandidateInput],
        review_cases: list[TechnicalReviewCaseInput],
        promoted_facts: list[PromotedTechnicalFactInput],
        extraction_steps_json: Any,
        validation_summary_json: Any,
        requires_review: bool,
    ) -> IngestionRunSnapshot:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id, for_update=True)
            run = await self._require_run(session, run_id, for_update=True)
            collection = await self._require_collection(session, run.collection_id)

            await session.execute(
                delete(TechnicalReviewCase).where(TechnicalReviewCase.ingestion_run_id == run_id)
            )
            await session.execute(
                delete(TechnicalFactCandidate).where(
                    TechnicalFactCandidate.ingestion_run_id == run_id
                )
            )
            await session.execute(
                delete(TechnicalFact).where(TechnicalFact.product_id == product.id)
            )
            await session.flush()

            persisted_candidates: list[TechnicalFactCandidate] = []
            for candidate in candidates:
                persisted = TechnicalFactCandidate(
                    ingestion_run_id=run.id,
                    source_id=candidate.source_id,
                    field_name=candidate.field_name,
                    raw_value=candidate.raw_value,
                    normalized_value=candidate.normalized_value,
                    unit=candidate.unit,
                    extractor_confidence=candidate.extractor_confidence,
                    extraction_method=ExtractionMethod.EXTRACT,
                    validation_status=candidate.validation_status,
                    source_page=candidate.source_page,
                )
                session.add(persisted)
                persisted_candidates.append(persisted)
            await session.flush()

            for review_case in review_cases:
                metadata_json = _review_case_metadata_with_candidate_ids(
                    review_case.metadata_json,
                    persisted_candidates,
                )
                persisted_case = TechnicalReviewCase(
                    ingestion_run_id=run.id,
                    source_id=review_case.source_id,
                    fact_candidate_id=(
                        persisted_candidates[review_case.candidate_index].id
                        if review_case.candidate_index is not None
                        else None
                    ),
                    case_type=review_case.case_type,
                    trigger_source=review_case.trigger_source,
                    severity=review_case.severity,
                    status=TechnicalReviewStatus.A_TRAITER,
                    field_name=review_case.field_name,
                    title=review_case.title,
                    description=review_case.description,
                    detected_value=review_case.detected_value,
                    detected_unit=review_case.detected_unit,
                    suggested_value=review_case.suggested_value,
                    suggested_unit=review_case.suggested_unit,
                    metadata_json=metadata_json,
                )
                session.add(persisted_case)

            now = datetime.now(UTC)
            for promoted in promoted_facts:
                persisted_candidate = persisted_candidates[promoted.candidate_index]
                persisted_candidate.validation_status = StatutTechnicalFactCandidate.PROMOTED
                fact = TechnicalFact(
                    product_id=product.id,
                    source_candidate_id=persisted_candidate.id,
                    field_name=promoted.field_name,
                    occurrence_index=promoted.occurrence_index,
                    value=promoted.value,
                    unit=promoted.unit,
                    validation_source=TechnicalFactValidationSource.SYSTEM,
                    validated_at=now,
                    validated_by="system",
                )
                session.add(fact)

            final_run_status = (
                StatutDocumentIngestionRun.A_VALIDER
                if requires_review
                else StatutDocumentIngestionRun.TERMINE
            )
            final_collection_status = (
                StatutDocumentCollection.A_VALIDER
                if requires_review
                else StatutDocumentCollection.TERMINE
            )
            final_source_status = StatutSource.TERMINE
            run.statut = final_run_status
            run.current_step = CurrentStep.HUMAN_REVIEW if requires_review else CurrentStep.DONE
            run.validation_summary_json = validation_summary_json
            run.extraction_steps_json = extraction_steps_json
            run.completed_at = None if requires_review else now
            collection.statut = final_collection_status
            for source in collection.document_sources:
                source.statut = final_source_status
            await session.flush()
            return self._to_run_snapshot(run)

    async def list_technical_facts(
        self, *, product_id: uuid.UUID
    ) -> tuple[TechnicalFactSnapshot, ...]:
        async with self._session_factory() as session:
            facts = list(
                (
                    await session.scalars(
                        select(TechnicalFact)
                        .where(TechnicalFact.product_id == product_id)
                        .order_by(TechnicalFact.field_name, TechnicalFact.occurrence_index)
                    )
                ).all()
            )
            return tuple(
                TechnicalFactSnapshot(
                    id=fact.id,
                    field_name=fact.field_name,
                    occurrence_index=fact.occurrence_index,
                    value=fact.value,
                    unit=fact.unit,
                )
                for fact in facts
            )

    async def create_product_context_snapshot(
        self,
        *,
        product_id: uuid.UUID,
        technical_ingestion_run_id: uuid.UUID,
        style_pack_id: uuid.UUID,
        commercial_signal_snapshot_id: uuid.UUID,
        technical_fact_ids: tuple[uuid.UUID, ...],
        snapshot_json: Any,
    ) -> ProductContextSnapshotResult:
        async with self._session_factory() as session, session.begin():
            existing = (
                await session.scalars(
                    select(ProductContextSnapshot).where(
                        ProductContextSnapshot.product_id == product_id,
                        ProductContextSnapshot.technical_ingestion_run_id
                        == technical_ingestion_run_id,
                    )
                )
            ).first()
            if existing is not None:
                return _to_product_context_snapshot_result(existing)

            await self._require_product(session, product_id)
            run = await self._require_run(session, technical_ingestion_run_id, for_update=True)
            style_pack = await session.get(StylePack, style_pack_id)
            commercial_snapshot = await session.get(
                CommercialSignalSnapshot,
                commercial_signal_snapshot_id,
            )
            if style_pack is None:
                raise RuntimeError("Style pack introuvable pour le contexte produit.")
            if commercial_snapshot is None:
                raise RuntimeError("Snapshot commercial introuvable pour le contexte produit.")

            context_snapshot = ProductContextSnapshot(
                product_id=product_id,
                technical_ingestion_run_id=technical_ingestion_run_id,
                style_pack_id=style_pack_id,
                commercial_signal_snapshot_id=commercial_signal_snapshot_id,
                technical_fact_ids=[str(fact_id) for fact_id in technical_fact_ids],
                snapshot_json=snapshot_json,
            )
            session.add(context_snapshot)

            validation_summary = dict(run.validation_summary_json or {})
            validation_summary["product_context_snapshot"] = {
                "style_pack_id": str(style_pack_id),
                "commercial_signal_snapshot_id": str(commercial_signal_snapshot_id),
                "technical_fact_ids": [str(fact_id) for fact_id in technical_fact_ids],
            }
            run.validation_summary_json = validation_summary
            await session.flush()
            return _to_product_context_snapshot_result(context_snapshot)

    async def prepare_product_sheet_generation(
        self,
        *,
        product_id: uuid.UUID,
    ) -> ProductSheetGenerationSnapshot:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id, for_update=True)
            context_snapshot = await self._get_latest_product_context_snapshot(
                session,
                product.id,
            )
            if context_snapshot is None:
                raise RuntimeError(
                    "Le contexte produit n'est pas prêt pour générer la fiche produit."
                )

            existing = await self._get_latest_product_sheet_generation(
                session,
                product.id,
                context_snapshot.id,
                for_update=True,
            )
            if existing is not None and existing.status in {
                ProductSheetGenerationStatus.EN_COURS,
                ProductSheetGenerationStatus.TERMINE,
                ProductSheetGenerationStatus.A_VALIDER,
            }:
                return _to_product_sheet_generation_snapshot(existing)

            now = datetime.now(UTC)
            generation = ProductSheetGeneration(
                product_id=product.id,
                product_context_snapshot_id=context_snapshot.id,
                status=ProductSheetGenerationStatus.EN_COURS,
                started_at=now,
            )
            session.add(generation)
            await session.flush()
            return _to_product_sheet_generation_snapshot(generation)

    async def mark_product_sheet_generation_started(
        self,
        *,
        generation_id: uuid.UUID,
        workflow_id: str,
    ) -> ProductSheetGenerationSnapshot:
        async with self._session_factory() as session, session.begin():
            generation = await self._require_product_sheet_generation(
                session,
                generation_id,
                for_update=True,
            )
            generation.workflow_id = workflow_id
            generation.status = ProductSheetGenerationStatus.EN_COURS
            generation.error_message = None
            if generation.started_at is None:
                generation.started_at = datetime.now(UTC)
            await session.flush()
            return _to_product_sheet_generation_snapshot(generation)

    async def load_product_sheet_generation_context(
        self,
        *,
        generation_id: uuid.UUID,
    ) -> ProductSheetGenerationContext:
        async with self._session_factory() as session:
            generation = await self._require_product_sheet_generation(
                session,
                generation_id,
                load_context=True,
            )
            product = generation.product
            context_snapshot = generation.product_context_snapshot
            style_pack = context_snapshot.style_pack
            commercial_snapshot = context_snapshot.commercial_signal_snapshot
            facts = await self._list_technical_facts_by_ids(
                session,
                tuple(uuid.UUID(value) for value in context_snapshot.technical_fact_ids),
            )
            return ProductSheetGenerationContext(
                generation=_to_product_sheet_generation_snapshot(generation),
                product=self._to_product_snapshot(product),
                product_context_snapshot_id=context_snapshot.id,
                product_context_snapshot_json=context_snapshot.snapshot_json,
                technical_facts=facts,
                style_rules_json=tuple(
                    {
                        "type_regle": rule.type_regle.value,
                        "niveau_contrainte": rule.niveau_contrainte.value,
                        "texte_regle": rule.texte_regle,
                        "famille_code": (
                            rule.taxonomie_produit.famille_code
                            if rule.taxonomie_produit is not None
                            else None
                        ),
                    }
                    for rule in style_pack.style_rules
                    if rule.est_actif
                ),
                commercial_signals_json={
                    "snapshot_id": commercial_snapshot.snapshot_id,
                    "cohort_key": commercial_snapshot.cohort_key,
                    "famille_code": commercial_snapshot.famille_code,
                    "segment_prix_code": commercial_snapshot.segment_prix_code,
                    "season_code": commercial_snapshot.season_code,
                    "sales_signals": commercial_snapshot.sales_signals_json,
                    "feedback_signals": commercial_snapshot.feedback_signals_json,
                },
            )

    async def complete_product_sheet_generation(
        self,
        *,
        generation_id: uuid.UUID,
        status: str,
        prompt_registry_provider: str,
        prompt_name: str,
        prompt_version: str,
        llm_model: str,
        llm_temperature: float,
        llm_max_tokens: int,
        llm_response_format_name: str,
        rendered_system_prompt_hash: str,
        rendered_user_prompt_hash: str,
        sheet_json: Any,
        self_check_json: Any,
    ) -> ProductSheetGenerationSnapshot:
        async with self._session_factory() as session, session.begin():
            generation = await self._require_product_sheet_generation(
                session,
                generation_id,
                for_update=True,
            )
            generation.status = ProductSheetGenerationStatus(status)
            generation.prompt_registry_provider = prompt_registry_provider
            generation.prompt_name = prompt_name
            generation.prompt_version = prompt_version
            generation.llm_model = llm_model
            generation.llm_temperature = llm_temperature
            generation.llm_max_tokens = llm_max_tokens
            generation.llm_response_format_name = llm_response_format_name
            generation.rendered_system_prompt_hash = rendered_system_prompt_hash
            generation.rendered_user_prompt_hash = rendered_user_prompt_hash
            generation.sheet_json = sheet_json
            generation.self_check_json = self_check_json
            generation.error_message = None
            generation.completed_at = datetime.now(UTC)
            await session.flush()
            return _to_product_sheet_generation_snapshot(generation)

    async def mark_product_sheet_generation_failed(
        self,
        *,
        generation_id: uuid.UUID,
        error_message: str,
    ) -> ProductSheetGenerationSnapshot:
        async with self._session_factory() as session, session.begin():
            generation = await self._require_product_sheet_generation(
                session,
                generation_id,
                for_update=True,
            )
            generation.status = ProductSheetGenerationStatus.ERREUR
            generation.error_message = error_message
            generation.completed_at = datetime.now(UTC)
            await session.flush()
            return _to_product_sheet_generation_snapshot(generation)

    async def list_products_for_style_pack_activation(
        self,
        *,
        max_results: int = 250,
    ) -> tuple[ProductSnapshot, ...]:
        async with self._session_factory() as session:
            products = list(
                (
                    await session.scalars(
                        select(Product)
                        .options(_product_taxonomy_load_option())
                        .order_by(Product.created_at.desc())
                        .limit(max_results)
                    )
                ).all()
            )
            return tuple(self._to_product_snapshot(product) for product in products)

    async def mark_technical_ingestion_failed(
        self,
        *,
        product_id: uuid.UUID,
        error_message: str,
    ) -> None:
        async with self._session_factory() as session, session.begin():
            collection = await self._get_latest_technical_collection(
                session,
                product_id,
                for_update=True,
            )
            if collection is None:
                return
            collection.statut = StatutDocumentCollection.ERREUR
            collection.dernier_message_erreur = error_message
            run = await self._get_latest_run(session, collection.id, for_update=True)
            if run is not None:
                run.statut = StatutDocumentIngestionRun.ERREUR
                run.error_message = error_message
                run.completed_at = datetime.now(UTC)
            for source in collection.document_sources:
                source.statut = StatutSource.ERREUR
                source.dernier_message_erreur = error_message

    async def resolve_review_case(
        self,
        *,
        product_id: uuid.UUID,
        case_id: uuid.UUID,
        action: TechnicalReviewResolutionAction,
        resolved_by: str,
        corrected_value: str | None,
        corrected_unit: str | None,
        selected_candidate_id: uuid.UUID | None,
        comment: str | None,
    ) -> dict[str, Any]:
        async with self._session_factory() as session, session.begin():
            product = await self._require_product(session, product_id)
            stmt = (
                select(TechnicalReviewCase)
                .where(TechnicalReviewCase.id == case_id)
                .options(
                    selectinload(TechnicalReviewCase.ingestion_run).selectinload(
                        DocumentIngestionRun.collection
                    )
                )
                .with_for_update()
            )
            review_case = (await session.scalars(stmt)).first()
            if review_case is None:
                raise RuntimeError("Cas de revue technique introuvable.")
            if review_case.ingestion_run.collection.product_id != product.id:
                raise RuntimeError("Ce cas de revue n'appartient pas au produit demandé.")

            review_case.resolution_action = action
            review_case.resolution_comment = comment
            review_case.resolved_by = resolved_by
            review_case.resolved_at = datetime.now(UTC)

            is_classification_review = (
                review_case.case_type == TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN
            )

            if is_classification_review:
                await self._resolve_classification_review_case(
                    session,
                    review_case=review_case,
                    action=action,
                    corrected_value=corrected_value,
                )
            elif action == TechnicalReviewResolutionAction.REJECT_VALUE:
                if review_case.severity == TechnicalReviewSeverity.BLOCKING:
                    raise RuntimeError(
                        "Un blocage technique doit être corrigé ou confirmé avant de continuer."
                    )
                review_case.status = TechnicalReviewStatus.REJETE
            elif action == TechnicalReviewResolutionAction.REQUEST_NEW_DOCUMENT:
                review_case.status = TechnicalReviewStatus.DOCUMENT_A_REMPLACER
            else:
                selected_candidate = None
                if selected_candidate_id is not None:
                    selected_candidate = await session.get(
                        TechnicalFactCandidate,
                        selected_candidate_id,
                    )
                    if (
                        selected_candidate is None
                        or selected_candidate.ingestion_run_id != review_case.ingestion_run_id
                    ):
                        raise RuntimeError("Candidat technique sélectionné introuvable.")

                value = (
                    corrected_value
                    or (
                        selected_candidate.normalized_value or selected_candidate.raw_value
                        if selected_candidate is not None
                        else None
                    )
                    or review_case.detected_value
                )
                unit = (
                    corrected_unit
                    or (selected_candidate.unit if selected_candidate is not None else None)
                    or review_case.detected_unit
                )
                if not review_case.field_name or not value:
                    raise RuntimeError("Impossible de résoudre ce cas sans champ et valeur.")
                occurrence_index = _review_case_occurrence_index(review_case)
                await session.execute(
                    delete(TechnicalFact).where(
                        TechnicalFact.product_id == product.id,
                        TechnicalFact.field_name == review_case.field_name,
                        TechnicalFact.occurrence_index == occurrence_index,
                    )
                )
                fact = TechnicalFact(
                    product_id=product.id,
                    source_candidate_id=(
                        selected_candidate.id
                        if selected_candidate is not None
                        else review_case.fact_candidate_id
                    ),
                    field_name=review_case.field_name,
                    occurrence_index=occurrence_index,
                    value=value,
                    unit=unit,
                    validation_source=TechnicalFactValidationSource.HUMAN,
                    validated_at=datetime.now(UTC),
                    validated_by=resolved_by,
                )
                session.add(fact)
                await session.flush()
                review_case.resolved_fact_id = fact.id
                review_case.corrected_value = corrected_value
                review_case.corrected_unit = corrected_unit
                review_case.status = (
                    TechnicalReviewStatus.CORRIGE
                    if action == TechnicalReviewResolutionAction.CORRECT_VALUE
                    else TechnicalReviewStatus.APPROUVE
                )

            await session.flush()

            open_review_case_count = await self._count_open_technical_review_cases(
                session,
                review_case.ingestion_run_id,
            )
            review_complete = open_review_case_count == 0
            if review_complete:
                if is_classification_review:
                    review_case.ingestion_run.statut = StatutDocumentIngestionRun.EN_COURS
                    review_case.ingestion_run.current_step = CurrentStep.FACT_EXTRACTION
                    review_case.ingestion_run.completed_at = None
                    review_case.ingestion_run.collection.statut = StatutDocumentCollection.EN_COURS
                else:
                    review_case.ingestion_run.statut = StatutDocumentIngestionRun.TERMINE
                    review_case.ingestion_run.current_step = CurrentStep.DONE
                    review_case.ingestion_run.completed_at = datetime.now(UTC)
                    review_case.ingestion_run.collection.statut = StatutDocumentCollection.TERMINE

            return {
                "case_id": str(review_case.id),
                "status": review_case.status.value,
                "ingestion_run_id": str(review_case.ingestion_run_id),
                "open_review_case_count": open_review_case_count,
                "review_complete": review_complete,
            }

    async def _resolve_classification_review_case(
        self,
        session: AsyncSession,
        *,
        review_case: TechnicalReviewCase,
        action: TechnicalReviewResolutionAction,
        corrected_value: str | None,
    ) -> None:
        if action == TechnicalReviewResolutionAction.REQUEST_NEW_DOCUMENT:
            review_case.status = TechnicalReviewStatus.DOCUMENT_A_REMPLACER
            return

        if action == TechnicalReviewResolutionAction.REJECT_VALUE:
            review_case.status = TechnicalReviewStatus.DOCUMENT_A_REMPLACER
            return

        document_type_value = (
            corrected_value
            if action == TechnicalReviewResolutionAction.CORRECT_VALUE
            else review_case.detected_value
        )
        if review_case.source_id is None or not document_type_value:
            raise RuntimeError("Impossible de résoudre cette classification sans source et type.")

        source = await session.get(DocumentSource, review_case.source_id, with_for_update=True)
        if source is None:
            raise RuntimeError("Source technique introuvable pour la classification.")

        if not _is_routable_technical_document_type(document_type_value):
            source.document_type = DocumentType.UNKNOWN
            review_case.status = TechnicalReviewStatus.DOCUMENT_A_REMPLACER
            return

        source.document_type = _to_document_type(document_type_value)
        review_case.corrected_value = (
            corrected_value if action == TechnicalReviewResolutionAction.CORRECT_VALUE else None
        )
        review_case.corrected_unit = None
        review_case.status = (
            TechnicalReviewStatus.CORRIGE
            if action == TechnicalReviewResolutionAction.CORRECT_VALUE
            else TechnicalReviewStatus.APPROUVE
        )

    async def _count_open_technical_review_cases(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> int:
        count = await session.scalar(
            select(func.count())
            .select_from(TechnicalReviewCase)
            .where(
                TechnicalReviewCase.ingestion_run_id == run_id,
                TechnicalReviewCase.status.in_(
                    [
                        TechnicalReviewStatus.A_TRAITER,
                        TechnicalReviewStatus.DOCUMENT_A_REMPLACER,
                    ]
                ),
            )
        )
        return int(count or 0)

    async def get_product_overview(self, product_id: uuid.UUID) -> dict[str, Any]:
        async with self._session_factory() as session:
            product = await self._require_product(session, product_id)
            collection = await self._get_latest_technical_collection(session, product_id)
            run = await self._get_latest_run(session, collection.id) if collection else None

            facts = list(
                (
                    await session.scalars(
                        select(TechnicalFact)
                        .where(TechnicalFact.product_id == product_id)
                        .order_by(TechnicalFact.field_name, TechnicalFact.occurrence_index)
                    )
                ).all()
            )

            review_cases: list[TechnicalReviewCase] = []
            candidates: list[TechnicalFactCandidate] = []
            if run is not None:
                review_cases = list(
                    (
                        await session.scalars(
                            select(TechnicalReviewCase)
                            .where(TechnicalReviewCase.ingestion_run_id == run.id)
                            .order_by(TechnicalReviewCase.created_at)
                        )
                    ).all()
                )
                candidates = list(
                    (
                        await session.scalars(
                            select(TechnicalFactCandidate)
                            .where(TechnicalFactCandidate.ingestion_run_id == run.id)
                            .order_by(TechnicalFactCandidate.created_at)
                        )
                    ).all()
                )

            product_sheet_generation = await self._get_latest_product_sheet_generation_for_product(
                session,
                product_id,
            )
            product_sheet_generation_snapshot = (
                _to_product_sheet_generation_snapshot(product_sheet_generation)
                if product_sheet_generation is not None
                else None
            )

            return {
                "product": _product_to_dict(self._to_product_snapshot(product)),
                "technical_collection": _collection_to_dict(collection) if collection else None,
                "sources": [
                    _source_to_dict(self._to_source_snapshot(source))
                    for source in (
                        _active_current_sources(collection.document_sources) if collection else []
                    )
                ],
                "technical_classifications": _technical_classifications_to_dict(
                    sources=(
                        list(_active_current_sources(collection.document_sources))
                        if collection
                        else []
                    ),
                    run=run,
                    review_cases=review_cases,
                ),
                "run": _run_to_dict(self._to_run_snapshot(run)) if run is not None else None,
                "facts": [_technical_fact_to_dict(fact) for fact in facts],
                "fact_candidates": [_candidate_to_dict(candidate) for candidate in candidates],
                "review_cases": [_review_case_to_dict(case) for case in review_cases],
                "commercial_signal_snapshot": (
                    (run.validation_summary_json or {}).get("commercial_signal_snapshot")
                    if run is not None
                    else None
                ),
                "product_sheet_readiness": (
                    (run.validation_summary_json or {}).get("product_sheet_readiness")
                    or (run.validation_summary_json or {}).get("generation_readiness")
                    if run is not None
                    else None
                ),
                "product_context_snapshot": (
                    (run.validation_summary_json or {}).get("product_context_snapshot")
                    if run is not None
                    else None
                ),
                "product_sheet_generation": _product_sheet_generation_to_dict(
                    product_sheet_generation_snapshot
                ),
            }

    async def _get_latest_product_context_snapshot(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
    ) -> ProductContextSnapshot | None:
        stmt = (
            select(ProductContextSnapshot)
            .where(ProductContextSnapshot.product_id == product_id)
            .order_by(ProductContextSnapshot.created_at.desc())
        )
        return (await session.scalars(stmt)).first()

    async def _get_latest_product_sheet_generation(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
        context_snapshot_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> ProductSheetGeneration | None:
        stmt = (
            select(ProductSheetGeneration)
            .where(
                ProductSheetGeneration.product_id == product_id,
                ProductSheetGeneration.product_context_snapshot_id == context_snapshot_id,
            )
            .order_by(ProductSheetGeneration.created_at.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await session.scalars(stmt)).first()

    async def _get_latest_product_sheet_generation_for_product(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
    ) -> ProductSheetGeneration | None:
        stmt = (
            select(ProductSheetGeneration)
            .where(ProductSheetGeneration.product_id == product_id)
            .order_by(ProductSheetGeneration.created_at.desc())
        )
        return (await session.scalars(stmt)).first()

    async def _require_product_sheet_generation(
        self,
        session: AsyncSession,
        generation_id: uuid.UUID,
        *,
        for_update: bool = False,
        load_context: bool = False,
    ) -> ProductSheetGeneration:
        stmt = select(ProductSheetGeneration).where(ProductSheetGeneration.id == generation_id)
        if load_context:
            stmt = stmt.options(
                selectinload(ProductSheetGeneration.product)
                .selectinload(Product.taxonomie_produit)
                .selectinload(TaxonomieProduit.parent),
                selectinload(ProductSheetGeneration.product_context_snapshot)
                .selectinload(ProductContextSnapshot.style_pack)
                .selectinload(StylePack.style_rules)
                .selectinload(StyleRule.taxonomie_produit),
                selectinload(ProductSheetGeneration.product_context_snapshot).selectinload(
                    ProductContextSnapshot.commercial_signal_snapshot
                ),
            )
        if for_update:
            stmt = stmt.with_for_update()
        generation = (await session.scalars(stmt)).first()
        if generation is None:
            raise RuntimeError("Génération de fiche produit introuvable.")
        return generation

    async def _list_technical_facts_by_ids(
        self,
        session: AsyncSession,
        fact_ids: tuple[uuid.UUID, ...],
    ) -> tuple[TechnicalFactSnapshot, ...]:
        if not fact_ids:
            return ()

        facts = list(
            (
                await session.scalars(
                    select(TechnicalFact)
                    .where(TechnicalFact.id.in_(fact_ids))
                    .order_by(TechnicalFact.field_name, TechnicalFact.occurrence_index)
                )
            ).all()
        )
        return tuple(
            TechnicalFactSnapshot(
                id=fact.id,
                field_name=fact.field_name,
                occurrence_index=fact.occurrence_index,
                value=fact.value,
                unit=fact.unit,
            )
            for fact in facts
        )

    async def _resolve_product_taxonomy(
        self,
        session: AsyncSession,
        *,
        famille_code: str,
        sous_famille_code: str | None,
    ) -> TaxonomieProduit:
        family = await self._require_taxonomy_by_code(session, famille_code)

        if family.parent_id is not None:
            raise RuntimeError(f"{famille_code} est une sous-famille, pas une famille produit.")

        if sous_famille_code is None or sous_famille_code == famille_code:
            return family

        subfamily = await self._require_taxonomy_by_code(session, sous_famille_code)

        if subfamily.parent_id is None or subfamily.parent_id != family.id:
            raise RuntimeError(
                f"La sous-famille {sous_famille_code} n'appartient pas à la famille {famille_code}."
            )

        return subfamily

    async def _require_taxonomy_by_code(
        self,
        session: AsyncSession,
        code: str,
    ) -> TaxonomieProduit:
        stmt = (
            select(TaxonomieProduit)
            .where(TaxonomieProduit.famille_code == code)
            .options(selectinload(TaxonomieProduit.parent))
        )
        taxonomy = (await session.scalars(stmt)).first()

        if taxonomy is None:
            raise RuntimeError(f"Taxonomie produit inconnue: {code}.")

        return taxonomy

    async def _get_product(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Product | None:
        stmt = (
            select(Product).where(Product.id == product_id).options(_product_taxonomy_load_option())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await session.scalars(stmt)).first()

    async def _require_product(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Product:
        product = await self._get_product(session, product_id, for_update=for_update)
        if product is None:
            raise RuntimeError("Produit introuvable.")
        return product

    async def _get_or_create_open_technical_collection(
        self,
        session: AsyncSession,
        product: Product,
    ) -> DocumentCollection:
        collection = await self._get_latest_technical_collection(session, product.id)
        if collection is not None and collection.statut in (
            StatutDocumentCollection.EN_ATTENTE,
            StatutDocumentCollection.EN_COURS,
        ):
            return collection
        collection = DocumentCollection(
            collection_kind=CollectionKind.TECHNICAL_DOSSIER,
            product_id=product.id,
            statut=StatutDocumentCollection.EN_ATTENTE,
        )
        session.add(collection)
        await session.flush()
        return collection

    async def _get_latest_technical_collection(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> DocumentCollection | None:
        stmt = (
            select(DocumentCollection)
            .where(
                DocumentCollection.product_id == product_id,
                DocumentCollection.collection_kind == CollectionKind.TECHNICAL_DOSSIER,
                DocumentCollection.replaced_by_collection_id.is_(None),
            )
            .options(
                selectinload(DocumentCollection.document_sources),
                selectinload(DocumentCollection.ingestion_runs),
            )
            .order_by(DocumentCollection.created_at.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await session.scalars(stmt)).first()

    async def _get_latest_run(
        self,
        session: AsyncSession,
        collection_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> DocumentIngestionRun | None:
        stmt = (
            select(DocumentIngestionRun)
            .where(DocumentIngestionRun.collection_id == collection_id)
            .order_by(DocumentIngestionRun.created_at.desc())
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await session.scalars(stmt)).first()

    async def _require_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> DocumentIngestionRun:
        stmt = select(DocumentIngestionRun).where(DocumentIngestionRun.id == run_id)
        if for_update:
            stmt = stmt.with_for_update()
        run = (await session.scalars(stmt)).first()
        if run is None:
            raise RuntimeError("Run d'ingestion technique introuvable.")
        return run

    async def _require_collection(
        self,
        session: AsyncSession,
        collection_id: uuid.UUID,
    ) -> DocumentCollection:
        stmt = (
            select(DocumentCollection)
            .where(DocumentCollection.id == collection_id)
            .options(selectinload(DocumentCollection.document_sources))
        )
        collection = (await session.scalars(stmt)).first()
        if collection is None:
            raise RuntimeError("Dossier technique introuvable.")
        return collection

    async def _cancel_latest_run_for_replaced_lot(
        self,
        session: AsyncSession,
        collection_id: uuid.UUID,
    ) -> uuid.UUID | None:
        run = await self._get_latest_run(session, collection_id, for_update=True)
        if run is None:
            return None

        now = datetime.now(UTC)
        run.statut = StatutDocumentIngestionRun.ANNULE
        run.completed_at = now
        run.error_message = "Lot technique remplacé par un nouvel import."

        review_cases = list(
            (
                await session.scalars(
                    select(TechnicalReviewCase)
                    .where(
                        TechnicalReviewCase.ingestion_run_id == run.id,
                        TechnicalReviewCase.status.in_(
                            [
                                TechnicalReviewStatus.A_TRAITER,
                                TechnicalReviewStatus.DOCUMENT_A_REMPLACER,
                            ]
                        ),
                    )
                    .with_for_update()
                )
            ).all()
        )
        for review_case in review_cases:
            review_case.status = TechnicalReviewStatus.REJETE
            review_case.resolution_action = TechnicalReviewResolutionAction.REQUEST_NEW_DOCUMENT
            review_case.resolution_comment = "Lot technique remplacé par un nouvel import."
            review_case.resolved_by = "system"
            review_case.resolved_at = now

        return run.id

    async def _list_collection_sources(
        self,
        session: AsyncSession,
        collection_id: uuid.UUID,
    ) -> list[DocumentSource]:
        return list(
            (
                await session.scalars(
                    select(DocumentSource).where(DocumentSource.collection_id == collection_id)
                )
            ).all()
        )

    def _to_product_snapshot(self, product: Product) -> ProductSnapshot:
        taxonomy = product.taxonomie_produit
        parent_taxonomy = taxonomy.parent
        famille_code = (
            parent_taxonomy.famille_code if parent_taxonomy is not None else taxonomy.famille_code
        )
        sous_famille_code = (
            taxonomy.famille_code if parent_taxonomy is not None else product.sous_famille_code
        )

        return ProductSnapshot(
            id=product.id,
            sku=product.sku,
            name=product.name,
            famille_code=famille_code,
            sous_famille_code=sous_famille_code,
            season_code=product.season_code,
            segment_prix_code=product.segment_prix_code,
            langue_principale=product.langue_principale,
            created_at=product.created_at,
        )

    def _to_product_taxonomy_snapshot(
        self,
        taxonomy: TaxonomieProduit,
    ) -> ProductTaxonomySnapshot:
        return ProductTaxonomySnapshot(
            id=taxonomy.id,
            code=taxonomy.famille_code,
            libelle_fr=taxonomy.libelle_fr,
            parent_id=taxonomy.parent_id,
        )

    def _to_source_snapshot(self, source: DocumentSource) -> DocumentSourceSnapshot:
        return DocumentSourceSnapshot(
            id=source.id,
            collection_id=source.collection_id,
            original_file_name=source.original_file_name,
            storage_uri=source.storage_uri,
            storage_generation=source.storage_generation,
            storage_metageneration=source.storage_metageneration,
            storage_content_type=source.storage_content_type,
            storage_size_bytes=source.storage_size_bytes,
            document_type=source.document_type.value,
            classification_confidence=source.classification_confidence,
            statut=source.statut.value,
            created_at=source.created_at,
            updated_at=source.updated_at,
        )

    def _to_run_snapshot(self, run: DocumentIngestionRun) -> IngestionRunSnapshot:
        return IngestionRunSnapshot(
            id=run.id,
            collection_id=run.collection_id,
            workflow_id=run.temporal_workflow_id,
            statut=run.statut.value,
            current_step=run.current_step.value,
            validation_summary_json=run.validation_summary_json,
            extraction_steps_json=run.extraction_steps_json,
            created_at=run.created_at,
            updated_at=run.updated_at,
            started_at=run.started_at,
            completed_at=run.completed_at,
        )
