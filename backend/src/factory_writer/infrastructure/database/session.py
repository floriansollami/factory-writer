from collections.abc import AsyncGenerator
from functools import lru_cache

from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)

from factory_writer.core.config import get_settings


@lru_cache
def get_engine() -> AsyncEngine:
    settings = get_settings()
    if not settings.db.url:
        raise RuntimeError("DB__URL is required to initialize the database engine.")

    # SOTA 2026 : Moteur asynchrone pour SQLAlchemy 2.0 via psycopg3
    return create_async_engine(
        settings.db.url,
        echo=False,
        future=True,
        # SOTA : Pool pre-ping pour éliminer les erreurs de connexions zombies.
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
    # SOTA 2026 : expire_on_commit=False est OBLIGATOIRE avec les sessions HTTP et async
    # pour éviter des MissingGreenletExceptions quand on accède aux attributs après commit.
    return async_sessionmaker(
        bind=get_engine(),
        class_=AsyncSession,
        expire_on_commit=False,
        autocommit=False,
        autoflush=False,
    )


async def dispose_engine() -> None:
    if get_engine.cache_info().currsize == 0:
        return
    await get_engine().dispose()


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection FastAPI pour obtenir une session base de données.
    Garanti par `yield` de fermer proprement la session même en cas de crash HTTP.
    """

    # La session est retournée à FastAPI, puis proprement fermée au yield grâce au async_sessionmaker.
    session_factory = get_session_factory()
    async with session_factory() as session:
        yield session
