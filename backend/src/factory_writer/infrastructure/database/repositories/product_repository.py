from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload, selectinload

from factory_writer.application.ports.product_technical_ingestion import (
    CommercialSignalSnapshotSelection,
    DocumentSourceSnapshot,
    GenerationReadinessProfileSnapshot,
    IngestionRunSnapshot,
    ProductContextSnapshotResult,
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
    GenerationReadinessProfile,
    Product,
    ProductContextSnapshot,
    StylePack,
    TechnicalFact,
    TechnicalFactCandidate,
    TechnicalReviewCase,
)
from factory_writer.infrastructure.database.models.taxonomy import TaxonomieProduit


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

    async def load_generation_readiness_profile(
        self,
        *,
        product: ProductSnapshot,
        channel_code: str = "product_sheet",
    ) -> GenerationReadinessProfileSnapshot:
        async with self._session_factory() as session:
            stmt = (
                select(GenerationReadinessProfile)
                .where(
                    GenerationReadinessProfile.is_active.is_(True),
                    GenerationReadinessProfile.channel_code == channel_code,
                    GenerationReadinessProfile.famille_code.in_([product.famille_code, "*"]),
                )
                .order_by(GenerationReadinessProfile.created_at.desc())
            )
            profiles = list((await session.scalars(stmt)).all())

            matching_profiles = [
                profile
                for profile in profiles
                if profile.sous_famille_code in {product.sous_famille_code, None, "*"}
            ]
            if not matching_profiles:
                raise RuntimeError(
                    "Aucun profil de readiness generation actif pour "
                    f"{product.famille_code}/{product.sous_famille_code or '*'} "
                    f"sur {channel_code}."
                )

            selected = max(
                matching_profiles,
                key=lambda profile: _generation_readiness_profile_specificity(
                    product=product,
                    profile=profile,
                ),
            )
            return _to_generation_readiness_profile_snapshot(selected)

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
                        review_required=candidate.review_required,
                        review_reason=candidate.review_reason,
                        source_evidence_text=candidate.source_evidence_text,
                        source_page=candidate.source_page,
                        source_bbox_json=candidate.source_bbox_json,
                        raw_entity_json=candidate.raw_entity_json,
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
                    review_required=candidate.review_required,
                    review_reason=candidate.review_reason,
                    source_evidence_text=candidate.source_evidence_text,
                    source_page=candidate.source_page,
                    source_bbox_json=candidate.source_bbox_json,
                    raw_entity_json=candidate.raw_entity_json,
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
                    joinedload(TechnicalReviewCase.ingestion_run).joinedload(
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
                "generation_readiness": (
                    (run.validation_summary_json or {}).get("generation_readiness")
                    if run is not None
                    else None
                ),
                "product_context_snapshot": (
                    (run.validation_summary_json or {}).get("product_context_snapshot")
                    if run is not None
                    else None
                ),
            }

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


def _choose_commercial_snapshot(
    product: ProductSnapshot,
    snapshots: list[CommercialSignalSnapshot],
) -> tuple[CommercialSignalSnapshot, str]:
    for snapshot in snapshots:
        if _commercial_snapshot_matches_product(product=product, snapshot=snapshot):
            return snapshot, "matched_family_segment_season"

    raise RuntimeError(_commercial_snapshot_missing_message(product))


def _generation_readiness_profile_specificity(
    *,
    product: ProductSnapshot,
    profile: GenerationReadinessProfile,
) -> tuple[int, int]:
    family_score = 2 if profile.famille_code == product.famille_code else 0
    subfamily_score = (
        2
        if profile.sous_famille_code == product.sous_famille_code
        else 1
        if profile.sous_famille_code in {None, "*"}
        else 0
    )
    return family_score, subfamily_score


def _to_generation_readiness_profile_snapshot(
    profile: GenerationReadinessProfile,
) -> GenerationReadinessProfileSnapshot:
    return GenerationReadinessProfileSnapshot(
        id=profile.id,
        profile_code=profile.profile_code,
        famille_code=profile.famille_code,
        sous_famille_code=profile.sous_famille_code,
        channel_code=profile.channel_code,
        requirements_json=profile.requirements_json,
    )


def _commercial_snapshot_matches_product(
    *,
    product: ProductSnapshot,
    snapshot: CommercialSignalSnapshot,
) -> bool:
    return (
        snapshot.famille_code == product.famille_code
        and snapshot.segment_prix_code == product.segment_prix_code
        and snapshot.season_code == product.season_code
    )


def _commercial_snapshot_missing_message(product: ProductSnapshot) -> str:
    return (
        "Aucun snapshot commercial actif compatible "
        f"pour famille={product.famille_code}, "
        f"saison={product.season_code}, "
        f"segment={product.segment_prix_code}."
    )


def _active_current_sources(sources: list[DocumentSource]) -> tuple[DocumentSource, ...]:
    sources_by_file_name: dict[str, DocumentSource] = {}
    for source in sources:
        if source.replaced_by_source_id is not None:
            continue

        current_source = sources_by_file_name.get(source.original_file_name)
        if current_source is None or source.created_at > current_source.created_at:
            sources_by_file_name[source.original_file_name] = source

    return tuple(
        sorted(
            sources_by_file_name.values(),
            key=lambda source: (source.created_at, source.original_file_name),
        )
    )


def _product_taxonomy_load_option() -> Any:
    return selectinload(Product.taxonomie_produit).selectinload(TaxonomieProduit.parent)


def _to_document_type(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError:
        return DocumentType.UNKNOWN


def _is_routable_technical_document_type(value: str | None) -> bool:
    return value in {
        DocumentType.TECHNICAL_SHEET.value,
        DocumentType.ASSEMBLY_NOTICE.value,
        DocumentType.MATERIAL_SPECIFICATION.value,
    }


def _to_product_context_snapshot_result(
    snapshot: ProductContextSnapshot,
) -> ProductContextSnapshotResult:
    return ProductContextSnapshotResult(
        id=snapshot.id,
        product_id=snapshot.product_id,
        technical_ingestion_run_id=snapshot.technical_ingestion_run_id,
        style_pack_id=snapshot.style_pack_id,
        commercial_signal_snapshot_id=snapshot.commercial_signal_snapshot_id,
        technical_fact_ids=tuple(uuid.UUID(value) for value in snapshot.technical_fact_ids),
    )


def _product_to_dict(product: ProductSnapshot) -> dict[str, Any]:
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


def _collection_to_dict(collection: DocumentCollection) -> dict[str, Any]:
    return {
        "id": str(collection.id),
        "kind": collection.collection_kind.value,
        "statut": collection.statut.value,
    }


def _source_to_dict(source: DocumentSourceSnapshot) -> dict[str, Any]:
    return {
        "id": str(source.id),
        "collection_id": str(source.collection_id),
        "original_file_name": source.original_file_name,
        "storage_uri": source.storage_uri,
        "storage_generation": source.storage_generation,
        "storage_metageneration": source.storage_metageneration,
        "storage_content_type": source.storage_content_type,
        "storage_size_bytes": source.storage_size_bytes,
        "document_type": source.document_type,
        "classification_confidence": source.classification_confidence,
        "statut": source.statut,
        "created_at": source.created_at.isoformat() if source.created_at is not None else None,
        "updated_at": source.updated_at.isoformat() if source.updated_at is not None else None,
    }


def _run_to_dict(run: IngestionRunSnapshot) -> dict[str, Any]:
    return {
        "id": str(run.id),
        "collection_id": str(run.collection_id),
        "workflow_id": run.workflow_id,
        "statut": run.statut,
        "current_step": run.current_step,
        "validation_summary_json": run.validation_summary_json,
        "extraction_steps_json": run.extraction_steps_json,
        "created_at": run.created_at.isoformat() if run.created_at is not None else None,
        "updated_at": run.updated_at.isoformat() if run.updated_at is not None else None,
        "started_at": run.started_at.isoformat() if run.started_at is not None else None,
        "completed_at": run.completed_at.isoformat() if run.completed_at is not None else None,
    }


def _technical_fact_to_dict(fact: TechnicalFact) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "field_name": fact.field_name,
        "occurrence_index": fact.occurrence_index,
        "value": fact.value,
        "unit": fact.unit,
        "validation_source": fact.validation_source.value,
        "validated_at": fact.validated_at.isoformat(),
    }


def _candidate_to_dict(candidate: TechnicalFactCandidate) -> dict[str, Any]:
    return {
        "id": str(candidate.id),
        "source_id": str(candidate.source_id),
        "field_name": candidate.field_name,
        "raw_value": candidate.raw_value,
        "normalized_value": candidate.normalized_value,
        "unit": candidate.unit,
        "extractor_confidence": candidate.extractor_confidence,
        "validation_status": candidate.validation_status.value,
        "review_required": candidate.review_required,
        "review_reason": candidate.review_reason,
        "source_evidence_text": candidate.source_evidence_text,
        "source_page": candidate.source_page,
        "source_bbox_json": candidate.source_bbox_json,
    }


def _technical_classifications_to_dict(
    *,
    sources: list[DocumentSource],
    run: DocumentIngestionRun | None,
    review_cases: list[TechnicalReviewCase],
) -> list[dict[str, Any]]:
    classification_steps_by_source_id = _classification_steps_by_source_id(run)
    blocking_cases_by_source_id = _blocking_classification_cases_by_source_id(review_cases)
    results: list[dict[str, Any]] = []

    for source in sources:
        source_id = str(source.id)
        step = classification_steps_by_source_id.get(source_id, {})
        blocking_case = blocking_cases_by_source_id.get(source_id)
        has_classification_result = (
            bool(step)
            or source.classification_confidence is not None
            or source.document_type != DocumentType.UNKNOWN
            or blocking_case is not None
        )
        if not has_classification_result:
            continue

        document_type = _optional_string(step.get("document_type")) or source.document_type.value
        confidence = _optional_float(step.get("confidence"))
        if confidence is None:
            confidence = source.classification_confidence

        blocking_reason = _classification_blocking_reason(
            document_type=document_type,
            confidence=confidence,
            blocking_case=blocking_case,
        )

        results.append(
            {
                "source_id": source_id,
                "file_name": source.original_file_name,
                "document_type": document_type,
                "confidence": confidence,
                "is_blocking": blocking_reason is not None,
                "blocking_reason": blocking_reason,
            }
        )

    return results


def _classification_steps_by_source_id(
    run: DocumentIngestionRun | None,
) -> dict[str, dict[str, Any]]:
    extraction_steps_json = run.extraction_steps_json if run is not None else None
    if not isinstance(extraction_steps_json, dict):
        return {}

    steps = extraction_steps_json.get("steps")
    if not isinstance(steps, list):
        return {}

    indexed_steps: dict[str, dict[str, Any]] = {}
    for step in steps:
        if not isinstance(step, dict) or step.get("step") != "classification":
            continue

        source_id = _optional_string(step.get("source_id"))
        if source_id is not None:
            indexed_steps[source_id] = step

    return indexed_steps


def _blocking_classification_cases_by_source_id(
    review_cases: list[TechnicalReviewCase],
) -> dict[str, TechnicalReviewCase]:
    blocking_cases: dict[str, TechnicalReviewCase] = {}

    for review_case in review_cases:
        if (
            review_case.case_type != TechnicalReviewCaseType.CLASSIFICATION_UNCERTAIN
            or review_case.source_id is None
            or review_case.status
            not in {
                TechnicalReviewStatus.A_TRAITER,
                TechnicalReviewStatus.DOCUMENT_A_REMPLACER,
            }
        ):
            continue

        blocking_cases[str(review_case.source_id)] = review_case

    return blocking_cases


def _classification_blocking_reason(
    *,
    document_type: str,
    confidence: float | None,
    blocking_case: TechnicalReviewCase | None,
) -> str | None:
    if blocking_case is None:
        return None

    metadata_json = blocking_case.metadata_json
    is_out_of_scope = (
        isinstance(metadata_json, dict) and metadata_json.get("is_out_of_scope") is True
    )
    if is_out_of_scope or not _is_routable_technical_document_type(document_type):
        return "OUT_OF_SCOPE"

    if confidence is None:
        return "MISSING_CONFIDENCE"

    return "LOW_CONFIDENCE"


def _review_case_to_dict(review_case: TechnicalReviewCase) -> dict[str, Any]:
    return {
        "id": str(review_case.id),
        "source_id": str(review_case.source_id) if review_case.source_id else None,
        "case_type": review_case.case_type.value,
        "severity": review_case.severity.value,
        "status": review_case.status.value,
        "field_name": review_case.field_name,
        "title": review_case.title,
        "description": review_case.description,
        "detected_value": review_case.detected_value,
        "detected_unit": review_case.detected_unit,
        "suggested_value": review_case.suggested_value,
        "suggested_unit": review_case.suggested_unit,
        "corrected_value": review_case.corrected_value,
        "corrected_unit": review_case.corrected_unit,
        "resolution_action": (
            review_case.resolution_action.value if review_case.resolution_action else None
        ),
        "resolution_comment": review_case.resolution_comment,
        "metadata_json": review_case.metadata_json,
    }


def _review_case_occurrence_index(review_case: TechnicalReviewCase) -> int:
    metadata = review_case.metadata_json if isinstance(review_case.metadata_json, dict) else {}
    raw_value = metadata.get("occurrence_index")
    return raw_value if isinstance(raw_value, int) and raw_value >= 0 else 0


def _review_case_metadata_with_candidate_ids(
    metadata_json: Any | None,
    persisted_candidates: list[TechnicalFactCandidate],
) -> Any | None:
    if not isinstance(metadata_json, dict):
        return metadata_json

    metadata = dict(metadata_json)
    candidate_index = metadata.get("candidate_index")
    if isinstance(candidate_index, int) and 0 <= candidate_index < len(persisted_candidates):
        metadata["candidate_id"] = str(persisted_candidates[candidate_index].id)

    candidates = metadata.get("candidates")
    if isinstance(candidates, list):
        enriched_candidates: list[Any] = []
        for candidate in candidates:
            if not isinstance(candidate, dict):
                enriched_candidates.append(candidate)
                continue
            enriched = dict(candidate)
            nested_candidate_index = enriched.get("candidate_index")
            if isinstance(nested_candidate_index, int) and 0 <= nested_candidate_index < len(
                persisted_candidates
            ):
                enriched["candidate_id"] = str(persisted_candidates[nested_candidate_index].id)
            enriched_candidates.append(enriched)
        metadata["candidates"] = enriched_candidates

    return metadata


def _optional_string(value: Any) -> str | None:
    if value is None:
        return None

    text = str(value).strip()
    return text or None


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None

    try:
        return float(value)
    except (TypeError, ValueError):
        return None
