import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import get_settings
from domain.exceptions import NotAPdfError, StyleGuideAlreadyExistsError, WrongBucketError
from infrastructure.database.models.style_guide import SourceGuideStyle, StatutSource

settings = get_settings()

logger = structlog.get_logger(__name__)


async def trigger_style_ingestion(
    bucket_name: str, file_name: str, session: AsyncSession
) -> dict[str, str]:
    """
    Cas d'usage : Gère la logique métier "Zero Hallucination" de l'ingestion d'un Style Guide.
    Couche Application : Ignorant des protocoles HTTP, il ne connait que Python et SQLAlchemy.
    """
    # 1. Vérification de domaine (Sécurité et pertinence)
    if bucket_name != settings.gcp.style_guide_bucket_name:
        raise WrongBucketError(
            bucket_name=bucket_name, expected_bucket=settings.gcp.style_guide_bucket_name
        )

    if not file_name.lower().endswith(".pdf"):
        raise NotAPdfError(file_name=file_name)

    # 2. Construction formatée URI Standard GCS
    target_uri = f"gs://{bucket_name}/{file_name}"

    # 3. Logique d'Idempotence en BDD (Éviter les ingestions parallèles liées aux retries Cloud)
    stmt = select(SourceGuideStyle).where(SourceGuideStyle.uri_fichier == target_uri)
    result = await session.execute(stmt)
    existing_source = result.scalar_one_or_none()

    if existing_source is not None:
        if existing_source.statut != StatutSource.ERREUR:
            raise StyleGuideAlreadyExistsError(uri=target_uri)
        else:
            existing_source.statut = StatutSource.EN_ATTENTE
            source = existing_source
    else:
        # Création nominale
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
        temporal_host=settings.temporal.address,
    )
    # Dans la Phase 3, nous utiliserons :
    # await temporal_client.execute_workflow(...)

    return {"status": "success", "source_id": str(source.id), "uri": source.uri_fichier}
