import asyncio
import logging

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from factory_writer.infrastructure.database.models.style_guide import TaxonomieProduit
from factory_writer.infrastructure.database.session import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_TAXONOMIES_POC = [
    ("mobilier_jardin", "Mobilier de jardin"),
    ("outils_jardin", "Outils de jardin"),
]


async def seed() -> None:
    """
    Script d'amorçage SOTA 2026 : injecte la taxonomie de base issue du PIM.
    """
    logger.info("Début du seeding de la taxonomie...")

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            for famille_code, libelle_fr in _TAXONOMIES_POC:
                result = await session.execute(
                    select(TaxonomieProduit).where(TaxonomieProduit.famille_code == famille_code)
                )
                taxonomy = result.scalar_one_or_none()
                if taxonomy is None:
                    session.add(
                        TaxonomieProduit(
                            famille_code=famille_code,
                            libelle_fr=libelle_fr,
                        )
                    )
                else:
                    taxonomy.libelle_fr = libelle_fr

            await session.commit()
            logger.info("✅ Taxonomie injectée avec succès.")
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.warning("Erreur pendant le seeding de la taxonomie", exc_info=exc)


if __name__ == "__main__":
    asyncio.run(seed())
