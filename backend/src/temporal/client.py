import logging

from temporalio.client import Client
from temporalio.contrib.pydantic import pydantic_data_converter

from core.config import get_settings

logger = logging.getLogger(__name__)


async def get_temporal_client() -> Client:
    """
    Instance mutualisée de la connexion Temporal (SaaS ou Local).
    Règle absolue d'Asymétrie Nulle : L'API et le Worker utilisent cette fonction
    pour partager exactement le même DataConverter (Pydantic V2) et le même mode d'Auth.
    """
    settings = get_settings()
    temporal_address = settings.temporal.address
    temporal_namespace = settings.temporal.namespace
    temporal_api_key = settings.temporal.api_key

    # Connexion SOTA 2026 : Le pydantic_data_converter est requis pour l'input/output
    logger.info(
        f"⏳ Connexion à Temporal sur {temporal_address} (Namespace: {temporal_namespace})..."
    )

    client = await Client.connect(
        temporal_address,
        namespace=temporal_namespace,
        api_key=temporal_api_key,
        data_converter=pydantic_data_converter,
    )

    logger.info("✅ Connecté avec succès au cluster Temporal.")
    return client
