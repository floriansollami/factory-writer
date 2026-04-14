from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from api.core.config import settings

# SOTA 2026 : Moteur asynchrone pour SQLAlchemy 2.0 via psycopg3
engine = create_async_engine(
    settings.DATABASE_URL,
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

    # C'est là que réside une des plus grandes différences de syntaxe entre JS et Python :
    # Il n'y a pas de mot-clé new en Python.
    # En Python, pour faire un new (pour créer ou cloner un nouvel objet à partir d'un modèle),
    # il suffit simplement d'ajouter des parenthèses () après le nom !
    async with AsyncSessionLocal() as session:
        # Le yield remet le contôle de la situation à FastAPI.
        # Il lui dit : "Tiens, voilà la session SQL, sers-t'en pour ta route /users.
        # Moi (la fonction), je me mets en pause ici et je patiente gentiment,
        # repasse me voir quand t'as fini."
        yield session


# // L'équivalent TypeScript EXACT du "async with ... as session" de Python :
# let session;
# try {
#     session = new AsyncSessionLocal(); // On exécute l'usine

#     // ======== C'EST ICI QU'ON METS CE QUI EST INDENTÉ EN PYTHON (le yield) ========

# } finally {
#     // Le "finally" s'exécute TOUJOURS en JS, même si un crash énorme a lieu dans le try
#     if (session) {
#         await session.close();
#     }
# }
