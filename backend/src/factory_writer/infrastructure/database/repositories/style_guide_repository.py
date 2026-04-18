import uuid
from datetime import UTC, datetime

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from factory_writer.application.ports.style_guide_ingestion import (
    DraftStylePackExtractionV1,
    StyleGuideChunkPersistResult,
    StyleGuideDraftPackGenerationMetadata,
    StyleGuideDraftPackSnapshot,
    StyleGuideFragmentCandidate,
    StyleGuideFragmentSnapshot,
    StyleGuideSourceSnapshot,
    StyleGuideTaxonomySnapshot,
)
from factory_writer.domain.style_guide_types import StatutPack, StatutSource
from factory_writer.infrastructure.database.models.style_guide import (
    FragmentStyle,
    PackStyle,
    RegleStyle,
    SourceGuideStyle,
    TaxonomieProduit,
)


class StyleGuideRepository:
    def __init__(self, session_factory: async_sessionmaker[AsyncSession]):
        self._session_factory = session_factory

    async def get_by_uri(self, uri: str) -> StyleGuideSourceSnapshot | None:
        async with self._session_factory() as session:
            stmt = select(SourceGuideStyle).where(SourceGuideStyle.uri_fichier == uri)
            result = await session.execute(stmt)
            source = result.scalar_one_or_none()
            if source is None:
                return None
            return self._to_snapshot(source)

    async def create_source(self, uri: str) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = SourceGuideStyle(uri_fichier=uri)
            session.add(source)
            return await self._commit_and_snapshot(session, source)

    async def update_source_status(
        self,
        source_id: uuid.UUID,
        statut: StatutSource,
        error_message: str | None = None,
        only_if_not_terminal: bool = False,
    ) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)

            if only_if_not_terminal and source.statut in (
                StatutSource.EN_COURS,
                StatutSource.TERMINE,
            ):
                return self._to_snapshot(source)

            if statut == StatutSource.ERREUR and source.statut == StatutSource.TERMINE:
                return self._to_snapshot(source)

            source.statut = statut
            if error_message is not None:
                source.dernier_message_erreur = error_message
            if statut in (StatutSource.EN_ATTENTE, StatutSource.EN_COURS):
                source.dernier_message_erreur = None

            return await self._commit_and_snapshot(session, source)

    async def update_storage_metadata(
        self,
        source_id: uuid.UUID,
        uri: str,
        generation: str,
        metageneration: str,
    ) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)
            source.storage_uri = uri
            source.storage_generation = generation
            source.storage_metageneration = metageneration
            return await self._commit_and_snapshot(session, source)

    async def update_parser_output(
        self,
        source_id: uuid.UUID,
        parser_resource_id: str,
        operation_id: str,
        output_uri: str,
    ) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)
            source.parser_resource_id = parser_resource_id
            source.parser_operation_id = operation_id
            source.parser_output_uri = output_uri
            source.dernier_message_erreur = None
            return await self._commit_and_snapshot(session, source)

    async def replace_fragments(
        self,
        source_id: uuid.UUID,
        fragments: list[StyleGuideFragmentCandidate],
    ) -> StyleGuideChunkPersistResult:
        async with self._session_factory() as session:
            await self._get_required(session, source_id)
            await session.execute(delete(FragmentStyle).where(FragmentStyle.source_id == source_id))

            rows = [
                FragmentStyle(
                    source_id=source_id,
                    index_fragment=fragment.index_fragment,
                    contenu=fragment.contenu,
                )
                for fragment in fragments
            ]

            session.add_all(rows)
            await session.commit()

            return StyleGuideChunkPersistResult(
                source_id=source_id,
                fragment_ids=[str(row.id) for row in rows],
            )

    async def get_fragments_by_ids(
        self,
        fragment_ids: list[str],
    ) -> list[StyleGuideFragmentSnapshot]:
        ids = [uuid.UUID(fragment_id) for fragment_id in fragment_ids]
        if not ids:
            return []

        async with self._session_factory() as session:
            stmt = (
                select(FragmentStyle)
                .where(FragmentStyle.id.in_(ids))
                .order_by(FragmentStyle.index_fragment)
            )
            result = await session.execute(stmt)
            fragments = list(result.scalars().all())

            return [
                StyleGuideFragmentSnapshot(
                    id=fragment.id,
                    source_id=fragment.source_id,
                    index_fragment=fragment.index_fragment,
                    contenu=fragment.contenu,
                )
                for fragment in fragments
            ]

    async def list_taxonomies(self) -> list[StyleGuideTaxonomySnapshot]:
        async with self._session_factory() as session:
            result = await session.execute(
                select(TaxonomieProduit).order_by(TaxonomieProduit.famille_code)
            )
            taxonomies = list(result.scalars().all())

            return [
                StyleGuideTaxonomySnapshot(
                    id=taxonomy.id,
                    famille_code=taxonomy.famille_code,
                    libelle_fr=taxonomy.libelle_fr,
                )
                for taxonomy in taxonomies
            ]

    async def replace_draft_pack(
        self,
        source_id: uuid.UUID,
        candidate: DraftStylePackExtractionV1,
        metadata: StyleGuideDraftPackGenerationMetadata,
    ) -> StyleGuideDraftPackSnapshot:
        async with self._session_factory() as session:
            await self._get_required(session, source_id)
            await session.execute(
                delete(PackStyle).where(
                    PackStyle.source_id == source_id,
                    PackStyle.statut == StatutPack.BROUILLON,
                )
            )

            taxonomy_result = await session.execute(select(TaxonomieProduit))
            taxonomy_map = {
                taxonomy.famille_code: taxonomy.id for taxonomy in taxonomy_result.scalars()
            }
            pack = PackStyle(
                source_id=source_id,
                prompt_registry_provider=metadata.prompt_registry_provider,
                prompt_name=metadata.prompt_name,
                prompt_version=metadata.prompt_version,
                llm_model=metadata.llm_model,
                llm_temperature=metadata.llm_temperature,
                llm_max_tokens=metadata.llm_max_tokens,
                llm_response_format=metadata.llm_response_format,
                system_prompt_hash=metadata.system_prompt_hash,
                user_prompt_hash=metadata.user_prompt_hash,
                statut=StatutPack.BROUILLON,
                est_actif=False,
            )
            session.add(pack)
            await session.flush()

            rules = [
                RegleStyle(
                    pack_id=pack.id,
                    fragment_source_id=uuid.UUID(rule.fragment_source_id),
                    taxonomie_produit_id=(
                        taxonomy_map[rule.famille_code] if rule.famille_code is not None else None
                    ),
                    type_regle=rule.type_regle,
                    niveau_contrainte=rule.niveau_contrainte,
                    texte_regle=rule.texte_regle,
                    est_actif=True,
                )
                for rule in candidate.regles
            ]

            session.add_all(rules)

            await session.commit()

            return StyleGuideDraftPackSnapshot(
                draft_pack_id=str(pack.id),
            )

    async def promote_pack(self, draft_pack_id: str) -> str:
        async with self._session_factory() as session:
            pack = await session.get(PackStyle, uuid.UUID(draft_pack_id))
            if pack is None:
                raise KeyError(draft_pack_id)

            source = await self._get_required(session, pack.source_id)

            result = await session.execute(select(PackStyle).where(PackStyle.est_actif.is_(True)))
            for active_pack in result.scalars():
                active_pack.est_actif = False
                active_pack.statut = StatutPack.APPROUVE

            pack.statut = StatutPack.ACTIF
            pack.est_actif = True
            pack.approuve_le = datetime.now(UTC)

            source.statut = StatutSource.TERMINE
            source.dernier_message_erreur = None

            await session.commit()
            return str(pack.id)

    async def _get_required(self, session: AsyncSession, source_id: uuid.UUID) -> SourceGuideStyle:
        source = await session.get(SourceGuideStyle, source_id)
        if source is None:
            raise KeyError(str(source_id))
        return source

    async def _commit_and_snapshot(
        self,
        session: AsyncSession,
        source: SourceGuideStyle,
    ) -> StyleGuideSourceSnapshot:
        await session.commit()
        await session.refresh(source)
        return self._to_snapshot(source)

    def _to_snapshot(self, source: SourceGuideStyle) -> StyleGuideSourceSnapshot:
        return StyleGuideSourceSnapshot(
            id=source.id,
            uri_fichier=source.uri_fichier,
            statut=source.statut,
            storage_generation=source.storage_generation,
            parser_operation_id=source.parser_operation_id,
            parser_output_uri=source.parser_output_uri,
        )
