import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from api.core.config import settings
from api.infrastructure.database.models.style_guide import SourceGuideStyle, StatutSource

logger = structlog.get_logger(__name__)


async def trigger_style_ingestion(
    bucket_name: str, file_name: str, session: AsyncSession
) -> dict[str, str]:
    """
    Cas d'usage : Gère la logique métier "Zero Hallucination" de l'ingestion d'un Style Guide.
    Couche Application : Ignorant des protocoles HTTP, il ne connait que Python et SQLAlchemy.
    """
    # 1. Vérification de domaine (Sécurité et pertinence)
    if bucket_name != settings.GCP_STYLE_GUIDE_BUCKET_NAME:
        logger.warning(
            "Ingestion ignorée : Fichier déposé dans un bucket non surveillé.",
            bucket_indesirable=bucket_name,
            bucket_attendu=settings.GCP_STYLE_GUIDE_BUCKET_NAME,
        )
        return {"status": "ignored", "reason": "wrong_bucket"}

    if not file_name.lower().endswith(".pdf"):
        logger.warning("Ingestion ignorée : Le fichier n'est pas un PDF.", fichier=file_name)
        return {"status": "ignored", "reason": "not_a_pdf"}

    # 2. Construction formatée URI Standard GCS
    target_uri = f"gs://{bucket_name}/{file_name}"

    # 3. Logique d'Idempotence en BDD (Éviter les ingestions parallèles liées aux retries Cloud)
    stmt = select(SourceGuideStyle).where(SourceGuideStyle.uri_fichier == target_uri)
    result = await session.execute(stmt)
    existing_source = result.scalar_one_or_none()

    if existing_source is not None:
        if existing_source.statut != StatutSource.ERREUR:
            logger.info(
                "Ingestion ignorée : Ce document a déjà été ingéré ou est en cours.",
                uri=target_uri,
                statut=existing_source.statut,
            )
            return {"status": "ignored", "reason": "already_exists"}
        else:
            logger.info("Reprise sur erreur : On réingère un ancien échec.", uri=target_uri)
            existing_source.statut = StatutSource.EN_ATTENTE
            source = existing_source
    else:
        # Création nominale
        logger.info("Trace métier : Nouvelle entrée SourceGuideStyle créée.", uri=target_uri)
        source = SourceGuideStyle(uri_fichier=target_uri, statut=StatutSource.EN_ATTENTE)
        session.add(source)

    # 4. Persistence base de données
    await session.commit()
    await session.refresh(source)

    # 5. Déclenchement de l'Orchestrateur Temporal
    # === SIMULATION TEMPORAL STUB (SOTA 2026 MvP) ===
    logger.info(
        "🚀 [SIMULATION TEMPORAL STUB] Exécution du Workflow asynchrone !",
        workflow_name="StyleGuideIngestionWorkflow",
        source_id=str(source.id),
        target_uri=source.uri_fichier,
        temporal_host=settings.TEMPORAL_HOST,
    )
    # Dans la Phase 3, nous utiliserons :
    # await temporal_client.execute_workflow(...)

    return {"status": "success", "source_id": str(source.id), "uri": source.uri_fichier}
