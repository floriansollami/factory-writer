import asyncio
import logging
import uuid

from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from factory_writer.infrastructure.database.models.poc_ingestion import Product
from factory_writer.infrastructure.database.models.taxonomy import TaxonomieProduit
from factory_writer.infrastructure.database.session import get_session_factory

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

_TAXONOMIES_POC: tuple[tuple[str, str, tuple[tuple[str, str], ...]], ...] = (
    (
        "mobilier_jardin",
        "Mobilier de jardin",
        (("table_repas_exterieur", "Table repas extérieur"),),
    ),
    (
        "outils_jardin",
        "Outils de jardin",
        (("secateur", "Sécateur"),),
    ),
)


async def seed() -> None:
    """
    Script d'amorçage SOTA 2026 : injecte la taxonomie de base issue du PIM.
    """
    logger.info("Début du seeding de la taxonomie...")

    session_factory = get_session_factory()
    async with session_factory() as session:
        try:
            for code, label, children in _TAXONOMIES_POC:
                parent = await _upsert_taxonomy(
                    session,
                    code=code,
                    label=label,
                    parent_id=None,
                )

                for child_code, child_label in children:
                    await _upsert_taxonomy(
                        session,
                        code=child_code,
                        label=child_label,
                        parent_id=parent.id,
                    )

            await _reconcile_existing_products(session)

            await session.commit()
            logger.info("Taxonomie injectée avec succès.")
        except SQLAlchemyError as exc:
            await session.rollback()
            logger.warning("Erreur pendant le seeding de la taxonomie", exc_info=exc)


async def _upsert_taxonomy(
    session: AsyncSession,
    *,
    code: str,
    label: str,
    parent_id: uuid.UUID | None,
) -> TaxonomieProduit:
    result = await session.execute(
        select(TaxonomieProduit).where(TaxonomieProduit.famille_code == code)
    )
    taxonomy = result.scalar_one_or_none()

    if taxonomy is None:
        taxonomy = TaxonomieProduit(
            famille_code=code,
            libelle_fr=label,
            parent_id=parent_id,
        )
        session.add(taxonomy)
    else:
        taxonomy.libelle_fr = label
        taxonomy.parent_id = parent_id

    await session.flush()

    return taxonomy


async def _reconcile_existing_products(session: AsyncSession) -> None:
    taxonomies = {
        taxonomy.famille_code: taxonomy
        for taxonomy in (await session.scalars(select(TaxonomieProduit))).all()
    }
    products = list(
        (await session.scalars(select(Product).where(Product.sous_famille_code.is_not(None)))).all()
    )

    updated_count = 0
    for product in products:
        if product.sous_famille_code is None:
            continue

        subfamily = taxonomies.get(product.sous_famille_code)
        if subfamily is None or subfamily.parent_id is None:
            continue

        if product.taxonomie_produit_id == subfamily.id:
            continue

        product.taxonomie_produit_id = subfamily.id
        updated_count += 1

    if updated_count > 0:
        logger.info("Produits réalignés sur leur sous-famille.", extra={"count": updated_count})


if __name__ == "__main__":
    asyncio.run(seed())
