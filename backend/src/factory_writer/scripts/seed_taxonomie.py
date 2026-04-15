import asyncio
import logging

from sqlalchemy.exc import SQLAlchemyError

from factory_writer.infrastructure.database.models.style_guide import TaxonomieProduit
from factory_writer.infrastructure.database.session import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed() -> None:
    """
    Script d'amorçage SOTA 2026 : injecte la taxonomie de base issue du PIM.
    """
    logger.info("Début du seeding de la taxonomie...")

    session_factory = get_session_factory()
    async with session_factory() as session:
        # Cible : les 2 familles de notre ERD
        tax1 = TaxonomieProduit(code_famille="OUTDOOR_MOB", libelle_fr="Mobilier de Jardin")
        tax2 = TaxonomieProduit(code_famille="OUTDOOR_TOOL", libelle_fr="Outils de Jardin")

        session.add_all([tax1, tax2])

        try:
            await session.commit()
            logger.info("✅ Taxonomie injectée avec succès.")
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.warning("Erreur pendant le seeding de la taxonomie", exc_info=exc)


if __name__ == "__main__":
    asyncio.run(seed())
