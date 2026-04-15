import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from factory_writer.application.ports.style_guide_ingestion import StyleGuideSourceSnapshot
from factory_writer.domain.exceptions import StyleGuideSourceNotFoundError
from factory_writer.domain.style_guide_types import StatutSource
from factory_writer.infrastructure.database.models.style_guide import (
    SourceGuideStyle,
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

    async def create_source(self, uri: str, statut: StatutSource) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = SourceGuideStyle(uri_fichier=uri, statut=statut)
            session.add(source)
            await session.commit()
            await session.refresh(source)
            return self._to_snapshot(source)

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
            if statut == StatutSource.EN_COURS:
                source.dernier_message_erreur = None

            await session.commit()
            await session.refresh(source)
            return self._to_snapshot(source)

    async def update_gcs_metadata(
        self,
        source_id: uuid.UUID,
        bucket_name: str,
        object_name: str,
        generation: str,
        metageneration: str,
    ) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)
            source.bucket_gcs = bucket_name
            source.objet_gcs = object_name
            source.generation_gcs = generation
            source.metageneration_gcs = metageneration
            await session.commit()
            await session.refresh(source)
            return self._to_snapshot(source)

    async def update_docai_output(
        self,
        source_id: uuid.UUID,
        docai_resource: str,
        operation_id: str,
        output_uri: str,
        error_message: str | None = None,
    ) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)
            source.ressource_processeur_docai = docai_resource
            source.operation_docai_id = operation_id
            source.uri_sortie_docai = output_uri
            if error_message is not None:
                source.dernier_message_erreur = error_message
            else:
                source.dernier_message_erreur = None
            await session.commit()
            await session.refresh(source)
            return self._to_snapshot(source)

    async def update_error_message(self, source_id: uuid.UUID, message: str) -> None:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)
            source.dernier_message_erreur = message
            await session.commit()

    async def get_required_source(self, source_id: uuid.UUID) -> StyleGuideSourceSnapshot:
        async with self._session_factory() as session:
            source = await self._get_required(session, source_id)
            return self._to_snapshot(source)

    async def _get_required(self, session: AsyncSession, source_id: uuid.UUID) -> SourceGuideStyle:
        result = await session.execute(
            select(SourceGuideStyle).where(SourceGuideStyle.id == source_id)
        )
        source = result.scalar_one_or_none()
        if source is None:
            raise StyleGuideSourceNotFoundError(str(source_id))
        return source

    def _to_snapshot(self, source: SourceGuideStyle) -> StyleGuideSourceSnapshot:
        return StyleGuideSourceSnapshot(
            id=source.id,
            uri_fichier=source.uri_fichier,
            statut=source.statut,
            generation_gcs=source.generation_gcs,
            operation_docai_id=source.operation_docai_id,
            uri_sortie_docai=source.uri_sortie_docai,
        )
