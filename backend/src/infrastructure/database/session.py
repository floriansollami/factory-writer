from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import get_settings

settings = get_settings()

# SOTA 2026 : Moteur asynchrone pour SQLAlchemy 2.0 via psycopg3
engine = create_async_engine(
    settings.db.url,
    echo=False,
    future=True,
    # SOTA : Pool pre-ping pour éliminer les erreurs "MySQL server has gone away" ou coupures réseau fantômes.
    pool_pre_ping=True,
)

# SOTA 2026 : expire_on_commit=False est OBLIGATOIRE avec les sessions HTTP et async
# pour éviter des MissingGreenletExceptions quand on accède aux attributs d'un objet après un commit sans relouder.
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def get_db_session() -> AsyncGenerator[AsyncSession, None]:
    """
    Dependency Injection FastAPI pour obtenir une session base de données.
    Garanti par `yield` de fermer proprement la session même en cas de crash HTTP.
    """

    # La session est retournée à FastAPI, puis proprement fermée au yield grâce au async_sessionmaker.
    async with AsyncSessionLocal() as session:
        yield session
