from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import joinedload, selectinload

from factory_writer.application.ports.product_technical_ingestion import (
    CommercialSignalSnapshotSelection,
    DocumentSourceSnapshot,
    IngestionRunSnapshot,
    ProductContextSnapshotResult,
    ProductSnapshot,
    PromotedTechnicalFactInput,
    StylePackRuntimeSnapshot,
    TechnicalFactCandidateInput,
    TechnicalFactSnapshot,
    TechnicalIngestionStartPreparation,
    TechnicalReviewCaseInput,
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
    TechnicalReviewResolutionAction,
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
            taxonomy = await self._get_or_create_taxonomy(session, famille_code)
            product = Product(
                sku=sku,
                name=name,
                taxonomie_produit_id=taxonomy.id,
                taxonomie_produit=taxonomy,
                sous_famille_code=sous_famille_code,
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
            return tuple(self._to_source_snapshot(source) for source in persisted_sources)

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

            sources = [
                source
                for source in collection.document_sources
                if source.replaced_by_source_id is None
            ]
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
            workflow_id = f"product-lifecycle-{product.sku}"
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
        async with self._session_factory() as session:
            stmt = (
                select(CommercialSignalSnapshot)
                .where(
                    CommercialSignalSnapshot.is_active.is_(True),
                    CommercialSignalSnapshot.famille_code == product.famille_code,
                )
                .order_by(CommercialSignalSnapshot.created_at.desc())
            )
            snapshots = list((await session.scalars(stmt)).all())
            if not snapshots:
                raise RuntimeError(
                    f"Aucun snapshot commercial actif pour la famille {product.famille_code}."
                )

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
    ) -> IngestionRunSnapshot:
        async with self._session_factory() as session, session.begin():
            run = await self._require_run(session, run_id, for_update=True)
            run.current_step = current_step
            if statut is not None:
                run.statut = statut
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
                    metadata_json=review_case.metadata_json,
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
                        .order_by(TechnicalFact.field_name)
                    )
                ).all()
            )
            return tuple(
                TechnicalFactSnapshot(
                    id=fact.id,
                    field_name=fact.field_name,
                    value=fact.value,
                    unit=fact.unit,
                )
                for fact in facts
            )

    async def has_open_technical_review_cases(self, *, run_id: uuid.UUID) -> bool:
        async with self._session_factory() as session:
            review_case = (
                await session.scalars(
                    select(TechnicalReviewCase).where(
                        TechnicalReviewCase.ingestion_run_id == run_id,
                        TechnicalReviewCase.status.in_(
                            [
                                TechnicalReviewStatus.A_TRAITER,
                                TechnicalReviewStatus.DOCUMENT_A_REMPLACER,
                            ]
                        ),
                    )
                )
            ).first()
            return review_case is not None

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
                        .options(selectinload(Product.taxonomie_produit))
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

            if action == TechnicalReviewResolutionAction.REJECT_VALUE:
                review_case.status = TechnicalReviewStatus.REJETE
            elif action == TechnicalReviewResolutionAction.REQUEST_NEW_DOCUMENT:
                review_case.status = TechnicalReviewStatus.DOCUMENT_A_REMPLACER
            else:
                value = corrected_value or review_case.detected_value
                unit = corrected_unit or review_case.detected_unit
                if not review_case.field_name or not value:
                    raise RuntimeError("Impossible de résoudre ce cas sans champ et valeur.")
                await session.execute(
                    delete(TechnicalFact).where(
                        TechnicalFact.product_id == product.id,
                        TechnicalFact.field_name == review_case.field_name,
                    )
                )
                fact = TechnicalFact(
                    product_id=product.id,
                    source_candidate_id=review_case.fact_candidate_id,
                    field_name=review_case.field_name,
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

            blocking_stmt = select(TechnicalReviewCase).where(
                TechnicalReviewCase.ingestion_run_id == review_case.ingestion_run_id,
                TechnicalReviewCase.status.in_(
                    [
                        TechnicalReviewStatus.A_TRAITER,
                        TechnicalReviewStatus.DOCUMENT_A_REMPLACER,
                    ]
                ),
            )
            blocking_case = (await session.scalars(blocking_stmt)).first()
            if blocking_case is None:
                review_case.ingestion_run.statut = StatutDocumentIngestionRun.TERMINE
                review_case.ingestion_run.current_step = CurrentStep.DONE
                review_case.ingestion_run.completed_at = datetime.now(UTC)
                review_case.ingestion_run.collection.statut = StatutDocumentCollection.TERMINE

            return {
                "case_id": str(review_case.id),
                "status": review_case.status.value,
                "ingestion_run_id": str(review_case.ingestion_run_id),
            }

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
                        .order_by(TechnicalFact.field_name)
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
                    for source in (collection.document_sources if collection else [])
                ],
                "run": _run_to_dict(self._to_run_snapshot(run)) if run is not None else None,
                "facts": [_technical_fact_to_dict(fact) for fact in facts],
                "fact_candidates": [_candidate_to_dict(candidate) for candidate in candidates],
                "review_cases": [_review_case_to_dict(case) for case in review_cases],
                "commercial_signal_snapshot": (
                    (run.validation_summary_json or {}).get("commercial_signal_snapshot")
                    if run is not None
                    else None
                ),
                "product_context_snapshot": (
                    (run.validation_summary_json or {}).get("product_context_snapshot")
                    if run is not None
                    else None
                ),
            }

    async def _get_or_create_taxonomy(
        self,
        session: AsyncSession,
        famille_code: str,
    ) -> TaxonomieProduit:
        stmt = select(TaxonomieProduit).where(TaxonomieProduit.famille_code == famille_code)
        taxonomy = (await session.scalars(stmt)).first()
        if taxonomy is not None:
            return taxonomy
        taxonomy = TaxonomieProduit(famille_code=famille_code, libelle_fr=famille_code)
        session.add(taxonomy)
        await session.flush()
        return taxonomy

    async def _get_product(
        self,
        session: AsyncSession,
        product_id: uuid.UUID,
        *,
        for_update: bool = False,
    ) -> Product | None:
        stmt = (
            select(Product)
            .where(Product.id == product_id)
            .options(selectinload(Product.taxonomie_produit))
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

    def _to_product_snapshot(self, product: Product) -> ProductSnapshot:
        return ProductSnapshot(
            id=product.id,
            sku=product.sku,
            name=product.name,
            famille_code=product.taxonomie_produit.famille_code,
            sous_famille_code=product.sous_famille_code,
            season_code=product.season_code,
            segment_prix_code=product.segment_prix_code,
            langue_principale=product.langue_principale,
        )

    def _to_source_snapshot(self, source: DocumentSource) -> DocumentSourceSnapshot:
        return DocumentSourceSnapshot(
            id=source.id,
            collection_id=source.collection_id,
            original_file_name=source.original_file_name,
            storage_uri=source.storage_uri,
            storage_content_type=source.storage_content_type,
            storage_size_bytes=source.storage_size_bytes,
            document_type=source.document_type.value,
            classification_confidence=source.classification_confidence,
            statut=source.statut.value,
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
        )


def _choose_commercial_snapshot(
    product: ProductSnapshot,
    snapshots: list[CommercialSignalSnapshot],
) -> tuple[CommercialSignalSnapshot, str]:
    for snapshot in snapshots:
        if (
            snapshot.segment_prix_code == product.segment_prix_code
            and snapshot.season_code == product.season_code
        ):
            return snapshot, "matched_family_segment_season"
    for snapshot in snapshots:
        if snapshot.segment_prix_code == product.segment_prix_code:
            return snapshot, "matched_family_segment"
    for snapshot in snapshots:
        if snapshot.season_code == product.season_code:
            return snapshot, "matched_family_season"
    return snapshots[0], "matched_family_only"


def _to_document_type(value: str) -> DocumentType:
    try:
        return DocumentType(value)
    except ValueError:
        return DocumentType.UNKNOWN


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
        "storage_content_type": source.storage_content_type,
        "storage_size_bytes": source.storage_size_bytes,
        "document_type": source.document_type,
        "classification_confidence": source.classification_confidence,
        "statut": source.statut,
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
    }


def _technical_fact_to_dict(fact: TechnicalFact) -> dict[str, Any]:
    return {
        "id": str(fact.id),
        "field_name": fact.field_name,
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


def _review_case_to_dict(review_case: TechnicalReviewCase) -> dict[str, Any]:
    return {
        "id": str(review_case.id),
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
    }
