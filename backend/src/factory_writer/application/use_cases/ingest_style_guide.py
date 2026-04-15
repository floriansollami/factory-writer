import structlog
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from factory_writer.core.config import get_settings
from factory_writer.domain.exceptions import (
    NotAPdfError,
    StyleGuideAlreadyExistsError,
    WrongBucketError,
)
from factory_writer.domain.temporal_models import StyleGuideIngestionInput
from factory_writer.infrastructure.database.models.style_guide import (
    SourceGuideStyle,
    StatutSource,
)
from factory_writer.temporal.starter import start_style_guide_ingestion_workflow

settings = get_settings()

logger = structlog.get_logger(__name__)


async def trigger_style_ingestion(
    bucket_name: str, file_name: str, session: AsyncSession
) -> dict[str, str]:
    """
    Cas d'usage : Gère la logique métier "Zero Hallucination" de l'ingestion d'un Style Guide.
    Couche Application : Ignorant des protocoles HTTP, il ne connait que Python et SQLAlchemy.
    """
    if not settings.gcp.style_guide_bucket_name:
        raise RuntimeError("GCP__STYLE_GUIDE_BUCKET_NAME is required to ingest a style guide.")

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

    # 5. Déclenchement de l'Orchestrateur Temporal (SOTA 2026 - Fire and Forget)
    logger.info(
        "🚀 Démarrage asynchrone du StyleGuideIngestionWorkflow",
        source_id=str(source.id),
        target_uri=source.uri_fichier,
        temporal_host=settings.temporal.address,
    )

    try:
        workflow_id = await start_style_guide_ingestion_workflow(
            StyleGuideIngestionInput(
                source_id=str(source.id),
                file_uri=source.uri_fichier,
            )
        )
    except Exception:
        source.statut = StatutSource.ERREUR
        await session.commit()
        logger.exception(
            "StyleGuideIngestionWorkflow.start_failed",
            source_id=str(source.id),
            target_uri=source.uri_fichier,
        )
        raise

    return {
        "status": "success",
        "source_id": str(source.id),
        "uri": source.uri_fichier,
        "workflow_id": workflow_id,
    }
