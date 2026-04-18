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
        raise ValueError("DB__URL is required to initialize the database engine.")

    return create_async_engine(
        settings.db.url,
        echo=False,
        future=True,
        pool_pre_ping=True,
    )


@lru_cache
def get_session_factory() -> async_sessionmaker[AsyncSession]:
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
