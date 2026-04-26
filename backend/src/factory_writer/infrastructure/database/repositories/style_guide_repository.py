from __future__ import annotations

import uuid
from datetime import UTC, datetime
from pathlib import PurePosixPath
from typing import Any, cast

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from sqlalchemy.orm import selectinload

from factory_writer.application.ports.style_guide_ingestion import (
    DraftStylePackExtractionV1,
    StyleGuideChunkCandidate,
    StyleGuideDocumentSourceSnapshot,
    StyleGuideDraftPackGenerationMetadata,
    StyleGuideDraftPackSnapshot,
    StyleGuideIngestionRunSnapshot,
    StyleGuideIngestionStartPreparation,
    StyleGuidePackSnapshot,
    StyleGuideRuleSnapshot,
    StyleGuideTaxonomySnapshot,
)
from factory_writer.domain.document_ingestion_types import (
    CollectionKind,
    CurrentStep,
    DecisionEditorialeStyleRule,
    DocumentType,
    OrigineStyleRule,
    StatutDocumentCollection,
    StatutDocumentIngestionRun,
    StatutStylePack,
)
from factory_writer.domain.style_guide_types import NiveauContrainte, StatutSource, TypeRegle
from factory_writer.infrastructure.database.models.poc_ingestion import (
    DocumentCollection,
    DocumentIngestionRun,
    DocumentSource,
    StylePack,
    StyleRule,
)
from factory_writer.infrastructure.database.models.taxonomy import TaxonomieProduit


class StyleGuideRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_current_document_source(self) -> StyleGuideDocumentSourceSnapshot | None:
        async with self._session_factory() as session:
            document_source = await self._get_current_document_source(session)
            if document_source is None:
                return None
            return self._to_document_source_snapshot(document_source)

    async def get_document_source_by_id(
        self, document_source_id: uuid.UUID
    ) -> StyleGuideDocumentSourceSnapshot | None:
        async with self._session_factory() as session:
            document_source = await self._get_style_guide_document_source(
                session, document_source_id
            )
            if document_source is None:
                return None
            return self._to_document_source_snapshot(document_source)

    async def get_latest_ingestion_run_for_document_source(
        self,
        document_source_id: uuid.UUID,
    ) -> StyleGuideIngestionRunSnapshot | None:
        async with self._session_factory() as session:
            document_source = await self._require_style_guide_document_source(
                session, document_source_id
            )
            run = await self._get_latest_run_for_collection(session, document_source.collection_id)
            if run is None:
                return None
            return self._to_run_snapshot(run)

    async def prepare_ingestion_start(
        self,
        *,
        document_source_id: uuid.UUID,
        pipeline_kind: str,
    ) -> StyleGuideIngestionStartPreparation:
        async with self._session_factory() as session:
            async with session.begin():
                document_source = await self._require_style_guide_document_source_for_update(
                    session, document_source_id
                )

                if document_source.replaced_by_source_id is not None:
                    raise RuntimeError(
                        "Ce guide de style a été remplacé. Utilisez la version la plus récente."
                    )

                latest_run = await self._get_latest_run_for_collection(
                    session,
                    document_source.collection_id,
                    for_update=True,
                )

                if (
                    latest_run is not None
                    and latest_run.statut == StatutDocumentIngestionRun.EN_COURS
                ):
                    return StyleGuideIngestionStartPreparation(
                        document_source=self._to_document_source_snapshot(document_source),
                        run=self._to_run_snapshot(latest_run),
                        reused_existing_run=True,
                    )

                if document_source.collection.statut == StatutDocumentCollection.TERMINE:
                    raise RuntimeError("Ce guide de style est déjà terminé.")

                if (
                    latest_run is not None
                    and latest_run.statut == StatutDocumentIngestionRun.A_VALIDER
                ):
                    raise RuntimeError(
                        "Ce guide de style est déjà en attente de validation humaine."
                    )

                run_id = uuid.uuid4()
                workflow_id = f"style-guide-ingestion-{run_id}"

                run = DocumentIngestionRun(
                    id=run_id,
                    collection_id=document_source.collection_id,
                    pipeline_kind=pipeline_kind,
                    statut=StatutDocumentIngestionRun.EN_COURS,
                    current_step=CurrentStep.UPLOAD,
                    temporal_workflow_id=workflow_id,
                    temporal_run_id=None,
                    started_at=datetime.now(UTC),
                    completed_at=None,
                )

                session.add(run)
                await session.flush()

                await self._sync_source_and_collection_for_run(
                    session,
                    run=run,
                    document_source=document_source,
                    clear_errors=True,
                )

            return StyleGuideIngestionStartPreparation(
                document_source=self._to_document_source_snapshot(document_source),
                run=self._to_run_snapshot(run),
                reused_existing_run=False,
            )

    async def create_document_source(
        self,
        *,
        document_source_id: uuid.UUID,
        storage_uri: str,
        storage_bucket: str,
        storage_object_name: str,
        original_file_name: str,
        storage_content_type: str,
        storage_size_bytes: int,
        storage_generation: str,
        storage_metageneration: str,
    ) -> StyleGuideDocumentSourceSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                collection = DocumentCollection(
                    collection_kind=CollectionKind.STYLE_GUIDE,
                    statut=StatutDocumentCollection.EN_ATTENTE,
                    dernier_message_erreur=None,
                )

                session.add(collection)
                await session.flush()

                document_source = self._build_document_source(
                    document_source_id=document_source_id,
                    collection_id=collection.id,
                    original_file_name=original_file_name,
                    storage_uri=storage_uri,
                    storage_bucket=storage_bucket,
                    storage_object_name=storage_object_name,
                    storage_generation=storage_generation,
                    storage_metageneration=storage_metageneration,
                    storage_content_type=storage_content_type,
                    storage_size_bytes=storage_size_bytes,
                )
                document_source.collection = collection
                session.add(document_source)
                await session.flush()

            return self._to_document_source_snapshot(document_source)

    async def create_reuploaded_document_source(
        self,
        *,
        replaced_document_source_id: uuid.UUID,
        document_source_id: uuid.UUID,
        storage_uri: str,
        storage_bucket: str,
        storage_object_name: str,
        original_file_name: str,
        storage_content_type: str,
        storage_size_bytes: int,
        storage_generation: str,
        storage_metageneration: str,
    ) -> StyleGuideDocumentSourceSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                replaced_document_source = await self._require_style_guide_document_source(
                    session, replaced_document_source_id
                )
                if replaced_document_source.replaced_by_source_id is not None:
                    raise RuntimeError("Ce guide de style a déjà été remplacé.")

                new_collection = DocumentCollection(
                    collection_kind=CollectionKind.STYLE_GUIDE,
                    statut=StatutDocumentCollection.EN_ATTENTE,
                    dernier_message_erreur=None,
                )
                session.add(new_collection)
                await session.flush()

                document_source = self._build_document_source(
                    document_source_id=document_source_id,
                    collection_id=new_collection.id,
                    original_file_name=original_file_name,
                    storage_uri=storage_uri,
                    storage_bucket=storage_bucket,
                    storage_object_name=storage_object_name,
                    storage_generation=storage_generation,
                    storage_metageneration=storage_metageneration,
                    storage_content_type=storage_content_type,
                    storage_size_bytes=storage_size_bytes,
                )
                document_source.collection = new_collection
                session.add(document_source)
                await session.flush()

                replaced_document_source.replaced_by_source_id = document_source.id
                replaced_document_source.collection.replaced_by_collection_id = new_collection.id

            return self._to_document_source_snapshot(document_source)

    async def create_ingestion_run(
        self,
        *,
        document_source_id: uuid.UUID,
        pipeline_kind: str,
        temporal_workflow_id: str | None = None,
        temporal_run_id: str | None = None,
        statut: StatutDocumentIngestionRun = StatutDocumentIngestionRun.EN_COURS,
        current_step: CurrentStep = CurrentStep.UPLOAD,
    ) -> StyleGuideIngestionRunSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                document_source = await self._require_style_guide_document_source(
                    session, document_source_id
                )

                run_id = uuid.uuid4()
                resolved_workflow_id = temporal_workflow_id or f"style-guide-ingestion-{run_id}"

                run = DocumentIngestionRun(
                    id=run_id,
                    collection_id=document_source.collection_id,
                    pipeline_kind=pipeline_kind,
                    statut=statut,
                    current_step=current_step,
                    temporal_workflow_id=resolved_workflow_id,
                    temporal_run_id=temporal_run_id,
                    started_at=datetime.now(UTC)
                    if statut == StatutDocumentIngestionRun.EN_COURS
                    else None,
                    completed_at=(
                        datetime.now(UTC) if statut == StatutDocumentIngestionRun.TERMINE else None
                    ),
                )

                session.add(run)

                await session.flush()

                await self._sync_source_and_collection_for_run(
                    session,
                    run=run,
                    document_source=document_source,
                    clear_errors=True,
                )

            return self._to_run_snapshot(run)

    async def update_document_source_status(
        self,
        document_source_id: uuid.UUID,
        statut: StatutSource,
        error_message: str | None = None,
        only_if_not_terminal: bool = False,
    ) -> StyleGuideDocumentSourceSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                document_source = await self._require_style_guide_document_source(
                    session, document_source_id
                )

                if only_if_not_terminal and document_source.statut in (
                    StatutSource.EN_COURS,
                    StatutSource.TERMINE,
                ):
                    return self._to_document_source_snapshot(document_source)

                if statut == StatutSource.ERREUR and document_source.statut == StatutSource.TERMINE:
                    return self._to_document_source_snapshot(document_source)

                document_source.statut = statut
                if error_message is not None:
                    document_source.dernier_message_erreur = error_message
                elif statut in (
                    StatutSource.EN_ATTENTE,
                    StatutSource.EN_COURS,
                    StatutSource.TERMINE,
                ):
                    document_source.dernier_message_erreur = None

                await self._sync_collection_for_source_status(
                    session,
                    document_source=document_source,
                    error_message=error_message,
                )

            return self._to_document_source_snapshot(document_source)

    async def update_ingestion_run_status(
        self,
        run_id: uuid.UUID,
        *,
        statut: StatutDocumentIngestionRun,
        current_step: CurrentStep | None = None,
        temporal_run_id: str | None = None,
        validation_summary_json: Any | None = None,
        error_message: str | None = None,
        clear_error: bool = False,
        started_at: datetime | None = None,
        completed_at: datetime | None = None,
    ) -> StyleGuideIngestionRunSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                run = await self._require_style_guide_run(session, run_id)
                run.statut = statut

                if current_step is not None:
                    run.current_step = current_step
                if temporal_run_id is not None:
                    run.temporal_run_id = temporal_run_id
                if validation_summary_json is not None:
                    run.validation_summary_json = validation_summary_json
                if error_message is not None:
                    run.error_message = error_message
                elif clear_error or statut in (
                    StatutDocumentIngestionRun.EN_COURS,
                    StatutDocumentIngestionRun.A_VALIDER,
                    StatutDocumentIngestionRun.TERMINE,
                ):
                    run.error_message = None

                if started_at is not None:
                    run.started_at = started_at
                elif run.started_at is None and statut == StatutDocumentIngestionRun.EN_COURS:
                    run.started_at = datetime.now(UTC)

                if completed_at is not None:
                    run.completed_at = completed_at
                elif statut == StatutDocumentIngestionRun.TERMINE:
                    run.completed_at = datetime.now(UTC)

                document_source = await self._get_latest_document_source_for_collection(
                    session, run.collection_id
                )
                if document_source is None:
                    raise KeyError(
                        f"Aucune source guide de style pour la collection {run.collection_id}"
                    )

                await self._sync_source_and_collection_for_run(
                    session,
                    run=run,
                    document_source=document_source,
                    error_message=error_message,
                    clear_errors=clear_error,
                )

            return self._to_run_snapshot(run)

    async def record_layout_parse_result(
        self,
        *,
        run_id: uuid.UUID,
        parser_resource_id: str,
        mode: str,
        latency_ms: int | None = None,
        operation_id: str | None = None,
        output_uri: str | None = None,
    ) -> StyleGuideIngestionRunSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                run = await self._require_style_guide_run(session, run_id)

                document_source = await self._get_latest_document_source_for_collection(
                    session, run.collection_id
                )

                if document_source is None:
                    raise KeyError(
                        f"Aucune source guide de style pour la collection {run.collection_id}"
                    )

                run.current_step = CurrentStep.LAYOUT_PARSE
                run.statut = StatutDocumentIngestionRun.EN_COURS
                run.error_message = None

                document_source.statut = StatutSource.EN_COURS
                document_source.dernier_message_erreur = None
                document_source.collection.statut = StatutDocumentCollection.EN_COURS
                document_source.collection.dernier_message_erreur = None

                run.extraction_steps_json = _upsert_layout_parse_step(
                    steps=run.extraction_steps_json,
                    parser_resource_id=parser_resource_id,
                    mode=mode,
                    latency_ms=latency_ms,
                    operation_id=operation_id,
                    output_uri=output_uri,
                )

            return self._to_run_snapshot(run)

    async def record_llm_draft_pack_metadata(
        self,
        *,
        run_id: uuid.UUID,
        prompt_registry_provider: str,
        prompt_name: str,
        prompt_version: str,
        llm_model: str,
        llm_temperature: float,
        llm_max_tokens: int,
        llm_response_format: str,
        status: str,
        system_prompt_hash: str | None = None,
        user_prompt_hash: str | None = None,
    ) -> StyleGuideIngestionRunSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                run = await self._require_style_guide_run(session, run_id)

                run.extraction_steps_json = _upsert_llm_draft_pack_step(
                    steps=run.extraction_steps_json,
                    prompt_registry_provider=prompt_registry_provider,
                    prompt_name=prompt_name,
                    prompt_version=prompt_version,
                    llm_model=llm_model,
                    llm_temperature=llm_temperature,
                    llm_max_tokens=llm_max_tokens,
                    llm_response_format=llm_response_format,
                    status=status,
                    system_prompt_hash=system_prompt_hash,
                    user_prompt_hash=user_prompt_hash,
                )

            return self._to_run_snapshot(run)

    async def get_latest_draft_pack(self) -> StyleGuidePackSnapshot | None:
        async with self._session_factory() as session:
            pack = await self._get_latest_pack_by_status(
                session,
                StatutStylePack.BROUILLON,
            )
            if pack is None:
                return None
            return await self._to_pack_snapshot(session, pack)

    async def get_latest_active_pack(self) -> StyleGuidePackSnapshot | None:
        async with self._session_factory() as session:
            pack = await self._get_latest_pack_by_status(
                session,
                StatutStylePack.ACTIF,
            )
            if pack is None:
                return None
            return await self._to_pack_snapshot(session, pack)

    async def list_recent_packs(self, *, limit: int = 5) -> list[StyleGuidePackSnapshot]:
        async with self._session_factory() as session:
            stmt = (
                select(StylePack)
                .join(DocumentIngestionRun, StylePack.ingestion_run_id == DocumentIngestionRun.id)
                .join(
                    DocumentCollection, DocumentIngestionRun.collection_id == DocumentCollection.id
                )
                .where(
                    DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
                )
                .options(
                    selectinload(StylePack.ingestion_run).selectinload(
                        DocumentIngestionRun.collection
                    ),
                    selectinload(StylePack.style_rules).selectinload(StyleRule.taxonomie_produit),
                )
                .order_by(StylePack.updated_at.desc())
                .limit(limit)
            )
            packs = list((await session.scalars(stmt)).all())
            return [await self._to_pack_snapshot(session, pack) for pack in packs]

    async def get_pack_by_id(
        self,
        style_pack_id: uuid.UUID,
    ) -> StyleGuidePackSnapshot | None:
        async with self._session_factory() as session:
            pack = await self._get_style_guide_pack(session, style_pack_id)
            if pack is None:
                return None
            return await self._to_pack_snapshot(session, pack)

    async def list_rules_for_pack(
        self,
        style_pack_id: uuid.UUID,
    ) -> list[StyleGuideRuleSnapshot]:
        async with self._session_factory() as session:
            pack = await self._require_style_guide_pack(session, style_pack_id)
            return [self._to_rule_snapshot(rule) for rule in _ordered_pack_rules(pack.style_rules)]

    async def update_style_rule(
        self,
        *,
        style_pack_id: uuid.UUID,
        rule_id: uuid.UUID,
        texte_regle: str | None = None,
        type_regle: TypeRegle | None = None,
        niveau_contrainte: NiveauContrainte | None = None,
        taxonomie_code: str | None = None,
        decision_editoriale: DecisionEditorialeStyleRule | None = None,
        est_actif: bool | None = None,
        commentaire_review: str | None = None,
        reviewed_by: str,
    ) -> StyleGuideRuleSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                pack = await self._require_editable_style_guide_pack(session, style_pack_id)
                rule = _find_pack_rule(pack, rule_id)
                taxonomy_map = await self._load_taxonomy_map(session)
                mutated_business_fields = False

                normalized_texte_regle = (
                    _normalize_rule_text(texte_regle) if texte_regle is not None else None
                )
                normalized_taxonomie_code = (
                    _normalize_taxonomie_code(taxonomie_code)
                    if taxonomie_code is not None
                    else None
                )
                resolved_type_regle = type_regle or rule.type_regle
                resolved_niveau_contrainte = niveau_contrainte or rule.niveau_contrainte
                resolved_taxonomie_code = (
                    normalized_taxonomie_code
                    if taxonomie_code is not None
                    else _current_taxonomie_code(rule)
                )
                _validate_rule_invariants(
                    type_regle=resolved_type_regle,
                    niveau_contrainte=resolved_niveau_contrainte,
                    taxonomie_code=resolved_taxonomie_code,
                )

                if (
                    normalized_texte_regle is not None
                    and rule.texte_regle != normalized_texte_regle
                ):
                    rule.texte_regle = normalized_texte_regle
                    mutated_business_fields = True

                if type_regle is not None and rule.type_regle != type_regle:
                    rule.type_regle = type_regle
                    mutated_business_fields = True

                if niveau_contrainte is not None and rule.niveau_contrainte != niveau_contrainte:
                    rule.niveau_contrainte = niveau_contrainte
                    mutated_business_fields = True

                if taxonomie_code is not None:
                    taxonomy_id = (
                        taxonomy_map.get(normalized_taxonomie_code)
                        if normalized_taxonomie_code is not None
                        else None
                    )
                    if normalized_taxonomie_code is not None and taxonomy_id is None:
                        raise ValueError(f"Taxonomie produit inconnue: {normalized_taxonomie_code}")
                    resolved_taxonomy_id = taxonomy_id
                    if rule.taxonomie_produit_id != resolved_taxonomy_id:
                        rule.taxonomie_produit_id = resolved_taxonomy_id
                        mutated_business_fields = True

                normalized_decision = decision_editoriale
                if normalized_decision is not None:
                    rule.decision_editoriale = normalized_decision
                    if normalized_decision == DecisionEditorialeStyleRule.APPROUVEE:
                        rule.est_actif = True
                    elif normalized_decision == DecisionEditorialeStyleRule.DESACTIVEE:
                        rule.est_actif = False

                if est_actif is not None and decision_editoriale is None:
                    rule.est_actif = est_actif

                if commentaire_review is not None:
                    rule.commentaire_review = commentaire_review

                if mutated_business_fields:
                    rule.origine = OrigineStyleRule.MODIFIEE

                if decision_editoriale is not None or commentaire_review is not None:
                    rule.reviewed_at = datetime.now(UTC)
                    rule.reviewed_by = reviewed_by

                await session.flush()
                await self._refresh_pack_validation_summary(pack)

            return self._to_rule_snapshot(rule)

    async def list_taxonomies(self) -> list[StyleGuideTaxonomySnapshot]:
        async with self._session_factory() as session:
            stmt = (
                select(TaxonomieProduit)
                .where(TaxonomieProduit.parent_id.is_(None))
                .order_by(TaxonomieProduit.famille_code)
            )
            taxonomies = list((await session.scalars(stmt)).all())
            return [
                StyleGuideTaxonomySnapshot(
                    id=taxonomy.id,
                    famille_code=taxonomy.famille_code,
                    libelle_fr=taxonomy.libelle_fr,
                )
                for taxonomy in taxonomies
            ]

    async def replace_draft_style_pack(
        self,
        *,
        document_source_id: uuid.UUID,
        ingestion_run_id: uuid.UUID,
        chunks: list[StyleGuideChunkCandidate],
        candidate: DraftStylePackExtractionV1,
        metadata: StyleGuideDraftPackGenerationMetadata,
    ) -> StyleGuideDraftPackSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                document_source = await self._require_style_guide_document_source(
                    session, document_source_id
                )
                run = await self._require_style_guide_run(session, ingestion_run_id)
                if run.collection_id != document_source.collection_id:
                    raise ValueError(
                        "Le run d'ingestion ne correspond pas a la source style guide."
                    )
                taxonomy_map = await self._load_taxonomy_map(session)
                chunk_map = {chunk.provider_id: chunk for chunk in chunks}
                missing_provider_ids = [
                    rule.source_evidence_provider_id
                    for rule in candidate.regles
                    if rule.source_evidence_provider_id not in chunk_map
                ]
                if missing_provider_ids:
                    raise ValueError(
                        "Chunks de preuve introuvables pour les ids: "
                        + ", ".join(sorted(set(missing_provider_ids)))
                    )

                existing_draft_stmt = (
                    select(StylePack)
                    .join(
                        DocumentIngestionRun, StylePack.ingestion_run_id == DocumentIngestionRun.id
                    )
                    .where(
                        DocumentIngestionRun.collection_id == document_source.collection_id,
                        StylePack.statut == StatutStylePack.BROUILLON,
                    )
                    .options(selectinload(StylePack.style_rules))
                )
                existing_drafts = list((await session.scalars(existing_draft_stmt)).all())
                for existing_draft in existing_drafts:
                    await session.delete(existing_draft)

                pack = StylePack(
                    ingestion_run_id=run.id,
                    statut=StatutStylePack.BROUILLON,
                    est_actif=False,
                    prompt_registry_provider=metadata.prompt_registry_provider,
                    prompt_name=metadata.prompt_name,
                    prompt_version=metadata.prompt_version,
                    llm_model=metadata.llm_model,
                    llm_temperature=metadata.llm_temperature,
                    llm_max_tokens=metadata.llm_max_tokens,
                    llm_response_format_name=metadata.llm_response_format,
                    rendered_system_prompt_hash=metadata.system_prompt_hash,
                    rendered_user_prompt_hash=metadata.user_prompt_hash,
                    validation_summary_json={
                        "rules_generated": len(candidate.regles),
                        "rules_to_review": len(candidate.regles),
                    },
                )
                pack.ingestion_run = run
                run.extraction_steps_json = _upsert_llm_draft_pack_step(
                    steps=run.extraction_steps_json,
                    prompt_registry_provider=metadata.prompt_registry_provider,
                    prompt_name=metadata.prompt_name,
                    prompt_version=metadata.prompt_version,
                    llm_model=metadata.llm_model,
                    llm_temperature=metadata.llm_temperature,
                    llm_max_tokens=metadata.llm_max_tokens,
                    llm_response_format=metadata.llm_response_format,
                    status="SUCCEEDED",
                    system_prompt_hash=metadata.system_prompt_hash,
                    user_prompt_hash=metadata.user_prompt_hash,
                )

                new_rules = [
                    StyleRule(
                        taxonomie_produit_id=(
                            taxonomy_map[rule.famille_code] if rule.famille_code else None
                        ),
                        type_regle=rule.type_regle,
                        niveau_contrainte=rule.niveau_contrainte,
                        texte_regle_original=rule.texte_regle,
                        texte_regle=rule.texte_regle,
                        decision_editoriale=DecisionEditorialeStyleRule.A_VALIDER,
                        est_actif=False,
                        origine=OrigineStyleRule.LLM,
                        source_evidence_text=rule.citation_source,
                        source_evidence_provider_id=rule.source_evidence_provider_id,
                        source_evidence_page_start=chunk_map[
                            rule.source_evidence_provider_id
                        ].page_start,
                        source_evidence_page_end=chunk_map[
                            rule.source_evidence_provider_id
                        ].page_end,
                        source_evidence_json=_build_rule_evidence_json(
                            chunk_map[rule.source_evidence_provider_id]
                        ),
                    )
                    for rule in candidate.regles
                ]

                # Initialiser explicitement la collection avant le premier flush évite
                # un lazy-load async implicite sur pack.style_rules.
                pack.style_rules = new_rules

                session.add(pack)

                await session.flush()
                await self._refresh_pack_validation_summary(pack)
                run.statut = StatutDocumentIngestionRun.A_VALIDER
                run.current_step = CurrentStep.HUMAN_REVIEW
                document_source.statut = StatutSource.TERMINE
                document_source.dernier_message_erreur = None
                document_source.collection.statut = StatutDocumentCollection.A_VALIDER
                document_source.collection.dernier_message_erreur = None

            return StyleGuideDraftPackSnapshot(
                draft_pack_id=str(pack.id),
            )

    async def finalize_style_pack_approval(
        self,
        *,
        style_pack_id: uuid.UUID,
    ) -> StyleGuidePackSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                pack = await self._require_editable_style_guide_pack(session, style_pack_id)
                if any(
                    rule.decision_editoriale == DecisionEditorialeStyleRule.A_VALIDER
                    for rule in pack.style_rules
                ):
                    raise RuntimeError(
                        "Toutes les règles doivent recevoir une décision avant activation."
                    )

                active_packs_stmt = (
                    select(StylePack)
                    .join(
                        DocumentIngestionRun, StylePack.ingestion_run_id == DocumentIngestionRun.id
                    )
                    .join(
                        DocumentCollection,
                        DocumentIngestionRun.collection_id == DocumentCollection.id,
                    )
                    .where(
                        DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
                        StylePack.est_actif.is_(True),
                        StylePack.id != pack.id,
                    )
                )
                active_packs = list((await session.scalars(active_packs_stmt)).all())
                for active_pack in active_packs:
                    active_pack.est_actif = False
                    active_pack.statut = StatutStylePack.ARCHIVE

                if active_packs:
                    # La contrainte partielle uq_style_pack_est_actif_true n'autorise
                    # qu'un seul pack actif. On force donc le flush des désactivations
                    # avant d'activer le nouveau pack.
                    await session.flush()

                pack.est_actif = True
                pack.statut = StatutStylePack.ACTIF
                pack.approuve_le = datetime.now(UTC)
                for rule in pack.style_rules:
                    rule.est_actif = (
                        rule.decision_editoriale == DecisionEditorialeStyleRule.APPROUVEE
                    )

                run = pack.ingestion_run
                run.statut = StatutDocumentIngestionRun.TERMINE
                run.current_step = CurrentStep.DONE
                run.completed_at = datetime.now(UTC)
                run.error_message = None
                await self._refresh_pack_validation_summary(pack)

                document_source = await self._get_latest_document_source_for_collection(
                    session, run.collection_id
                )
                if document_source is None:
                    raise KeyError(
                        f"Aucune source guide de style pour la collection {run.collection_id}"
                    )
                document_source.statut = StatutSource.TERMINE
                document_source.dernier_message_erreur = None
                document_source.collection.statut = StatutDocumentCollection.TERMINE
                document_source.collection.dernier_message_erreur = None

            return await self._to_pack_snapshot(session, pack)

    async def finalize_style_pack_rejection(
        self,
        *,
        style_pack_id: uuid.UUID,
    ) -> StyleGuidePackSnapshot:
        async with self._session_factory() as session:
            async with session.begin():
                pack = await self._require_editable_style_guide_pack(session, style_pack_id)
                pack.est_actif = False
                pack.statut = StatutStylePack.ARCHIVE

                run = pack.ingestion_run
                run.statut = StatutDocumentIngestionRun.ANNULE
                run.current_step = CurrentStep.HUMAN_REVIEW
                run.completed_at = datetime.now(UTC)
                run.error_message = None
                await self._refresh_pack_validation_summary(pack)

                document_source = await self._get_latest_document_source_for_collection(
                    session, run.collection_id
                )
                if document_source is None:
                    raise KeyError(
                        f"Aucune source guide de style pour la collection {run.collection_id}"
                    )
                document_source.statut = StatutSource.TERMINE
                document_source.dernier_message_erreur = None
                document_source.collection.statut = StatutDocumentCollection.TERMINE
                document_source.collection.dernier_message_erreur = None

            return await self._to_pack_snapshot(session, pack)

    async def _get_style_guide_document_source(
        self,
        session: AsyncSession,
        document_source_id: uuid.UUID,
    ) -> DocumentSource | None:
        stmt = (
            select(DocumentSource)
            .options(selectinload(DocumentSource.collection))
            .join(DocumentCollection, DocumentSource.collection_id == DocumentCollection.id)
            .where(
                DocumentSource.id == document_source_id,
                DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
            )
        )
        return (await session.scalars(stmt)).one_or_none()

    async def _get_current_document_source(
        self,
        session: AsyncSession,
    ) -> DocumentSource | None:
        stmt = (
            select(DocumentSource)
            .options(selectinload(DocumentSource.collection))
            .join(DocumentCollection, DocumentSource.collection_id == DocumentCollection.id)
            .where(
                DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
                DocumentSource.replaced_by_source_id.is_(None),
            )
            .order_by(DocumentSource.created_at.desc())
            .limit(1)
        )
        return (await session.scalars(stmt)).one_or_none()

    async def _require_style_guide_document_source(
        self,
        session: AsyncSession,
        document_source_id: uuid.UUID,
    ) -> DocumentSource:
        document_source = await self._get_style_guide_document_source(session, document_source_id)
        if document_source is None:
            raise KeyError(str(document_source_id))
        return document_source

    async def _require_style_guide_document_source_for_update(
        self,
        session: AsyncSession,
        document_source_id: uuid.UUID,
    ) -> DocumentSource:
        stmt = (
            select(DocumentSource)
            .options(selectinload(DocumentSource.collection))
            .join(DocumentCollection, DocumentSource.collection_id == DocumentCollection.id)
            .where(
                DocumentSource.id == document_source_id,
                DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
            )
            .with_for_update()
        )
        document_source = (await session.scalars(stmt)).one_or_none()
        if document_source is None:
            raise KeyError(str(document_source_id))
        return document_source

    async def _require_style_guide_run(
        self,
        session: AsyncSession,
        run_id: uuid.UUID,
    ) -> DocumentIngestionRun:
        stmt = (
            select(DocumentIngestionRun)
            .join(DocumentCollection, DocumentIngestionRun.collection_id == DocumentCollection.id)
            .where(
                DocumentIngestionRun.id == run_id,
                DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
            )
            .options(selectinload(DocumentIngestionRun.collection))
        )
        run = await session.scalar(stmt)
        if run is None:
            raise KeyError(str(run_id))
        return run

    async def _get_latest_run_for_collection(
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
            .limit(1)
        )
        if for_update:
            stmt = stmt.with_for_update()
        return (await session.scalars(stmt)).one_or_none()

    async def _get_latest_document_source_for_collection(
        self,
        session: AsyncSession,
        collection_id: uuid.UUID,
    ) -> DocumentSource | None:
        stmt = (
            select(DocumentSource)
            .options(selectinload(DocumentSource.collection))
            .where(DocumentSource.collection_id == collection_id)
            .order_by(DocumentSource.created_at.desc())
            .limit(1)
        )
        return (await session.scalars(stmt)).one_or_none()

    async def _load_taxonomy_map(
        self,
        session: AsyncSession,
    ) -> dict[str, uuid.UUID]:
        stmt = select(TaxonomieProduit).where(TaxonomieProduit.parent_id.is_(None))
        taxonomies = list((await session.scalars(stmt)).all())
        return {taxonomy.famille_code: taxonomy.id for taxonomy in taxonomies}

    async def _get_latest_pack_by_status(
        self,
        session: AsyncSession,
        statut: StatutStylePack,
    ) -> StylePack | None:
        stmt = (
            select(StylePack)
            .join(DocumentIngestionRun, StylePack.ingestion_run_id == DocumentIngestionRun.id)
            .join(DocumentCollection, DocumentIngestionRun.collection_id == DocumentCollection.id)
            .where(
                DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
                StylePack.statut == statut,
            )
            .options(
                selectinload(StylePack.ingestion_run).selectinload(DocumentIngestionRun.collection),
                selectinload(StylePack.style_rules).selectinload(StyleRule.taxonomie_produit),
            )
            .order_by(StylePack.updated_at.desc())
            .limit(1)
        )
        return (await session.scalars(stmt)).one_or_none()

    async def _get_style_guide_pack(
        self,
        session: AsyncSession,
        style_pack_id: uuid.UUID,
    ) -> StylePack | None:
        stmt = (
            select(StylePack)
            .join(DocumentIngestionRun, StylePack.ingestion_run_id == DocumentIngestionRun.id)
            .join(DocumentCollection, DocumentIngestionRun.collection_id == DocumentCollection.id)
            .where(
                StylePack.id == style_pack_id,
                DocumentCollection.collection_kind == CollectionKind.STYLE_GUIDE,
            )
            .options(
                selectinload(StylePack.ingestion_run).selectinload(DocumentIngestionRun.collection),
                selectinload(StylePack.style_rules).selectinload(StyleRule.taxonomie_produit),
            )
        )
        return (await session.scalars(stmt)).one_or_none()

    async def _require_style_guide_pack(
        self,
        session: AsyncSession,
        style_pack_id: uuid.UUID,
    ) -> StylePack:
        pack = await self._get_style_guide_pack(session, style_pack_id)
        if pack is None:
            raise KeyError(str(style_pack_id))
        return pack

    async def _require_editable_style_guide_pack(
        self,
        session: AsyncSession,
        style_pack_id: uuid.UUID,
    ) -> StylePack:
        pack = await self._require_style_guide_pack(session, style_pack_id)
        if pack.statut != StatutStylePack.BROUILLON:
            raise RuntimeError("Seul un pack brouillon peut être modifié.")
        if pack.ingestion_run.statut != StatutDocumentIngestionRun.A_VALIDER:
            raise RuntimeError("Le pack n'est plus en attente de validation humaine.")
        return pack

    async def _refresh_pack_validation_summary(
        self,
        pack: StylePack,
    ) -> None:
        summary = {
            "rules_generated": len(pack.style_rules),
            "rules_to_review": sum(
                1
                for rule in pack.style_rules
                if rule.decision_editoriale == DecisionEditorialeStyleRule.A_VALIDER
            ),
            "approved_rules": sum(
                1
                for rule in pack.style_rules
                if rule.decision_editoriale == DecisionEditorialeStyleRule.APPROUVEE
            ),
            "disabled_rules": sum(
                1
                for rule in pack.style_rules
                if rule.decision_editoriale == DecisionEditorialeStyleRule.DESACTIVEE
            ),
        }
        pack.validation_summary_json = summary
        pack.ingestion_run.validation_summary_json = summary

    async def _sync_collection_for_source_status(
        self,
        session: AsyncSession,
        *,
        document_source: DocumentSource,
        error_message: str | None,
    ) -> None:
        latest_run = await self._get_latest_run_for_collection(
            session, document_source.collection_id
        )

        if document_source.statut == StatutSource.EN_ATTENTE:
            document_source.collection.statut = StatutDocumentCollection.EN_ATTENTE
            document_source.collection.dernier_message_erreur = None
            return

        if document_source.statut == StatutSource.EN_COURS:
            document_source.collection.statut = StatutDocumentCollection.EN_COURS
            document_source.collection.dernier_message_erreur = None
            return

        if document_source.statut == StatutSource.ERREUR:
            document_source.collection.statut = StatutDocumentCollection.ERREUR
            document_source.collection.dernier_message_erreur = (
                error_message or document_source.dernier_message_erreur
            )
            if latest_run is not None and latest_run.statut != StatutDocumentIngestionRun.TERMINE:
                latest_run.statut = StatutDocumentIngestionRun.ERREUR
                latest_run.error_message = document_source.collection.dernier_message_erreur
            return

        if latest_run is None or latest_run.statut == StatutDocumentIngestionRun.TERMINE:
            document_source.collection.statut = StatutDocumentCollection.TERMINE
            document_source.collection.dernier_message_erreur = None

    async def _sync_source_and_collection_for_run(
        self,
        session: AsyncSession,
        *,
        run: DocumentIngestionRun,
        document_source: DocumentSource,
        error_message: str | None = None,
        clear_errors: bool = False,
    ) -> None:
        collection = document_source.collection

        if clear_errors:
            document_source.dernier_message_erreur = None
            collection.dernier_message_erreur = None

        if run.statut == StatutDocumentIngestionRun.EN_ATTENTE:
            document_source.statut = StatutSource.EN_ATTENTE
            collection.statut = StatutDocumentCollection.EN_ATTENTE
            collection.dernier_message_erreur = None
            return

        if run.statut == StatutDocumentIngestionRun.EN_COURS:
            document_source.statut = StatutSource.EN_COURS
            collection.statut = StatutDocumentCollection.EN_COURS
            collection.dernier_message_erreur = None
            return

        if run.statut == StatutDocumentIngestionRun.A_VALIDER:
            document_source.statut = StatutSource.TERMINE
            document_source.dernier_message_erreur = None
            collection.statut = StatutDocumentCollection.A_VALIDER
            collection.dernier_message_erreur = None
            return

        if run.statut == StatutDocumentIngestionRun.TERMINE:
            document_source.statut = StatutSource.TERMINE
            document_source.dernier_message_erreur = None
            collection.statut = StatutDocumentCollection.TERMINE
            collection.dernier_message_erreur = None
            return

        if run.statut in (
            StatutDocumentIngestionRun.ERREUR,
            StatutDocumentIngestionRun.ANNULE,
        ):
            message = error_message or run.error_message or document_source.dernier_message_erreur
            document_source.statut = StatutSource.ERREUR
            document_source.dernier_message_erreur = message
            collection.statut = StatutDocumentCollection.ERREUR
            collection.dernier_message_erreur = message

    def _to_document_source_snapshot(
        self,
        document_source: DocumentSource,
    ) -> StyleGuideDocumentSourceSnapshot:
        return StyleGuideDocumentSourceSnapshot(
            id=document_source.id,
            collection_id=document_source.collection_id,
            storage_uri=document_source.storage_uri,
            statut=document_source.statut,
            collection_statut=document_source.collection.statut,
            document_type=document_source.document_type,
            original_file_name=document_source.original_file_name,
            dernier_message_erreur=document_source.dernier_message_erreur,
            replaced_by_source_id=document_source.replaced_by_source_id,
            replaced_by_collection_id=document_source.collection.replaced_by_collection_id,
            storage_generation=document_source.storage_generation,
            storage_metageneration=document_source.storage_metageneration,
            storage_content_type=document_source.storage_content_type,
            storage_size_bytes=document_source.storage_size_bytes,
            created_at=document_source.created_at,
            updated_at=document_source.updated_at,
        )

    def _to_run_snapshot(
        self,
        run: DocumentIngestionRun,
    ) -> StyleGuideIngestionRunSnapshot:
        return StyleGuideIngestionRunSnapshot(
            id=run.id,
            collection_id=run.collection_id,
            pipeline_kind=run.pipeline_kind,
            statut=run.statut,
            current_step=run.current_step,
            temporal_workflow_id=run.temporal_workflow_id,
            temporal_run_id=run.temporal_run_id,
            extraction_steps_json=run.extraction_steps_json,
            validation_summary_json=run.validation_summary_json,
            error_message=run.error_message,
            started_at=run.started_at,
            completed_at=run.completed_at,
            created_at=run.created_at,
            updated_at=run.updated_at,
        )

    async def _to_pack_snapshot(
        self,
        session: AsyncSession,
        pack: StylePack,
    ) -> StyleGuidePackSnapshot:
        document_source = await self._get_latest_document_source_for_collection(
            session,
            pack.ingestion_run.collection_id,
        )
        if document_source is None:
            raise KeyError(
                f"Aucune source guide de style pour la collection {pack.ingestion_run.collection_id}"
            )

        scoped_taxonomies = sorted(
            {
                rule.taxonomie_produit.famille_code
                for rule in pack.style_rules
                if rule.taxonomie_produit is not None
            }
        )
        has_global_rule = any(rule.taxonomie_produit is None for rule in pack.style_rules)
        scopes = (["Global"] if has_global_rule else []) + scoped_taxonomies

        return StyleGuidePackSnapshot(
            id=pack.id,
            ingestion_run_id=pack.ingestion_run_id,
            collection_id=pack.ingestion_run.collection_id,
            document_source_id=document_source.id,
            original_file_name=document_source.original_file_name,
            statut=pack.statut,
            est_actif=pack.est_actif,
            approuve_le=pack.approuve_le,
            temporal_workflow_id=pack.ingestion_run.temporal_workflow_id,
            run_statut=pack.ingestion_run.statut,
            run_current_step=pack.ingestion_run.current_step,
            prompt_registry_provider=pack.prompt_registry_provider,
            prompt_name=pack.prompt_name,
            prompt_version=pack.prompt_version,
            llm_model=pack.llm_model,
            llm_temperature=pack.llm_temperature,
            llm_max_tokens=pack.llm_max_tokens,
            llm_response_format_name=pack.llm_response_format_name,
            rendered_system_prompt_hash=pack.rendered_system_prompt_hash,
            rendered_user_prompt_hash=pack.rendered_user_prompt_hash,
            extraction_steps_json=pack.ingestion_run.extraction_steps_json,
            validation_summary_json=pack.validation_summary_json,
            created_at=pack.created_at,
            updated_at=pack.updated_at,
            rules_count=len(pack.style_rules),
            approved_rules_count=sum(
                1
                for rule in pack.style_rules
                if rule.decision_editoriale == DecisionEditorialeStyleRule.APPROUVEE
            ),
            disabled_rules_count=sum(
                1
                for rule in pack.style_rules
                if rule.decision_editoriale == DecisionEditorialeStyleRule.DESACTIVEE
            ),
            hard_rules_count=sum(
                1 for rule in pack.style_rules if rule.niveau_contrainte == NiveauContrainte.HARD
            ),
            soft_rules_count=sum(
                1 for rule in pack.style_rules if rule.niveau_contrainte == NiveauContrainte.SOFT
            ),
            scopes=scopes,
        )

    def _to_rule_snapshot(
        self,
        rule: StyleRule,
    ) -> StyleGuideRuleSnapshot:
        return StyleGuideRuleSnapshot(
            id=rule.id,
            pack_id=rule.pack_id,
            type_regle=rule.type_regle,
            niveau_contrainte=rule.niveau_contrainte,
            texte_regle=rule.texte_regle,
            taxonomie_code=(
                rule.taxonomie_produit.famille_code if rule.taxonomie_produit is not None else None
            ),
            est_actif=rule.est_actif,
            decision_editoriale=rule.decision_editoriale,
            origine=rule.origine,
            source_evidence_text=rule.source_evidence_text,
            source_evidence_provider_id=rule.source_evidence_provider_id,
            source_evidence_page_start=rule.source_evidence_page_start,
            source_evidence_page_end=rule.source_evidence_page_end,
            source_evidence_json=rule.source_evidence_json,
            commentaire_review=rule.commentaire_review,
            reviewed_at=rule.reviewed_at,
            reviewed_by=rule.reviewed_by,
            created_at=rule.created_at,
            updated_at=rule.updated_at,
        )

    def _build_document_source(
        self,
        *,
        document_source_id: uuid.UUID,
        collection_id: uuid.UUID,
        original_file_name: str,
        storage_uri: str,
        storage_bucket: str,
        storage_object_name: str,
        storage_generation: str,
        storage_metageneration: str,
        storage_content_type: str,
        storage_size_bytes: int,
    ) -> DocumentSource:
        return DocumentSource(
            id=document_source_id,
            collection_id=collection_id,
            original_file_name=original_file_name,
            storage_uri=storage_uri,
            storage_bucket=storage_bucket,
            storage_object_name=storage_object_name,
            storage_generation=storage_generation,
            storage_metageneration=storage_metageneration,
            storage_content_type=storage_content_type,
            storage_size_bytes=storage_size_bytes,
            document_type=DocumentType.STYLE_GUIDE,
            statut=StatutSource.EN_ATTENTE,
            dernier_message_erreur=None,
        )


def _upsert_layout_parse_step(
    *,
    steps: Any | None,
    parser_resource_id: str,
    mode: str,
    latency_ms: int | None,
    operation_id: str | None,
    output_uri: str | None,
) -> list[dict[str, Any]]:
    normalized_steps = [dict(step) for step in steps] if isinstance(steps, list) else []

    existing_step = next(
        (step for step in normalized_steps if step.get("step_kind") == "LAYOUT_PARSE"),
        None,
    )

    step_payload: dict[str, Any] = {
        "step_kind": "LAYOUT_PARSE",
        "provider": "google_document_ai",
        "processor_kind": "layout_parser",
        "mode": mode,
        "processor_resource_name": parser_resource_id,
        "status": "SUCCEEDED" if mode == "online" or existing_step is not None else "RUNNING",
    }

    if latency_ms is not None:
        step_payload["latency_ms"] = latency_ms
    if operation_id is not None:
        step_payload["provider_job_id"] = operation_id
    if output_uri is not None:
        step_payload["output_uri"] = output_uri

    processor_version = PurePosixPath(parser_resource_id).name
    if processor_version:
        step_payload["processor_version"] = processor_version

    if existing_step is None:
        normalized_steps.append(step_payload)
        return normalized_steps

    existing_step.update(step_payload)
    return normalized_steps


def _upsert_llm_draft_pack_step(
    *,
    steps: Any | None,
    prompt_registry_provider: str,
    prompt_name: str,
    prompt_version: str,
    llm_model: str,
    llm_temperature: float,
    llm_max_tokens: int,
    llm_response_format: str,
    status: str,
    system_prompt_hash: str | None,
    user_prompt_hash: str | None,
) -> list[dict[str, Any]]:
    normalized_steps = [dict(step) for step in steps] if isinstance(steps, list) else []

    existing_step = next(
        (step for step in normalized_steps if step.get("step_kind") == "LLM_DRAFT_PACK"),
        None,
    )

    step_payload: dict[str, Any] = {
        "step_kind": "LLM_DRAFT_PACK",
        "provider": "litellm",
        "status": status,
        "prompt_registry_provider": prompt_registry_provider,
        "prompt_name": prompt_name,
        "prompt_version": prompt_version,
        "llm_model": llm_model,
        "llm_temperature": llm_temperature,
        "llm_max_tokens": llm_max_tokens,
        "llm_response_format": llm_response_format,
    }

    if system_prompt_hash is not None:
        step_payload["system_prompt_hash"] = system_prompt_hash
    if user_prompt_hash is not None:
        step_payload["user_prompt_hash"] = user_prompt_hash

    if existing_step is None:
        normalized_steps.append(step_payload)
        return normalized_steps

    existing_step.update(step_payload)
    return normalized_steps


def _build_rule_evidence_json(chunk: StyleGuideChunkCandidate) -> dict[str, Any]:
    evidence_json = dict(chunk.evidence_json)
    evidence_json["index_chunk"] = chunk.index_chunk
    evidence_json["provider_id"] = chunk.provider_id
    return evidence_json


def _find_pack_rule(pack: StylePack, rule_id: uuid.UUID) -> StyleRule:
    rule = next((candidate for candidate in pack.style_rules if candidate.id == rule_id), None)
    if rule is None:
        raise KeyError(str(rule_id))
    return cast(StyleRule, rule)


def _ordered_pack_rules(rules: list[StyleRule]) -> list[StyleRule]:
    return sorted(
        rules,
        key=lambda rule: (
            rule.created_at or datetime.min.replace(tzinfo=UTC),
            str(rule.id),
        ),
    )


def _normalize_rule_text(value: str) -> str:
    normalized = value.strip()
    if len(normalized) < 8:
        raise ValueError("La règle doit être explicite.")
    return normalized


def _normalize_taxonomie_code(value: str | None) -> str | None:
    if value is None:
        return None
    normalized = value.strip()
    return normalized or None


def _current_taxonomie_code(rule: StyleRule) -> str | None:
    if rule.taxonomie_produit is None:
        return None
    return str(rule.taxonomie_produit.famille_code)


def _validate_rule_invariants(
    *,
    type_regle: TypeRegle,
    niveau_contrainte: NiveauContrainte,
    taxonomie_code: str | None,
) -> None:
    if type_regle == TypeRegle.TON and taxonomie_code is None:
        raise ValueError("Une règle de ton doit cibler une famille produit.")
    if type_regle != TypeRegle.TON and taxonomie_code is not None:
        raise ValueError("Seules les règles de ton peuvent cibler une famille produit.")
    if type_regle == TypeRegle.PROMESSE_INTERDITE and niveau_contrainte != NiveauContrainte.HARD:
        raise ValueError("Une promesse interdite doit toujours être en niveau HARD.")
