import asyncio
import logging

from api.infrastructure.database.models.style_guide import TaxonomieProduit
from api.infrastructure.database.session import AsyncSessionLocal

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def seed() -> None:
    """
    Script d'amorçage SOTA 2026 : injecte la taxonomie de base issue du PIM.
    """
    logger.info("Début du seeding de la taxonomie...")

    async with AsyncSessionLocal() as session:
        # Cible : les 2 familles de notre ERD
        tax1 = TaxonomieProduit(code_famille="OUTDOOR_MOB", libelle_fr="Mobilier de Jardin")
        tax2 = TaxonomieProduit(code_famille="OUTDOOR_TOOL", libelle_fr="Outils de Jardin")

        session.add_all([tax1, tax2])

        try:
            await session.commit()
            logger.info("✅ Taxonomie injectée avec succès.")
        except Exception as e:
            await session.rollback()
            logger.info(f"⚠️ Erreur ou taxonomie déjà présente : {e}")


if __name__ == "__main__":
    asyncio.run(seed())
