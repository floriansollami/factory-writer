import asyncio
import logging

from temporalio import activity
from temporalio.worker import Worker

from temporal.client import get_temporal_client
from temporal.workflows.style_guide_ingestion import StyleGuideIngestionWorkflow
from temporal.activities.style_guide_activities import (
    update_source_status_activity,
    update_source_status_erreur_activity,
    trigger_docai_batch_activity,
    poll_docai_completion_activity,
    process_layout_chunks_activity,
    extract_rules_litellm_activity,
    promote_style_pack_activity,
)
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@activity.defn
async def ping_activity() -> str:
    """Activité temporaire pour valider le démarrage du Worker."""
    return "Worker is alive"


async def main() -> None:
    """
    Démarre la boucle infinie d'exécution asynchrone du Worker Temporal.
    En environnement de production (Cloud Run Worker Pools), ce processus
    est maintenu actif perpétuellement.
    """
    # Étape 1 : Connexion mutuelle partagée avec l'API
    client = await get_temporal_client()

    # Étape 2 : Instantiation du Worker
    # On assigne les Workflows et Activités à une TaskQueue spécifique au POC
    worker = Worker(
        client,
        task_queue="style-guide-queue",
        workflows=[
            StyleGuideIngestionWorkflow,
        ],
        activities=[
            ping_activity,
            update_source_status_activity,
            update_source_status_erreur_activity,
            trigger_docai_batch_activity,
            poll_docai_completion_activity,
            process_layout_chunks_activity,
            extract_rules_litellm_activity,
            promote_style_pack_activity,
        ],
    )

    logger.info("🚀 Worker Temporal initialisé et en écoute sur `style-guide-queue`...")
    
    # Étape 3 : Polling continu
    await worker.run()


if __name__ == "__main__":
    # Démarre la boucle principale asynchrone
    asyncio.run(main())
